# -*- coding: utf-8 -*-
"""queue/ 에 쌓인 카드 묶음을 인스타그램에 캐러셀로 발행한다.

  queue/<id>/post.json   { "caption": "...", "cards": ["01.jpg", ...] }
  queue/<id>/01.jpg …

발행에 성공하면 posted/<id>/ 로 옮기고 result.json 을 남긴다.
실패하면 failed/<id>/ 로 옮기고 error.json 을 남긴다 — 다음 실행에서 다시 시도하지 않는다.
"""
import json, os, shutil, sys, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, 'config.json'), encoding='utf-8'))

TOKEN = os.environ.get('IG_ACCESS_TOKEN', '').strip()
REPO = os.environ.get('GITHUB_REPOSITORY', '').strip()
SHA = os.environ.get('GITHUB_SHA', 'main').strip()
GRAPH = 'https://graph.instagram.com'
V = CFG.get('api_version', 'v25.0')
IGID = str(CFG['ig_user_id'])


def req(url, data=None, timeout=90):
    body = urllib.parse.urlencode(data).encode() if data else None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=timeout) as r:
            return json.loads(r.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors='replace')
        try:
            err = json.loads(raw).get('error', {})
            msg = f"{err.get('message')} (code {err.get('code')}, subcode {err.get('error_subcode')})"
        except Exception:
            msg = raw[:500]
        raise RuntimeError(f'HTTP {e.code}: {msg}') from None
    except Exception as e:
        raise RuntimeError(f'{type(e).__name__}: {e}') from None


def retry(fn, tries=3, wait=6, label=''):
    last = None
    for i in range(tries):
        try:
            return fn()
        except RuntimeError as e:
            last = e
            s = str(e)
            # 토큰·권한 문제는 재시도해도 같다
            if 'HTTP 400' in s and ('OAuth' in s or 'permission' in s.lower()):
                raise
            print(f'   · {label} {i+1}번째 실패 — {wait*(i+1)}초 뒤 재시도')
            time.sleep(wait * (i + 1))
    raise RuntimeError(f'{label}: 3회 모두 실패 — {last}')


def raw_url(path):
    return f'https://raw.githubusercontent.com/{REPO}/{SHA}/{urllib.parse.quote(path)}'


def check_caption(text):
    bad = []
    n = len(text or '')
    if n > CFG['caption_max']:
        bad.append(f'캡션 {n}자 (최대 {CFG["caption_max"]})')
    tags = [w for w in (text or '').split() if w.startswith('#') and len(w) > 1]
    if len(tags) > CFG['hashtag_max']:
        bad.append(f'해시태그 {len(tags)}개 (최대 {CFG["hashtag_max"]})')
    return bad


def wait_ready(cid, timeout=240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = req(f'{GRAPH}/{V}/{cid}?' + urllib.parse.urlencode(
            {'fields': 'status_code,status', 'access_token': TOKEN}))
        code = r.get('status_code')
        if code == 'FINISHED':
            return
        if code == 'ERROR':
            raise RuntimeError(f'컨테이너 처리 실패: {r.get("status")}')
        time.sleep(5)
    raise RuntimeError(f'{timeout}초 안에 컨테이너가 준비되지 않음')


def publish_one(qid, qdir):
    post = json.load(open(os.path.join(qdir, 'post.json'), encoding='utf-8'))
    caption = post.get('caption', '')
    cards = post.get('cards') or sorted(f for f in os.listdir(qdir) if f.lower().endswith('.jpg'))

    if not (2 <= len(cards) <= CFG['carousel_max']):
        raise RuntimeError(f'카드 {len(cards)}장 — 캐러셀은 2~{CFG["carousel_max"]}장입니다')
    bad = check_caption(caption)
    if bad:
        raise RuntimeError('캡션 문제: ' + ' / '.join(bad))
    for c in cards:
        p = os.path.join(qdir, c)
        if not os.path.exists(p):
            raise RuntimeError(f'{c} 파일이 없습니다')
        if not c.lower().endswith(('.jpg', '.jpeg')):
            raise RuntimeError(f'{c} — 인스타는 JPEG 만 받습니다')

    print(f'   · 컨테이너 {len(cards)}개 생성')
    children = []
    for c in cards:
        url = raw_url(f'queue/{qid}/{c}')
        r = retry(lambda u=url: req(f'{GRAPH}/{V}/{IGID}/media',
                                    {'image_url': u, 'is_carousel_item': 'true',
                                     'access_token': TOKEN}),
                  label=f'{c} 컨테이너')
        children.append(r['id'])
    for cid in children:
        wait_ready(cid)

    print('   · 캐러셀 묶기')
    parent = retry(lambda: req(f'{GRAPH}/{V}/{IGID}/media',
                               {'media_type': 'CAROUSEL', 'children': ','.join(children),
                                'caption': caption, 'access_token': TOKEN}),
                   label='캐러셀')['id']
    wait_ready(parent)

    print('   · 발행')
    media_id = retry(lambda: req(f'{GRAPH}/{V}/{IGID}/media_publish',
                                 {'creation_id': parent, 'access_token': TOKEN}),
                     label='발행')['id']
    link = None
    try:
        link = req(f'{GRAPH}/{V}/{media_id}?' + urllib.parse.urlencode(
            {'fields': 'permalink', 'access_token': TOKEN})).get('permalink')
    except RuntimeError:
        pass
    return {'media_id': media_id, 'permalink': link, 'cards': len(cards),
            'published_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


def move(src, dstdir, name, payload, fname):
    os.makedirs(dstdir, exist_ok=True)
    dst = os.path.join(dstdir, name)
    if os.path.exists(dst):
        dst = dst + '-' + time.strftime('%H%M%S')
    shutil.move(src, dst)
    with open(os.path.join(dst, fname), 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return dst


def main():
    if not TOKEN:
        print('IG_ACCESS_TOKEN 비밀값이 없습니다. 저장소 Settings → Secrets 에 넣어 주세요.')
        return 1
    qroot = os.path.join(ROOT, 'queue')
    ids = sorted(d for d in os.listdir(qroot)
                 if os.path.isdir(os.path.join(qroot, d))
                 and os.path.exists(os.path.join(qroot, d, 'post.json')))
    if not ids:
        print('발행할 것이 없습니다.')
        return 0

    print(f'{len(ids)}건 발행 시작')
    failures = 0
    for qid in ids:
        qdir = os.path.join(qroot, qid)
        print(f'\n[{qid}]')
        try:
            res = publish_one(qid, qdir)
            move(qdir, os.path.join(ROOT, 'posted'), qid, res, 'result.json')
            print(f'   ✓ 발행됨 — {res.get("permalink") or res["media_id"]}')
        except Exception as e:
            failures += 1
            move(qdir, os.path.join(ROOT, 'failed'), qid,
                 {'error': str(e), 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())},
                 'error.json')
            print(f'   ✗ 실패 — {e}')

    print(f'\n끝. 성공 {len(ids)-failures} / 실패 {failures}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

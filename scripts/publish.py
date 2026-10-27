# -*- coding: utf-8 -*-
"""queue/ 에 쌓인 카드 묶음을 인스타그램에 캐러셀로 발행한다.

  queue/<id>/post.json   { "caption": "...", "cards": ["01.jpg", ...],
                           "publish_on": "2026-11-14" }   ← 없으면 언제든 발행
  queue/<id>/01.jpg …

한 번 돌 때 **한 건만** 올린다. publish_on 이 오늘(한국 시각) 이후인 것은 건너뛴다.
그래서 여러 편을 미리 queue 에 넣어 두면 날짜에 맞춰 하루 한 건씩 나간다.

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
IGID = str(CFG.get('ig_user_id') or '')   # resolve_igid() 가 실제 값으로 바꾼다
LIMIT = max(1, int(os.environ.get('PUBLISH_LIMIT') or 1))
LOW_QUEUE = 3                              # 남은 대기분이 이보다 적으면 알린다
WINDOW = (os.environ.get('PUBLISH_WINDOW') or '18-23').strip()   # 한국 시각, 이 사이에만 올린다
MIN_GAP_H = float(os.environ.get('MIN_GAP_HOURS') or 4)          # 직전 발행과 이만큼은 띄운다
# GITHUB_EVENT_NAME 은 러너가 덮어써서 workflow 의 env 로 바꿀 수 없다 — 별도 변수로 받는다
MANUAL = (os.environ.get('PUBLISH_MANUAL') or '').lower() in ('1', 'true', 'yes') \
         or os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'


def kst_hour():
    return int(time.strftime('%H', time.gmtime(time.time() + 9 * 3600)))


def in_window():
    """깃허브 예약 실행은 몇 시간씩 늦는다. 그래서 하루에 여러 번 돌리고,
    실제 발행은 한국 시각 저녁에만 한다."""
    if not WINDOW:
        return True
    try:
        a, b = (int(x) for x in WINDOW.split('-'))
    except Exception:
        return True
    return a <= kst_hour() < b


def last_published_at():
    """마지막으로 올린 시각(UTC epoch). 없으면 None."""
    import calendar
    proot = os.path.join(ROOT, 'posted')
    if not os.path.isdir(proot):
        return None
    best = None
    for d in sorted(os.listdir(proot)):
        f = os.path.join(proot, d, 'result.json')
        if not os.path.exists(f):
            continue
        try:
            ts = json.load(open(f, encoding='utf-8')).get('published_at') or ''
            t = calendar.timegm(time.strptime(ts, '%Y-%m-%dT%H:%M:%SZ'))
        except Exception:
            continue
        if best is None or t > best:
            best = t
    return best


def published_today():
    """오늘 몫을 이미 올렸으면 그 id. 여러 번 도는 동안 같은 건을 두 번 올리지 않기 위한 것이다.

    밀린 건(폴더 이름의 날짜가 어제 이하)을 오늘 올린 경우는 세지 않는다 —
    그래야 밀린 것을 낮에 올리고 그날 몫을 저녁에 또 올릴 수 있다."""
    import calendar
    proot = os.path.join(ROOT, 'posted')
    if not os.path.isdir(proot):
        return None
    today = today_kst()
    for d in sorted(os.listdir(proot)):
        if not d.startswith(today):          # 오늘 몫이 아니면 넘어간다
            continue
        f = os.path.join(proot, d, 'result.json')
        if not os.path.exists(f):
            continue
        try:
            ts = json.load(open(f, encoding='utf-8')).get('published_at') or ''
            t = calendar.timegm(time.strptime(ts, '%Y-%m-%dT%H:%M:%SZ'))
        except Exception:
            continue
        if time.strftime('%Y-%m-%d', time.gmtime(t + 9 * 3600)) == today:
            return d
    return None


def today_kst():
    return time.strftime('%Y-%m-%d', time.gmtime(time.time() + 9 * 3600))


def due_on(qdir):
    """이 묶음의 발행 예정일. 없으면 None(= 언제든)."""
    try:
        post = json.load(open(os.path.join(qdir, 'post.json'), encoding='utf-8'))
    except Exception:
        return None
    d = str(post.get('publish_on') or post.get('publish_after') or '').strip()
    return d[:10] if len(d) >= 10 else None


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


def resolve_igid():
    """토큰이 가리키는 계정 ID를 직접 물어본다.

    대시보드에 보이는 ID 와 이 경로에서 쓰는 ID 가 다를 수 있어서,
    설정값을 믿지 않고 매번 확인한다."""
    global IGID
    me = req(f'{GRAPH}/{V}/me?' + urllib.parse.urlencode(
        {'fields': 'user_id,username,account_type', 'access_token': TOKEN}))
    uid = str(me.get('user_id') or '').strip()
    if uid:
        if uid != IGID:
            print(f'   · 발행 ID 를 {IGID or "(없음)"} → {uid} 로 바꿉니다')
        IGID = uid
    elif not IGID:
        IGID = 'me'
    print(f'   계정: @{me.get("username")} ({me.get("account_type")}) · ID {IGID}')
    return me


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
    every = 5 if timeout <= 300 else 15
    while time.time() - t0 < timeout:
        r = req(f'{GRAPH}/{V}/{cid}?' + urllib.parse.urlencode(
            {'fields': 'status_code,status', 'access_token': TOKEN}))
        code = r.get('status_code')
        if code == 'FINISHED':
            return
        if code == 'ERROR':
            raise RuntimeError(f'컨테이너 처리 실패: {r.get("status")}')
        time.sleep(every)
    raise RuntimeError(f'{timeout}초 안에 컨테이너가 준비되지 않음')


def publish_reel(qid, qdir, post):
    """릴스 한 건. 영상은 raw 주소로 Meta 가 가져간다. 처리에 몇 분 걸리므로 오래 기다린다."""
    caption = post.get('caption', '')
    video = post.get('video') or 'reel.mp4'
    cover = post.get('cover')
    vp = os.path.join(qdir, video)
    if not os.path.exists(vp):
        raise RuntimeError(f'{video} 파일이 없습니다')
    if not video.lower().endswith(('.mp4', '.mov')):
        raise RuntimeError(f'{video} — 릴스는 MP4/MOV 만 받습니다')
    mb = os.path.getsize(vp) / 1e6
    if mb > 300:
        raise RuntimeError(f'{video} 가 {mb:.0f}MB — 300MB 를 넘습니다')
    bad = check_caption(caption)
    if bad:
        raise RuntimeError('캡션 문제: ' + ' / '.join(bad))

    print(f'   · 릴스 컨테이너 생성 ({mb:.1f}MB)')
    params = {'media_type': 'REELS', 'video_url': raw_url(f'queue/{qid}/{video}'),
              'caption': caption, 'share_to_feed': 'true', 'access_token': TOKEN}
    if cover and os.path.exists(os.path.join(qdir, cover)):
        params['cover_url'] = raw_url(f'queue/{qid}/{cover}')
    cid = retry(lambda: req(f'{GRAPH}/{V}/{IGID}/media', params), label='릴스 컨테이너')['id']
    print('   · 영상 처리 대기')
    wait_ready(cid, timeout=900)

    print('   · 발행')
    media_id = retry(lambda: req(f'{GRAPH}/{V}/{IGID}/media_publish',
                                 {'creation_id': cid, 'access_token': TOKEN}),
                     label='발행')['id']
    link = None
    try:
        link = req(f'{GRAPH}/{V}/{media_id}?' + urllib.parse.urlencode(
            {'fields': 'permalink', 'access_token': TOKEN})).get('permalink')
    except RuntimeError:
        pass
    return {'media_id': media_id, 'permalink': link, 'type': 'reel', 'video': video,
            'published_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


def publish_one(qid, qdir):
    post = json.load(open(os.path.join(qdir, 'post.json'), encoding='utf-8'))
    if (post.get('type') or '').lower() == 'reel':
        return publish_reel(qid, qdir, post)
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


def write_status(note=''):
    """바깥(Claude 등)에서 raw 주소로 읽을 수 있는 현황 파일.

    raw.githubusercontent.com 은 폴더 목록을 못 주기 때문에 목록을 파일로 남긴다."""
    qroot = os.path.join(ROOT, 'queue')
    pending = []
    for d in sorted(os.listdir(qroot)) if os.path.isdir(qroot) else []:
        qd = os.path.join(qroot, d)
        if not os.path.exists(os.path.join(qd, 'post.json')):
            continue
        try:
            post = json.load(open(os.path.join(qd, 'post.json'), encoding='utf-8'))
        except Exception:
            post = {}
        pending.append({'id': d, 'title': post.get('title', ''),
                        'publish_on': due_on(qd),
                        'type': (post.get('type') or 'carousel'),
                        'cards': len(post.get('cards') or [])})
    proot = os.path.join(ROOT, 'posted')
    posted = sorted(d for d in os.listdir(proot)
                    if os.path.isdir(os.path.join(proot, d))) if os.path.isdir(proot) else []
    last = None
    if posted:
        try:
            last = json.load(open(os.path.join(proot, posted[-1], 'result.json'),
                                  encoding='utf-8'))
            last['id'] = posted[-1]
        except Exception:
            last = {'id': posted[-1]}
    out = {'checked_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'today_kst': today_kst(),
           'pending_count': len(pending),
           'pending': pending,
           'posted_count': len(posted),
           'last_posted': last,
           'note': note}
    with open(os.path.join(ROOT, 'status.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


def main():
    if not TOKEN:
        print('IG_ACCESS_TOKEN 비밀값이 없습니다. 저장소 Settings → Secrets 에 넣어 주세요.')
        write_status('토큰 비밀값 없음')
        return 1
    qroot = os.path.join(ROOT, 'queue')
    allids = sorted(d for d in os.listdir(qroot)
                    if os.path.isdir(os.path.join(qroot, d))
                    and os.path.exists(os.path.join(qroot, d, 'post.json')))
    if not allids:
        print('대기 중인 것이 없습니다.')
        print('::warning::queue/ 가 비었습니다 — 다음 편을 만들어 넣어 주세요.')
        write_status('대기 없음')
        return 0

    today = today_kst()
    ids, later = [], []
    for d in allids:
        on = due_on(os.path.join(qroot, d))
        (ids if (on is None or on <= today) else later).append((d, on))
    ids.sort(key=lambda t: (t[1] or '', t[0]))

    print(f'오늘(KST) {today} · 대기 {len(allids)}건 — 발행 가능 {len(ids)}, 예정 {len(later)}')
    for d, on in later:
        print(f'   · {d} → {on} 에 나갑니다')
    if not ids:
        print('오늘 나갈 것이 없습니다.')
        write_status('오늘 차례인 것이 없음')
        return 0

    overdue = any((on or today) < today for _, on in ids)
    ids = [d for d, _ in ids][:LIMIT]

    if not MANUAL:
        done = published_today()
        if done:
            print(f'오늘은 이미 [{done}] 를 올렸습니다 — 건너뜁니다.')
            write_status(f'오늘 발행 완료: {done}')
            return 0
        last = last_published_at()
        if last is not None:
            gap = (time.time() - last) / 3600.0
            if gap < MIN_GAP_H:
                print(f'직전 발행에서 {gap:.1f}시간밖에 안 지났습니다 '
                      f'(최소 {MIN_GAP_H:g}시간) — 다음 실행에 올립니다.')
                write_status(f'간격 대기 ({gap:.1f}/{MIN_GAP_H:g}시간)')
                return 0
        if not in_window() and not overdue:
            print(f'지금 한국 시각 {kst_hour()}시 — 발행 시간대({WINDOW}시)가 아닙니다. 다음 실행에 올립니다.')
            write_status(f'시간대 대기 (현재 {kst_hour()}시 · 창 {WINDOW}시)')
            return 0
        if overdue and not in_window():
            print('날짜가 지난 건이 있어 시간대를 무시하고 올립니다.')

    if len(allids) - len(ids) < LOW_QUEUE:
        print(f'::warning::이번 건을 빼면 대기분이 {len(allids)-len(ids)}건뿐입니다 — 다음 편을 채워 주세요.')

    try:
        resolve_igid()
    except RuntimeError as e:
        print(f'계정 확인 실패 — {e}')
        write_status(f'계정 확인 실패: {e}')
        return 1

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
    write_status(f'성공 {len(ids)-failures} / 실패 {failures}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())

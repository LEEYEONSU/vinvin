# -*- coding: utf-8 -*-
"""인스타그램 장기 토큰(60일)을 갱신하고 저장소 비밀값에 다시 넣는다.

갱신 조건: 토큰이 24시간 이상 지났고 아직 살아 있을 것.
만료된 토큰은 갱신할 수 없고, Meta 대시보드에서 새로 받아야 한다.
"""
import base64, json, os, sys, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ.get('IG_ACCESS_TOKEN', '').strip()
PAT = os.environ.get('GH_PAT', '').strip()
REPO = os.environ.get('GITHUB_REPOSITORY', '').strip()
SECRET_NAME = 'IG_ACCESS_TOKEN'


def gh(path, data=None, method=None):
    url = f'https://api.github.com/repos/{REPO}{path}'
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, method=method, headers={
        'Authorization': f'Bearer {PAT}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
        'User-Agent': 'wine-hoeoe'})
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def main():
    if not TOKEN:
        print('IG_ACCESS_TOKEN 이 없습니다.')
        return 1

    # 1) 토큰 갱신
    try:
        res = json.loads(urllib.request.urlopen(
            'https://graph.instagram.com/refresh_access_token?' + urllib.parse.urlencode(
                {'grant_type': 'ig_refresh_token', 'access_token': TOKEN}),
            timeout=60).read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors='replace')
        print('갱신 실패 — Meta 응답:', raw[:400])
        print('토큰이 이미 만료되었을 수 있습니다. Meta 대시보드에서 새로 받아')
        print(f'저장소 Settings → Secrets → {SECRET_NAME} 에 넣어 주세요.')
        return 1

    new_token = res.get('access_token')
    expires_in = int(res.get('expires_in') or 0)
    if not new_token:
        print('응답에 토큰이 없습니다:', json.dumps(res)[:300])
        return 1
    days = expires_in // 86400
    print(f'갱신 성공 — 앞으로 {days}일')

    status = {'refreshed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'expires_in_days': days,
              'expires_at': time.strftime('%Y-%m-%d', time.gmtime(time.time() + expires_in))}
    with open(os.path.join(ROOT, 'token_status.json'), 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False, indent=1)

    # 2) 저장소 비밀값에 다시 넣기
    if not PAT:
        print('GH_PAT 이 없어 비밀값을 갱신하지 못했습니다.')
        print(f'새 토큰을 직접 {SECRET_NAME} 에 넣어 주세요.')
        return 1
    try:
        from nacl import encoding, public
    except ImportError:
        print('pynacl 이 필요합니다 (워크플로에서 pip install pynacl).')
        return 1

    key = gh('/actions/secrets/public-key')
    sealed = public.SealedBox(
        public.PublicKey(key['key'].encode(), encoding.Base64Encoder())
    ).encrypt(new_token.encode())
    gh(f'/actions/secrets/{SECRET_NAME}',
       {'encrypted_value': base64.b64encode(sealed).decode(), 'key_id': key['key_id']},
       method='PUT')
    print(f'{SECRET_NAME} 비밀값을 새 토큰으로 바꿨습니다.')

    if days < 10:
        print(f'::warning::토큰이 {days}일 뒤 만료됩니다. 갱신이 제대로 돌고 있는지 확인하세요.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

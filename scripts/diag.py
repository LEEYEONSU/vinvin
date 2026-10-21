# -*- coding: utf-8 -*-
"""Meta 쪽에서 무엇을 막고 있는지 원문 그대로 받아 적는다.

Claude 환경에서는 graph.instagram.com 이 막혀 있어 응답을 직접 볼 수 없다.
그래서 Actions 안에서 받아 파일로 남기고 커밋한다. 토큰 값은 적지 않는다.
"""
import json, os, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ.get('IG_ACCESS_TOKEN', '').strip()
GRAPH = 'https://graph.instagram.com'
V = json.load(open(os.path.join(ROOT, 'config.json'), encoding='utf-8')).get('api_version', 'v25.0')


def probe(label, url):
    try:
        with urllib.request.urlopen(url, timeout=45) as r:
            return {'label': label, 'ok': True, 'data': json.loads(r.read().decode() or '{}')}
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors='replace')
        out = {'label': label, 'ok': False, 'status': e.code, 'raw': raw[:900]}
        try:
            out['error'] = json.loads(raw).get('error', {})
        except Exception:
            pass
        return out
    except Exception as e:
        return {'label': label, 'ok': False, 'error': f'{type(e).__name__}: {e}'}


def q(path, base=GRAPH, ver=True, **params):
    params['access_token'] = TOKEN
    v = f'/{V}' if ver else ''
    return f'{base}{v}/{path}?' + urllib.parse.urlencode(params)


out = {'checked_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'api_version': V, 'token_present': bool(TOKEN),
       'token_len': len(TOKEN), 'token_tail': TOKEN[-6:] if TOKEN else None,
       'probes': []}
out['probes'].append(probe('me (버전 있음)', q('me', fields='user_id,username,account_type')))
out['probes'].append(probe('me (버전 없음)', q('me', ver=False, fields='user_id,username,account_type')))
out['probes'].append(probe('me/content_publishing_limit', q('me/content_publishing_limit', fields='quota_usage')))
out['probes'].append(probe('refresh_access_token (갱신 가능한지만)',
                           f'{GRAPH}/refresh_access_token?' + urllib.parse.urlencode(
                               {'grant_type': 'ig_refresh_token', 'access_token': TOKEN})))

with open(os.path.join(ROOT, 'diag.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1)[:2000])

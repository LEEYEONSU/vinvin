# -*- coding: utf-8 -*-
"""토큰이 어떤 계정을 가리키는지, 어떤 ID로 발행해야 하는지 알아내고 diag.json 에 적는다.

Claude 쪽에서는 graph.instagram.com 이 막혀 있어서 응답을 직접 볼 수 없다.
그래서 결과를 파일로 남기고 커밋한다.
"""
import json, os, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, 'config.json'), encoding='utf-8'))
TOKEN = os.environ.get('IG_ACCESS_TOKEN', '').strip()
GRAPH = 'https://graph.instagram.com'
V = CFG.get('api_version', 'v25.0')


def probe(label, url):
    try:
        with urllib.request.urlopen(url, timeout=45) as r:
            return {'label': label, 'ok': True, 'data': json.loads(r.read().decode() or '{}')}
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors='replace')
        try:
            err = json.loads(raw).get('error', {})
            return {'label': label, 'ok': False,
                    'status': e.code, 'message': err.get('message'),
                    'code': err.get('code'), 'subcode': err.get('error_subcode')}
        except Exception:
            return {'label': label, 'ok': False, 'status': e.code, 'raw': raw[:300]}
    except Exception as e:
        return {'label': label, 'ok': False, 'error': f'{type(e).__name__}: {e}'}


def q(path, **params):
    params['access_token'] = TOKEN
    return f'{GRAPH}/{V}/{path}?' + urllib.parse.urlencode(params)


out = {'checked_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
       'api_version': V,
       'token_present': bool(TOKEN),
       'token_tail': TOKEN[-6:] if TOKEN else None,
       'config_ig_user_id': str(CFG.get('ig_user_id')),
       'probes': []}

cfgid = str(CFG.get('ig_user_id'))
out['probes'].append(probe('me (버전 있음)', q('me', fields='user_id,username,account_type')))
out['probes'].append(probe('me (버전 없음)',
                           f'{GRAPH}/me?' + urllib.parse.urlencode(
                               {'fields': 'user_id,username,account_type', 'access_token': TOKEN})))
out['probes'].append(probe('me/content_publishing_limit',
                           q('me/content_publishing_limit', fields='config,quota_usage')))
out['probes'].append(probe(f'{cfgid} (설정값)', q(cfgid, fields='username')))
out['probes'].append(probe(f'{cfgid}/content_publishing_limit',
                           q(f'{cfgid}/content_publishing_limit', fields='quota_usage')))

# me 가 돌려준 id 로도 확인
for p in out['probes']:
    if p['label'].startswith('me (') and p.get('ok'):
        uid = str((p.get('data') or {}).get('user_id') or '')
        if uid and uid != cfgid:
            out['resolved_user_id'] = uid
            out['probes'].append(probe(f'{uid} (me 가 알려준 id)', q(uid, fields='username')))
            out['probes'].append(probe(f'{uid}/content_publishing_limit',
                                       q(f'{uid}/content_publishing_limit', fields='quota_usage')))
        elif uid:
            out['resolved_user_id'] = uid
        break

with open(os.path.join(ROOT, 'diag.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print(json.dumps(out, ensure_ascii=False, indent=1))

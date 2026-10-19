#!/bin/bash
# 이 저장소에 push 할 수 있도록 깃허브 토큰을 한 번만 저장한다.
# 토큰은 .git/.gitcreds 에만 들어가고, 저장소에는 절대 올라가지 않는다.
set -e
cd "$(dirname "$0")/.."
printf '깃허브 토큰(github_pat_… )을 붙여 넣고 엔터: '
read -rs TOK; echo
if [ -z "$TOK" ]; then echo "입력이 없습니다."; exit 1; fi
git config credential.helper 'store --file=.git/.gitcreds'   # 상대경로여야 맥·리눅스 양쪽에서 읽힌다
umask 077
printf 'https://x-access-token:%s@github.com\n' "$TOK" > .git/.gitcreds
chmod 600 .git/.gitcreds
unset TOK
echo "저장했습니다. 확인 중…"
if git push --dry-run origin main >/dev/null 2>&1; then
  echo "통과 — 이제 push 가 됩니다."
else
  echo "실패 — 토큰이나 권한(Contents: Read and write)을 확인해 주세요."
  exit 1
fi

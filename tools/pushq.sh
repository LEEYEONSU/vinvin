#!/bin/bash
# queue/ 에 쌓인 것을 깃허브로 올린다. 올라가면 Actions 가 인스타에 발행한다.
#   사용법:  cd ~/git/vinvin && ./tools/pushq.sh
set -e
cd "$(dirname "$0")/.."
find .git -name '*.lock' -delete 2>/dev/null || true
if [ -z "$(ls -A queue 2>/dev/null | grep -v '^\.')" ]; then
  echo "queue/ 가 비어 있습니다 — 올릴 것이 없습니다."; exit 0
fi
git pull --quiet --rebase origin main || true
git add -A queue
if git diff --cached --quiet; then echo "새로 올릴 변화가 없습니다."; exit 0; fi
N=$(ls -1 queue | grep -v '^\.' | tr '\n' ' ')
git commit --quiet -m "발행 대기: $N"
git push --quiet origin main
echo "올렸습니다: $N"
echo "진행 상황 → https://github.com/LEEYEONSU/vinvin/actions"

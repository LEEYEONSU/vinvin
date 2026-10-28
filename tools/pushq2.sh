#!/bin/bash
# queue/ 에 새로 넣은 묶음을 깃허브로 올린다 — 연결 폴더의 삭제 권한 없이도 되는 판.
#
#   맥에 연결된 작업본(이 파일이 있는 곳)은 Claude 쪽에서 파일을 지울 수 없어
#   git 이 .lock 을 못 지우고 멈춘다. 그래서 VM 의 홈($HOME, 삭제 가능)에 저장소를
#   새로 받아 거기서 커밋·push 하고, 올린 묶음은 작업본에서 _pushed/ 로 옮겨 둔다.
#
#   사용법:  cd <작업본> && ./tools/pushq2.sh
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"
CRED="$SRC/.git/.gitcreds"
[ -f "$CRED" ] || { echo "push 토큰이 없습니다 — ./tools/set-token.sh 를 먼저 돌려 주세요."; exit 1; }
NEW=$(ls -1 "$SRC/queue" 2>/dev/null | grep -v '^\.' | grep -v '^_' || true)
if [ -z "$NEW" ]; then echo "queue/ 에 새 묶음이 없습니다."; exit 0; fi

W="$HOME/.vinvin-push"; rm -rf "$W"
git clone -q --depth 1 https://github.com/LEEYEONSU/vinvin.git "$W"
cd "$W"
git config credential.helper "store --file=$CRED"
git config user.name  'wine-hoeoe bot'
git config user.email 'lee.butterylee@gmail.com'

ADDED=""
for d in $NEW; do
  if [ -d "$W/queue/$d" ] || [ -d "$W/posted/$d" ]; then
    echo "  · $d 는 이미 저장소에 있습니다 — 건너뜀"
  else
    cp -R "$SRC/queue/$d" "$W/queue/$d"; ADDED="$ADDED $d"
  fi
done
if [ -z "$ADDED" ]; then echo "새로 올릴 것이 없습니다."; exit 0; fi

git add -A queue
git commit -q -m "발행 대기:$ADDED"
git push -q origin main
echo "올렸습니다:$ADDED"

# 작업본 쪽에서는 지우지 않고 _pushed/ 로 옮겨 둔다 (연결 폴더에서는 rm 이 막혀 있다)
mkdir -p "$SRC/queue/_pushed"
for d in $ADDED; do mv "$SRC/queue/$d" "$SRC/queue/_pushed/$d-$(date +%H%M%S)" 2>/dev/null || true; done
echo "진행 상황 → https://github.com/LEEYEONSU/vinvin/actions"

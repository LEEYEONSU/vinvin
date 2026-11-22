#!/bin/bash
# queue/ 에 새로 넣은 묶음을 깃허브로 올린다 — 연결 폴더의 삭제 권한 없이도 되는 판.
#
#   맥에 연결된 작업본(이 파일이 있는 곳)은 Claude 쪽에서 파일을 지울 수 없어
#   git 이 .lock 을 못 지우고 멈춘다. 그래서 VM 의 홈($HOME, 삭제 가능)에 저장소를
#   새로 받아 거기서 커밋·push 하고, 올린 묶음은 작업본에서 _pushed/ 로 옮겨 둔다.
#
#   2026-11 부터 Claude(Cowork) 쪽에서는 git push 가 정책으로 막힌다(403).
#   그래서 이 스크립트는 맥 자체에서 돈다 — 사람이 터미널에서 직접, 또는
#   tools/install-autopush.sh 로 깔아 둔 launchd 가 20분마다.
#
#   올린 묶음 가운데 발행일이 오늘(한국 시각) 이전인 것이 있으면 publish.now 도 건드려
#   GitHub Actions 가 그 자리에서 돌게 한다(밀린 건을 바로 내보내기 위해).
#
#   사용법:  cd <작업본> && ./tools/pushq2.sh        (PUSHQ_QUIET=1 이면 올릴 것이 없을 때 아무 말도 않는다)
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"
CRED="$SRC/.git/.gitcreds"
[ -f "$CRED" ] || { echo "push 토큰이 없습니다 — ./tools/set-token.sh 를 먼저 돌려 주세요."; exit 1; }
NEW=$(ls -1 "$SRC/queue" 2>/dev/null | grep -v '^\.' | grep -v '^_' || true)
if [ -z "$NEW" ]; then [ -n "$PUSHQ_QUIET" ] || echo "queue/ 에 새 묶음이 없습니다."; exit 0; fi

W="$HOME/.vinvin-push"; rm -rf "$W"
git clone -q --depth 1 https://github.com/LEEYEONSU/vinvin.git "$W"
cd "$W"
git config credential.helper "store --file=$CRED"
git config user.name  'wine-hoeoe bot'
git config user.email 'lee.butterylee@gmail.com'

TODAY=$(TZ=Asia/Seoul date +%F)
ADDED=""; DUE=""
for d in $NEW; do
  if [ -d "$W/queue/$d" ] || [ -d "$W/posted/$d" ]; then
    echo "  · $d 는 이미 저장소에 있습니다 — 건너뜀"
  elif [ ! -f "$SRC/queue/$d/post.json" ]; then
    echo "  · $d 에는 post.json 이 없습니다 — 건너뜀"
  else
    cp -R "$SRC/queue/$d" "$W/queue/$d"; ADDED="$ADDED $d"
    ON=$(grep -o '"publish_on" *: *"[0-9-]*"' "$SRC/queue/$d/post.json" | grep -o '[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}' | head -1)
    if [ -n "$ON" ] && [ "$ON" \< "$TODAY" -o "$ON" = "$TODAY" ]; then DUE="$DUE $d($ON)"; fi
  fi
done
if [ -z "$ADDED" ]; then [ -n "$PUSHQ_QUIET" ] || echo "새로 올릴 것이 없습니다."; exit 0; fi

git add -A queue
if [ -n "$DUE" ]; then
  date -u +%FT%TZ >> publish.now; git add publish.now
fi
git commit -q -m "발행 대기:$ADDED${DUE:+ (지금 발행:$DUE)}"
git push -q origin main
echo "$(date '+%F %T') 올렸습니다:$ADDED"
[ -n "$DUE" ] && echo "  발행일이 지났거나 오늘인 묶음이 있어 publish.now 를 건드렸습니다 — Actions 가 곧 돕니다:$DUE"

# 작업본 쪽에서는 지우지 않고 _pushed/ 로 옮겨 둔다 (연결 폴더에서는 rm 이 막혀 있다)
mkdir -p "$SRC/queue/_pushed"
for d in $ADDED; do mv "$SRC/queue/$d" "$SRC/queue/_pushed/$d-$(date +%H%M%S)" 2>/dev/null || true; done
echo "진행 상황 → https://github.com/LEEYEONSU/vinvin/actions"

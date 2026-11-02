#!/bin/bash
# 작업본의 파일 몇 개(SKILL.md, tools/*.sh 같은 것)를 깃허브로 올린다 — 연결 폴더의 삭제 권한 없이 되는 판.
#
#   pushq2.sh 와 같은 방식: VM 홈에 저장소를 새로 받아 거기에 파일을 복사해 커밋·push 한다.
#   작업본 자체에서는 git 을 돌리지 않는다(연결 폴더에서는 .lock 을 못 지워 멈춘다).
#
#   사용법:  cd <작업본> && ./tools/pushfile.sh "커밋 메시지" SKILL.md tools/pushfile.sh ...
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"
CRED="$SRC/.git/.gitcreds"
[ -f "$CRED" ] || { echo "push 토큰이 없습니다 — ./tools/set-token.sh 를 먼저 돌려 주세요."; exit 1; }
MSG="$1"; shift
[ -n "$MSG" ] && [ $# -ge 1 ] || { echo "사용법: ./tools/pushfile.sh \"커밋 메시지\" <파일> [<파일> ...]"; exit 1; }

W="$HOME/.vinvin-push"; rm -rf "$W"
git clone -q --depth 1 https://github.com/LEEYEONSU/vinvin.git "$W"
cd "$W"
git config credential.helper "store --file=$CRED"
git config user.name  'wine-hoeoe bot'
git config user.email 'lee.butterylee@gmail.com'

for f in "$@"; do
  [ -f "$SRC/$f" ] || { echo "  · $f 가 작업본에 없습니다"; exit 1; }
  mkdir -p "$W/$(dirname "$f")"
  cp "$SRC/$f" "$W/$f"
  git add "$f"
done
if git diff --cached --quiet; then echo "바뀐 것이 없습니다."; exit 0; fi
git commit -q -m "$MSG"
git push -q origin main
echo "올렸습니다: $*"

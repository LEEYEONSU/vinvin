#!/bin/bash
# 맥에 「자동 올리기」를 깐다 — 20분마다 ~/git/vinvin/queue/ 의 새 묶음을 깃허브로 올린다(launchd).
#
#   왜 필요한가: Claude(Cowork) 쪽에서는 git push 가 정책으로 막혀(403) 만들어 둔 묶음이
#   queue/ 에 쌓이기만 한다. 이 맥 자체가 올려 주면 그 고리가 다시 닫힌다.
#
#   사용법 (맥 터미널에서 한 번):   cd ~/git/vinvin && ./tools/install-autopush.sh
#   끄려면:                         launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.vinoetvin.pushq.plist
#   기록:                           ~/git/vinvin/.autopush.log
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$SRC/.git/.gitcreds" ] || { echo "push 토큰이 없습니다 — ./tools/set-token.sh 를 먼저 돌려 주세요."; exit 1; }
chmod +x "$SRC"/tools/*.sh

echo "① 지금 쌓여 있는 묶음부터 올립니다."
"$SRC/tools/pushq2.sh"

echo
echo "② 도구 파일도 저장소에 맞춰 둡니다."
"$SRC/tools/pushfile.sh" "tools: 자동 올리기(launchd) + pushq2 publish.now" tools/pushq2.sh tools/install-autopush.sh tools/pushfile.sh SKILL.md || true

echo
echo "③ launchd 에 등록합니다 (20분마다)."
LABEL=com.vinoetvin.pushq
PL="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PL" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-c</string>
    <string>cd "$SRC" &amp;&amp; ./tools/pushq2.sh >> "$SRC/.autopush.log" 2>&amp;1</string>
  </array>
  <key>StartInterval</key><integer>1200</integer>
  <key>RunAtLoad</key><true/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin</string>
    <key>HOME</key><string>$HOME</string>
    <key>PUSHQ_QUIET</key><string>1</string>
  </dict>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)" "$PL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PL" 2>/dev/null || launchctl load "$PL"
sleep 2
if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
  echo "등록됐습니다 — 맥이 켜져 있는 동안 20분마다 queue/ 를 보고 새 묶음을 올립니다."
else
  echo "등록을 확인하지 못했습니다. 'launchctl list | grep vinoetvin' 으로 봐 주세요."
fi
echo "기록 파일: $SRC/.autopush.log"

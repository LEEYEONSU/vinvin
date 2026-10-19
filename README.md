# vinvin — 와인호외 인스타 발행

[@vinoetvin](https://instagram.com/vinoetvin) 에 카드뉴스를 올리는 자동 발행 저장소입니다.

```
Claude            카드 제작 → JPEG → queue/<번호>/ 에 넣기
   ↓                (맥의 ~/git/vinvin 작업본에 직접 씀)
tools/pushq.sh    queue/ 를 깃허브로 push
   ↓
GitHub Actions    queue/ 변화 감지 → 인스타 API 호출 → 발행
   ↓
posted/           result.json 에 게시물 주소 기록
```

## 왜 이렇게 돌아가는가

- Claude 쪽 클라우드에서는 **Meta API 가 네트워크 정책으로 막혀** 있습니다. 그래서 발행은
  GitHub Actions 가 대신 합니다.
- Claude 쪽 클라우드에서는 **이 저장소로 push 도 막혀** 있습니다. 그래서 push 는 맥에 연결된
  작업본(`~/git/vinvin`)에서 나갑니다. **맥이 켜져 있어야 그날 발행이 됩니다.**
- 이미지는 Meta 가 `raw.githubusercontent.com` 에서 직접 가져갑니다. 그래서 이 저장소는
  **반드시 공개(public)** 여야 합니다.

## 폴더

| 경로 | 쓰임 |
|---|---|
| `queue/<id>/` | 발행 대기. `post.json` + `01.jpg`… |
| `posted/<id>/` | 발행 완료. `result.json` 에 게시물 주소 |
| `failed/<id>/` | 실패. `error.json` 에 사유. **자동 재시도하지 않습니다** |
| `config.json` | API 버전, 길이 제한 (계정 ID 는 발행 때 `/me` 로 직접 확인) |
| `token_status.json` | 토큰 만료일 (갱신 워크플로가 씀) |
| `tools/pushq.sh` | `queue/` 를 한 줄로 올리기 |
| `tools/set-token.sh` | push 용 깃허브 토큰 한 번만 저장 |

## post.json

```json
{
  "title": "제29호 「코르크의 내력」",
  "caption": "첫 줄 …\n\n#와인호외 #비노에뱅통신",
  "cards": ["01.jpg", "02.jpg", "03.jpg"]
}
```

## 비밀값 (Settings → Secrets and variables → Actions)

| 이름 | 값 |
|---|---|
| `IG_ACCESS_TOKEN` | 인스타 장기 액세스 토큰 (60일, 일요일 새벽 자동 갱신) |
| `GH_PAT` | 이 저장소에 `Secrets: Read and write` 권한을 준 세분화 토큰 |

`GH_PAT` 은 갱신한 토큰을 `IG_ACCESS_TOKEN` 에 다시 써 넣는 데만 씁니다.

맥 작업본의 push 토큰은 `.git/.gitcreds` 에 있습니다 — `.git` 안이라 **저장소에는 올라가지
않습니다.** 다시 넣어야 하면 `./tools/set-token.sh`.

## 지켜야 하는 제약

- 이미지는 **JPEG 만**. PNG·WebP 는 Meta 가 거부합니다
- 캐러셀은 **2~10장**. 10장을 넘으면 나눠 올려야 합니다
- 비율은 **4:5 ~ 1.91:1**. 카드 규격 1080×1350 은 정확히 4:5
- 캡션 2200자, 해시태그 30개
- 저장소가 **비공개가 되면 발행이 전부 실패**합니다
- 24시간에 100건까지

## 수동 실행

Actions 탭 → 「인스타 발행」 → Run workflow. `queue/` 에 있는 것을 다시 시도합니다.
실패한 건은 `failed/` 에서 `queue/` 로 폴더를 되돌리면 다시 시도됩니다.

## 맥에서 git 이 안 될 때

연결된 폴더에서는 삭제가 기본적으로 막혀 있어서, git 이 자기 `.lock` 파일을 못 지우고
다음 명령이 `File exists` 로 실패합니다. `find .git -name '*.lock' -delete` 로 치우면 됩니다
(`tools/pushq.sh` 는 알아서 합니다).

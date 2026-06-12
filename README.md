# jhawk-board

가족·소규모 공유용 경량 게시판 API. FastAPI + SQLite, j-hawk VPS(Docker Compose + Caddy)에서 운영.

여러 프로젝트가 `board` 키로 게시판을 나눠 쓰는 범용 백엔드. 첫 사용처는 전라도 가족여행 지도(`tour-jeolla-jhawk.netlify.app`)의 **추가·삭제 의견** 게시판(`board=jeolla`).

## 배포 정보

| 항목 | 값 |
|------|---|
| 도메인 | `board.jhawk.kr` |
| 컨테이너 | `board` (내부 8000) |
| repo 폴더(VPS) | `/opt/j-hawk/jhawk-board` |
| 헬스 | `/healthz` |
| 데이터 | `board_data` 볼륨 → `/data/board.db` (SQLite) |
| env | `.env.board` (`BOARD_KEY`, `BOARD_NAMES`, `BOARD_ORIGINS`) |

## API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET  | `/healthz` | 헬스체크 |
| GET  | `/api/{board}/posts` | 게시물 목록(최신순, 최대 200) |
| POST | `/api/{board}/posts` | 게시물 등록 (헤더 `X-Board-Key` = `BOARD_KEY`) |
| DELETE | `/api/{board}/posts/{id}` | 게시물 삭제 (헤더 `X-Board-Key` = **`BOARD_ADMIN_KEY`**, 미설정 시 `BOARD_KEY` 폴백) |

POST 본문:
```json
{ "name": "이름(선택, 20자)", "kind": "add|remove|etc", "text": "내용(1~500자)" }
```

- `BOARD_KEY`가 설정돼 있으면 POST에 `X-Board-Key` 헤더 일치 필요(GET은 공개).
- `BOARD_KEY`는 클라이언트(정적 HTML)에 박혀 공개되므로 *비밀*이 아니라 봇 스팸 차단용.
- `BOARD_ADMIN_KEY`(삭제 전용)는 **페이지 소스에 노출하지 않는다** — 공개 페이지에서도 관리자만 삭제 가능. 프론트는 삭제 시 키를 prompt로 입력받는다. 미설정 시 `BOARD_KEY` 폴백(구버전 호환).
- IP별 분당 20건 쓰기 제한.

## 로컬 실행

```bash
pip install -r requirements.txt
BOARD_DB=./board.db BOARD_KEY=dev uvicorn main:app --reload
# http://127.0.0.1:8000/api/jeolla/posts
```

## 배포

main 브랜치 push 시 GH Actions(`.github/workflows/deploy.yml`)가 VPS에서 `git pull → docker compose build/up → 헬스체크`. 수동 배포는 워크스페이스 `vps-deploy` 스킬 참조.

Secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.

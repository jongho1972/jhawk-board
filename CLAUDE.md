# CLAUDE.md — jhawk-board

가족·소규모 공유용 범용 게시판 API (FastAPI + SQLite, 단일 `main.py`). `board` 키로 게시판을 나눠 쓴다.

## 현재 상태

- 첫 사용처였던 tour_jeolla 의견 게시판(`board=jeolla`)은 2026-05 일반 공개 전환 때 프론트에서 제거됨 → **현재 사용처 없음**.
- 백엔드·데이터(`board_data` 볼륨)는 유지 중. 새 게시판으로 재활용할 때는 `.env.board`의 `BOARD_NAMES`·`BOARD_ORIGINS`에 추가한다.

## 핵심 정보

- 도메인 `board.jhawk.kr` · 컨테이너 `board`(내부 8000) · 헬스 `/healthz`
- env: `BOARD_DB`, `BOARD_KEY`(쓰기용, 프론트에 노출되는 스팸 차단 키), `BOARD_ADMIN_KEY`(삭제용, 프론트 노출 금지), `BOARD_NAMES`, `BOARD_ORIGINS`
- API·로컬 실행 방법은 `README.md` 참조

## 배포

- git `jongho1972/jhawk-board`, main push 시 GH Actions가 VPS에 자동 배포
- 수동 배포·롤백·헬스체크는 워크스페이스 `vps-deploy` 스킬, 공통 인프라는 `deploy/README.md`

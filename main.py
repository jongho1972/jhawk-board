"""jhawk-board — 가족·소규모 공유용 경량 게시판 API (FastAPI + SQLite).

여러 프로젝트가 board 키로 게시판을 나눠 쓰는 범용 백엔드.
첫 사용처: 전라도 가족여행 지도(tour_jeolla) 의 '추가·삭제 의견' 게시판.

환경변수
  BOARD_DB       SQLite 경로 (기본 /data/board.db, 볼륨 마운트)
  BOARD_KEY      쓰기(POST/DELETE) 보호 키. 비우면 검증 생략
  BOARD_NAMES    허용 게시판 이름(쉼표구분, 기본 "jeolla")
  BOARD_ORIGINS  CORS 허용 오리진(쉼표구분)
"""
import os
import re
import time
import sqlite3
from contextlib import closing

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB_PATH = os.environ.get("BOARD_DB", "/data/board.db")
BOARD_KEY = os.environ.get("BOARD_KEY", "")
ALLOWED_BOARDS = {b.strip() for b in os.environ.get("BOARD_NAMES", "jeolla").split(",") if b.strip()}
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "BOARD_ORIGINS",
        "https://tour-jeolla-jhawk.netlify.app,http://localhost,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if o.strip()
]

KIND_VALUES = {"add", "remove", "etc"}
BOARD_RE = re.compile(r"^[a-z0-9_-]{1,32}$")

app = FastAPI(title="jhawk-board", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


def db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=3000")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with closing(db()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                board      TEXT NOT NULL,
                name       TEXT NOT NULL DEFAULT '',
                kind       TEXT NOT NULL DEFAULT 'etc',
                text       TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_board_created ON posts(board, created_at)")
        conn.execute("PRAGMA journal_mode=WAL")  # 동시 읽기/쓰기 잠금 완화
        conn.commit()


init_db()


class PostIn(BaseModel):
    name: str = Field(default="", max_length=20)
    kind: str = Field(default="etc")
    text: str = Field(min_length=1, max_length=500)


def require_board(board: str):
    if board not in ALLOWED_BOARDS or not BOARD_RE.match(board):
        raise HTTPException(status_code=404, detail="unknown board")


def require_key(key: str):
    if BOARD_KEY and key != BOARD_KEY:
        raise HTTPException(status_code=401, detail="invalid key")


# 아주 단순한 IP별 분당 쓰기 제한 (가족용 수준의 스팸 방지).
# 단일 워커 전제(Dockerfile). --workers N 추가 시 워커별 카운트라 한도가 느슨해짐.
_hits: dict[str, list[float]] = {}


def throttle(ip: str, limit: int = 20):
    now = time.time()
    # 오래된 IP 키 누적 방지: 키가 많이 쌓이면 만료된 항목 정리
    if len(_hits) > 256:
        for k in [k for k, v in _hits.items() if all(now - t >= 60 for t in v)]:
            del _hits[k]
    recent = [t for t in _hits.get(ip, []) if now - t < 60]
    if len(recent) >= limit:
        raise HTTPException(status_code=429, detail="too many requests")
    recent.append(now)
    _hits[ip] = recent


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/{board}/posts")
def list_posts(board: str):
    require_board(board)
    with closing(db()) as conn:
        rows = conn.execute(
            "SELECT id, name, kind, text, created_at FROM posts "
            "WHERE board=? ORDER BY created_at DESC, id DESC LIMIT 200",
            (board,),
        ).fetchall()
    return {"posts": [dict(r) for r in rows]}


@app.post("/api/{board}/posts")
def create_post(board: str, post: PostIn, request: Request, x_board_key: str = Header(default="")):
    require_board(board)
    require_key(x_board_key)
    throttle(request.client.host if request.client else "?")
    text = post.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty text")
    kind = post.kind if post.kind in KIND_VALUES else "etc"
    name = (post.name or "").strip()[:20]
    with closing(db()) as conn:
        cur = conn.execute(
            "INSERT INTO posts(board, name, kind, text, created_at) VALUES (?,?,?,?,?)",
            (board, name, kind, text, int(time.time())),
        )
        conn.commit()
        new_id = cur.lastrowid
    return {"id": new_id}


@app.delete("/api/{board}/posts/{post_id}")
def delete_post(board: str, post_id: int, x_board_key: str = Header(default="")):
    require_board(board)
    require_key(x_board_key)
    with closing(db()) as conn:
        cur = conn.execute("DELETE FROM posts WHERE board=? AND id=?", (board, post_id))
        conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="not found")
    return {"deleted": post_id}

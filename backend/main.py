import warnings
warnings.filterwarnings("ignore")

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db.songs import init_db
from routers import auth, users, songs, analysis
from config import MAX_UPLOAD_BYTES


class RequestBodyTooLargeError(Exception):
    """リクエストボディサイズ超過を示す例外。"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """サーバー起動時に SQLite・DeepFilterNet・Silero VAD を初期化する。"""
    init_db()
    from audio.noise import init_deepfilter, init_silero_vad
    init_deepfilter()
    init_silero_vad()
    yield


app = FastAPI(title="Voice Range Analysis API", lifespan=lifespan)

# ── CORS ──────────────────────────────────────────────────────
# ALLOWED_ORIGINS 環境変数でオリジンをカンマ区切りで指定する。
# 未設定の場合はローカル開発用のデフォルト値を使用。
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
)
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── アップロードサイズ制限ミドルウェア ────────────────────────
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    """Content-Length と実測サイズの両方で上限（50MB）を超えるリクエストを拒否する。"""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=413,
            content={"error": f"ファイルサイズが上限（{MAX_UPLOAD_BYTES // (1024 * 1024)}MB）を超えています"},
        )

    received_size = 0
    original_receive = request.receive

    async def limited_receive() -> dict:
        nonlocal received_size
        message = await original_receive()
        if message.get("type") == "http.request":
            body = message.get("body", b"")
            received_size += len(body)
            if received_size > MAX_UPLOAD_BYTES:
                raise RequestBodyTooLargeError()
        return message

    wrapped_request = Request(request.scope, limited_receive)
    try:
        return await call_next(wrapped_request)
    except RequestBodyTooLargeError:
        return JSONResponse(
            status_code=413,
            content={"error": f"ファイルサイズが上限（{MAX_UPLOAD_BYTES // (1024 * 1024)}MB）を超えています"},
        )

# ── ヘルスチェック ─────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health_check() -> dict:
    """サーバーの死活監視エンドポイント。ロードバランサー・監視ツール向け。"""
    return {"status": "ok"}


# ── ルーター登録 ──────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(songs.router)
app.include_router(analysis.router)

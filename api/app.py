"""FastAPI 应用: CORS、token 认证。"""
import os
import secrets
import logging

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("bedcode")

API_TOKEN = os.environ.get("BEDCODE_API_TOKEN", "")
if not API_TOKEN:
    API_TOKEN = secrets.token_hex(16)

app = FastAPI(title="BedCode API", docs_url="/api/docs", redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class NoCacheHTML(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        ct = response.headers.get("content-type", "")
        if "text/html" in ct:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

app.add_middleware(NoCacheHTML)


async def verify_token(request: Request):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token or token != API_TOKEN:
        raise HTTPException(401, "Invalid token")


def setup_routes():
    from api.routes import router
    from api.ws import router as ws_router
    app.include_router(router, prefix="/api", dependencies=[Depends(verify_token)])
    app.include_router(ws_router)
    # 静态文件（Web UI）— 放最后，作为 fallback
    web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
    if os.path.isdir(web_dir):
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")

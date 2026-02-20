"""FastAPI application factory."""
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .data.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "dashboard" / "static"
DASHBOARD_DIR = Path(__file__).parent / "dashboard"


def create_app() -> FastAPI:
    init_db()

    app = FastAPI(
        title="코인 자동매매 봇",
        description="업비트 + 바이비트 자동매매 | 김프 차익거래 | 실시간 분석",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files if directory exists
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Include API router
    app.include_router(router)

    @app.get("/")
    async def index():
        html_path = DASHBOARD_DIR / "index.html"
        if html_path.exists():
            return FileResponse(str(html_path))
        return {"status": "running", "docs": "/docs"}

    @app.on_event("startup")
    async def startup():
        logger.info("=== 코인 자동매매 봇 시작 ===")
        logger.info("대시보드: http://localhost:8000")
        logger.info("API 문서: http://localhost:8000/docs")

    return app


app = create_app()

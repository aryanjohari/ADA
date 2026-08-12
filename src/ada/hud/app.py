"""FastAPI app factory for the M03 control-plane HUD."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ada.hud.chat_service import ChatService
from ada.hud.routes_api import router as api_router
from ada.hud.routes_pages import router as pages_router

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="ADA HUD", docs_url=None, redoc_url=None)
    app.state.chat = ChatService()
    app.include_router(pages_router)
    app.include_router(api_router)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    return app

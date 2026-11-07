"""Punto de entrada de la API. ``create_app()`` es el unico que lee la configuracion."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import install_access_log_filter

# D-3: solo lo que usa el frontend; la sesion viaja en Authorization, no en cookies.
CORS_ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_ALLOWED_HEADERS = ["Authorization", "Content-Type"]


def create_app() -> FastAPI:
    settings = get_settings()
    install_access_log_filter()  # DD-77: la busqueda ?q= no llega al registro
    app = FastAPI(title="Sistema Odontologico", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=CORS_ALLOWED_METHODS,
        allow_headers=CORS_ALLOWED_HEADERS,
    )
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()

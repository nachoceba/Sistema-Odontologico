"""Router raiz versionado: todo cuelga de ``/api/v1``."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.health import router as health_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)

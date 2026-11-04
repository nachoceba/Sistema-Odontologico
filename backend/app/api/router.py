"""Router raiz versionado: todo cuelga de ``/api/v1``."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.appointments import appointments_router, professionals_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.users import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(appointments_router)
api_router.include_router(professionals_router)

"""Chequeo de salud publico: no consulta base ni Redis y no expone datos (api-health)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Responde ``{"status": "ok"}`` mientras el proceso este en marcha."""
    return {"status": "ok"}

"""Aplicacion Celery minima (D-4): broker Redis, zona del consultorio, sin tareas.

Todo lo de Celery vive en esta carpeta; si la herramienta cambia, no se toca el
dominio ni la API. Las tareas de negocio (emails, recordatorio) las agrega C-11.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery("odonto", broker=_settings.REDIS_URL)
celery_app.conf.update(
    timezone=_settings.CLINIC_TIMEZONE,
    enable_utc=True,
)

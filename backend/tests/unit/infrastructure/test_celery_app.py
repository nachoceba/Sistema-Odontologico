"""Tests del esqueleto de Celery (spec local-environment): sin tareas de negocio."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from typing import Any

import pytest

from app.core.config import get_settings

ENV = {
    "DATABASE_URL": "postgresql+psycopg://odonto:odonto_dev@db:5432/odonto",
    "REDIS_URL": "redis://redis:6379/0",
    "JWT_SECRET_KEY": "k" * 48,
    "SMTP_HOST": "mailpit",
    "SMTP_PORT": "1025",
    "EMAIL_FROM": "turnos@consultorio.test",
    "CLINIC_TIMEZONE": "America/Argentina/Buenos_Aires",
    "CORS_ORIGINS": "http://localhost:5173",
}


@pytest.fixture
def celery_conf(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    import app.infrastructure.tasks.celery_app as module

    reloaded = importlib.reload(module)
    yield reloaded.celery_app
    get_settings.cache_clear()


def test_broker_is_redis_url(celery_conf: Any) -> None:
    assert celery_conf.conf.broker_url == "redis://redis:6379/0"


def test_timezone_follows_clinic_and_utc_internally(celery_conf: Any) -> None:
    assert celery_conf.conf.timezone == "America/Argentina/Buenos_Aires"
    assert celery_conf.conf.enable_utc is True


def test_no_business_tasks_registered(celery_conf: Any) -> None:
    own = [name for name in celery_conf.tasks if not name.startswith("celery.")]
    assert own == []
    assert not celery_conf.conf.beat_schedule

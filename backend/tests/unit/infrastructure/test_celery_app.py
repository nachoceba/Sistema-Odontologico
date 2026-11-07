"""Tests del esqueleto de Celery (spec local-environment): sin tareas de negocio."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from typing import Any

import pytest
from celery.schedules import crontab

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


def test_the_only_own_tasks_are_send_email_requeue_pending_and_send_reminders(
    celery_conf: Any,
) -> None:
    own = sorted(name for name in celery_conf.tasks if not name.startswith("celery."))
    assert own == ["enviar_email", "enviar_recordatorios", "reencolar_pendientes"]


def test_beat_has_exactly_two_own_entries(celery_conf: Any) -> None:
    assert sorted(celery_conf.conf.beat_schedule) == [
        "enviar-recordatorios",
        "reencolar-pendientes",
    ]


def test_requeue_runs_every_ten_minutes(celery_conf: Any) -> None:
    entry = celery_conf.conf.beat_schedule["reencolar-pendientes"]
    assert entry["task"] == "reencolar_pendientes"
    assert entry["schedule"] == 600.0


def test_reminders_run_at_minute_zero_of_every_hour_and_never_force(celery_conf: Any) -> None:
    entry = celery_conf.conf.beat_schedule["enviar-recordatorios"]
    assert entry["task"] == "enviar_recordatorios"
    assert entry["schedule"] == crontab(minute=0)
    assert not entry.get("args")
    assert not entry.get("kwargs")


def test_publishing_has_a_short_connection_timeout(celery_conf: Any) -> None:
    options = celery_conf.conf.broker_transport_options
    assert 0 < options["socket_connect_timeout"] <= 2


def test_tasks_use_json_so_arguments_are_plain_ids(celery_conf: Any) -> None:
    assert celery_conf.conf.task_serializer == "json"

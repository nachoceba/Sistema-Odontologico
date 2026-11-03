"""Fixtures de los tests de API: entorno valido y fabrica de clientes."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import get_settings

API_ENV: dict[str, str] = {
    "DATABASE_URL": "postgresql+psycopg://odonto:odonto_dev@db-inexistente.invalid:5432/odonto",
    "REDIS_URL": "redis://redis-inexistente.invalid:6379/0",
    "JWT_SECRET_KEY": "k" * 48,
    "SMTP_HOST": "mailpit",
    "SMTP_PORT": "1025",
    "EMAIL_FROM": "turnos@consultorio.test",
    "CLINIC_TIMEZONE": "America/Argentina/Buenos_Aires",
    "CORS_ORIGINS": "http://localhost:5173",
}


@pytest.fixture(autouse=True)
def api_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name, value in API_ENV.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def make_client() -> Callable[[], tuple[FastAPI, TestClient]]:
    from app.main import create_app

    def build() -> tuple[FastAPI, TestClient]:
        app = create_app()
        return app, TestClient(app, raise_server_exceptions=False)

    return build


@pytest.fixture
def client(make_client: Callable[[], tuple[FastAPI, TestClient]]) -> TestClient:
    return make_client()[1]

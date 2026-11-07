"""Contrato de ``docker-compose.yml`` (specs local-environment y runtime-configuration, D-1).

Lee el YAML del repositorio (``/docker-compose.yml`` montado dentro del contenedor, o
``COMPOSE_FILE_PATH``). Si no se encuentra el test FALLA: esconderlo seria peor que un fallo claro.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

SECRET_NAMES = (
    "JWT_SECRET_KEY",
    "SMTP_PASSWORD",
    "DATABASE_URL",
    "POSTGRES_PASSWORD",
    "SEED_DEMO_PASSWORD",
)


def compose_path() -> Path:
    configured = os.environ.get("COMPOSE_FILE_PATH")
    if configured:
        return Path(configured)
    in_repo = Path(__file__).resolve().parents[3] / "docker-compose.yml"
    return in_repo if in_repo.exists() else Path("/docker-compose.yml")


@pytest.fixture(scope="module")
def services() -> dict[str, dict[str, Any]]:
    path = compose_path()
    assert path.is_file(), f"No se encontro docker-compose.yml en {path}"
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    found: dict[str, dict[str, Any]] = loaded["services"]
    return found


def test_the_seven_services_are_declared_plus_the_one_shot_migrate(
    services: dict[str, dict[str, Any]],
) -> None:
    assert set(services) == {
        "db",
        "redis",
        "migrate",
        "api",
        "worker",
        "beat",
        "frontend",
        "mailpit",
    }


def test_migrate_runs_once_with_migrations_then_seed(services: dict[str, dict[str, Any]]) -> None:
    migrate = services["migrate"]

    assert migrate["restart"] == "no"
    assert migrate["env_file"] == ".env"
    command = " ".join(migrate["command"])
    assert command.index("alembic upgrade head") < command.index("python -m scripts.seed")
    assert migrate["depends_on"]["db"]["condition"] == "service_healthy"
    assert "ports" not in migrate


@pytest.mark.parametrize("name", ["api", "worker"])
def test_api_and_worker_wait_for_migrate_to_finish_successfully(
    services: dict[str, dict[str, Any]], name: str
) -> None:
    depends = services[name]["depends_on"]

    assert depends["migrate"]["condition"] == "service_completed_successfully"
    assert depends["db"]["condition"] == "service_healthy"
    assert depends["redis"]["condition"] == "service_healthy"


def test_beat_does_not_wait_for_the_database_preparation(
    services: dict[str, dict[str, Any]],
) -> None:
    assert "migrate" not in services["beat"]["depends_on"]


def test_frontend_receives_only_the_public_api_url(services: dict[str, dict[str, Any]]) -> None:
    frontend = services["frontend"]

    assert "env_file" not in frontend
    assert set(frontend["environment"]) == {"VITE_API_URL"}
    assert frontend["build"]["target"] == "dev"
    assert not any(name in str(frontend) for name in SECRET_NAMES)


@pytest.mark.parametrize("name", ["db", "redis", "migrate"])
def test_database_and_redis_publish_no_ports(
    services: dict[str, dict[str, Any]], name: str
) -> None:
    assert "ports" not in services[name]

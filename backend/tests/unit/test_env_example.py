"""Contrato del archivo de ejemplo de variables de entorno (D-7, runtime-configuration).

Si el archivo no se encuentra el test FALLA: esconderlo seria peor que un fallo claro.
Ruta: variable ``ENV_EXAMPLE_PATH``, o ``<repo>/.env.example``, o ``/.env.example``
(montado dentro del contenedor).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.core.config import Settings

SENSITIVE_FRAGMENTS = ("SECRET", "PASSWORD", "TOKEN", "KEY", "DATABASE")
EMPTY_REQUIRED = ("JWT_SECRET_KEY", "SMTP_PASSWORD", "SEED_DEMO_PASSWORD")
POSTGRES_VARIABLES = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")


def is_sensitive_name(name: str) -> bool:
    """True si un nombre de variable sugiere un secreto (no debe llevar prefijo VITE_)."""
    upper = name.upper()
    return any(fragment in upper for fragment in SENSITIVE_FRAGMENTS)


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip()
    return values


def env_example_path() -> Path:
    configured = os.environ.get("ENV_EXAMPLE_PATH")
    if configured:
        return Path(configured)
    in_repo = Path(__file__).resolve().parents[3] / ".env.example"
    return in_repo if in_repo.exists() else Path("/.env.example")


@pytest.fixture(scope="module")
def example() -> dict[str, str]:
    path = env_example_path()
    assert path.is_file(), f"No se encontro .env.example en {path}"
    return parse_env(path.read_text(encoding="utf-8"))


def test_every_settings_field_is_declared(example: dict[str, str]) -> None:
    missing = [name for name in Settings.model_fields if name not in example]
    assert missing == []


def test_postgres_and_vite_variables_are_declared(example: dict[str, str]) -> None:
    for name in (*POSTGRES_VARIABLES, "VITE_API_URL"):
        assert name in example


def test_email_redirect_is_declared_empty_in_example(example: dict[str, str]) -> None:
    assert example["EMAIL_REDIRECT_TO"] == ""


@pytest.mark.parametrize("name", EMPTY_REQUIRED)
def test_secrets_are_empty_in_example(example: dict[str, str], name: str) -> None:
    assert example[name] == ""


def test_the_only_vite_variable_is_api_url(example: dict[str, str]) -> None:
    assert [name for name in example if name.startswith("VITE_")] == ["VITE_API_URL"]


def test_vite_variables_have_no_sensitive_names(example: dict[str, str]) -> None:
    offenders = [n for n in example if n.startswith("VITE_") and is_sensitive_name(n)]
    assert offenders == []


@pytest.mark.parametrize(
    "name",
    ["VITE_JWT_SECRET_KEY", "VITE_SMTP_PASSWORD", "VITE_API_TOKEN", "VITE_DATABASE_URL"],
)
def test_sensitive_vite_names_are_detected(name: str) -> None:
    assert is_sensitive_name(name)


def test_public_names_are_not_flagged() -> None:
    assert not is_sensitive_name("VITE_API_URL")


def test_parse_env_ignores_comments_and_keeps_empty_values() -> None:
    parsed = parse_env("# comentario\n\nA=1\nB=\nC=x=y\n")

    assert parsed == {"A": "1", "B": "", "C": "x=y"}


def test_missing_file_fails_instead_of_skipping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV_EXAMPLE_PATH", str(Path("no") / "existe" / ".env.example"))

    assert not env_example_path().is_file()


def test_cors_origins_list_the_dev_and_demo_origins_and_no_wildcard(
    example: dict[str, str],
) -> None:
    origins = [item.strip() for item in example["CORS_ORIGINS"].split(",")]

    assert "http://localhost:5173" in origins
    assert "http://localhost:8080" in origins
    assert "*" not in origins


def test_example_cors_origins_pass_the_settings_validation(
    example: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, value in {
        "DATABASE_URL": "postgresql+psycopg://odonto:odonto_dev@db:5432/odonto",
        "REDIS_URL": "redis://redis:6379/0",
        "JWT_SECRET_KEY": "k" * 48,
        "SMTP_HOST": "mailpit",
        "SMTP_PORT": "1025",
        "EMAIL_FROM": "turnos@consultorio.test",
        "CLINIC_TIMEZONE": "America/Argentina/Buenos_Aires",
        "CORS_ORIGINS": example["CORS_ORIGINS"],
    }.items():
        monkeypatch.setenv(name, value)

    assert Settings(_env_file=None).CORS_ORIGINS == [
        "http://localhost:5173",
        "http://localhost:8080",
    ]

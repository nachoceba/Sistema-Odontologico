"""Tests de la configuracion validada (spec runtime-configuration). Datos ficticios."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings

JWT_KEY = "k" * 48

VALID_ENV: dict[str, str] = {
    "DATABASE_URL": "postgresql+psycopg://odonto:odonto_dev@db:5432/odonto",
    "REDIS_URL": "redis://redis:6379/0",
    "JWT_SECRET_KEY": JWT_KEY,
    "SMTP_HOST": "mailpit",
    "SMTP_PORT": "1025",
    "EMAIL_FROM": "turnos@consultorio.test",
    "CLINIC_TIMEZONE": "America/Argentina/Buenos_Aires",
    "CORS_ORIGINS": "http://localhost:5173",
}

ALL_NAMES = [
    *VALID_ENV,
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_USE_TLS",
    "EMAIL_REDIRECT_TO",
]


def load(monkeypatch: pytest.MonkeyPatch, **overrides: str | None) -> Settings:
    """Construye Settings solo con el entorno indicado (None quita la variable)."""
    for name in ALL_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in {**VALID_ENV, **overrides}.items():
        if value is not None:
            monkeypatch.setenv(name, value)
    return Settings(_env_file=None)


def error_text(monkeypatch: pytest.MonkeyPatch, **overrides: str | None) -> str:
    with pytest.raises(ValidationError) as info:
        load(monkeypatch, **overrides)
    return str(info.value)


def test_complete_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load(monkeypatch)

    assert settings.CLINIC_TIMEZONE == "America/Argentina/Buenos_Aires"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.CORS_ORIGINS == ["http://localhost:5173"]
    assert settings.JWT_ALGORITHM == "HS256"
    assert settings.SMTP_PORT == 1025
    assert settings.SMTP_USE_TLS is False
    assert settings.JWT_SECRET_KEY.get_secret_value() == JWT_KEY


def test_optional_values_can_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load(monkeypatch, ACCESS_TOKEN_EXPIRE_MINUTES="15", SMTP_USE_TLS="true")

    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15
    assert settings.SMTP_USE_TLS is True


@pytest.mark.parametrize(
    "name",
    [
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SECRET_KEY",
        "SMTP_HOST",
        "SMTP_PORT",
        "EMAIL_FROM",
        "CLINIC_TIMEZONE",
        "CORS_ORIGINS",
    ],
)
def test_missing_required_variable_names_it(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    assert name in error_text(monkeypatch, **{name: None})


def test_short_jwt_key_is_rejected_without_revealing_it(monkeypatch: pytest.MonkeyPatch) -> None:
    text = error_text(monkeypatch, JWT_SECRET_KEY="corta-1234")

    assert "JWT_SECRET_KEY" in text
    assert "corta-1234" not in text


def test_empty_jwt_key_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    assert "JWT_SECRET_KEY" in error_text(monkeypatch, JWT_SECRET_KEY="")


def test_database_url_password_is_not_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load(monkeypatch, DATABASE_URL="postgresql+psycopg://u:clave-secreta@db/odonto")

    assert "clave-secreta" not in repr(settings)
    assert "clave-secreta" not in str(settings)


@pytest.mark.parametrize("zone", ["America/Inexistente", "", "no es una zona"])
def test_invalid_timezone(monkeypatch: pytest.MonkeyPatch, zone: str) -> None:
    assert "CLINIC_TIMEZONE" in error_text(monkeypatch, CLINIC_TIMEZONE=zone)


@pytest.mark.parametrize("algorithm", ["none", "HS512", "RS256"])
def test_jwt_algorithm_not_allowed(monkeypatch: pytest.MonkeyPatch, algorithm: str) -> None:
    assert "JWT_ALGORITHM" in error_text(monkeypatch, JWT_ALGORITHM=algorithm)


@pytest.mark.parametrize("minutes", ["0", "-5", "abc"])
def test_invalid_token_lifetime(monkeypatch: pytest.MonkeyPatch, minutes: str) -> None:
    assert "ACCESS_TOKEN_EXPIRE_MINUTES" in error_text(
        monkeypatch, ACCESS_TOKEN_EXPIRE_MINUTES=minutes
    )


@pytest.mark.parametrize("port", ["0", "65536", "abc"])
def test_invalid_smtp_port(monkeypatch: pytest.MonkeyPatch, port: str) -> None:
    assert "SMTP_PORT" in error_text(monkeypatch, SMTP_PORT=port)


def test_several_cors_origins_are_split_and_trimmed(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load(monkeypatch, CORS_ORIGINS="http://localhost:5173, http://127.0.0.1:5173")

    assert settings.CORS_ORIGINS == ["http://localhost:5173", "http://127.0.0.1:5173"]


@pytest.mark.parametrize("value", ["", " , "])
def test_empty_cors_origins_are_rejected(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    assert "CORS_ORIGINS" in error_text(monkeypatch, CORS_ORIGINS=value)


def test_smtp_credentials_default_to_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load(monkeypatch)

    assert settings.SMTP_USER == ""
    assert settings.SMTP_PASSWORD.get_secret_value() == ""


def test_empty_smtp_credentials_are_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load(monkeypatch, SMTP_USER="", SMTP_PASSWORD="")

    assert settings.SMTP_USER == ""
    assert settings.SMTP_PASSWORD.get_secret_value() == ""


def test_get_settings_is_lazy_and_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    for name, value in VALID_ENV.items():
        monkeypatch.setenv(name, value)
    try:
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()


def test_email_redirect_is_empty_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    assert load(monkeypatch).EMAIL_REDIRECT_TO == ""


def test_a_valid_email_redirect_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = load(monkeypatch, EMAIL_REDIRECT_TO="equipo.demo@example.org")
    assert settings.EMAIL_REDIRECT_TO == "equipo.demo@example.org"


@pytest.mark.parametrize("value", ["no-es-un-email", "dos@@example.org", "con espacio@example.org"])
def test_an_invalid_email_redirect_names_the_variable_without_repeating_the_value(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    text = error_text(monkeypatch, EMAIL_REDIRECT_TO=value)

    assert "EMAIL_REDIRECT_TO" in text
    assert value not in text

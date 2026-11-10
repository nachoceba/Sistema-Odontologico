"""Configuracion del sistema desde variables de entorno (spec runtime-configuration).

La configuracion se carga a demanda con ``get_settings()``: importar el dominio
o ``app.core.timezone`` nunca la dispara. Los campos usan el mismo nombre que la
variable de entorno para que los errores de validacion nombren la variable.
Los valores sensibles son ``SecretStr`` y los errores no repiten el valor recibido.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BeforeValidator, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.domain.users.rules import is_valid_email

JWT_SECRET_MIN_LENGTH = 32
CORS_ORIGIN_SCHEMES = ("http://", "https://")


def _split_comma(value: Any) -> Any:
    """Parte ``"a, b"`` en ``["a", "b"]`` (D-2); descarta elementos vacios."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


CommaSeparated = Annotated[list[str], NoDecode, BeforeValidator(_split_comma)]


class Settings(BaseSettings):
    """Variables de entorno del backend. Sin lectura de ``.env`` desde Python (D-2)."""

    model_config = SettingsConfigDict(
        extra="ignore",
        hide_input_in_errors=True,
        env_file=None,
    )

    DATABASE_URL: SecretStr
    REDIS_URL: str
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)
    SMTP_HOST: str
    SMTP_PORT: int = Field(ge=1, le=65535)
    SMTP_USER: str = ""
    SMTP_PASSWORD: SecretStr = SecretStr("")
    SMTP_USE_TLS: bool = False
    EMAIL_FROM: str
    EMAIL_REDIRECT_TO: str = ""
    CLINIC_TIMEZONE: str
    CORS_ORIGINS: CommaSeparated = Field(min_length=1)
    ONLINE_BOOKING_HOLD_MINUTES: int = Field(default=60, ge=5, le=1440)
    PUBLIC_APP_URL: str = "http://localhost:5173"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def _jwt_key_long_enough(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < JWT_SECRET_MIN_LENGTH:
            raise ValueError(f"debe tener al menos {JWT_SECRET_MIN_LENGTH} caracteres")
        return value

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _origins_are_explicit(cls, value: list[str]) -> list[str]:
        if any(not origin.startswith(CORS_ORIGIN_SCHEMES) for origin in value):
            raise ValueError("cada origen debe ser explicito, con http:// o https:// (sin comodin)")
        return value

    @field_validator("PUBLIC_APP_URL")
    @classmethod
    def _public_url_is_an_origin(cls, value: str) -> str:
        if not value.startswith(CORS_ORIGIN_SCHEMES) or value.endswith("/"):
            raise ValueError("debe empezar con http:// o https:// y no terminar en /")
        return value

    @field_validator("EMAIL_REDIRECT_TO")
    @classmethod
    def _redirect_is_an_email(cls, value: str) -> str:
        if value and not is_valid_email(value):
            raise ValueError("no es una direccion de email valida")
        return value

    @field_validator("CLINIC_TIMEZONE")
    @classmethod
    def _timezone_exists(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, OSError, KeyError) as error:
            raise ValueError("no es una zona horaria IANA existente") from error
        return value


@lru_cache
def get_settings() -> Settings:
    """Settings de proceso, cargada la primera vez que se pide."""
    return Settings()

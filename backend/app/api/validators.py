"""Validadores de Pydantic compartidos por los esquemas de la API."""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field

from app.domain.users.rules import is_valid_email


def strip_text(value: object) -> object:
    """Recorta los espacios de un texto; cualquier otro valor pasa igual y lo valida Pydantic."""
    return value.strip() if isinstance(value, str) else value


def check_email(value: str) -> str:
    """Mismo formato de email para cuentas del personal y pacientes (RN-PA-02)."""
    if not is_valid_email(value):
        raise ValueError("El email no tiene un formato válido")
    return value


Email = Annotated[
    str,
    BeforeValidator(strip_text),
    Field(min_length=3, max_length=254),
    AfterValidator(check_email),
]

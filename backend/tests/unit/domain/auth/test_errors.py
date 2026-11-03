"""Errores de autenticacion y autorizacion (spec error-model, P-5)."""

from __future__ import annotations

import pytest

from app.core.errors import DomainError
from app.domain.auth import ForbiddenError, InvalidCredentialsError, NotAuthenticatedError


@pytest.mark.parametrize(
    ("error_class", "code", "message"),
    [
        (InvalidCredentialsError, "INVALID_CREDENTIALS", "Email o contraseña incorrectos"),
        (NotAuthenticatedError, "NOT_AUTHENTICATED", "Tu sesión terminó. Volvé a ingresar"),
        (ForbiddenError, "FORBIDDEN", "No tenés permiso para esta acción"),
    ],
)
def test_error_has_code_and_generic_message(
    error_class: type[DomainError], code: str, message: str
) -> None:
    error = error_class()
    assert isinstance(error, DomainError)
    assert error.code == code
    assert str(error) == message


def test_codes_are_distinct() -> None:
    codes = {
        InvalidCredentialsError.code,
        NotAuthenticatedError.code,
        ForbiddenError.code,
    }
    assert len(codes) == 3

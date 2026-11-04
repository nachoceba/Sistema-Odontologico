"""Errores de la gestion de usuarios (spec error-model y frontend-user-management)."""

from __future__ import annotations

import pytest

from app.core.errors import DomainError
from app.domain.users.errors import (
    EmailTakenError,
    RoleChangeNotAllowedError,
    SelfModificationError,
    UserNotFoundError,
)


@pytest.mark.parametrize(
    ("error_class", "code", "message"),
    [
        (UserNotFoundError, "USER_NOT_FOUND", "El usuario ya no existe"),
        (EmailTakenError, "EMAIL_TAKEN", "Ya existe un usuario con ese email"),
        (
            RoleChangeNotAllowedError,
            "ROLE_CHANGE_NOT_ALLOWED",
            "No se puede cambiar el rol de un odontólogo",
        ),
        (
            SelfModificationError,
            "SELF_MODIFICATION_NOT_ALLOWED",
            "No podés desactivar ni cambiar el rol de tu propia cuenta",
        ),
    ],
)
def test_error_has_code_and_screen_message(
    error_class: type[DomainError], code: str, message: str
) -> None:
    error = error_class()
    assert isinstance(error, DomainError)
    assert error.code == code
    assert str(error) == message

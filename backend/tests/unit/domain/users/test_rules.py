"""Reglas puras de la gestion de usuarios (spec user-management, design D-1)."""

from __future__ import annotations

import pytest

from app.domain.auth import Role
from app.domain.users.errors import RoleChangeNotAllowedError, SelfModificationError
from app.domain.users.rules import (
    check_can_deactivate,
    check_role_change,
    is_valid_email,
    normalize_email,
    professional_for_new_dentist,
)
from app.domain.users.types import NewProfessional


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Nueva.Recepcion@Example.COM ", "nueva.recepcion@example.com"),
        ("ya@minuscula.com", "ya@minuscula.com"),
        ("\tAdmin@Example.com\n", "admin@example.com"),
    ],
)
def test_normalize_email_trims_and_lowercases(raw: str, expected: str) -> None:
    assert normalize_email(raw) == expected


@pytest.mark.parametrize(
    "email",
    ["a@b", "recepcion@example.com", "a.b+c@sub.example.org"],
)
def test_valid_emails_are_accepted(email: str) -> None:
    assert is_valid_email(email) is True


def test_limits_are_3_and_254_characters() -> None:
    assert is_valid_email("a@b") is True  # 3 caracteres
    assert is_valid_email("@b") is False  # 2 caracteres
    at_limit = "a" * 252 + "@b"
    assert len(at_limit) == 254
    assert is_valid_email(at_limit) is True
    assert is_valid_email("a" + at_limit) is False  # 255 caracteres


@pytest.mark.parametrize(
    "email",
    [
        "sin-arroba.example.com",
        "dos@arrobas@example.com",
        "con espacio@example.com",
        "usuario@exa mple.com",
        "@example.com",
        "usuario@",
        "",
    ],
)
def test_invalid_emails_are_rejected(email: str) -> None:
    assert is_valid_email(email) is False


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (Role.ADMIN, Role.RECEPTIONIST),
        (Role.RECEPTIONIST, Role.ADMIN),
        (Role.RECEPTIONIST, Role.DENTIST),
        (Role.ADMIN, Role.DENTIST),
    ],
)
def test_allowed_role_changes_pass(current: Role, new: Role) -> None:
    check_role_change(current, new, is_self=False)


@pytest.mark.parametrize("new", [Role.RECEPTIONIST, Role.ADMIN])
def test_dentist_cannot_change_to_another_role(new: Role) -> None:
    with pytest.raises(RoleChangeNotAllowedError):
        check_role_change(Role.DENTIST, new, is_self=False)


@pytest.mark.parametrize("role", list(Role))
def test_same_role_is_not_a_change(role: Role) -> None:
    check_role_change(role, role, is_self=False)


def test_changing_the_own_role_is_rejected_even_if_allowed() -> None:
    with pytest.raises(SelfModificationError):
        check_role_change(Role.ADMIN, Role.RECEPTIONIST, is_self=True)


def test_sending_the_own_role_unchanged_is_not_a_modification() -> None:
    check_role_change(Role.ADMIN, Role.ADMIN, is_self=True)


def test_deactivating_another_account_is_allowed() -> None:
    check_can_deactivate(is_self=False)


def test_deactivating_the_own_account_is_rejected() -> None:
    with pytest.raises(SelfModificationError):
        check_can_deactivate(is_self=True)


def test_new_dentist_uses_the_trimmed_display_name_and_license() -> None:
    result = professional_for_new_dentist("Ana Pérez", "  Dra. Ana  ", " MN-0001 ")
    assert result == NewProfessional(display_name="Dra. Ana", license_number="MN-0001")


@pytest.mark.parametrize("display_name", [None, "", "   "])
def test_missing_display_name_falls_back_to_the_full_name(display_name: str | None) -> None:
    result = professional_for_new_dentist("Ana Pérez", display_name, None)
    assert result.display_name == "Ana Pérez"


@pytest.mark.parametrize("license_number", [None, "", "  "])
def test_blank_license_number_is_none(license_number: str | None) -> None:
    result = professional_for_new_dentist("Ana Pérez", "Dra. Ana", license_number)
    assert result.license_number is None

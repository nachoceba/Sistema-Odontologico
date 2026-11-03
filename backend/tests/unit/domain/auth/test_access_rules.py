"""Regla de alcance propio del odontologo (spec access-control, RN-AU-04)."""

from __future__ import annotations

import pytest

from app.domain.auth import Principal, Role, can_access_professional

PROF_A = "11111111-1111-4111-8111-111111111111"
PROF_B = "22222222-2222-4222-8222-222222222222"


def principal(role: Role, professional_id: str | None = None) -> Principal:
    return Principal(user_id="u-1", role=role, professional_id=professional_id)


def test_dentist_can_access_own_professional() -> None:
    assert can_access_professional(principal(Role.DENTIST, PROF_A), PROF_A) is True


def test_dentist_cannot_access_another_professional() -> None:
    assert can_access_professional(principal(Role.DENTIST, PROF_A), PROF_B) is False


@pytest.mark.parametrize("role", [Role.RECEPTIONIST, Role.ADMIN])
@pytest.mark.parametrize("target", [PROF_A, PROF_B])
def test_reception_and_admin_access_any_professional(role: Role, target: str) -> None:
    assert can_access_professional(principal(role), target) is True


def test_dentist_without_professional_record_accesses_nothing() -> None:
    assert can_access_professional(principal(Role.DENTIST, None), PROF_A) is False


@pytest.mark.parametrize("malformed", ["", "no-es-uuid", "1" * 40])
def test_malformed_professional_id_is_denied_to_dentist(malformed: str) -> None:
    assert can_access_professional(principal(Role.DENTIST, PROF_A), malformed) is False


def test_dentist_without_record_is_denied_even_with_malformed_id() -> None:
    assert can_access_professional(principal(Role.DENTIST, None), "") is False

"""``Role`` (dominio) y ``UserRole`` (infraestructura) deben tener los mismos valores."""

from __future__ import annotations

from app.domain.auth import Role
from app.infrastructure.db.enums import UserRole


def test_role_and_user_role_have_exactly_the_same_values() -> None:
    assert {role.value for role in Role} == {role.value for role in UserRole}


def test_every_user_role_converts_to_a_role_by_value() -> None:
    for user_role in UserRole:
        assert Role(user_role.value).name == user_role.name

"""Bateria de contrato del repositorio de cuentas (spec user-account-repository)."""

from __future__ import annotations

import uuid

from app.domain.auth import Role
from tests.contract.conftest import RepositoryFactory


def test_exact_email_returns_the_account(factory: RepositoryFactory) -> None:
    expected = factory.add_account("rec", email="recepcion@example.com", role=Role.RECEPTIONIST)
    account = factory.user_accounts().get_by_email("recepcion@example.com")
    assert account is not None
    assert account.id == expected.id
    assert account.role is Role.RECEPTIONIST
    assert account.active is True
    assert account.professional_id is None
    assert account.full_name == expected.full_name
    assert account.password_hash == "hash-ficticio"


def test_email_with_other_case_returns_dentist_with_professional(
    factory: RepositoryFactory,
) -> None:
    expected = factory.add_account(
        "dra", email="Dra.Lopez@Example.com", role=Role.DENTIST, with_professional=True
    )
    account = factory.user_accounts().get_by_email("DRA.LOPEZ@EXAMPLE.COM")
    assert account is not None
    assert account.role is Role.DENTIST
    assert account.professional_id == expected.professional_id
    assert account.professional_id is not None


def test_unknown_email_returns_none(factory: RepositoryFactory) -> None:
    factory.add_account("rec", email="recepcion@example.com", role=Role.RECEPTIONIST)
    assert factory.user_accounts().get_by_email("nadie@example.com") is None


def test_deactivated_account_is_returned_as_inactive(factory: RepositoryFactory) -> None:
    factory.add_account("baja", email="baja@example.com", role=Role.RECEPTIONIST, active=False)
    account = factory.user_accounts().get_by_email("baja@example.com")
    assert account is not None
    assert account.active is False


def test_existing_id_returns_the_admin(factory: RepositoryFactory) -> None:
    expected = factory.add_account("admin", email="admin@example.com", role=Role.ADMIN)
    account = factory.user_accounts().get_by_id(expected.id)
    assert account is not None
    assert account.role is Role.ADMIN
    assert account.email == "admin@example.com"


def test_unknown_valid_uuid_returns_none(factory: RepositoryFactory) -> None:
    factory.add_account("admin", email="admin@example.com", role=Role.ADMIN)
    assert factory.user_accounts().get_by_id(str(uuid.uuid4())) is None


def test_malformed_id_returns_none_without_error(factory: RepositoryFactory) -> None:
    assert factory.user_accounts().get_by_id("no-es-un-uuid") is None


def test_dentist_without_professional_has_no_professional_id(factory: RepositoryFactory) -> None:
    expected = factory.add_account("sinficha", email="sinficha@example.com", role=Role.DENTIST)
    account = factory.user_accounts().get_by_id(expected.id)
    assert account is not None
    assert account.role is Role.DENTIST
    assert account.professional_id is None

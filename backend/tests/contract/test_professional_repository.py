"""Bateria de contrato del repositorio de profesionales (spec professional-repository)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import DBAPIError

from app.domain.auth import Role, UserAccount
from app.domain.users.types import AccountChanges, NewAccount, NewProfessional
from tests.contract.conftest import RepositoryFactory

STORAGE_FAILURES = (ValueError, DBAPIError)


def _dentist(factory: RepositoryFactory, name: str) -> UserAccount:
    return factory.add_account(
        name, email=f"{name}@example.com", role=Role.DENTIST, with_professional=True
    )


def test_list_returns_the_professionals_ordered_by_display_name(
    factory: RepositoryFactory,
) -> None:
    second = _dentist(factory, "b")
    first = _dentist(factory, "a")
    listed = factory.professionals().list()
    assert [p.user_id for p in listed] == [first.id, second.id]
    assert [p.id for p in listed] == [first.professional_id, second.professional_id]
    assert [p.display_name for p in listed] == ["Profesional a", "Profesional b"]


def test_list_orders_ignoring_case(factory: RepositoryFactory) -> None:
    repo = factory.user_accounts()
    for email, name in [("1@e.com", "carla"), ("2@e.com", "Ana"), ("3@e.com", "Bruno")]:
        repo.create(NewAccount(email, name, "hash", Role.DENTIST, NewProfessional(name)))
    assert [p.display_name for p in factory.professionals().list()] == ["Ana", "Bruno", "carla"]


def test_list_only_active_omits_deactivated_professionals(factory: RepositoryFactory) -> None:
    active = _dentist(factory, "a")
    gone = _dentist(factory, "b")
    factory.user_accounts().update(gone.id, AccountChanges(active=False))
    professionals = factory.professionals()
    assert [p.id for p in professionals.list(only_active=True)] == [active.professional_id]
    assert len(professionals.list()) == 2


def test_list_is_empty_without_professionals(factory: RepositoryFactory) -> None:
    assert factory.professionals().list() == []
    assert factory.professionals().list(only_active=True) == []


def test_get_by_id_returns_the_professional(factory: RepositoryFactory) -> None:
    account = _dentist(factory, "dra")
    assert account.professional_id is not None
    found = factory.professionals().get_by_id(account.professional_id)
    assert found is not None
    assert found.user_id == account.id
    assert found.display_name == "Profesional dra"
    assert found.license_number is None
    assert found.active is True


def test_get_by_id_returns_inactive_professionals_too(factory: RepositoryFactory) -> None:
    account = _dentist(factory, "dra")
    factory.user_accounts().update(account.id, AccountChanges(active=False))
    assert account.professional_id is not None
    found = factory.professionals().get_by_id(account.professional_id)
    assert found is not None
    assert found.active is False


@pytest.mark.parametrize("professional_id", [str(uuid.uuid4()), "no-es-un-uuid"])
def test_get_by_id_of_unknown_or_malformed_id_returns_none(
    factory: RepositoryFactory, professional_id: str
) -> None:
    _dentist(factory, "dra")
    assert factory.professionals().get_by_id(professional_id) is None


# --- La ficha que crea o toca el repositorio de cuentas (spec user-account-repository) ---------


def test_created_dentist_has_an_active_professional_with_the_given_data(
    factory: RepositoryFactory,
) -> None:
    created = factory.user_accounts().create(
        NewAccount(
            "dra@example.com",
            "Nombre Completo",
            "hash",
            Role.DENTIST,
            NewProfessional("Dra. Nueva", "MN-0001"),
        )
    )
    assert created.professional_id is not None
    found = factory.professionals().get_by_id(created.professional_id)
    assert found is not None
    assert (found.user_id, found.display_name, found.license_number, found.active) == (
        created.id,
        "Dra. Nueva",
        "MN-0001",
        True,
    )


def test_deactivating_and_reactivating_the_account_toggles_the_professional(
    factory: RepositoryFactory,
) -> None:
    account = _dentist(factory, "dra")
    assert account.professional_id is not None
    accounts, professionals = factory.user_accounts(), factory.professionals()
    accounts.update(account.id, AccountChanges(active=False))
    off = professionals.get_by_id(account.professional_id)
    assert off is not None
    assert off.active is False
    accounts.update(account.id, AccountChanges(active=True))
    on = professionals.get_by_id(account.professional_id)
    assert on is not None
    assert on.active is True


def test_changing_a_receptionist_to_dentist_creates_an_active_professional(
    factory: RepositoryFactory,
) -> None:
    account = factory.add_account("rec", email="r@example.com", role=Role.RECEPTIONIST)
    updated = factory.user_accounts().update(
        account.id,
        AccountChanges(role=Role.DENTIST, new_professional=NewProfessional("Dra. Reconvertida")),
    )
    assert updated.professional_id is not None
    found = factory.professionals().get_by_id(updated.professional_id)
    assert found is not None
    assert (found.user_id, found.display_name, found.active) == (
        account.id,
        "Dra. Reconvertida",
        True,
    )


def test_failed_creation_leaves_no_professional(factory: RepositoryFactory) -> None:
    broken = NewAccount("d@example.com", "X", "hash", Role.DENTIST, NewProfessional("Rota \x00"))
    with pytest.raises(STORAGE_FAILURES):
        factory.user_accounts().create(broken)
    assert factory.professionals().list() == []

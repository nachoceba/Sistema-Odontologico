"""Bateria de contrato del repositorio de profesionales (spec professional-repository)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import DBAPIError

from app.domain.appointments.errors import ProfessionalNotFoundError
from app.domain.auth import Role, UserAccount
from app.domain.professionals import UNSET
from app.domain.users.types import AccountChanges, NewAccount, NewProfessional
from tests.contract.conftest import InMemoryFactory, RepositoryFactory

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


# --- Editar nombre a mostrar y matricula (spec professional-repository, C-07) -------------------


def test_update_display_name_keeps_the_rest_and_reorders_the_list(
    factory: RepositoryFactory,
) -> None:
    dra = _dentist(factory, "z")
    other = _dentist(factory, "m")
    assert dra.professional_id is not None
    professionals = factory.professionals()
    professionals.update(dra.professional_id, license_number="MN-1")
    updated = professionals.update(dra.professional_id, display_name="Dra. Ana Pérez")
    found = professionals.get_by_id(dra.professional_id)
    assert found == updated
    assert found is not None
    assert (found.display_name, found.license_number, found.user_id, found.active) == (
        "Dra. Ana Pérez",
        "MN-1",
        dra.id,
        True,
    )
    assert [p.id for p in professionals.list()] == [dra.professional_id, other.professional_id]


def test_update_can_clear_the_license_without_touching_the_name(
    factory: RepositoryFactory,
) -> None:
    dr = _dentist(factory, "b")
    assert dr.professional_id is not None
    professionals = factory.professionals()
    professionals.update(dr.professional_id, license_number="MN-9")
    cleared = professionals.update(dr.professional_id, license_number=None)
    assert (cleared.license_number, cleared.display_name) == (None, "Profesional b")
    kept = professionals.update(dr.professional_id, display_name="Dr. B")
    assert kept.license_number is None
    assert professionals.update(dr.professional_id, license_number="MN-2").license_number == "MN-2"


def test_update_without_fields_returns_the_unchanged_record(factory: RepositoryFactory) -> None:
    dr = _dentist(factory, "b")
    assert dr.professional_id is not None
    professionals = factory.professionals()
    before = professionals.get_by_id(dr.professional_id)
    assert professionals.update(dr.professional_id, license_number=UNSET) == before


def test_update_of_an_inactive_professional_keeps_it_inactive(factory: RepositoryFactory) -> None:
    dra = _dentist(factory, "a")
    factory.user_accounts().update(dra.id, AccountChanges(active=False))
    assert dra.professional_id is not None
    updated = factory.professionals().update(dra.professional_id, license_number="MN-7")
    assert (updated.license_number, updated.active) == ("MN-7", False)
    found = factory.professionals().get_by_id(dra.professional_id)
    assert found is not None
    assert found.active is False


@pytest.mark.parametrize("professional_id", [str(uuid.uuid4()), "no-es-un-uuid"])
def test_update_of_unknown_or_malformed_id_is_rejected_and_changes_nothing(
    factory: RepositoryFactory, professional_id: str
) -> None:
    dra = _dentist(factory, "a")
    assert dra.professional_id is not None
    professionals = factory.professionals()
    before = professionals.list()
    with pytest.raises(ProfessionalNotFoundError):
        professionals.update(professional_id, display_name="Otro", license_number="X")
    assert professionals.list() == before


def test_in_memory_account_repository_shares_the_edited_record(
    factory: RepositoryFactory,
) -> None:
    if not isinstance(factory, InMemoryFactory):
        pytest.skip("solo aplica al almacen compartido en memoria")
    dra = _dentist(factory, "a")
    assert dra.professional_id is not None
    factory.professionals().update(dra.professional_id, display_name="Dra. Editada")
    shared = factory.user_accounts().professionals  # type: ignore[attr-defined]
    assert shared[dra.professional_id].display_name == "Dra. Editada"

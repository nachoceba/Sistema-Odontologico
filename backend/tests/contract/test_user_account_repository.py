"""Bateria de contrato del repositorio de cuentas (spec user-account-repository)."""

from __future__ import annotations

import uuid
from dataclasses import replace

import pytest
from sqlalchemy.exc import DBAPIError

from app.domain.auth import Role
from app.domain.users.errors import EmailTakenError, UserNotFoundError
from app.domain.users.types import AccountChanges, NewAccount, NewProfessional
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


# --- Escritura (C-04): listar, crear y actualizar -----------------------------------------------

# La falla de la ficha se provoca con un NUL en el nombre a mostrar: PostgreSQL rechaza ese caracter
# en un texto (DataError) y el doble en memoria lo rechaza igual (ValueError).
STORAGE_FAILURES = (ValueError, DBAPIError)
NUL_NAME = "Dra. \x00 Rota"


def _new(
    email: str, role: Role = Role.RECEPTIONIST, professional: NewProfessional | None = None
) -> NewAccount:
    return NewAccount(
        email=email,
        full_name="Persona Nueva",
        password_hash="hash-nuevo",
        role=role,
        professional=professional,
    )


def test_list_all_orders_by_full_name_ignoring_case(factory: RepositoryFactory) -> None:
    repo = factory.user_accounts()
    repo.create(replace(_new("c@example.com"), full_name="carla"))
    repo.create(replace(_new("a@example.com"), full_name="Ana"))
    repo.create(replace(_new("b@example.com"), full_name="Bruno"))
    assert [a.full_name for a in repo.list_all()] == ["Ana", "Bruno", "carla"]


def test_list_all_includes_inactive_accounts_and_professional_ids(
    factory: RepositoryFactory,
) -> None:
    factory.add_account("baja", email="baja@example.com", role=Role.RECEPTIONIST, active=False)
    dentist = factory.add_account(
        "dra", email="dra@example.com", role=Role.DENTIST, with_professional=True
    )
    listed = {a.email: a for a in factory.user_accounts().list_all()}
    assert listed["baja@example.com"].active is False
    assert listed["dra@example.com"].professional_id == dentist.professional_id
    assert listed["dra@example.com"].professional_id is not None


def test_list_all_is_empty_without_accounts(factory: RepositoryFactory) -> None:
    assert factory.user_accounts().list_all() == []


def test_create_receptionist_is_active_without_professional(factory: RepositoryFactory) -> None:
    repo = factory.user_accounts()
    created = repo.create(_new("nueva@example.com"))
    found = repo.get_by_email("nueva@example.com")
    assert found == created
    assert created.active is True
    assert created.role is Role.RECEPTIONIST
    assert created.professional_id is None
    assert created.password_hash == "hash-nuevo"


def test_create_dentist_returns_the_professional_id(factory: RepositoryFactory) -> None:
    repo = factory.user_accounts()
    created = repo.create(
        _new(
            "dra@example.com",
            Role.DENTIST,
            NewProfessional(display_name="Dra. Nueva", license_number="MN-0001"),
        )
    )
    assert created.professional_id is not None
    assert repo.get_by_id(created.id) == created


def test_create_with_the_email_of_another_account_in_other_case_fails(
    factory: RepositoryFactory,
) -> None:
    factory.add_account("rec", email="recepcion@example.com", role=Role.RECEPTIONIST)
    repo = factory.user_accounts()
    with pytest.raises(EmailTakenError):
        repo.create(_new("RECEPCION@Example.COM"))
    assert len(repo.list_all()) == 1


def test_failure_creating_the_professional_leaves_no_account(factory: RepositoryFactory) -> None:
    repo = factory.user_accounts()
    broken = _new("dra@example.com", Role.DENTIST, NewProfessional(NUL_NAME))
    with pytest.raises(STORAGE_FAILURES):
        repo.create(broken)
    assert repo.list_all() == []
    assert repo.get_by_email("dra@example.com") is None
    # El email sigue libre para un nuevo intento.
    retry = _new("dra@example.com", Role.DENTIST, NewProfessional("Dra. Ok"))
    assert repo.create(retry).professional_id is not None


def test_update_changes_name_and_email(factory: RepositoryFactory) -> None:
    original = factory.add_account("rec", email="recepcion@example.com", role=Role.RECEPTIONIST)
    repo = factory.user_accounts()
    updated = repo.update(
        original.id, AccountChanges(full_name="Nombre Nuevo", email="nuevo@example.com")
    )
    assert updated.full_name == "Nombre Nuevo"
    assert updated.email == "nuevo@example.com"
    assert updated.role is Role.RECEPTIONIST
    assert repo.get_by_email("nuevo@example.com") == updated
    assert repo.get_by_email("recepcion@example.com") is None


def test_update_with_the_email_of_another_account_fails_and_changes_nothing(
    factory: RepositoryFactory,
) -> None:
    first = factory.add_account("rec", email="recepcion@example.com", role=Role.RECEPTIONIST)
    second = factory.add_account("adm", email="admin@example.com", role=Role.ADMIN)
    repo = factory.user_accounts()
    with pytest.raises(EmailTakenError):
        repo.update(first.id, AccountChanges(full_name="Otro", email="ADMIN@example.com"))
    assert repo.get_by_id(first.id) == first
    assert repo.get_by_id(second.id) == second


def test_update_may_change_the_case_of_the_own_email(factory: RepositoryFactory) -> None:
    account = factory.add_account("rec", email="recepcion@example.com", role=Role.RECEPTIONIST)
    repo = factory.user_accounts()
    updated = repo.update(account.id, AccountChanges(email="Recepcion@Example.com"))
    assert updated.email == "Recepcion@Example.com"


def test_update_to_dentist_creates_the_professional(factory: RepositoryFactory) -> None:
    account = factory.add_account("rec", email="recepcion@example.com", role=Role.RECEPTIONIST)
    repo = factory.user_accounts()
    updated = repo.update(
        account.id,
        AccountChanges(role=Role.DENTIST, new_professional=NewProfessional("Dra. Reconvertida")),
    )
    assert updated.role is Role.DENTIST
    assert updated.professional_id is not None
    assert repo.get_by_id(account.id) == updated


def test_failure_creating_the_professional_on_update_keeps_the_old_role(
    factory: RepositoryFactory,
) -> None:
    account = factory.add_account("rec", email="recepcion@example.com", role=Role.RECEPTIONIST)
    repo = factory.user_accounts()
    changes = AccountChanges(role=Role.DENTIST, new_professional=NewProfessional(NUL_NAME))
    with pytest.raises(STORAGE_FAILURES):
        repo.update(account.id, changes)
    assert repo.get_by_id(account.id) == account


def test_deactivate_and_reactivate_a_dentist_keep_the_professional_id(
    factory: RepositoryFactory,
) -> None:
    dentist = factory.add_account(
        "dra", email="dra@example.com", role=Role.DENTIST, with_professional=True
    )
    repo = factory.user_accounts()
    off = repo.update(dentist.id, AccountChanges(active=False))
    assert off.active is False
    assert off.professional_id == dentist.professional_id
    assert repo.update(dentist.id, AccountChanges(active=False)).active is False  # idempotente
    on = repo.update(dentist.id, AccountChanges(active=True))
    assert on.active is True
    assert on.professional_id == dentist.professional_id


def test_update_replaces_the_password_hash(factory: RepositoryFactory) -> None:
    account = factory.add_account("rec", email="recepcion@example.com", role=Role.RECEPTIONIST)
    repo = factory.user_accounts()
    repo.update(account.id, AccountChanges(password_hash="otro-hash"))
    found = repo.get_by_id(account.id)
    assert found is not None
    assert found.password_hash == "otro-hash"
    assert found.full_name == account.full_name


@pytest.mark.parametrize("user_id", [str(uuid.uuid4()), "no-es-un-uuid"])
def test_update_of_an_unknown_or_malformed_id_raises_user_not_found(
    factory: RepositoryFactory, user_id: str
) -> None:
    with pytest.raises(UserNotFoundError):
        factory.user_accounts().update(user_id, AccountChanges(full_name="X"))

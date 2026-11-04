"""Casos de uso de la gestion de usuarios con el repositorio en memoria (spec user-management)."""

from __future__ import annotations

import pytest

from app.application.users import (
    create_user,
    deactivate_user,
    list_users,
    reactivate_user,
    set_password,
    update_user,
)
from app.core.security import hash_password, verify_password
from app.domain.auth import Principal, Role, UserAccount
from app.domain.users.errors import (
    EmailTakenError,
    RoleChangeNotAllowedError,
    SelfModificationError,
    UserNotFoundError,
)
from app.infrastructure.in_memory import InMemoryUserAccountRepository

ADMIN = Principal(user_id="u-admin", role=Role.ADMIN)
OLD_PASSWORD = "clave-vieja-ficticia"


def _account(
    user_id: str,
    email: str,
    role: Role,
    *,
    full_name: str = "Persona Demo",
    active: bool = True,
    professional_id: str | None = None,
) -> UserAccount:
    return UserAccount(
        id=user_id,
        email=email,
        full_name=full_name,
        password_hash="hash-viejo",
        role=role,
        active=active,
        professional_id=professional_id,
    )


@pytest.fixture
def repo() -> InMemoryUserAccountRepository:
    return InMemoryUserAccountRepository(
        [
            _account("u-admin", "admin@example.com", Role.ADMIN, full_name="Admin Demo"),
            _account("u-rec", "recepcion@example.com", Role.RECEPTIONIST, full_name="Rec Demo"),
            _account(
                "u-dra",
                "dra@example.com",
                Role.DENTIST,
                full_name="Dra Demo",
                professional_id="p-dra",
            ),
        ]
    )


def test_list_users_returns_every_account_ordered_by_name(
    repo: InMemoryUserAccountRepository,
) -> None:
    assert [a.full_name for a in list_users(repo)] == ["Admin Demo", "Dra Demo", "Rec Demo"]


# --- Alta ----------------------------------------------------------------------------------------


def test_create_normalizes_the_email_and_stores_only_the_hash(
    repo: InMemoryUserAccountRepository,
) -> None:
    created = create_user(
        repo,
        email="  Nueva.Recepcion@Example.COM ",
        full_name="Nueva Recepcion",
        role=Role.RECEPTIONIST,
        password="clave-inicial-12",
    )
    assert created.email == "nueva.recepcion@example.com"
    assert created.active is True
    assert created.professional_id is None
    assert created.password_hash != "clave-inicial-12"
    assert verify_password(created.password_hash, "clave-inicial-12") is True
    assert repo.get_by_email("nueva.recepcion@example.com") == created


def test_create_dentist_builds_the_professional_with_the_given_data(
    repo: InMemoryUserAccountRepository,
) -> None:
    created = create_user(
        repo,
        email="nueva@example.com",
        full_name="Dra. Ficticia Nueva",
        role=Role.DENTIST,
        password="clave-inicial-12",
        display_name=" Dra. Nueva ",
        license_number="MN-0001",
    )
    assert created.professional_id is not None
    professional = repo.professionals[created.professional_id]
    assert (professional.display_name, professional.license_number) == ("Dra. Nueva", "MN-0001")
    assert professional.active is True


def test_create_dentist_without_display_name_uses_the_full_name(
    repo: InMemoryUserAccountRepository,
) -> None:
    created = create_user(
        repo,
        email="nueva@example.com",
        full_name="Dra. Ficticia Nueva",
        role=Role.DENTIST,
        password="clave-inicial-12",
    )
    assert created.professional_id is not None
    assert repo.professionals[created.professional_id].display_name == "Dra. Ficticia Nueva"


def test_create_ignores_the_professional_fields_for_other_roles(
    repo: InMemoryUserAccountRepository,
) -> None:
    created = create_user(
        repo,
        email="nueva@example.com",
        full_name="Nueva",
        role=Role.RECEPTIONIST,
        password="clave-inicial-12",
        display_name="Nadie",
        license_number="MN-9",
    )
    assert created.professional_id is None
    assert len(repo.professionals) == 1  # solo la de la odontologa del fixture


def test_create_with_a_taken_email_in_other_case_fails(
    repo: InMemoryUserAccountRepository,
) -> None:
    with pytest.raises(EmailTakenError):
        create_user(
            repo,
            email="RECEPCION@example.com",
            full_name="Otra",
            role=Role.RECEPTIONIST,
            password="clave-inicial-12",
        )
    assert len(list_users(repo)) == 3


# --- Edicion -------------------------------------------------------------------------------------


def test_update_changes_name_and_email_and_leaves_the_rest(
    repo: InMemoryUserAccountRepository,
) -> None:
    updated = update_user(
        repo, ADMIN, "u-rec", full_name="Nombre Nuevo", email="  Nuevo@Example.com "
    )
    assert (updated.full_name, updated.email) == ("Nombre Nuevo", "nuevo@example.com")
    assert updated.role is Role.RECEPTIONIST
    assert updated.password_hash == "hash-viejo"


def test_update_accepts_the_own_email_in_other_case(repo: InMemoryUserAccountRepository) -> None:
    updated = update_user(repo, ADMIN, "u-rec", email="RECEPCION@EXAMPLE.COM")
    assert updated.email == "recepcion@example.com"


def test_update_with_the_email_of_another_account_fails(
    repo: InMemoryUserAccountRepository,
) -> None:
    with pytest.raises(EmailTakenError):
        update_user(repo, ADMIN, "u-rec", email="Dra@example.com")
    assert repo.get_by_id("u-rec") is not None
    assert repo.get_by_email("recepcion@example.com") is not None


def test_changing_a_receptionist_to_dentist_creates_the_professional_with_its_name(
    repo: InMemoryUserAccountRepository,
) -> None:
    updated = update_user(repo, ADMIN, "u-rec", role=Role.DENTIST)
    assert updated.role is Role.DENTIST
    assert updated.professional_id is not None
    professional = repo.professionals[updated.professional_id]
    assert (professional.display_name, professional.active) == ("Rec Demo", True)


def test_changing_a_receptionist_to_admin_is_allowed(repo: InMemoryUserAccountRepository) -> None:
    assert update_user(repo, ADMIN, "u-rec", role=Role.ADMIN).role is Role.ADMIN


@pytest.mark.parametrize("new_role", [Role.RECEPTIONIST, Role.ADMIN])
def test_a_dentist_cannot_change_role(repo: InMemoryUserAccountRepository, new_role: Role) -> None:
    with pytest.raises(RoleChangeNotAllowedError):
        update_user(repo, ADMIN, "u-dra", role=new_role)
    stored = repo.get_by_id("u-dra")
    assert stored is not None
    assert stored.role is Role.DENTIST


def test_sending_the_same_role_changes_nothing(repo: InMemoryUserAccountRepository) -> None:
    before = repo.get_by_id("u-dra")
    assert update_user(repo, ADMIN, "u-dra", role=Role.DENTIST) == before


def test_the_admin_cannot_change_the_own_role(repo: InMemoryUserAccountRepository) -> None:
    with pytest.raises(SelfModificationError):
        update_user(repo, ADMIN, "u-admin", role=Role.RECEPTIONIST)
    stored = repo.get_by_id("u-admin")
    assert stored is not None
    assert stored.role is Role.ADMIN


def test_the_admin_may_edit_the_own_name(repo: InMemoryUserAccountRepository) -> None:
    assert update_user(repo, ADMIN, "u-admin", full_name="Admin Nueva").full_name == "Admin Nueva"


# --- Desactivar y reactivar ----------------------------------------------------------------------


def test_deactivate_and_reactivate_a_dentist_toggle_the_professional(
    repo: InMemoryUserAccountRepository,
) -> None:
    off = deactivate_user(repo, ADMIN, "u-dra")
    assert off.active is False
    assert repo.professionals["p-dra"].active is False
    on = reactivate_user(repo, "u-dra")
    assert on.active is True
    assert repo.professionals["p-dra"].active is True


def test_deactivate_and_reactivate_are_idempotent(repo: InMemoryUserAccountRepository) -> None:
    deactivate_user(repo, ADMIN, "u-rec")
    assert deactivate_user(repo, ADMIN, "u-rec").active is False
    assert reactivate_user(repo, "u-admin").active is True


def test_the_admin_cannot_deactivate_the_own_account(
    repo: InMemoryUserAccountRepository,
) -> None:
    with pytest.raises(SelfModificationError):
        deactivate_user(repo, ADMIN, "u-admin")
    stored = repo.get_by_id("u-admin")
    assert stored is not None
    assert stored.active is True


def test_an_admin_can_deactivate_another_admin() -> None:
    repo = InMemoryUserAccountRepository(
        [_account("u-a", "a@example.com", Role.ADMIN), _account("u-b", "b@example.com", Role.ADMIN)]
    )
    assert deactivate_user(repo, Principal("u-a", Role.ADMIN), "u-b").active is False


# --- Contrasena ----------------------------------------------------------------------------------


def test_set_password_replaces_the_hash(repo: InMemoryUserAccountRepository) -> None:
    repo.add(
        UserAccount(
            "u-pw", "pw@example.com", "Pw", hash_password(OLD_PASSWORD), Role.RECEPTIONIST, True
        )
    )
    set_password(repo, "u-pw", "clave-nueva-ficticia")
    stored = repo.get_by_id("u-pw")
    assert stored is not None
    assert verify_password(stored.password_hash, "clave-nueva-ficticia") is True
    assert verify_password(stored.password_hash, OLD_PASSWORD) is False


# --- Cuenta inexistente --------------------------------------------------------------------------


@pytest.mark.parametrize("user_id", ["u-inexistente", "no-es-un-uuid"])
def test_unknown_id_raises_user_not_found_in_every_operation(
    repo: InMemoryUserAccountRepository, user_id: str
) -> None:
    with pytest.raises(UserNotFoundError):
        update_user(repo, ADMIN, user_id, full_name="X")
    with pytest.raises(UserNotFoundError):
        deactivate_user(repo, ADMIN, user_id)
    with pytest.raises(UserNotFoundError):
        reactivate_user(repo, user_id)
    with pytest.raises(UserNotFoundError):
        set_password(repo, user_id, "clave-nueva-ficticia")

"""Casos de uso de autenticacion con el repositorio en memoria (spec user-authentication)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.application.auth import TokenConfig, authenticate, resolve_principal
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.auth import InvalidCredentialsError, NotAuthenticatedError, Role, UserAccount
from app.infrastructure.in_memory import InMemoryUserAccountRepository

PASSWORD = "clave-ficticia-de-prueba"
CONFIG = TokenConfig(secret="c" * 48, expires_minutes=30)
NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)


def account(
    user_id: str = "u-1",
    email: str = "recepcion@example.com",
    role: Role = Role.RECEPTIONIST,
    active: bool = True,
    professional_id: str | None = None,
) -> UserAccount:
    return UserAccount(
        id=user_id,
        email=email,
        full_name="Recepcion Demo",
        password_hash=hash_password(PASSWORD),
        role=role,
        active=active,
        professional_id=professional_id,
    )


def test_authenticate_returns_token_and_account() -> None:
    repo = InMemoryUserAccountRepository([account()])
    token, found = authenticate("recepcion@example.com", PASSWORD, repo, CONFIG, now=NOW)
    assert found.id == "u-1"
    principal = resolve_principal(token, repo, CONFIG, now=NOW)
    assert principal.user_id == "u-1"
    assert principal.role is Role.RECEPTIONIST


@pytest.mark.parametrize("typed", ["  Recepcion@Example.COM ", "RECEPCION@EXAMPLE.COM"])
def test_email_is_trimmed_and_case_insensitive(typed: str) -> None:
    repo = InMemoryUserAccountRepository([account()])
    _, found = authenticate(typed, PASSWORD, repo, CONFIG, now=NOW)
    assert found.id == "u-1"


def test_password_is_not_trimmed() -> None:
    repo = InMemoryUserAccountRepository([account()])
    with pytest.raises(InvalidCredentialsError):
        authenticate("recepcion@example.com", PASSWORD + " ", repo, CONFIG, now=NOW)


def failure_message(email: str, password: str, repo: InMemoryUserAccountRepository) -> str:
    with pytest.raises(InvalidCredentialsError) as info:
        authenticate(email, password, repo, CONFIG, now=NOW)
    return str(info.value)


def test_the_three_failures_raise_the_same_error_and_message() -> None:
    repo = InMemoryUserAccountRepository(
        [account(), account("u-2", "baja@example.com", active=False)]
    )
    wrong_password = failure_message("recepcion@example.com", "otra", repo)
    unknown_email = failure_message("nadie@example.com", PASSWORD, repo)
    deactivated = failure_message("baja@example.com", PASSWORD, repo)
    assert wrong_password == unknown_email == deactivated == "Email o contraseña incorrectos"


def test_unknown_email_still_verifies_a_dummy_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    real = verify_password

    def spy(password_hash: str, plain: str) -> bool:
        calls.append(password_hash)
        return real(password_hash, plain)

    monkeypatch.setattr("app.application.auth.verify_password", spy)
    repo = InMemoryUserAccountRepository([])
    with pytest.raises(InvalidCredentialsError):
        authenticate("nadie@example.com", PASSWORD, repo, CONFIG, now=NOW)
    assert len(calls) == 1
    assert calls[0].startswith("$argon2")


def test_resolve_principal_for_dentist_carries_professional_id() -> None:
    repo = InMemoryUserAccountRepository(
        [account("u-d", "dr@example.com", Role.DENTIST, professional_id="prof-1")]
    )
    token, _ = authenticate("dr@example.com", PASSWORD, repo, CONFIG, now=NOW)
    principal = resolve_principal(token, repo, CONFIG, now=NOW)
    assert principal.role is Role.DENTIST
    assert principal.professional_id == "prof-1"


def test_resolve_principal_rejects_deleted_account() -> None:
    token = create_access_token(
        user_id="fantasma", role=Role.ADMIN, secret=CONFIG.secret, expires_minutes=30, now=NOW
    )
    with pytest.raises(NotAuthenticatedError):
        resolve_principal(token, InMemoryUserAccountRepository([]), CONFIG, now=NOW)


def test_resolve_principal_rejects_account_deactivated_after_login() -> None:
    repo = InMemoryUserAccountRepository([account()])
    token, _ = authenticate("recepcion@example.com", PASSWORD, repo, CONFIG, now=NOW)
    repo.add(account(active=False))
    with pytest.raises(NotAuthenticatedError):
        resolve_principal(token, repo, CONFIG, now=NOW)


def test_resolve_principal_rejects_role_changed_after_login() -> None:
    repo = InMemoryUserAccountRepository([account()])
    token, _ = authenticate("recepcion@example.com", PASSWORD, repo, CONFIG, now=NOW)
    repo.add(account(role=Role.ADMIN))
    with pytest.raises(NotAuthenticatedError):
        resolve_principal(token, repo, CONFIG, now=NOW)


def test_resolve_principal_rejects_expired_token() -> None:
    repo = InMemoryUserAccountRepository([account()])
    token, _ = authenticate("recepcion@example.com", PASSWORD, repo, CONFIG, now=NOW)
    with pytest.raises(NotAuthenticatedError):
        resolve_principal(token, repo, CONFIG, now=NOW + timedelta(minutes=31))

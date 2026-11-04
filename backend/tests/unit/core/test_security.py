"""Hash de contrasenas (spec seed-data: contrasena guardada solo como hash, P-5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from argon2 import PasswordHasher

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.domain.auth import NotAuthenticatedError, Role

PLAIN = "contrasena-de-prueba-ficticia"


def test_hash_is_not_the_plain_password_and_has_argon2_format() -> None:
    hashed = hash_password(PLAIN)
    assert hashed != PLAIN
    assert PLAIN not in hashed
    assert hashed.startswith("$argon2")


def test_same_password_hashes_differently_each_time() -> None:
    assert hash_password(PLAIN) != hash_password(PLAIN)


def test_different_passwords_give_different_hashes_with_the_same_format() -> None:
    first = hash_password("otra-contrasena-ficticia")
    assert first.startswith("$argon2")
    assert first != hash_password(PLAIN)


def test_hash_is_verifiable_by_the_library() -> None:
    assert PasswordHasher().verify(hash_password(PLAIN), PLAIN)


def test_verify_password_accepts_the_right_password() -> None:
    assert verify_password(hash_password(PLAIN), PLAIN) is True


def test_verify_password_rejects_a_wrong_password() -> None:
    assert verify_password(hash_password(PLAIN), PLAIN + "x") is False


def test_verify_password_rejects_an_empty_password() -> None:
    assert verify_password(hash_password(PLAIN), "") is False


@pytest.mark.parametrize("corrupt", ["", "no-es-un-hash", "$argon2id$v=19$m=1$corrupto"])
def test_verify_password_with_a_corrupt_hash_is_false_without_exception(corrupt: str) -> None:
    assert verify_password(corrupt, PLAIN) is False


def test_verify_password_is_case_and_whitespace_exact() -> None:
    hashed = hash_password(PLAIN)
    assert verify_password(hashed, PLAIN.upper()) is False
    assert verify_password(hashed, PLAIN + " ") is False


# --- JWT (spec user-authentication) ---

SECRET = "s" * 48
NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)


def test_token_has_minimal_claims_and_expires_in_configured_minutes() -> None:
    token = create_access_token(
        user_id="u-1", role=Role.DENTIST, secret=SECRET, expires_minutes=30, now=NOW
    )
    claims = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_exp": False})
    assert set(claims) == {"sub", "role", "iat", "exp"}
    assert claims["sub"] == "u-1"
    assert claims["role"] == "dentist"
    assert claims["iat"] == int(NOW.timestamp())
    assert claims["exp"] == int((NOW + timedelta(minutes=30)).timestamp())


def test_token_does_not_carry_email_or_name() -> None:
    token = create_access_token(
        user_id="u-1", role=Role.ADMIN, secret=SECRET, expires_minutes=5, now=NOW
    )
    payload = token.split(".")[1]
    assert "email" not in payload
    assert set(jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_exp": False})) == {
        "sub",
        "role",
        "iat",
        "exp",
    }


def test_decode_returns_subject_and_role_while_valid() -> None:
    token = create_access_token(
        user_id="u-9", role=Role.RECEPTIONIST, secret=SECRET, expires_minutes=30, now=NOW
    )
    claims = decode_access_token(token, secret=SECRET, now=NOW + timedelta(minutes=29))
    assert claims.user_id == "u-9"
    assert claims.role is Role.RECEPTIONIST


def test_expired_token_is_rejected() -> None:
    token = create_access_token(
        user_id="u-1", role=Role.ADMIN, secret=SECRET, expires_minutes=30, now=NOW
    )
    with pytest.raises(NotAuthenticatedError):
        decode_access_token(token, secret=SECRET, now=NOW + timedelta(minutes=30, seconds=1))


def test_token_signed_with_another_key_is_rejected() -> None:
    token = create_access_token(
        user_id="u-1", role=Role.ADMIN, secret="o" * 48, expires_minutes=30, now=NOW
    )
    with pytest.raises(NotAuthenticatedError):
        decode_access_token(token, secret=SECRET, now=NOW)


def test_algorithm_none_is_rejected() -> None:
    payload = {"sub": "u-1", "role": "admin", "iat": int(NOW.timestamp()), "exp": 9999999999}
    token = jwt.encode(payload, key=None, algorithm="none")
    with pytest.raises(NotAuthenticatedError):
        decode_access_token(token, secret=SECRET, now=NOW)


def test_token_without_exp_is_rejected() -> None:
    token = jwt.encode(
        {"sub": "u-1", "role": "admin", "iat": int(NOW.timestamp())}, SECRET, algorithm="HS256"
    )
    with pytest.raises(NotAuthenticatedError):
        decode_access_token(token, secret=SECRET, now=NOW)


def test_token_without_sub_is_rejected() -> None:
    claims = {"role": "admin", "iat": int(NOW.timestamp()), "exp": int(NOW.timestamp()) + 600}
    token = jwt.encode(claims, SECRET, algorithm="HS256")
    with pytest.raises(NotAuthenticatedError):
        decode_access_token(token, secret=SECRET, now=NOW)


@pytest.mark.parametrize("garbage", ["", "abc", "a.b.c"])
def test_garbage_token_is_rejected(garbage: str) -> None:
    with pytest.raises(NotAuthenticatedError):
        decode_access_token(garbage, secret=SECRET, now=NOW)


def test_token_with_unknown_role_is_rejected() -> None:
    issued = int(NOW.timestamp())
    claims = {"sub": "u", "role": "superuser", "iat": issued, "exp": issued + 600}
    token = jwt.encode(claims, SECRET, algorithm="HS256")
    with pytest.raises(NotAuthenticatedError):
        decode_access_token(token, secret=SECRET, now=NOW)


def test_a_fresh_hash_does_not_need_rehash() -> None:
    assert needs_rehash(hash_password(PLAIN)) is False


def test_a_hash_with_weaker_parameters_needs_rehash() -> None:
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PLAIN)
    assert needs_rehash(weak) is True


def test_a_corrupt_hash_does_not_raise_in_needs_rehash() -> None:
    assert needs_rehash("esto-no-es-un-hash") is False

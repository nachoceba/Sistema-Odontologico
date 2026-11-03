"""Hash de contrasenas (spec seed-data: contrasena guardada solo como hash, P-5)."""

from __future__ import annotations

from argon2 import PasswordHasher

from app.core.security import hash_password

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

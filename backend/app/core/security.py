"""Seguridad de contrasenas: solo el hash (C-02, P-5). La verificacion y el JWT son de C-03."""

from __future__ import annotations

from argon2 import PasswordHasher

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    """Hash argon2 (con sal aleatoria) de una contrasena; nunca se guarda el texto plano."""
    return _hasher.hash(plain)

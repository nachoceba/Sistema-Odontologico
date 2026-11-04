"""Reglas puras de la gestion de usuarios (design D-1)."""

from __future__ import annotations

from app.domain.auth.types import Role
from app.domain.users.errors import RoleChangeNotAllowedError, SelfModificationError
from app.domain.users.types import NewProfessional

EMAIL_MIN_LENGTH = 3
EMAIL_MAX_LENGTH = 254


def normalize_email(text: str) -> str:
    """El email recortado y en minusculas (DD-38: unico sin distinguir mayusculas)."""
    return text.strip().lower()


def is_valid_email(text: str) -> bool:
    """3 a 254 caracteres, un unico ``@``, sin espacios y con texto a ambos lados."""
    if not EMAIL_MIN_LENGTH <= len(text) <= EMAIL_MAX_LENGTH:
        return False
    if any(char.isspace() for char in text):
        return False
    local, separator, domain = text.partition("@")
    return bool(separator) and bool(local) and bool(domain) and "@" not in domain


def check_role_change(current: Role, new: Role, *, is_self: bool) -> None:
    """P-4 y P-5: un odontologo conserva su rol y nadie cambia el suyo propio.

    Entre administrador y recepcion el cambio es libre; de ellos a odontologo tambien (el
    repositorio crea la ficha). Enviar el mismo rol no es un cambio.
    """
    if new is current:
        return
    if is_self:
        raise SelfModificationError
    if current is Role.DENTIST:
        raise RoleChangeNotAllowedError


def check_can_deactivate(*, is_self: bool) -> None:
    """P-5: el administrador no desactiva su propia cuenta."""
    if is_self:
        raise SelfModificationError


def professional_for_new_dentist(
    full_name: str, display_name: str | None, license_number: str | None
) -> NewProfessional:
    """P-10: sin nombre a mostrar se usa el nombre completo; matricula vacia queda en None."""
    shown = (display_name or "").strip()
    license_text = (license_number or "").strip()
    return NewProfessional(
        display_name=shown or full_name,
        license_number=license_text or None,
    )

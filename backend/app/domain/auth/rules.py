"""Reglas puras de acceso (RN-AU-04: el odontologo solo accede a lo propio)."""

from __future__ import annotations

import uuid

from app.domain.auth.types import Principal, Role


def _normalize(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None


def can_access_professional(principal: Principal, professional_id: str) -> bool:
    """Admin y recepcion acceden a cualquier profesional; el odontologo solo a su ficha.

    Un odontologo sin ficha o un id mal formado nunca coinciden: se niega sin error.
    """
    if principal.role is not Role.DENTIST:
        return True
    if principal.professional_id is None:
        return False
    own = _normalize(principal.professional_id)
    requested = _normalize(professional_id)
    return own is not None and own == requested

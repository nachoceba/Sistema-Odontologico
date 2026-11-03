"""Conversion de identificadores del dominio (``str``) a UUID de la base."""

from __future__ import annotations

import uuid


def parse_uuid(value: str) -> uuid.UUID | None:
    """El UUID, o ``None`` si el texto no tiene ese formato (por ejemplo ``no-existe``)."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None

"""Validadores de Pydantic compartidos por los esquemas de la API."""

from __future__ import annotations


def strip_text(value: object) -> object:
    """Recorta los espacios de un texto; cualquier otro valor pasa igual y lo valida Pydantic."""
    return value.strip() if isinstance(value, str) else value

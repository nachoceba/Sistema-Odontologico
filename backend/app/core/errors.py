"""Familia comun de errores de dominio. Solo libreria estandar (regla dura 2).

Cada error expone un ``code`` estable en mayusculas que la API traduce a un
estado HTTP (``app/api/errors.py``). Los errores de programacion del llamador
siguen siendo ``ValueError`` (DD-18) y no pertenecen a esta familia.
"""

from __future__ import annotations

from typing import ClassVar


class DomainError(Exception):
    """Base de los errores de negocio; las subclases definen su propio ``code``."""

    code: ClassVar[str] = "DOMAIN_ERROR"

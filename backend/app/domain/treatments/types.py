"""Tipos del catalogo de tratamientos (C-17). Solo libreria estandar."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Treatment:
    """Tratamiento del catalogo, tal como lo lee el repositorio."""

    id: str
    name: str
    active: bool


@dataclass(frozen=True)
class NewTreatment:
    """Entrada de ``add``: el nombre ya limpio por ``clean_treatment_name``."""

    name: str

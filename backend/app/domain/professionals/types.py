"""Ficha de profesional tal como la lee el repositorio (C-04, design D-8)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Professional:
    id: str
    user_id: str
    display_name: str
    license_number: str | None
    active: bool

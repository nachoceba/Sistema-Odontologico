"""Repositorio de profesionales en memoria: lee las fichas del repositorio de cuentas (D-8)."""

from __future__ import annotations

from app.domain.professionals import Professional
from app.infrastructure.in_memory.users import InMemoryUserAccountRepository


class InMemoryProfessionalRepository:
    def __init__(self, accounts: InMemoryUserAccountRepository) -> None:
        # Comparte el almacen de fichas con las cuentas para que ambos sean coherentes.
        self._accounts = accounts

    def list(self, *, only_active: bool = False) -> list[Professional]:
        professionals = [
            p for p in self._accounts.professionals.values() if p.active or not only_active
        ]
        return sorted(professionals, key=lambda p: p.display_name.lower())

    def get_by_id(self, professional_id: str) -> Professional | None:
        return self._accounts.professionals.get(professional_id)

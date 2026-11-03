"""Repositorio de cuentas en memoria (solo lectura para el login; ``add`` es para tests)."""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.auth import UserAccount


class InMemoryUserAccountRepository:
    def __init__(self, initial: Iterable[UserAccount] = ()) -> None:
        self._accounts: dict[str, UserAccount] = {}
        for account in initial:
            self.add(account)

    def add(self, account: UserAccount) -> None:
        self._accounts[account.id] = account

    def get_by_email(self, email: str) -> UserAccount | None:
        wanted = email.lower()
        for account in self._accounts.values():
            if account.email.lower() == wanted:
                return account
        return None

    def get_by_id(self, user_id: str) -> UserAccount | None:
        return self._accounts.get(user_id)

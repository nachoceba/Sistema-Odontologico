"""Repositorio de cuentas en memoria: doble de prueba del puerto, con fichas de profesional.

Guarda tambien las fichas para emular la transaccion cuenta + ficha (design D-2, D-3). ``add`` es
un atajo de fixtures. La falla de la ficha se simula como PostgreSQL: un NUL en un texto se rechaza.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import replace

from app.domain.auth import UserAccount
from app.domain.professionals import Professional
from app.domain.users.errors import EmailTakenError, UserNotFoundError
from app.domain.users.types import AccountChanges, NewAccount, NewProfessional


def _check_storable(professional: NewProfessional) -> None:
    for text in (professional.display_name, professional.license_number or ""):
        if "\x00" in text:
            raise ValueError("Los textos no pueden contener el caracter NUL")


class InMemoryUserAccountRepository:
    def __init__(self, initial: Iterable[UserAccount] = ()) -> None:
        self._accounts: dict[str, UserAccount] = {}
        self.professionals: dict[str, Professional] = {}
        for account in initial:
            self.add(account)

    def add(self, account: UserAccount) -> None:
        self._accounts[account.id] = account
        if (
            account.professional_id is not None
            and account.professional_id not in self.professionals
        ):
            self.professionals[account.professional_id] = Professional(
                id=account.professional_id,
                user_id=account.id,
                display_name=account.full_name,
                license_number=None,
                active=account.active,
            )

    def get_by_email(self, email: str) -> UserAccount | None:
        wanted = email.lower()
        for account in self._accounts.values():
            if account.email.lower() == wanted:
                return account
        return None

    def get_by_id(self, user_id: str) -> UserAccount | None:
        return self._accounts.get(user_id)

    def list_all(self) -> list[UserAccount]:
        return sorted(self._accounts.values(), key=lambda account: account.full_name.lower())

    def create(self, account: NewAccount) -> UserAccount:
        if self.get_by_email(account.email) is not None:
            raise EmailTakenError
        if account.professional is not None:
            _check_storable(account.professional)
        user_id = str(uuid.uuid4())
        professional_id: str | None = None
        if account.professional is not None:
            professional_id = self._new_professional(user_id, account.professional)
        created = UserAccount(
            id=user_id,
            email=account.email,
            full_name=account.full_name,
            password_hash=account.password_hash,
            role=account.role,
            active=True,
            professional_id=professional_id,
        )
        self._accounts[user_id] = created
        return created

    def update(self, user_id: str, changes: AccountChanges) -> UserAccount:
        current = self._accounts.get(user_id)
        if current is None:
            raise UserNotFoundError
        if changes.email is not None:
            other = self.get_by_email(changes.email)
            if other is not None and other.id != current.id:
                raise EmailTakenError
        if changes.new_professional is not None:
            _check_storable(changes.new_professional)

        professional_id = current.professional_id
        if changes.new_professional is not None and professional_id is None:
            professional_id = self._new_professional(current.id, changes.new_professional)
        active = current.active if changes.active is None else changes.active
        if professional_id is not None and professional_id in self.professionals:
            self.professionals[professional_id] = replace(
                self.professionals[professional_id], active=active
            )
        updated = UserAccount(
            id=current.id,
            email=current.email if changes.email is None else changes.email,
            full_name=current.full_name if changes.full_name is None else changes.full_name,
            password_hash=(
                current.password_hash if changes.password_hash is None else changes.password_hash
            ),
            role=current.role if changes.role is None else changes.role,
            active=active,
            professional_id=professional_id,
        )
        self._accounts[user_id] = updated
        return updated

    def _new_professional(self, user_id: str, data: NewProfessional) -> str:
        professional_id = str(uuid.uuid4())
        self.professionals[professional_id] = Professional(
            id=professional_id,
            user_id=user_id,
            display_name=data.display_name,
            license_number=data.license_number,
            active=True,
        )
        return professional_id

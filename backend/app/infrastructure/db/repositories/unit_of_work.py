"""Unidad de trabajo de la agenda sobre PostgreSQL (design D-2, DD-36).

Una sola sesion y una sola transaccion para los repositorios de turnos y de notificaciones: al
salir del bloque ``with`` sin excepcion se confirma todo; con una excepcion se revierte todo.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.repositories.appointments import SqlAlchemyAppointmentRepository
from app.infrastructure.db.repositories.notifications import SqlAlchemyNotificationRepository
from app.infrastructure.db.scope import SessionScope


class SqlAlchemyAgendaUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        # La sesion no abre conexion hasta la primera consulta.
        self._session = session_factory()
        scope = SessionScope(shared=self._session)
        self.appointments = SqlAlchemyAppointmentRepository(scope=scope)
        self.notifications = SqlAlchemyNotificationRepository(scope=scope)

    def __enter__(self) -> SqlAlchemyAgendaUnitOfWork:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                self._session.commit()
            else:
                self._session.rollback()
        finally:
            self._session.close()

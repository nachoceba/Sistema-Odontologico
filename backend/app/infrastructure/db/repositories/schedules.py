"""Repositorios de horarios y licencias sobre PostgreSQL (design D-6, D-7)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.appointments.ranges import require_time_off_range
from app.domain.appointments.types import WorkingHours
from app.domain.schedules.types import TimeOffEntry
from app.infrastructure.db.models import TimeOffModel, WorkingHoursModel
from app.infrastructure.db.repositories._ids import parse_uuid


class SqlAlchemyWorkingHoursRepository:
    """No valida los tramos: el caso de uso llama antes a ``validate_working_hours`` (C-05d D-8)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_for_professional(self, professional_id: str) -> list[WorkingHours]:
        key = parse_uuid(professional_id)
        if key is None:
            return []
        query = (
            select(WorkingHoursModel)
            .where(WorkingHoursModel.professional_id == key)
            .order_by(WorkingHoursModel.weekday, WorkingHoursModel.start_time)
        )
        with self._session_factory() as session:
            return [
                WorkingHours(weekday=r.weekday, start_time=r.start_time, end_time=r.end_time)
                for r in session.scalars(query)
            ]

    def replace_for_professional(
        self, professional_id: str, blocks: Sequence[WorkingHours]
    ) -> None:
        """DELETE + INSERT en una sola transaccion: o queda el conjunto nuevo o el anterior."""
        key = parse_uuid(professional_id)
        if key is None:
            raise ValueError("identificador de profesional invalido")
        with self._session_factory.begin() as session:
            session.execute(
                delete(WorkingHoursModel).where(WorkingHoursModel.professional_id == key)
            )
            session.add_all(
                WorkingHoursModel(
                    professional_id=key,
                    weekday=block.weekday,
                    start_time=block.start_time,
                    end_time=block.end_time,
                )
                for block in blocks
            )


class SqlAlchemyTimeOffRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def add(
        self,
        professional_id: str,
        starts_on: date,
        ends_on: date,
        reason: str | None = None,
    ) -> TimeOffEntry:
        require_time_off_range(starts_on, ends_on)
        key = parse_uuid(professional_id)
        if key is None:
            raise ValueError("identificador de profesional invalido")
        row = TimeOffModel(professional_id=key, starts_on=starts_on, ends_on=ends_on, reason=reason)
        with self._session_factory.begin() as session:
            session.add(row)
            session.flush()
            return _to_entry(row)

    def list_for_professional(self, professional_id: str) -> list[TimeOffEntry]:
        key = parse_uuid(professional_id)
        if key is None:
            return []
        query = (
            select(TimeOffModel)
            .where(TimeOffModel.professional_id == key)
            .order_by(TimeOffModel.starts_on, TimeOffModel.ends_on)
        )
        with self._session_factory() as session:
            return [_to_entry(r) for r in session.scalars(query)]

    def delete(self, professional_id: str, time_off_id: str) -> bool:
        professional_key = parse_uuid(professional_id)
        entry_key = parse_uuid(time_off_id)
        if professional_key is None or entry_key is None:
            return False
        statement = (
            delete(TimeOffModel)
            .where(TimeOffModel.id == entry_key, TimeOffModel.professional_id == professional_key)
            .returning(TimeOffModel.id)
        )
        with self._session_factory.begin() as session:
            return session.scalars(statement).first() is not None


def _to_entry(row: TimeOffModel) -> TimeOffEntry:
    return TimeOffEntry(
        id=str(row.id),
        professional_id=str(row.professional_id),
        starts_on=row.starts_on,
        ends_on=row.ends_on,
        reason=row.reason,
    )

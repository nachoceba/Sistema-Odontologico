"""Repositorio de turnos sobre PostgreSQL (design D-6, D-7).

La barrera real contra la superposicion es el constraint de exclusion
``ex_appointments_no_overlap`` (regla dura 3 y 6): este repositorio no consulta antes, escribe y
traduce el rechazo de la base (SQLSTATE 23P01) a ``SlotTakenError``. Cada operacion corre en su
propia transaccion (DD-36). Valida en Python, antes de tocar la base, lo mismo que el repositorio
en memoria (rangos con zona e inicio < fin), con las mismas funciones.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from psycopg import errors as pg_errors
from sqlalchemy import ColumnElement, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import InstrumentedAttribute, Session, sessionmaker

from app.domain.appointments.errors import AppointmentNotFoundError, SlotTakenError
from app.domain.appointments.ranges import require_query_range, require_range
from app.domain.appointments.types import Appointment, AppointmentStatus, NewAppointment
from app.domain.public_booking.rules import can_confirm
from app.infrastructure.db.models import AppointmentModel
from app.infrastructure.db.repositories._ids import parse_uuid
from app.infrastructure.db.scope import SessionScope


def _to_domain(row: AppointmentModel) -> Appointment:
    """Fila -> tipo de dominio; los instantes salen en UTC."""
    return Appointment(
        id=str(row.id),
        patient_id=str(row.patient_id),
        professional_id=str(row.professional_id),
        starts_at=row.starts_at.astimezone(UTC),
        ends_at=row.ends_at.astimezone(UTC),
        status=row.status,
        cancel_reason=row.cancel_reason,
        created_by=None if row.created_by is None else str(row.created_by),
        pending_until=None if row.pending_until is None else row.pending_until.astimezone(UTC),
    )


def _required_uuid(value: str, what: str) -> uuid.UUID:
    key = parse_uuid(value)
    if key is None:
        raise ValueError(f"identificador de {what} invalido")
    return key


def _flush_or_slot_taken(session: Session, row: AppointmentModel) -> None:
    """Escribe y traduce el rechazo del constraint de exclusion a ``SlotTakenError``.

    Dos escrituras simultaneas del mismo horario pueden terminar de dos maneras: una falla con
    SQLSTATE 23P01 (violacion de exclusion) o, si cada una espera a la otra mientras verifica el
    constraint, PostgreSQL aborta una por deadlock (SQLSTATE 40P01). En los dos casos otra
    escritura se quedo con el horario, asi que ambos son ``SlotTakenError``. Cualquier otro error
    se propaga: es un error de programacion o de datos. Al salir de ``begin()`` con una excepcion
    se hace rollback (todo o nada).
    """
    # Se leen antes del flush: si falla, la sesion expira los objetos y ya no se pueden leer.
    professional_id = str(row.professional_id)
    starts_at = row.starts_at.astimezone(UTC)
    try:
        session.flush()
    except IntegrityError as error:
        if isinstance(error.orig, pg_errors.ExclusionViolation):
            raise SlotTakenError(professional_id, starts_at) from error
        raise
    except DBAPIError as error:
        if isinstance(error.orig, pg_errors.DeadlockDetected):
            raise SlotTakenError(professional_id, starts_at) from error
        raise


class SqlAlchemyAppointmentRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        scope: SessionScope | None = None,
    ) -> None:
        # Sin alcance propio, cada operacion abre su transaccion (DD-36); dentro de una unidad
        # de trabajo la sesion es compartida y la confirma la unidad (D-2).
        self._scope = scope if scope is not None else SessionScope(session_factory)

    def add(self, new: NewAppointment) -> Appointment:
        require_range(new.starts_at, new.ends_at)
        if new.created_by is None:
            raise ValueError("el turno de recepcion necesita un usuario creador")
        row = AppointmentModel(
            patient_id=_required_uuid(new.patient_id, "paciente"),
            professional_id=_required_uuid(new.professional_id, "profesional"),
            starts_at=new.starts_at,
            ends_at=new.ends_at,
            status=AppointmentStatus.SCHEDULED,
            created_by=_required_uuid(new.created_by, "usuario"),
        )
        with self._scope.write() as session:
            session.add(row)
            _flush_or_slot_taken(session, row)
            return _to_domain(row)

    def add_pending(
        self, new: NewAppointment, token_hash: str, pending_until: datetime
    ) -> Appointment:
        require_range(new.starts_at, new.ends_at)
        if new.created_by is not None:
            raise ValueError("un turno pendiente no tiene usuario creador")
        row = AppointmentModel(
            patient_id=_required_uuid(new.patient_id, "paciente"),
            professional_id=_required_uuid(new.professional_id, "profesional"),
            starts_at=new.starts_at,
            ends_at=new.ends_at,
            status=AppointmentStatus.SCHEDULED,
            created_by=None,
            pending_until=pending_until,
            confirmation_token_hash=token_hash,
        )
        with self._scope.write() as session:
            session.add(row)
            _flush_or_slot_taken(session, row)
            return _to_domain(row)

    def find_pending_by_token_hash(self, token_hash: str, now: datetime) -> Appointment | None:
        query = select(AppointmentModel).where(
            AppointmentModel.confirmation_token_hash == token_hash
        )
        with self._scope.read() as session:
            row = session.scalars(query).first()
            if row is None:
                return None
            appointment = _to_domain(row)
            return appointment if can_confirm(appointment, now) else None

    def confirm_by_token_hash(self, token_hash: str, now: datetime) -> Appointment | None:
        query = (
            select(AppointmentModel)
            .where(AppointmentModel.confirmation_token_hash == token_hash)
            .with_for_update()
        )
        with self._scope.write() as session:
            row = session.scalars(query).first()
            if row is None or not can_confirm(_to_domain(row), now):
                return None
            row.pending_until = None
            row.confirmation_token_hash = None
            session.flush()
            return _to_domain(row)

    def get(self, appointment_id: str) -> Appointment | None:
        key = parse_uuid(appointment_id)
        if key is None:
            return None
        with self._scope.read() as session:
            row = session.get(AppointmentModel, key)
            return None if row is None else _to_domain(row)

    def change_status(
        self,
        appointment_id: str,
        status: AppointmentStatus,
        cancel_reason: str | None = None,
    ) -> Appointment:
        with self._scope.write() as session:
            row = self._locked(session, appointment_id)
            row.status = status
            row.cancel_reason = cancel_reason
            if status is AppointmentStatus.CANCELLED:
                row.pending_until = None
                row.confirmation_token_hash = None
            _flush_or_slot_taken(session, row)
            return _to_domain(row)

    def reschedule(
        self, appointment_id: str, starts_at: datetime, ends_at: datetime
    ) -> Appointment:
        with self._scope.write() as session:
            row = self._locked(session, appointment_id)
            require_range(starts_at, ends_at)
            row.starts_at = starts_at
            row.ends_at = ends_at
            _flush_or_slot_taken(session, row)
            return _to_domain(row)

    def list_for_professional(
        self, professional_id: str, start: datetime, end: datetime | None = None
    ) -> list[Appointment]:
        return self._list(AppointmentModel.professional_id, professional_id, start, end)

    def list_for_patient(
        self, patient_id: str, start: datetime, end: datetime | None = None
    ) -> list[Appointment]:
        return self._list(AppointmentModel.patient_id, patient_id, start, end)

    def list_scheduled_starting_between(self, start: datetime, end: datetime) -> list[Appointment]:
        require_query_range(start, end)
        query = (
            select(AppointmentModel)
            .where(
                AppointmentModel.status == AppointmentStatus.SCHEDULED,
                AppointmentModel.pending_until.is_(None),
                AppointmentModel.starts_at >= start,
                AppointmentModel.starts_at < end,
            )
            .order_by(AppointmentModel.starts_at, AppointmentModel.id)
        )
        with self._scope.read() as session:
            return [_to_domain(row) for row in session.scalars(query)]

    # --- internos ---------------------------------------------------------------

    @staticmethod
    def _locked(session: Session, appointment_id: str) -> AppointmentModel:
        """El turno con bloqueo de fila; un id inexistente o mal formado es 'no encontrado'."""
        key = parse_uuid(appointment_id)
        row = None if key is None else session.get(AppointmentModel, key, with_for_update=True)
        if row is None:
            raise AppointmentNotFoundError(appointment_id)
        return row

    def _list(
        self,
        owner: InstrumentedAttribute[uuid.UUID],
        owner_id: str,
        start: datetime,
        end: datetime | None,
    ) -> list[Appointment]:
        require_query_range(start, end)
        key = parse_uuid(owner_id)
        if key is None:
            return []
        conditions: list[ColumnElement[bool]] = [owner == key, AppointmentModel.ends_at > start]
        if end is not None:
            conditions.append(AppointmentModel.starts_at < end)
        query = select(AppointmentModel).where(*conditions).order_by(AppointmentModel.starts_at)
        with self._scope.read() as session:
            return [_to_domain(row) for row in session.scalars(query)]

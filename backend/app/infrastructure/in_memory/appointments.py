"""Repositorio de turnos en memoria: doble fiel del constraint de exclusion (D-5).

No es seguro entre hilos ni lo conecta produccion; sirve para tests de aplicacion.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from uuid import uuid4

from app.domain.appointments.errors import AppointmentNotFoundError, SlotTakenError
from app.domain.appointments.ranges import require_query_range, require_range
from app.domain.appointments.rules import overlaps_scheduled, ranges_overlap
from app.domain.appointments.types import (
    Appointment,
    AppointmentStatus,
    NewAppointment,
)
from app.domain.public_booking.rules import EXPIRED_BOOKING_REASON, can_confirm


def _touches_range(appointment: Appointment, start: datetime, end: datetime | None) -> bool:
    if end is None:
        return appointment.ends_at > start
    return ranges_overlap(appointment.starts_at, appointment.ends_at, start, end)


class InMemoryAppointmentRepository:
    def __init__(self) -> None:
        self._appointments: dict[str, Appointment] = {}
        self._token_hashes: dict[str, str] = {}  # turno -> hash; nunca sale en el Appointment

    def snapshot(self) -> tuple[dict[str, Appointment], dict[str, str]]:
        """Copia del estado, para que la unidad de trabajo pueda revertir."""
        return dict(self._appointments), dict(self._token_hashes)

    def restore(self, state: tuple[dict[str, Appointment], dict[str, str]]) -> None:
        self._appointments = dict(state[0])
        self._token_hashes = dict(state[1])

    def add_pending(
        self, new: NewAppointment, token_hash: str, pending_until: datetime
    ) -> Appointment:
        require_range(new.starts_at, new.ends_at)
        if new.created_by is not None:
            raise ValueError("un turno pendiente no tiene usuario creador")
        if token_hash in self._token_hashes.values():
            raise ValueError("hash de token repetido")
        saved = Appointment(
            id=str(uuid4()),
            patient_id=new.patient_id,
            professional_id=new.professional_id,
            starts_at=new.starts_at,
            ends_at=new.ends_at,
            status=AppointmentStatus.SCHEDULED,
            cancel_reason=None,
            created_by=None,
            pending_until=pending_until,
        )
        self._store(saved)
        self._token_hashes[saved.id] = token_hash
        return saved

    def find_pending_by_token_hash(self, token_hash: str, now: datetime) -> Appointment | None:
        appointment_id = next((k for k, v in self._token_hashes.items() if v == token_hash), None)
        if appointment_id is None:
            return None
        current = self._appointments[appointment_id]
        return current if can_confirm(current, now) else None

    def confirm_by_token_hash(self, token_hash: str, now: datetime) -> Appointment | None:
        appointment_id = next((k for k, v in self._token_hashes.items() if v == token_hash), None)
        if appointment_id is None:
            return None
        current = self._appointments[appointment_id]
        if not can_confirm(current, now):
            return None
        confirmed = replace(current, pending_until=None)
        self._appointments[appointment_id] = confirmed
        del self._token_hashes[appointment_id]
        return confirmed

    def expire_pending(self, now: datetime, limit: int = 200) -> list[Appointment]:
        due = sorted(
            (
                a
                for a in self._appointments.values()
                if a.status is AppointmentStatus.SCHEDULED
                and a.pending_until is not None
                and a.pending_until <= now
            ),
            key=lambda a: (a.pending_until, a.id),
        )
        expired: list[Appointment] = []
        for current in due[:limit]:
            self._appointments[current.id] = replace(
                current,
                status=AppointmentStatus.CANCELLED,
                cancel_reason=EXPIRED_BOOKING_REASON,
                pending_until=None,
            )
            self._token_hashes.pop(current.id, None)
            expired.append(current)
        return expired

    def add(self, new: NewAppointment) -> Appointment:
        require_range(new.starts_at, new.ends_at)
        saved = Appointment(
            id=str(uuid4()),
            patient_id=new.patient_id,
            professional_id=new.professional_id,
            starts_at=new.starts_at,
            ends_at=new.ends_at,
            status=AppointmentStatus.SCHEDULED,
            cancel_reason=None,
            created_by=new.created_by,
        )
        self._store(saved)
        return saved

    def get(self, appointment_id: str) -> Appointment | None:
        return self._appointments.get(appointment_id)

    def change_status(
        self,
        appointment_id: str,
        status: AppointmentStatus,
        cancel_reason: str | None = None,
    ) -> Appointment:
        current = self._existing(appointment_id)
        updated = replace(current, status=status, cancel_reason=cancel_reason)
        if status is AppointmentStatus.CANCELLED:
            updated = replace(updated, pending_until=None)
            self._token_hashes.pop(appointment_id, None)
        self._store(updated)
        return updated

    def reschedule(
        self, appointment_id: str, starts_at: datetime, ends_at: datetime
    ) -> Appointment:
        current = self._existing(appointment_id)
        require_range(starts_at, ends_at)
        updated = replace(current, starts_at=starts_at, ends_at=ends_at)
        self._store(updated)
        return updated

    def list_for_professional(
        self, professional_id: str, start: datetime, end: datetime | None = None
    ) -> list[Appointment]:
        return self._list(lambda a: a.professional_id == professional_id, start, end)

    def list_for_patient(
        self, patient_id: str, start: datetime, end: datetime | None = None
    ) -> list[Appointment]:
        return self._list(lambda a: a.patient_id == patient_id, start, end)

    def list_scheduled_starting_between(self, start: datetime, end: datetime) -> list[Appointment]:
        require_query_range(start, end)
        matches = [
            a
            for a in self._appointments.values()
            if a.status is AppointmentStatus.SCHEDULED
            and a.pending_until is None
            and start <= a.starts_at < end
        ]
        return sorted(matches, key=lambda a: (a.starts_at, a.id))

    def _existing(self, appointment_id: str) -> Appointment:
        current = self._appointments.get(appointment_id)
        if current is None:
            raise AppointmentNotFoundError(appointment_id)
        return current

    def _store(self, candidate: Appointment) -> None:
        """Valida contra los demas scheduled y recien despues escribe (regla dura 6)."""
        if candidate.status == AppointmentStatus.SCHEDULED:
            others = [
                other.to_existing()
                for other in self._appointments.values()
                if other.id != candidate.id
            ]
            if overlaps_scheduled(
                candidate.professional_id,
                candidate.starts_at,
                candidate.ends_at,
                others,
            ):
                raise SlotTakenError(candidate.professional_id, candidate.starts_at)
        self._appointments[candidate.id] = candidate

    def _list(
        self,
        belongs: Callable[[Appointment], bool],
        start: datetime,
        end: datetime | None,
    ) -> list[Appointment]:
        require_query_range(start, end)
        matches = [
            a for a in self._appointments.values() if belongs(a) and _touches_range(a, start, end)
        ]
        return sorted(matches, key=lambda a: a.starts_at)

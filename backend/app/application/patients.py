"""Casos de uso de pacientes (C-06, design D-4; sin FastAPI ni SQLAlchemy).

Orden de cada escritura: rol (defensa en profundidad, RN-PR-02) -> existe -> validar ->
guardar. El reloj llega como dato (``PatientDeps.clock``). Ningun caso de uso crea, mueve ni
cancela turnos: la agenda sigue siendo de C-08 (regla dura 6).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.core.timezone import to_local
from app.domain.appointments import Appointment, AppointmentStatus
from app.domain.appointments.errors import PatientNotFoundError
from app.domain.appointments.ports import AppointmentRepository
from app.domain.auth import ForbiddenError, Principal, Role
from app.domain.patients.errors import PatientHasAppointmentsError
from app.domain.patients.ports import PatientRepository
from app.domain.patients.rules import (
    check_birth_date,
    clean_email,
    clean_name,
    clean_phone,
    normalize_document,
)
from app.domain.patients.types import NewPatient, PatientChanges, PatientRecord
from app.domain.professionals import UNSET, Unset
from app.domain.settings.ports import ClinicSettingsRepository

MAX_SEARCH_RESULTS = 50

_READERS = frozenset({Role.ADMIN, Role.RECEPTIONIST, Role.DENTIST})
_WRITERS = frozenset({Role.ADMIN, Role.RECEPTIONIST})
_DELETERS = frozenset({Role.ADMIN})
_EARLIEST = datetime(1970, 1, 1, tzinfo=UTC)  # ningun turno es anterior


@dataclass(frozen=True)
class PatientDeps:
    """Puertos y reloj de los casos de uso de pacientes."""

    patients: PatientRepository
    appointments: AppointmentRepository
    settings: ClinicSettingsRepository
    clock: Callable[[], datetime]


@dataclass(frozen=True)
class PatientSearchResult:
    """Hasta ``MAX_SEARCH_RESULTS`` pacientes y si habia mas coincidencias."""

    items: list[PatientRecord]
    truncated: bool


def _require(principal: Principal, allowed: frozenset[Role]) -> None:
    if principal.role not in allowed:
        raise ForbiddenError


def search_patients(
    deps: PatientDeps,
    principal: Principal,
    *,
    text: str | None = None,
    include_inactive: bool = False,
) -> PatientSearchResult:
    """Busca por apellido o inicio de documento; pide uno de mas para saber si hay mas."""
    _require(principal, _READERS)
    found = deps.patients.search(
        text=(text or "").strip(),
        include_inactive=include_inactive,
        limit=MAX_SEARCH_RESULTS + 1,
    )
    return PatientSearchResult(
        items=found[:MAX_SEARCH_RESULTS], truncated=len(found) > MAX_SEARCH_RESULTS
    )


def get_patient(deps: PatientDeps, principal: Principal, patient_id: str) -> PatientRecord:
    _require(principal, _READERS)
    record = deps.patients.get_record(patient_id)
    if record is None:
        raise PatientNotFoundError
    return record


def _clinic_today(deps: PatientDeps) -> date:
    """El dia de hoy en la zona del consultorio (RN-GL-01), con el reloj inyectado."""
    return to_local(deps.clock(), deps.settings.get().timezone).date()


def create_patient(
    deps: PatientDeps,
    principal: Principal,
    *,
    first_name: str,
    last_name: str,
    document_number: str,
    email: str,
    phone: str | None = None,
    birth_date: date | None = None,
) -> PatientRecord:
    """Alta activa (RN-PA-01, RN-PA-02); ``ValueError`` si un texto no cumple las reglas."""
    _require(principal, _WRITERS)
    new = NewPatient(
        first_name=clean_name(first_name),
        last_name=clean_name(last_name),
        document_number=normalize_document(document_number),
        email=clean_email(email),
        phone=None if phone is None else clean_phone(phone),
        birth_date=birth_date,
    )
    if birth_date is not None:
        check_birth_date(birth_date, today=_clinic_today(deps))
    return deps.patients.add(new)


def update_patient(
    deps: PatientDeps,
    principal: Principal,
    patient_id: str,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    document_number: str | None = None,
    email: str | None = None,
    phone: str | None | Unset = UNSET,
    birth_date: date | None | Unset = UNSET,
) -> PatientRecord:
    """Cambia solo lo enviado (P-9), tambien en pacientes inactivos; ``None``/``UNSET`` aparte."""
    _require(principal, _WRITERS)
    if deps.patients.get_record(patient_id) is None:
        raise PatientNotFoundError
    if isinstance(birth_date, date):
        check_birth_date(birth_date, today=_clinic_today(deps))
    changes = PatientChanges(
        first_name=None if first_name is None else clean_name(first_name),
        last_name=None if last_name is None else clean_name(last_name),
        document_number=None if document_number is None else normalize_document(document_number),
        email=None if email is None else clean_email(email),
        phone=phone if phone is None or isinstance(phone, Unset) else clean_phone(phone),
        birth_date=birth_date,
    )
    return deps.patients.update(patient_id, changes)


@dataclass(frozen=True)
class PatientDeactivation:
    """Paciente desactivado y sus turnos ``scheduled`` que todavia no empezaron."""

    patient: PatientRecord
    upcoming_appointments: list[Appointment]


def deactivate_patient(
    deps: PatientDeps, principal: Principal, patient_id: str
) -> PatientDeactivation:
    """RN-PA-03 y DD-25: desactiva sin cancelar ni mover turnos y lista los futuros (DD-23)."""
    _require(principal, _WRITERS)
    patient = deps.patients.set_active(patient_id, False)
    now = deps.clock()
    upcoming = [
        appointment
        for appointment in deps.appointments.list_for_patient(patient_id, now)
        if appointment.status is AppointmentStatus.SCHEDULED and appointment.starts_at > now
    ]
    upcoming.sort(key=lambda appointment: appointment.starts_at)
    return PatientDeactivation(patient=patient, upcoming_appointments=upcoming)


def reactivate_patient(deps: PatientDeps, principal: Principal, patient_id: str) -> PatientRecord:
    """Vuelve a permitir turnos nuevos; no cambia ningun turno."""
    _require(principal, _WRITERS)
    return deps.patients.set_active(patient_id, True)


def delete_patient(deps: PatientDeps, principal: Principal, patient_id: str) -> None:
    """Solo el administrador, y solo sin turnos en ningun estado (RN-PA-03, DD-75).

    La verificacion previa cubre la memoria (donde el repositorio de pacientes no conoce los
    turnos); en PostgreSQL la clave foranea es la ultima barrera.
    """
    _require(principal, _DELETERS)
    if deps.patients.get_record(patient_id) is None:
        raise PatientNotFoundError
    if deps.appointments.list_for_patient(patient_id, _EARLIEST):
        raise PatientHasAppointmentsError
    if not deps.patients.delete(patient_id):
        raise PatientNotFoundError

"""Casos de uso de fichas, horarios y licencias de profesionales (C-07, design D-3).

Sin FastAPI ni SQLAlchemy. Orden de cada escritura: permiso (solo administrador) ->
profesional existe -> validacion con el dominio -> guardar -> calcular conflictos
(lectura posterior, RN-HO-04). El reloj llega como dato (``ScheduleDeps.clock``).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime

from app.domain.appointments.errors import ProfessionalNotFoundError
from app.domain.appointments.ports import AppointmentRepository
from app.domain.appointments.types import TimeOff, WorkingHours
from app.domain.auth import ForbiddenError, Principal, Role, can_access_professional
from app.domain.professionals import UNSET, Professional, ProfessionalRepository, Unset
from app.domain.schedules import (
    TimeOffEntry,
    TimeOffRepository,
    WorkingHoursRepository,
    validate_time_off,
    validate_working_hours,
)
from app.domain.schedules.conflicts import ScheduleConflict, find_schedule_conflicts
from app.domain.schedules.errors import (
    InvalidTimeOffError,
    InvalidWorkingHoursError,
    TimeOffNotFoundError,
)
from app.domain.settings.ports import ClinicSettingsRepository

MAX_DISPLAY_NAME = 200
MAX_LICENSE_NUMBER = 50
MAX_TIME_OFF_REASON = 500


@dataclass(frozen=True)
class WorkingHoursSaved:
    """Horario guardado y turnos que quedaron en conflicto (sin tocarlos)."""

    blocks: list[WorkingHours]
    conflicts: list[ScheduleConflict]


@dataclass(frozen=True)
class TimeOffSaved:
    """Licencia guardada y turnos que quedaron en conflicto (sin tocarlos)."""

    time_off: TimeOffEntry
    conflicts: list[ScheduleConflict]


@dataclass(frozen=True)
class ScheduleDeps:
    """Puertos y reloj de los casos de uso de profesionales, horarios y licencias."""

    professionals: ProfessionalRepository
    working_hours: WorkingHoursRepository
    time_off: TimeOffRepository
    appointments: AppointmentRepository
    settings: ClinicSettingsRepository
    clock: Callable[[], datetime]


def _require_admin(principal: Principal) -> None:
    """DD-48 / RN-PR-02: solo el administrador escribe (defensa en profundidad)."""
    if principal.role is not Role.ADMIN:
        raise ForbiddenError


def _require_access(principal: Principal, professional_id: str) -> None:
    """RN-AU-04 / DD-53: el odontologo solo accede a su propia ficha."""
    if not can_access_professional(principal, professional_id):
        raise ForbiddenError


def _require_professional(deps: ScheduleDeps, professional_id: str) -> Professional:
    professional = deps.professionals.get_by_id(professional_id)
    if professional is None:
        raise ProfessionalNotFoundError
    return professional


def _conflicts(deps: ScheduleDeps, professional_id: str) -> list[ScheduleConflict]:
    """Turnos en conflicto con lo que hoy esta guardado (RN-HO-04); solo lee."""
    now = deps.clock()
    return find_schedule_conflicts(
        professional_id=professional_id,
        working_hours=deps.working_hours.list_for_professional(professional_id),
        time_off=[e.to_time_off() for e in deps.time_off.list_for_professional(professional_id)],
        appointments=deps.appointments.list_for_professional(professional_id, now),
        now=now,
        timezone=deps.settings.get().timezone,
    )


def _clean_text(value: str, maximum: int) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > maximum:
        raise ValueError(f"el texto debe tener de 1 a {maximum} caracteres")
    return cleaned


def list_professionals(deps: ScheduleDeps, principal: Principal) -> list[Professional]:
    """Todas las fichas (activas e inactivas); el odontologo ve solo la suya (P-7)."""
    professionals = deps.professionals.list()
    if principal.role is Role.DENTIST:
        return [p for p in professionals if can_access_professional(principal, p.id)]
    return professionals


def get_professional(
    deps: ScheduleDeps, principal: Principal, professional_id: str
) -> Professional:
    _require_access(principal, professional_id)
    return _require_professional(deps, professional_id)


def update_professional(
    deps: ScheduleDeps,
    principal: Principal,
    professional_id: str,
    *,
    display_name: str | None = None,
    license_number: str | None | Unset = UNSET,
) -> Professional:
    """Edita nombre a mostrar y matricula (P-8); ``None`` en la matricula la borra."""
    _require_admin(principal)
    cleaned_name = None if display_name is None else _clean_text(display_name, MAX_DISPLAY_NAME)
    cleaned_license = (
        license_number
        if license_number is None or isinstance(license_number, Unset)
        else _clean_text(license_number, MAX_LICENSE_NUMBER)
    )
    _require_professional(deps, professional_id)
    return deps.professionals.update(
        professional_id, display_name=cleaned_name, license_number=cleaned_license
    )


def get_working_hours(
    deps: ScheduleDeps, principal: Principal, professional_id: str
) -> list[WorkingHours]:
    _require_access(principal, professional_id)
    _require_professional(deps, professional_id)
    return deps.working_hours.list_for_professional(professional_id)


def replace_working_hours(
    deps: ScheduleDeps,
    principal: Principal,
    professional_id: str,
    blocks: Sequence[WorkingHours],
) -> WorkingHoursSaved:
    """Reemplaza la semana completa; guarda aunque queden turnos en conflicto (P-5)."""
    _require_admin(principal)
    _require_professional(deps, professional_id)
    result = validate_working_hours(blocks)
    if not result.valid:
        raise InvalidWorkingHoursError(result.problems)
    deps.working_hours.replace_for_professional(professional_id, blocks)
    return WorkingHoursSaved(
        blocks=deps.working_hours.list_for_professional(professional_id),
        conflicts=_conflicts(deps, professional_id),
    )


def list_time_off(
    deps: ScheduleDeps, principal: Principal, professional_id: str
) -> list[TimeOffEntry]:
    """Todas las licencias, tambien las pasadas, por fecha de inicio (DD-28)."""
    _require_access(principal, professional_id)
    _require_professional(deps, professional_id)
    return deps.time_off.list_for_professional(professional_id)


def add_time_off(
    deps: ScheduleDeps,
    principal: Principal,
    professional_id: str,
    starts_on: date,
    ends_on: date,
    reason: str | None = None,
) -> TimeOffSaved:
    """Carga una licencia (fechas locales inclusivas); motivo recortado, vacio = sin motivo."""
    _require_admin(principal)
    _require_professional(deps, professional_id)
    if not validate_time_off(TimeOff(starts_on, ends_on)).valid:
        raise InvalidTimeOffError
    cleaned = None if reason is None else reason.strip() or None
    if cleaned is not None and len(cleaned) > MAX_TIME_OFF_REASON:
        raise ValueError(f"el motivo no puede superar {MAX_TIME_OFF_REASON} caracteres")
    entry = deps.time_off.add(professional_id, starts_on, ends_on, cleaned)
    return TimeOffSaved(time_off=entry, conflicts=_conflicts(deps, professional_id))


def delete_time_off(
    deps: ScheduleDeps, principal: Principal, professional_id: str, time_off_id: str
) -> None:
    """Borra una licencia del profesional indicado (P-4); no existe o es de otro: no encontrada."""
    _require_admin(principal)
    _require_professional(deps, professional_id)
    if not deps.time_off.delete(professional_id, time_off_id):
        raise TimeOffNotFoundError


def list_conflicts(
    deps: ScheduleDeps, principal: Principal, professional_id: str
) -> list[ScheduleConflict]:
    """Turnos en conflicto calculados en el momento del pedido (P-1: no se guardan)."""
    _require_access(principal, professional_id)
    _require_professional(deps, professional_id)
    return _conflicts(deps, professional_id)

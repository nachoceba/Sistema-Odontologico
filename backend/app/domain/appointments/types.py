"""Tipos del dominio de turnos. Solo libreria estandar, sin ORM."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import Enum


class AppointmentStatus(Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class RejectionReason(Enum):
    INSUFFICIENT_NOTICE = "INSUFFICIENT_NOTICE"
    OFF_GRID = "OFF_GRID"
    OUTSIDE_WORKING_HOURS = "OUTSIDE_WORKING_HOURS"
    PROFESSIONAL_TIME_OFF = "PROFESSIONAL_TIME_OFF"
    OVERLAPS_EXISTING = "OVERLAPS_EXISTING"


@dataclass(frozen=True)
class WorkingHours:
    """Tramo de horario de trabajo en hora local. weekday: 0 = lunes ... 6 = domingo."""

    weekday: int
    start_time: time
    end_time: time


@dataclass(frozen=True)
class TimeOff:
    """Licencia por dias completos; fechas locales, ambas inclusivas."""

    starts_on: date
    ends_on: date


@dataclass(frozen=True)
class ExistingAppointment:
    professional_id: str
    starts_at: datetime  # UTC
    ends_at: datetime  # UTC
    status: AppointmentStatus


@dataclass(frozen=True)
class ValidationResult:
    """Aceptado <=> ends_at presente y reason ausente."""

    accepted: bool
    ends_at: datetime | None = None
    reason: RejectionReason | None = None

    @classmethod
    def accept(cls, ends_at: datetime) -> ValidationResult:
        return cls(accepted=True, ends_at=ends_at, reason=None)

    @classmethod
    def reject(cls, reason: RejectionReason) -> ValidationResult:
        return cls(accepted=False, ends_at=None, reason=reason)

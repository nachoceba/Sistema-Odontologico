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
class NewAppointment:
    """Entrada del repositorio: turno a guardar. Instantes con zona horaria."""

    patient_id: str
    professional_id: str
    starts_at: datetime
    ends_at: datetime
    created_by: str | None


@dataclass(frozen=True)
class Appointment:
    """Turno guardado, con identidad. Salida del repositorio (design D-3)."""

    id: str
    patient_id: str
    professional_id: str
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    cancel_reason: str | None
    created_by: str | None  # None: reserva online (C-15)
    pending_until: datetime | None = None  # no nulo: pendiente de confirmacion (C-15)

    def to_existing(self) -> ExistingAppointment:
        """Dato que consumen validate_appointment y compute_slots."""
        return ExistingAppointment(
            professional_id=self.professional_id,
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            status=self.status,
        )


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


class SlotStatus(Enum):
    FREE = "FREE"
    BUSY = "BUSY"
    OUTSIDE_HOURS = "OUTSIDE_HOURS"


@dataclass(frozen=True)
class Slot:
    """Franja del dia local de un profesional; inicio y fin en UTC (fin excluido)."""

    starts_at: datetime  # UTC
    ends_at: datetime  # UTC
    status: SlotStatus


class NotificationKind(Enum):
    """Mismos valores que el enumerado ``notification_kind`` de la base."""

    CONFIRMATION = "confirmation"
    REMINDER = "reminder"


class NotificationStatus(Enum):
    """Mismos valores que ``notification_status``; no hay estado "descartada" (DD-62)."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass(frozen=True)
class Notification:
    """Registro de un email de un turno (tabla ``email_notifications``)."""

    id: str
    appointment_id: str
    kind: NotificationKind
    status: NotificationStatus
    sent_at: datetime | None
    error: str | None
    appointment_starts_at: datetime  # UTC: el horario del turno al que corresponde

"""Errores de dominio del repositorio de turnos. Solo libreria estandar."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from app.core.errors import DomainError
from app.domain.appointments.transitions import TransitionRejection
from app.domain.appointments.types import RejectionReason


class SlotTakenError(DomainError):
    """El horario ya esta ocupado por otro turno scheduled del profesional."""

    code: ClassVar[str] = "SLOT_TAKEN"

    def __init__(self, professional_id: str, starts_at: datetime) -> None:
        super().__init__("Ese horario acaba de ocuparse. Elegí otro.")
        self.professional_id = professional_id
        self.starts_at = starts_at


class AppointmentNotFoundError(DomainError):
    """No existe un turno con ese identificador."""

    code: ClassVar[str] = "APPOINTMENT_NOT_FOUND"

    def __init__(self, appointment_id: str) -> None:
        super().__init__(f"{self.code}: {appointment_id}")
        self.appointment_id = appointment_id


class PatientNotFoundError(DomainError):
    code: ClassVar[str] = "PATIENT_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("El paciente no existe")


class ProfessionalNotFoundError(DomainError):
    code: ClassVar[str] = "PROFESSIONAL_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__("El profesional no existe")


class PatientInactiveError(DomainError):
    code: ClassVar[str] = "PATIENT_INACTIVE"

    def __init__(self) -> None:
        super().__init__("El paciente está desactivado y no puede recibir turnos")


class ProfessionalInactiveError(DomainError):
    code: ClassVar[str] = "PROFESSIONAL_INACTIVE"

    def __init__(self) -> None:
        super().__init__("El profesional está desactivado y no recibe turnos nuevos")


class PatientDoubleBookedError(DomainError):
    code: ClassVar[str] = "PATIENT_DOUBLE_BOOKED"

    def __init__(self) -> None:
        super().__init__("El paciente ya tiene otro turno en ese horario")


class RescheduleSameTimeError(DomainError):
    code: ClassVar[str] = "RESCHEDULE_SAME_TIME"

    def __init__(self) -> None:
        super().__init__("El turno ya está en ese horario")


class InsufficientNoticeError(DomainError):
    code: ClassVar[str] = "INSUFFICIENT_NOTICE"

    def __init__(self) -> None:
        super().__init__("El turno no cumple la anticipación mínima")


class OffGridError(DomainError):
    code: ClassVar[str] = "OFF_GRID"

    def __init__(self) -> None:
        super().__init__("El horario no coincide con los turnos del consultorio")


class OutsideWorkingHoursError(DomainError):
    code: ClassVar[str] = "OUTSIDE_WORKING_HOURS"

    def __init__(self) -> None:
        super().__init__("El horario está fuera del horario de trabajo del profesional")


class ProfessionalTimeOffError(DomainError):
    code: ClassVar[str] = "PROFESSIONAL_TIME_OFF"

    def __init__(self) -> None:
        super().__init__("El profesional tiene licencia ese día")


class CancelledIsFinalError(DomainError):
    code: ClassVar[str] = "CANCELLED_IS_FINAL"

    def __init__(self) -> None:
        super().__init__("El turno está cancelado y no se puede modificar")


class AttendanceAlreadyRecordedError(DomainError):
    code: ClassVar[str] = "ATTENDANCE_ALREADY_RECORDED"

    def __init__(self) -> None:
        super().__init__("La asistencia de este turno ya fue registrada")


class AlreadyStartedError(DomainError):
    code: ClassVar[str] = "ALREADY_STARTED"

    def __init__(self) -> None:
        super().__init__("El turno ya empezó")


class NotStartedYetError(DomainError):
    code: ClassVar[str] = "NOT_STARTED_YET"

    def __init__(self) -> None:
        super().__init__("El turno todavía no empezó")


def error_for_rejection(
    reason: RejectionReason, *, professional_id: str, starts_at: datetime
) -> DomainError:
    """Error de dominio de un motivo de validate_appointment (superposicion -> SLOT_TAKEN)."""
    if reason is RejectionReason.OVERLAPS_EXISTING:
        return SlotTakenError(professional_id, starts_at)
    return _REJECTION_ERRORS[reason]()


def error_for_transition(reason: TransitionRejection) -> DomainError:
    """Error de dominio de un TransitionRejection; INVALID_TARGET_STATUS es del llamador."""
    try:
        return _TRANSITION_ERRORS[reason]()
    except KeyError:
        raise ValueError(f"motivo de transicion sin error de caso de uso: {reason}") from None


_REJECTION_ERRORS: dict[RejectionReason, type[DomainError]] = {
    RejectionReason.INSUFFICIENT_NOTICE: InsufficientNoticeError,
    RejectionReason.OFF_GRID: OffGridError,
    RejectionReason.OUTSIDE_WORKING_HOURS: OutsideWorkingHoursError,
    RejectionReason.PROFESSIONAL_TIME_OFF: ProfessionalTimeOffError,
}
_TRANSITION_ERRORS: dict[TransitionRejection, type[DomainError]] = {
    TransitionRejection.CANCELLED_IS_FINAL: CancelledIsFinalError,
    TransitionRejection.ATTENDANCE_ALREADY_RECORDED: AttendanceAlreadyRecordedError,
    TransitionRejection.ALREADY_STARTED: AlreadyStartedError,
    TransitionRejection.NOT_STARTED_YET: NotStartedYetError,
}

"""Transiciones de estado de un turno y elegibilidad para reprogramar.

Funciones puras, solo libreria estandar. No leen el reloj: ``now`` llega como dato.
Orden de evaluacion (design D-7): cancelled -> asistencia registrada -> destino invalido
-> reglas de tiempo. Respaldo: RN-TU-05 (cancelar), RN-TU-06 (reprogramar),
RN-TU-07 (cancelled final; asistencia solo con turno iniciado), US-010.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.domain.appointments.types import AppointmentStatus


class TransitionRejection(Enum):
    CANCELLED_IS_FINAL = "CANCELLED_IS_FINAL"
    ATTENDANCE_ALREADY_RECORDED = "ATTENDANCE_ALREADY_RECORDED"
    INVALID_TARGET_STATUS = "INVALID_TARGET_STATUS"
    NOT_STARTED_YET = "NOT_STARTED_YET"
    ALREADY_STARTED = "ALREADY_STARTED"


@dataclass(frozen=True)
class TransitionResult:
    """Aceptado <=> reason ausente."""

    allowed: bool
    reason: TransitionRejection | None = None

    @classmethod
    def accept(cls) -> TransitionResult:
        return cls(allowed=True, reason=None)

    @classmethod
    def reject(cls, reason: TransitionRejection) -> TransitionResult:
        return cls(allowed=False, reason=reason)


def _require_aware(*moments: datetime) -> None:
    if any(moment.tzinfo is None or moment.utcoffset() is None for moment in moments):
        raise ValueError("starts_at y now deben tener zona horaria")


def _final_state_rejection(current: AppointmentStatus) -> TransitionRejection | None:
    if current == AppointmentStatus.CANCELLED:
        return TransitionRejection.CANCELLED_IS_FINAL  # RN-TU-07
    if current in (AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW):
        return TransitionRejection.ATTENDANCE_ALREADY_RECORDED
    return None


def validate_status_change(
    current: AppointmentStatus,
    target: AppointmentStatus,
    starts_at: datetime,
    now: datetime,
) -> TransitionResult:
    """Decide si un turno puede pasar de ``current`` a ``target``; no modifica nada."""
    _require_aware(starts_at, now)
    final = _final_state_rejection(current)
    if final is not None:
        return TransitionResult.reject(final)
    if target == AppointmentStatus.SCHEDULED:
        return TransitionResult.reject(TransitionRejection.INVALID_TARGET_STATUS)
    started = now >= starts_at  # instantes; el inicio exacto cuenta como iniciado
    if target == AppointmentStatus.CANCELLED:  # RN-TU-05
        if started:
            return TransitionResult.reject(TransitionRejection.ALREADY_STARTED)
        return TransitionResult.accept()
    if not started:  # completed / no_show, RN-TU-07 y US-010
        return TransitionResult.reject(TransitionRejection.NOT_STARTED_YET)
    return TransitionResult.accept()


def validate_reschedule_eligibility(
    current: AppointmentStatus, starts_at: datetime, now: datetime
) -> TransitionResult:
    """RN-TU-06: solo se reprograma un turno scheduled que todavia no inicio."""
    _require_aware(starts_at, now)
    final = _final_state_rejection(current)
    if final is not None:
        return TransitionResult.reject(final)
    if now >= starts_at:
        return TransitionResult.reject(TransitionRejection.ALREADY_STARTED)
    return TransitionResult.accept()

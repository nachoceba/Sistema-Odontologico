"""Reglas puras de la entrega de notificaciones (design D-2)."""

from __future__ import annotations

from datetime import datetime

from app.domain.appointments.types import (
    Appointment,
    AppointmentStatus,
    Notification,
    NotificationStatus,
)
from app.domain.notifications.types import DeliveryDecision


def decide_delivery(
    notification: Notification, appointment: Appointment, now: datetime
) -> DeliveryDecision:
    """SKIP si ya no corresponde tocarla, EXPIRE si el turno no esta vigente, SEND si no.

    La ausencia de fila o de turno se resuelve antes de llamar (SKIP). ``now`` es un dato.
    """
    if notification.status is not NotificationStatus.PENDING:
        return DeliveryDecision.SKIP
    if notification.appointment_starts_at != appointment.starts_at:
        return DeliveryDecision.SKIP
    if appointment.status is not AppointmentStatus.SCHEDULED or appointment.starts_at <= now:
        return DeliveryDecision.EXPIRE
    return DeliveryDecision.SEND

"""Reglas puras de la entrega de notificaciones (design D-2)."""

from __future__ import annotations

from datetime import datetime

from app.domain.appointments.types import (
    Appointment,
    AppointmentStatus,
    Notification,
    NotificationKind,
    NotificationStatus,
)
from app.domain.notifications.types import DeliveryDecision
from app.domain.public_booking.rules import EXPIRED_BOOKING_REASON


def decide_delivery(
    notification: Notification, appointment: Appointment, now: datetime
) -> DeliveryDecision:
    """SKIP si ya no corresponde tocarla, EXPIRE si el turno no esta vigente, SEND si no.

    La ausencia de fila o de turno se resuelve antes de llamar (SKIP). ``now`` es un dato.
    """
    if notification.status is not NotificationStatus.PENDING:
        return DeliveryDecision.SKIP
    if notification.kind is NotificationKind.BOOKING_EXPIRED:
        return _decide_booking_expired(notification, appointment, now)
    if notification.appointment_starts_at != appointment.starts_at:
        return DeliveryDecision.SKIP
    if appointment.status is not AppointmentStatus.SCHEDULED or appointment.starts_at <= now:
        return DeliveryDecision.EXPIRE
    return DeliveryDecision.SEND


def _decide_booking_expired(
    notification: Notification, appointment: Appointment, now: datetime
) -> DeliveryDecision:
    """El aviso de vencimiento solo sale si el sistema cancelo el turno y todavia no empezo.

    Es el inverso de los demas avisos: el turno debe estar ``cancelled`` con el motivo del
    vencimiento, con el mismo inicio, y ``now`` anterior a ese inicio (C-16, DD-140).
    """
    cancelled_by_expiry = (
        appointment.status is AppointmentStatus.CANCELLED
        and appointment.cancel_reason == EXPIRED_BOOKING_REASON
    )
    if (
        not cancelled_by_expiry
        or notification.appointment_starts_at != appointment.starts_at
        or appointment.starts_at <= now
    ):
        return DeliveryDecision.EXPIRE
    return DeliveryDecision.SEND

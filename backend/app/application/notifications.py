"""Casos de uso de envio de notificaciones (design D-2, D-3, D-4; sin Celery ni SQLAlchemy).

``deliver_notification`` toma la fila ``pending`` dentro de una transaccion, decide con la regla
pura ``decide_delivery``, envia por el puerto ``EmailSender`` y registra ``sent`` o ``failed``.
Recibe el reloj como dato. Los registros llevan solo ids, tipo y resultado (D-12): nunca el
destinatario ni nombres.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.appointments.ports import NotificationRepository, NotificationSendUnitOfWork
from app.domain.appointments.types import Notification
from app.domain.notifications import (
    DeliveryDecision,
    DeliveryOutcome,
    EmailSender,
    EmailSendError,
    OutgoingEmail,
    decide_delivery,
    sanitize_error,
)
from app.domain.patients.ports import PatientRepository
from app.domain.professionals import ProfessionalRepository
from app.domain.settings.ports import ClinicSettingsRepository
from app.infrastructure.email.templates import EmailData, render_email

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
EXPIRED_ERROR = "EXPIRED"
MISSING_DATA_ERROR = "MISSING_DATA"
REQUEUE_MIN_AGE = timedelta(minutes=5)
REQUEUE_LIMIT = 100


@dataclass(frozen=True)
class NotificationDeps:
    """Lo que necesita el envio: transaccion con la fila, lecturas, remitente y reloj."""

    unit_of_work: Callable[[], NotificationSendUnitOfWork]
    patients: PatientRepository
    professionals: ProfessionalRepository
    settings: ClinicSettingsRepository
    sender: EmailSender
    clock: Callable[[], datetime]


def _log(notification: Notification, outcome: DeliveryOutcome) -> DeliveryOutcome:
    logger.info(
        "notificacion %s turno %s tipo %s resultado %s",
        notification.id,
        notification.appointment_id,
        notification.kind.value,
        outcome.value,
    )
    return outcome


def deliver_notification(
    deps: NotificationDeps,
    notification_id: str,
    *,
    attempt: int = 1,
    max_attempts: int = MAX_ATTEMPTS,
) -> DeliveryOutcome:
    """Procesa una notificacion: a lo sumo un email por tipo, turno y horario (RN-NO-03)."""
    with deps.unit_of_work() as uow:
        notification = uow.notifications.claim_pending(notification_id)
        if notification is None:
            logger.info("notificacion %s resultado %s", notification_id, "SKIPPED")
            return DeliveryOutcome.SKIPPED
        appointment = uow.appointments.get(notification.appointment_id)
        if appointment is None:
            return _log(notification, DeliveryOutcome.SKIPPED)
        now = deps.clock()
        decision = decide_delivery(notification, appointment, now)
        if decision is DeliveryDecision.SKIP:
            return _log(notification, DeliveryOutcome.SKIPPED)
        if decision is DeliveryDecision.EXPIRE:
            uow.notifications.mark_failed(notification.id, EXPIRED_ERROR)
            return _log(notification, DeliveryOutcome.EXPIRED)

        patient = deps.patients.get(appointment.patient_id)
        professional = deps.professionals.get_by_id(appointment.professional_id)
        if patient is None or professional is None:
            uow.notifications.mark_failed(notification.id, MISSING_DATA_ERROR)
            return _log(notification, DeliveryOutcome.FAILED)
        clinic = deps.settings.get()
        subject, body = render_email(
            notification.kind,
            EmailData(
                patient_first_name=patient.first_name,
                patient_last_name=patient.last_name,
                professional_name=professional.display_name,
                starts_at=appointment.starts_at,
                timezone=clinic.timezone,
                clinic_name=clinic.clinic_name,
                address=clinic.address,
                phone=clinic.phone,
            ),
        )
        try:
            deps.sender.send(OutgoingEmail(patient.email, subject, body))
        except EmailSendError as error:
            if error.temporary and attempt < max_attempts:
                return _log(notification, DeliveryOutcome.RETRY)
            uow.notifications.mark_failed(notification.id, sanitize_error(error))
            return _log(notification, DeliveryOutcome.FAILED)
        uow.notifications.mark_sent(notification.id, deps.clock())
        return _log(notification, DeliveryOutcome.SENT)


@dataclass(frozen=True)
class RequeueDeps:
    """Lo que necesita el reencolado: el registro, la publicacion de una tarea y el reloj."""

    notifications: NotificationRepository
    publish: Callable[[str], None]
    clock: Callable[[], datetime]


def requeue_pending(deps: RequeueDeps) -> int:
    """Vuelve a pedir el envio de las ``pending`` de mas de 5 minutos (tope 100 por pasada).

    Devuelve cuantas se pidieron. Reencolar algo que ya estaba en la cola no duplica el email
    (idempotencia de ``deliver_notification``). Registra solo la cantidad (D-12).
    """
    cutoff = deps.clock() - REQUEUE_MIN_AGE
    requested = 0
    for notification in deps.notifications.list_pending_created_before(cutoff, REQUEUE_LIMIT):
        try:
            deps.publish(notification.id)
        except Exception as error:  # noqa: BLE001  (un fallo de la cola no corta la pasada)
            logger.warning("no se pudo reencolar una notificacion: %s", type(error).__name__)
        else:
            requested += 1
    logger.info("reencolado: %d notificaciones pendientes", requested)
    return requested

"""Caso de uso de la pasada de recordatorios (design D-1, D-2, D-5, D-6; sin Celery).

``send_reminders`` decide con la regla pura ``reminder_target_day`` si es la hora configurada,
toma los turnos ``scheduled`` que empiezan el dia local siguiente, registra un ``reminder``
``pending`` por turno y horario (sin duplicar, RN-NO-03) y lo envia en el momento con el mismo
envio de C-11 (``deliver_notification``). Un fallo en un turno no corta el lote (US-011). Los
registros llevan solo cantidades, ids y clases de error: nunca datos del paciente (DD-77).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.application.notifications import NotificationDeps, deliver_notification
from app.core.timezone import local_day_bounds
from app.domain.appointments.ports import AgendaUnitOfWork, AppointmentRepository
from app.domain.appointments.types import Appointment
from app.domain.notifications import DeliveryOutcome, ReminderRunSummary, reminder_target_day
from app.domain.settings.ports import ClinicSettingsRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReminderDeps:
    """Lo que necesita la pasada: alta en una transaccion, listado global, configuracion,
    el envio de C-11 y el reloj."""

    unit_of_work: Callable[[], AgendaUnitOfWork]
    appointments: AppointmentRepository
    settings: ClinicSettingsRepository
    notification_deps: NotificationDeps
    clock: Callable[[], datetime]


def send_reminders(deps: ReminderDeps, *, force: bool = False) -> ReminderRunSummary:
    """Una pasada: registra y envia los recordatorios del dia local siguiente.

    Solo actua a la hora ``reminder_send_hour`` en la zona de ``clinic_settings`` (o con
    ``force``). Fuera de hora no lee turnos ni registra nada.
    """
    clinic = deps.settings.get()
    day = reminder_target_day(deps.clock(), clinic.timezone, clinic.reminder_send_hour, force=force)
    if day is None:
        logger.info("recordatorios: fuera de la hora configurada")
        return ReminderRunSummary()
    start, end = local_day_bounds(day, clinic.timezone)
    sent = failed = pending = 0
    for appointment in deps.appointments.list_scheduled_starting_between(start, end):
        outcome = _remind(deps, appointment)
        if outcome is DeliveryOutcome.SENT:
            sent += 1
        elif outcome in (DeliveryOutcome.FAILED, DeliveryOutcome.EXPIRED):
            failed += 1
        elif outcome is not None:
            pending += 1
    summary = ReminderRunSummary(sent=sent, failed=failed, pending=pending)
    logger.info(summary.log_text())
    return summary


def _remind(deps: ReminderDeps, appointment: Appointment) -> DeliveryOutcome | None:
    """Registra y envia el recordatorio de un turno; ``None`` si no corresponde registrarlo.

    Un error inesperado se registra con el id del turno y la clase del error. Cuenta como
    ``FAILED`` solo si el recordatorio llego a registrarse.
    """
    registered = False
    try:
        with deps.unit_of_work() as uow:
            notification = uow.notifications.add_pending_reminder(
                appointment.id, appointment.starts_at
            )
        if notification is None:
            return None
        registered = True
        return deliver_notification(deps.notification_deps, notification.id, attempt=1)
    except Exception as error:  # noqa: BLE001  (un turno con error no corta el lote)
        logger.warning("recordatorio del turno %s: error %s", appointment.id, type(error).__name__)
        return DeliveryOutcome.FAILED if registered else None

"""Tareas Celery de notificaciones (spec notification-tasks, design D-7).

``enviar_email`` recibe solo el id de la notificacion (ningun dato del paciente viaja por la
cola). Un fallo temporal se reintenta con esperas de 1 y 2 minutos; el resto lo decide el caso
de uso. ``reencolar_pendientes`` y ``enviar_recordatorios`` las dispara Celery Beat;
``enviar_recordatorios`` acepta ``forzar`` solo para la consola (nunca viaja con Beat).
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from app.application.notifications import MAX_ATTEMPTS, deliver_notification, requeue_pending
from app.application.reminders import send_reminders
from app.domain.notifications import DeliveryOutcome
from app.infrastructure.tasks import wiring

logger = logging.getLogger(__name__)

RETRY_BASE_SECONDS = 60


@shared_task(bind=True, name="enviar_email", max_retries=MAX_ATTEMPTS - 1)  # type: ignore[untyped-decorator]
def enviar_email(self: Any, notification_id: str) -> str:
    attempt = int(self.request.retries) + 1
    outcome = deliver_notification(
        wiring.build_notification_deps(), notification_id, attempt=attempt
    )
    if outcome is DeliveryOutcome.RETRY:
        raise self.retry(countdown=RETRY_BASE_SECONDS * 2 ** (attempt - 1))
    return str(outcome.value)


@shared_task(name="reencolar_pendientes")  # type: ignore[untyped-decorator]
def reencolar_pendientes() -> int:
    return requeue_pending(wiring.build_requeue_deps())


@shared_task(name="enviar_recordatorios", max_retries=0)  # type: ignore[untyped-decorator]
def enviar_recordatorios(forzar: bool = False) -> dict[str, int]:
    """Pasada de recordatorios; ``forzar`` la hace actuar fuera de la hora configurada.

    Sin reintentos: un error al empezar (por ejemplo la base caida) se registra con la clase
    del error, nunca con datos del paciente, y la proxima oportunidad es la del dia siguiente.
    """
    try:
        summary = send_reminders(wiring.build_reminder_deps(), force=forzar)
    except Exception as error:
        # Solo la clase del error, sin traza ni mensaje (TRY400: no se usa ``exception``).
        logger.error("recordatorios: la pasada fallo: %s", type(error).__name__)  # noqa: TRY400
        raise
    return {
        "processed": summary.processed,
        "sent": summary.sent,
        "failed": summary.failed,
        "pending": summary.pending,
    }

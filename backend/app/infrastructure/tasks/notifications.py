"""Tareas Celery de notificaciones (spec notification-tasks, design D-7).

``enviar_email`` recibe solo el id de la notificacion (ningun dato del paciente viaja por la
cola). Un fallo temporal se reintenta con esperas de 1 y 2 minutos; el resto lo decide el caso
de uso. ``reencolar_pendientes`` la dispara Celery Beat.
"""

from __future__ import annotations

from typing import Any

from celery import shared_task

from app.application.notifications import MAX_ATTEMPTS, deliver_notification, requeue_pending
from app.domain.notifications import DeliveryOutcome
from app.infrastructure.tasks import wiring

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

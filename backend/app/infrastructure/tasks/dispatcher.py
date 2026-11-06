"""Despachador posterior al commit: publica un ``enviar_email`` por notificacion (design D-8).

Un Redis caido o lento nunca rompe agendar ni reprogramar (RN-NO-04): cada fallo se registra con
el id del turno y la clase del error, y la fila ``pending`` queda para ``reencolar_pendientes``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

from app.domain.appointments.types import Notification

logger = logging.getLogger(__name__)


class CeleryNotificationDispatcher:
    def __init__(self, publish: Callable[[str], None]) -> None:
        self._publish = publish

    def dispatch(self, notifications: Sequence[Notification]) -> None:
        for notification in notifications:
            try:
                self._publish(notification.id)
            except Exception as error:  # noqa: BLE001  (nada de la cola debe romper el turno)
                logger.warning(
                    "no se pudo publicar el envio del turno %s: %s",
                    notification.appointment_id,
                    type(error).__name__,
                )


def publish_send_email(notification_id: str) -> None:
    """Encola ``enviar_email`` con solo el id, sin reintentar la publicacion (design D-7).

    La aplicacion Celery se importa aca y no al cargar el modulo: asi importar la API no
    abre ninguna conexion ni exige la configuracion de Celery hasta que se publica algo.
    """
    from app.infrastructure.tasks.celery_app import celery_app

    celery_app.tasks["enviar_email"].apply_async(args=[notification_id], retry=False)


def build_dispatcher() -> CeleryNotificationDispatcher:
    return CeleryNotificationDispatcher(publish_send_email)

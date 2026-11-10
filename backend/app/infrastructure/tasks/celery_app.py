"""Aplicacion Celery (D-4): broker Redis, zona del consultorio y tareas de notificaciones.

Todo lo de Celery vive en esta carpeta; si la herramienta cambia, no se toca el
dominio ni la API. Las tareas propias son ``enviar_email`` y ``reencolar_pendientes`` (C-11),
``enviar_recordatorios`` (C-12) y ``vencer_reservas_pendientes`` (C-16). Beat dispara
``enviar_recordatorios`` cada hora en punto (``crontab(minute=0)``, evaluado en la zona de
``CLINIC_TIMEZONE``; la propia tarea decide si es la hora configurada) y el vencimiento de
reservas cada 5 minutos.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery("odonto", broker=_settings.REDIS_URL)
celery_app.conf.update(
    timezone=_settings.CLINIC_TIMEZONE,
    enable_utc=True,
    task_serializer="json",
    beat_schedule={
        "reencolar-pendientes": {"task": "reencolar_pendientes", "schedule": 600.0},
        # Libera las franjas de las reservas online sin confirmar (C-16, DD-132).
        "vencer-reservas-pendientes": {"task": "vencer_reservas_pendientes", "schedule": 300.0},
        # Sin argumentos: Beat nunca fuerza la pasada (solo la consola, design D-5).
        "enviar-recordatorios": {"task": "enviar_recordatorios", "schedule": crontab(minute=0)},
    },
    accept_content=["json"],
    # El timeout de conexion del productor va en las opciones del transporte:
    # ``broker_connection_timeout`` solo aplica al worker (design D-7). Un solo reintento de
    # conexion y breve: con Redis caido ``apply_async`` falla en pocos segundos (RN-NO-04).
    broker_transport_options={
        "socket_connect_timeout": 2,
        "max_retries": 1,
        "interval_start": 0,
        "interval_step": 0.2,
        "interval_max": 0.5,
    },
)

# Registra las tareas (``shared_task``) en esta aplicacion; va al final por el import circular.
from app.infrastructure.tasks import notifications as _notifications  # noqa: E402,F401

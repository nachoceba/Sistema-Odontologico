"""Arma lo que necesitan las tareas del worker (design D-1, D-7).

Las dependencias se crean cuando corre la tarea, no al importar el modulo.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.notifications import NotificationDeps, RequeueDeps
from app.core.config import get_settings
from app.infrastructure.db.repositories import (
    SqlAlchemyAgendaUnitOfWork,
    SqlAlchemyClinicSettingsRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyPatientRepository,
    SqlAlchemyProfessionalRepository,
)
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.email.redirect import RedirectingEmailSender
from app.infrastructure.email.smtp import SmtpEmailSender
from app.infrastructure.tasks.dispatcher import publish_send_email


def build_notification_deps() -> NotificationDeps:
    settings = get_settings()
    sessions = get_session_factory()
    sender = SmtpEmailSender(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        user=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD.get_secret_value(),
        use_tls=settings.SMTP_USE_TLS,
        sender=settings.EMAIL_FROM,
    )
    return NotificationDeps(
        unit_of_work=lambda: SqlAlchemyAgendaUnitOfWork(sessions),
        patients=SqlAlchemyPatientRepository(sessions),
        professionals=SqlAlchemyProfessionalRepository(sessions),
        settings=SqlAlchemyClinicSettingsRepository(sessions),
        sender=RedirectingEmailSender(sender, settings.EMAIL_REDIRECT_TO),
        clock=lambda: datetime.now(UTC),
    )


def build_requeue_deps() -> RequeueDeps:
    return RequeueDeps(
        notifications=SqlAlchemyNotificationRepository(get_session_factory()),
        publish=publish_send_email,
        clock=lambda: datetime.now(UTC),
    )

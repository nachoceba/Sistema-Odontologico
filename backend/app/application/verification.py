"""Envio del email de verificacion de una reserva online (C-15, design D-7; sin Celery).

El token en claro llega solo por el mensaje de la cola: nunca se guarda ni se registra. Antes de
enviar se comprueba que el turno siga pendiente, no haya vencido y el hash coincida. Los
registros llevan solo el id del turno y el resultado.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.domain.appointments.ports import AppointmentRepository
from app.domain.notifications import (
    DeliveryOutcome,
    EmailSender,
    EmailSendError,
    OutgoingEmail,
)
from app.domain.patients.ports import PatientRepository
from app.domain.professionals import ProfessionalRepository
from app.domain.settings.ports import ClinicSettingsRepository
from app.infrastructure.email.templates import VerificationEmailData, render_verification_email

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class VerificationDeps:
    appointments: AppointmentRepository
    patients: PatientRepository
    professionals: ProfessionalRepository
    settings: ClinicSettingsRepository
    sender: EmailSender
    clock: Callable[[], datetime]
    hash_token: Callable[[str], str]
    public_app_url: str


def _log(appointment_id: str, outcome: DeliveryOutcome) -> DeliveryOutcome:
    logger.info("verificacion turno %s resultado %s", appointment_id, outcome.value)
    return outcome


def send_verification(
    deps: VerificationDeps,
    appointment_id: str,
    token: str,
    *,
    attempt: int = 1,
    max_attempts: int = MAX_ATTEMPTS,
) -> DeliveryOutcome:
    """Envia el enlace al email de la ficha si el turno sigue pendiente y el token coincide."""
    appointment = deps.appointments.find_pending_by_token_hash(deps.hash_token(token), deps.clock())
    if appointment is None or appointment.id != appointment_id:
        return _log(appointment_id, DeliveryOutcome.SKIPPED)
    patient = deps.patients.get(appointment.patient_id)
    professional = deps.professionals.get_by_id(appointment.professional_id)
    if patient is None or appointment.pending_until is None or professional is None:
        return _log(appointment_id, DeliveryOutcome.FAILED)
    clinic = deps.settings.get()
    subject, body = render_verification_email(
        VerificationEmailData(
            patient_first_name=patient.first_name,
            patient_last_name=patient.last_name,
            professional_name=professional.display_name,
            starts_at=appointment.starts_at,
            confirm_before=appointment.pending_until,
            timezone=clinic.timezone,
            clinic_name=clinic.clinic_name,
            address=clinic.address,
            phone=clinic.phone,
            confirm_url=f"{deps.public_app_url}/turnos/confirmar#token={token}",
        )
    )
    try:
        deps.sender.send(OutgoingEmail(patient.email, subject, body))
    except EmailSendError as error:
        if error.temporary and attempt < max_attempts:
            return _log(appointment_id, DeliveryOutcome.RETRY)
        return _log(appointment_id, DeliveryOutcome.FAILED)
    return _log(appointment_id, DeliveryOutcome.SENT)

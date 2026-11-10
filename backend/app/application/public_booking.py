"""Casos de uso de la reserva online sin cuenta (C-15, design D-6; sin FastAPI ni SQLAlchemy).

Reutilizan las reglas de agenda de la recepcion (``validated_end``, ``slots_for_day``) y el mismo
constraint de exclusion: la reserva pendiente es un turno ``scheduled`` que ocupa su franja
(DD-130). Ningun caso de uso devuelve datos de una ficha ni modifica una existente (DD-129).
Los registros llevan solo ids y la clase del error: nunca el token ni datos del paciente.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.application.appointments import (
    AgendaDeps,
    _dispatch,
    check_booking_treatment,
    slots_for_day,
    validated_end,
)
from app.core.timezone import to_local
from app.domain.appointments import (
    AgendaUnitOfWork,
    NewAppointment,
    NotificationDispatcher,
    Slot,
    SlotStatus,
)
from app.domain.appointments.errors import (
    InsufficientNoticeError,
    OffGridError,
    OutsideWorkingHoursError,
    PatientDoubleBookedError,
    ProfessionalNotFoundError,
    ProfessionalTimeOffError,
)
from app.domain.appointments.rules import patient_has_overlap
from app.domain.patients.errors import DocumentTakenError
from app.domain.patients.rules import (
    clean_email,
    clean_name,
    clean_phone,
    normalize_document,
    same_person_name,
)
from app.domain.patients.types import NewPatient
from app.domain.professionals import Professional
from app.domain.public_booking.errors import (
    BookingNotPossibleError,
    ConfirmationLinkInvalidError,
    SlotUnavailableError,
)
from app.domain.public_booking.ports import VerificationDispatcher
from app.domain.public_booking.rules import pending_until_for
from app.domain.treatments.errors import TreatmentNotAvailableError
from app.domain.treatments.rules import BookingCheck

logger = logging.getLogger(__name__)

HORIZON_DAYS = 13  # hoy y los 13 dias siguientes (P-4)

_SLOT_REJECTIONS = (
    OffGridError,
    InsufficientNoticeError,
    OutsideWorkingHoursError,
    ProfessionalTimeOffError,
)


@dataclass(frozen=True)
class PublicBookingDeps:
    """La agenda, el generador de tokens, el plazo de la reserva y el aviso de verificacion."""

    agenda: AgendaDeps
    new_token: Callable[[], str]
    hash_token: Callable[[str], str]
    hold_minutes: int
    verification: VerificationDispatcher


@dataclass(frozen=True)
class PublicProfessional:
    """De un profesional ofrecido, solo identificador y nombre visible."""

    id: str
    display_name: str


@dataclass(frozen=True)
class PublicTreatment:
    """De un tratamiento ofrecido, solo identificador y nombre (C-17)."""

    id: str
    name: str


@dataclass(frozen=True)
class OnlineBooking:
    """Respuesta de una reserva: la misma para un DNI nuevo y para uno existente."""

    starts_at: datetime
    ends_at: datetime
    professional_display_name: str
    confirm_before: datetime
    treatment_name: str | None = None


@dataclass(frozen=True)
class OnlineConfirmation:
    starts_at: datetime
    ends_at: datetime
    professional_display_name: str
    treatment_name: str | None = None


def list_public_professionals(deps: PublicBookingDeps) -> list[PublicProfessional]:
    """Profesionales activos con horario y con algun tratamiento activo asignado (P-4, C-17)."""
    agenda = deps.agenda
    return [
        PublicProfessional(p.id, p.display_name)
        for p in agenda.professionals.list(only_active=True)
        if agenda.working_hours.list_for_professional(p.id) and agenda.treatments.offered_ids(p.id)
    ]


def _require_offered(deps: PublicBookingDeps, professional_id: str) -> Professional:
    agenda = deps.agenda
    professional = agenda.professionals.get_by_id(professional_id)
    if (
        professional is None
        or not professional.active
        or not agenda.working_hours.list_for_professional(professional_id)
        or not agenda.treatments.offered_ids(professional_id)
    ):
        raise ProfessionalNotFoundError
    return professional


def list_public_treatments(deps: PublicBookingDeps, professional_id: str) -> list[PublicTreatment]:
    """Tratamientos asignados y activos de un profesional ofrecido, por nombre (C-17)."""
    _require_offered(deps, professional_id)
    return [
        PublicTreatment(t.id, t.name) for t in deps.agenda.treatments.list_offered(professional_id)
    ]


def _inside_horizon(agenda: AgendaDeps, day: date) -> bool:
    today = to_local(agenda.clock(), agenda.settings.get().timezone).date()
    return today <= day <= today + timedelta(days=HORIZON_DAYS)


def public_day_slots(deps: PublicBookingDeps, professional_id: str, day: date) -> list[Slot]:
    """Franjas libres del dia local que respetan la anticipacion minima y el horizonte."""
    _require_offered(deps, professional_id)
    agenda = deps.agenda
    if not _inside_horizon(agenda, day):
        return []
    earliest = agenda.clock() + timedelta(hours=agenda.settings.get().min_notice_hours)
    return [
        slot
        for slot in slots_for_day(agenda, professional_id, day)
        if slot.status is SlotStatus.FREE and slot.starts_at >= earliest
    ]


def book_online(
    deps: PublicBookingDeps,
    *,
    professional_id: str,
    treatment_id: str,
    starts_at: datetime,
    document_number: str,
    first_name: str,
    last_name: str,
    email: str,
    phone: str | None,
) -> OnlineBooking:
    """Reserva un turno pendiente de confirmacion; los rechazos de paciente son genericos."""
    agenda = deps.agenda
    document = normalize_document(document_number)
    first, last, mail = clean_name(first_name), clean_name(last_name), clean_email(email)
    phone_number = None if phone is None else clean_phone(phone)
    professional = _require_offered(deps, professional_id)
    treatment_name = _require_offered_treatment(agenda, professional_id, treatment_id)
    ends_at = _validated_online_end(agenda, professional_id, starts_at)
    now = agenda.clock()
    token = deps.new_token()
    pending_until = pending_until_for(now, starts_at, deps.hold_minutes)
    try:
        with agenda.unit_of_work() as uow:
            record = uow.patients.get_by_document(document)
            if record is None:
                record = uow.patients.add(NewPatient(first, last, document, mail, phone_number))
            else:
                _require_linkable(agenda, record, first, last, starts_at, ends_at)
            saved = uow.appointments.add_pending(
                NewAppointment(
                    patient_id=record.id,
                    professional_id=professional_id,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    created_by=None,
                    treatment_id=treatment_id,
                ),
                deps.hash_token(token),
                pending_until,
            )
    except (DocumentTakenError, PatientDoubleBookedError):
        raise BookingNotPossibleError from None
    _request_verification(deps, saved.id, token)
    return OnlineBooking(
        saved.starts_at, saved.ends_at, professional.display_name, pending_until, treatment_name
    )


def _require_offered_treatment(agenda: AgendaDeps, professional_id: str, treatment_id: str) -> str:
    """Los tres motivos de rechazo dan el mismo TREATMENT_NOT_AVAILABLE (C-17, D-5)."""
    if check_booking_treatment(agenda, professional_id, treatment_id) is not BookingCheck.OK:
        raise TreatmentNotAvailableError
    treatment = agenda.treatments.get(treatment_id)
    assert treatment is not None
    return treatment.name


def _validated_online_end(
    agenda: AgendaDeps, professional_id: str, starts_at: datetime
) -> datetime:
    """Horizonte y reglas de agenda; cualquier motivo de horario es ``SLOT_UNAVAILABLE``."""
    if not _inside_horizon(agenda, to_local(starts_at, agenda.settings.get().timezone).date()):
        raise SlotUnavailableError
    try:
        return validated_end(agenda, None, professional_id, starts_at)
    except _SLOT_REJECTIONS:
        raise SlotUnavailableError from None


def _require_linkable(
    agenda: AgendaDeps,
    record: object,
    first: str,
    last: str,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    """El nombre coincide, la ficha esta activa y no hay otro turno superpuesto (DD-129)."""
    from app.domain.patients.types import PatientRecord

    assert isinstance(record, PatientRecord)
    if (
        not record.active
        or not same_person_name(first, record.first_name)
        or not same_person_name(last, record.last_name)
    ):
        raise BookingNotPossibleError
    others = agenda.appointments.list_for_patient(record.id, starts_at, ends_at)
    if patient_has_overlap(record.id, starts_at, ends_at, others):
        raise BookingNotPossibleError


def _request_verification(deps: PublicBookingDeps, appointment_id: str, token: str) -> None:
    """Pide el email despues del commit; un fallo nunca desarma la reserva (RN-NO-04)."""
    try:
        deps.verification.dispatch(appointment_id, token)
    except Exception as error:  # noqa: BLE001  (nada de la cola debe romper la reserva)
        logger.warning(
            "no se pudo pedir la verificacion del turno %s: %s",
            appointment_id,
            type(error).__name__,
        )


def confirm_online_booking(deps: PublicBookingDeps, token: str) -> OnlineConfirmation:
    """Confirma con el token de un solo uso; todo rechazo es ``CONFIRMATION_LINK_INVALID``."""
    agenda = deps.agenda
    with agenda.unit_of_work() as uow:
        confirmed = uow.appointments.confirm_by_token_hash(deps.hash_token(token), agenda.clock())
        if confirmed is None:
            raise ConfirmationLinkInvalidError
        confirmation = uow.notifications.add_pending_confirmation(confirmed.id, confirmed.starts_at)
    _dispatch(agenda, [confirmation])
    professional = agenda.professionals.get_by_id(confirmed.professional_id)
    name = "" if professional is None else professional.display_name
    treatment = (
        None if confirmed.treatment_id is None else agenda.treatments.get(confirmed.treatment_id)
    )
    return OnlineConfirmation(
        confirmed.starts_at,
        confirmed.ends_at,
        name,
        None if treatment is None else treatment.name,
    )


EXPIRY_BATCH_LIMIT = 200


@dataclass(frozen=True)
class ExpiryDeps:
    """Lo que necesita el vencimiento: la transaccion y el aviso posterior al commit."""

    unit_of_work: Callable[[], AgendaUnitOfWork]
    dispatcher: NotificationDispatcher
    clock: Callable[[], datetime]


def expire_pending_bookings(deps: ExpiryDeps) -> int:
    """Cancela las reservas online vencidas y registra el aviso de cada una (C-16, DD-132/140).

    La cancelacion y el registro de ``booking_expired`` van en la misma transaccion; el envio se
    pide despues del commit y un fallo del despachador nunca la deshace (RN-NO-04): la fila queda
    ``pending`` y la levanta ``reencolar_pendientes``. Devuelve cuantas se vencieron; el registro
    lleva solo esa cantidad, nunca datos de pacientes.
    """
    with deps.unit_of_work() as uow:
        expired = uow.appointments.expire_pending(deps.clock(), EXPIRY_BATCH_LIMIT)
        notices = [
            uow.notifications.add_pending_booking_expired(appointment.id, appointment.starts_at)
            for appointment in expired
        ]
    registered = [notice for notice in notices if notice is not None]
    if registered:
        try:
            deps.dispatcher.dispatch(registered)
        except Exception as error:  # noqa: BLE001  (nada de la cola debe deshacer el vencimiento)
            logger.warning(
                "no se pudo pedir el aviso de vencimiento (%d reservas): %s",
                len(registered),
                type(error).__name__,
            )
    logger.info("vencimiento de reservas: expired=%d", len(expired))
    return len(expired)

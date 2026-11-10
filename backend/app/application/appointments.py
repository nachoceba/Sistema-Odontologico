"""Casos de uso de la agenda de turnos (design D-1, D-3; sin FastAPI ni SQLAlchemy).

Orquestan: cargan datos por puertos, llaman a las reglas puras del dominio y escriben.
Reciben el reloj como dato (``AgendaDeps.clock``): nunca llaman a ``datetime.now``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.core.timezone import local_day_bounds, to_local
from app.domain.appointments import (
    Appointment,
    AppointmentStatus,
    NewAppointment,
    Notification,
    Slot,
    TimeOff,
    WorkingHours,
    compute_slots,
    validate_appointment,
    validate_reschedule_eligibility,
    validate_status_change,
)
from app.domain.appointments.errors import (
    AppointmentNotFoundError,
    OffGridError,
    PatientDoubleBookedError,
    PatientInactiveError,
    PatientNotFoundError,
    ProfessionalInactiveError,
    ProfessionalNotFoundError,
    RescheduleSameTimeError,
    error_for_rejection,
    error_for_transition,
)
from app.domain.appointments.ports import (
    AgendaUnitOfWork,
    AppointmentRepository,
    NotificationDispatcher,
)
from app.domain.appointments.rules import has_sub_minute_precision, patient_has_overlap
from app.domain.auth import ForbiddenError, Principal, can_access_professional
from app.domain.patients.eligibility import check_patient_can_book
from app.domain.patients.ports import PatientRepository
from app.domain.patients.types import Patient
from app.domain.professionals import Professional, ProfessionalRepository
from app.domain.public_booking.errors import PendingConfirmationError
from app.domain.schedules import TimeOffRepository, WorkingHoursRepository
from app.domain.settings.ports import ClinicSettingsRepository
from app.domain.settings.types import ClinicSettings
from app.domain.treatments.errors import TreatmentNotAvailableError, TreatmentNotFoundError
from app.domain.treatments.ports import TreatmentRepository
from app.domain.treatments.rules import BookingCheck, check_treatment_for_booking

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgendaDeps:
    """Lo que necesitan los casos de uso de agenda: lecturas, unidad de trabajo, aviso y reloj.

    ``appointments`` sirve para leer y para marcar atencion; agendar, reprogramar y cancelar
    escriben turno y notificaciones por ``unit_of_work`` (una sola transaccion, DD-36).
    """

    appointments: AppointmentRepository
    patients: PatientRepository
    professionals: ProfessionalRepository
    treatments: TreatmentRepository
    working_hours: WorkingHoursRepository
    time_off: TimeOffRepository
    settings: ClinicSettingsRepository
    unit_of_work: Callable[[], AgendaUnitOfWork]
    dispatcher: NotificationDispatcher
    clock: Callable[[], datetime]


@dataclass(frozen=True)
class AgendaContext:
    """Datos reales de un profesional alrededor de un horario pedido (D-3)."""

    settings: ClinicSettings
    working_hours: list[WorkingHours]
    time_off: list[TimeOff]
    appointments: list[Appointment]


def load_context(deps: AgendaDeps, professional_id: str, starts_at: datetime) -> AgendaContext:
    """Tramos, licencias, configuracion y turnos del dia local del inicio, con bordes.

    Los turnos se piden desde el comienzo del dia local hasta el fin del dia o del turno
    pedido (lo que termine despues): un turno que cruza la medianoche entra (DD-19).
    """
    settings = deps.settings.get()
    day_start, day_end = local_day_bounds(
        to_local(starts_at, settings.timezone).date(), settings.timezone
    )
    window_end = max(day_end, starts_at + timedelta(minutes=settings.slot_minutes))
    return AgendaContext(
        settings=settings,
        working_hours=deps.working_hours.list_for_professional(professional_id),
        time_off=[e.to_time_off() for e in deps.time_off.list_for_professional(professional_id)],
        appointments=deps.appointments.list_for_professional(
            professional_id, min(day_start, starts_at), window_end
        ),
    )


def _require_professional(deps: AgendaDeps, professional_id: str) -> Professional:
    professional = deps.professionals.get_by_id(professional_id)
    if professional is None:
        raise ProfessionalNotFoundError
    return professional


def book_appointment(
    deps: AgendaDeps,
    principal: Principal,
    *,
    patient_id: str,
    professional_id: str,
    treatment_id: str,
    starts_at: datetime,
) -> Appointment:
    """Agenda un turno; un unico motivo de rechazo, en el orden fijo de la spec.

    Orden: paciente y profesional existen y estan activos -> tratamiento (C-17, DD-142) ->
    reglas de horario -> escritura.
    """
    patient = deps.patients.get(patient_id)
    if patient is None:
        raise PatientNotFoundError
    professional = _require_professional(deps, professional_id)
    _require_active(patient, professional)
    require_treatment_for_booking(deps, professional_id, treatment_id)
    ends_at = validated_end(deps, patient_id, professional_id, starts_at)
    with deps.unit_of_work() as uow:
        saved = uow.appointments.add(
            NewAppointment(
                patient_id=patient_id,
                professional_id=professional_id,
                starts_at=starts_at,
                ends_at=ends_at,
                created_by=principal.user_id,
                treatment_id=treatment_id,
            )
        )
        confirmation = uow.notifications.add_pending_confirmation(saved.id, saved.starts_at)
    _dispatch(deps, [confirmation])
    return saved


def check_booking_treatment(
    deps: AgendaDeps, professional_id: str, treatment_id: str
) -> BookingCheck:
    """Aplica la regla pura al tratamiento y a lo que el profesional ofrece hoy."""
    return check_treatment_for_booking(
        deps.treatments.get(treatment_id), deps.treatments.offered_ids(professional_id)
    )


def require_treatment_for_booking(
    deps: AgendaDeps, professional_id: str, treatment_id: str
) -> None:
    """Inexistente: TREATMENT_NOT_FOUND; inactivo o no ofrecido: TREATMENT_NOT_AVAILABLE."""
    result = check_booking_treatment(deps, professional_id, treatment_id)
    if result is BookingCheck.NOT_FOUND:
        raise TreatmentNotFoundError
    if result is not BookingCheck.OK:
        raise TreatmentNotAvailableError


def _require_active(patient: Patient, professional: Professional) -> None:
    """RN-PA-04 y P-5: ni el paciente ni la ficha del profesional pueden estar inactivos."""
    if not check_patient_can_book(patient.active).allowed:
        raise PatientInactiveError
    if not professional.active:
        raise ProfessionalInactiveError


def validated_end(
    deps: AgendaDeps,
    patient_id: str | None,
    professional_id: str,
    starts_at: datetime,
    *,
    exclude_id: str | None = None,
) -> datetime:
    """Reglas de horario y de paciente sobre un inicio; devuelve el fin (slot vigente).

    ``exclude_id`` deja afuera el propio turno al reprogramar (Hallazgo 1). Con
    ``patient_id=None`` (reserva online de un paciente que todavia no existe) solo valida la
    agenda del profesional; el paciente se controla aparte (C-15).
    """
    if has_sub_minute_precision(starts_at):
        raise OffGridError
    context = load_context(deps, professional_id, starts_at)
    validation = validate_appointment(
        professional_id=professional_id,
        starts_at=starts_at,
        now=deps.clock(),
        working_hours=context.working_hours,
        time_off=context.time_off,
        existing_appointments=[a.to_existing() for a in context.appointments if a.id != exclude_id],
        slot_minutes=context.settings.slot_minutes,
        timezone=context.settings.timezone,
        min_notice_hours=context.settings.min_notice_hours,
    )
    if not validation.accepted or validation.ends_at is None:
        assert validation.reason is not None
        raise error_for_rejection(
            validation.reason, professional_id=professional_id, starts_at=starts_at
        )
    if patient_id is not None:
        _require_patient_free(
            deps, patient_id, starts_at, validation.ends_at, exclude_id=exclude_id
        )
    return validation.ends_at


def _require_patient_free(
    deps: AgendaDeps,
    patient_id: str,
    starts_at: datetime,
    ends_at: datetime,
    *,
    exclude_id: str | None = None,
) -> None:
    """P-3 (DD-63): el paciente no puede tener otro turno scheduled superpuesto."""
    others = deps.appointments.list_for_patient(patient_id, starts_at, ends_at)
    if patient_has_overlap(patient_id, starts_at, ends_at, others, exclude_id=exclude_id):
        raise PatientDoubleBookedError


MAX_LIST_DAYS = 31  # limite tecnico contra consultas enormes (design D-5)


def _require_access(principal: Principal, professional_id: str) -> None:
    """RN-AU-04 / DD-53: el odontologo solo accede a su propio profesional."""
    if not can_access_professional(principal, professional_id):
        raise ForbiddenError


def get_appointment(deps: AgendaDeps, principal: Principal, appointment_id: str) -> Appointment:
    """Un turno por id; inexistente es 404 para todos y el alcance sale del turno."""
    appointment = _load_appointment(deps, appointment_id)
    _require_access(principal, appointment.professional_id)
    return appointment


def list_appointments(
    deps: AgendaDeps,
    principal: Principal,
    professional_id: str,
    start: datetime,
    end: datetime,
) -> list[Appointment]:
    """Turnos de cualquier estado de un profesional en ``[start, end)``, por inicio."""
    _require_access(principal, professional_id)
    if end - start > timedelta(days=MAX_LIST_DAYS):
        raise ValueError(f"el rango no puede superar {MAX_LIST_DAYS} dias")
    return deps.appointments.list_for_professional(professional_id, start, end)


@dataclass(frozen=True)
class AppointmentView:
    """Un turno con el nombre vigente del paciente y del tratamiento (DD-79, DD-150)."""

    appointment: Appointment
    patient_first_name: str
    patient_last_name: str
    treatment_name: str | None = None  # nulo: turno anterior a C-17 (DD-148)


def _with_names(deps: AgendaDeps, appointments: Sequence[Appointment]) -> list[AppointmentView]:
    """Completa nombres con una lectura por paciente y por tratamiento distintos (design D-1)."""
    patients: dict[str, tuple[str, str]] = {}
    treatments: dict[str, str] = {}
    views: list[AppointmentView] = []
    for appointment in appointments:
        if appointment.patient_id not in patients:
            patient = deps.patients.get(appointment.patient_id)
            if patient is None:
                raise LookupError("turno con paciente inexistente")
            patients[appointment.patient_id] = (patient.first_name, patient.last_name)
        treatment_name = None
        if appointment.treatment_id is not None:
            if appointment.treatment_id not in treatments:
                treatment = deps.treatments.get(appointment.treatment_id)
                if treatment is None:
                    raise LookupError("turno con tratamiento inexistente")
                treatments[appointment.treatment_id] = treatment.name
            treatment_name = treatments[appointment.treatment_id]
        first_name, last_name = patients[appointment.patient_id]
        views.append(AppointmentView(appointment, first_name, last_name, treatment_name))
    return views


def get_appointment_view(
    deps: AgendaDeps, principal: Principal, appointment_id: str
) -> AppointmentView:
    """``get_appointment`` con el nombre del paciente; el 403 sale antes de leer pacientes."""
    appointment = get_appointment(deps, principal, appointment_id)
    return _with_names(deps, [appointment])[0]


def list_appointment_views(
    deps: AgendaDeps,
    principal: Principal,
    professional_id: str,
    start: datetime,
    end: datetime,
) -> list[AppointmentView]:
    """``list_appointments`` con el nombre del paciente de cada turno."""
    return _with_names(deps, list_appointments(deps, principal, professional_id, start, end))


def day_slots(
    deps: AgendaDeps, principal: Principal, professional_id: str, day: date
) -> list[Slot]:
    """Franjas del dia local del profesional; el mismo cargador de contexto que agendar."""
    _require_access(principal, professional_id)
    _require_professional(deps, professional_id)
    return slots_for_day(deps, professional_id, day)


def slots_for_day(deps: AgendaDeps, professional_id: str, day: date) -> list[Slot]:
    """Las franjas del dia local sin chequeos de acceso (los comparte la reserva online)."""
    settings = deps.settings.get()
    day_start, _ = local_day_bounds(day, settings.timezone)
    context = load_context(deps, professional_id, day_start)
    return compute_slots(
        professional_id=professional_id,
        day=day,
        working_hours=context.working_hours,
        time_off=context.time_off,
        existing_appointments=[a.to_existing() for a in context.appointments],
        slot_minutes=context.settings.slot_minutes,
        timezone=context.settings.timezone,
    )


def _load_appointment(deps: AgendaDeps, appointment_id: str) -> Appointment:
    appointment = deps.appointments.get(appointment_id)
    if appointment is None:
        raise AppointmentNotFoundError(appointment_id)
    return appointment


def _require_transition(
    deps: AgendaDeps, appointment: Appointment, target: AppointmentStatus
) -> None:
    result = validate_status_change(appointment.status, target, appointment.starts_at, deps.clock())
    if not result.allowed:
        assert result.reason is not None
        raise error_for_transition(result.reason)


def cancel_appointment(deps: AgendaDeps, appointment_id: str, reason: str) -> Appointment:
    """Cancela un turno con un motivo ya recortado y no vacio (P-7); no lo borra (RN-TU-05)."""
    if not reason.strip():
        raise ValueError("el motivo de cancelacion es obligatorio")
    appointment = _load_appointment(deps, appointment_id)
    _require_transition(deps, appointment, AppointmentStatus.CANCELLED)
    with deps.unit_of_work() as uow:
        cancelled = uow.appointments.change_status(
            appointment.id, AppointmentStatus.CANCELLED, reason
        )
        uow.notifications.delete_pending(appointment.id)
    return cancelled


def reschedule_appointment(
    deps: AgendaDeps, appointment_id: str, starts_at: datetime
) -> Appointment:
    """Mueve un turno a un nuevo inicio, con la duracion vigente (P-6, P-12)."""
    appointment = _load_appointment(deps, appointment_id)
    if appointment.pending_until is not None:
        raise PendingConfirmationError
    eligibility = validate_reschedule_eligibility(
        appointment.status, appointment.starts_at, deps.clock()
    )
    if not eligibility.allowed:
        assert eligibility.reason is not None
        raise error_for_transition(eligibility.reason)
    if starts_at == appointment.starts_at:
        raise RescheduleSameTimeError
    patient = deps.patients.get(appointment.patient_id)
    if patient is None:
        raise PatientNotFoundError
    professional = _require_professional(deps, appointment.professional_id)
    _require_active(patient, professional)
    ends_at = validated_end(
        deps,
        appointment.patient_id,
        appointment.professional_id,
        starts_at,
        exclude_id=appointment.id,
    )
    with deps.unit_of_work() as uow:
        uow.notifications.delete_pending(appointment.id, starts_at=appointment.starts_at)
        moved = uow.appointments.reschedule(appointment.id, starts_at, ends_at)
        confirmation = uow.notifications.add_pending_confirmation(appointment.id, moved.starts_at)
    _dispatch(deps, [confirmation])
    return moved


def record_attendance(
    deps: AgendaDeps, principal: Principal, appointment_id: str, status: AppointmentStatus
) -> Appointment:
    """Marca ``completed`` o ``no_show`` un turno ya iniciado (US-010, DD-22, DD-23).

    El alcance del odontologo se chequea antes que cualquier regla de estado.
    """
    if status not in (AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW):
        raise ValueError("el estado de atencion debe ser completed o no_show")
    appointment = get_appointment(deps, principal, appointment_id)
    if appointment.pending_until is not None:
        raise PendingConfirmationError
    _require_transition(deps, appointment, status)
    return deps.appointments.change_status(appointment.id, status)


def _dispatch(deps: AgendaDeps, notifications: Sequence[Notification | None]) -> None:
    """Avisa al despachador DESPUES del commit; un fallo nunca desarma la operacion (RN-NO-04).

    El log lleva solo ids y el tipo de error: nunca datos del paciente (RN-PR-01).
    """
    registered = [notification for notification in notifications if notification is not None]
    if not registered:
        return
    try:
        deps.dispatcher.dispatch(registered)
    except Exception as error:
        logger.warning(
            "Fallo el despachador de notificaciones (turnos %s): %s",
            ", ".join(n.appointment_id for n in registered),
            type(error).__name__,
        )

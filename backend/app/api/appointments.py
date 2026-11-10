"""Endpoints de turnos y franjas (spec appointment-api, design D-5).

Agendar, cancelar y reprogramar exigen administracion o recepcion (``require_role``). Detalle,
listado, franjas y marcar atencion exigen sesion y aplican el alcance del odontologo en el caso
de uso (RN-AU-04, DD-53). Los instantes entran con zona (``AwareDatetime``) y salen en UTC.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from pydantic import AwareDatetime, BaseModel, BeforeValidator, Field

from app.api.dependencies import Agenda, CurrentUser, require_role
from app.api.validators import strip_text
from app.application import appointments as use_cases
from app.application.appointments import MAX_LIST_DAYS
from app.domain.appointments import Appointment, AppointmentStatus, Slot
from app.domain.auth import Principal, Role

_staff_only = require_role(Role.ADMIN, Role.RECEPTIONIST)
StaffUser = Annotated[Principal, Depends(_staff_only)]

appointments_router = APIRouter(prefix="/appointments", tags=["appointments"])
professionals_router = APIRouter(prefix="/professionals", tags=["appointments"])

EntityId = Annotated[str, BeforeValidator(strip_text), Field(min_length=1, max_length=64)]
Reason = Annotated[str, BeforeValidator(strip_text), Field(min_length=1, max_length=500)]


class AppointmentOut(BaseModel):
    id: str
    patient_id: str
    professional_id: str
    starts_at: datetime
    ends_at: datetime
    status: str
    cancel_reason: str | None
    created_by: str | None  # None: reserva online (C-15)
    origin: Literal["staff", "online"]
    pending_until: datetime | None

    @classmethod
    def from_domain(cls, appointment: Appointment) -> AppointmentOut:
        return cls(
            id=appointment.id,
            patient_id=appointment.patient_id,
            professional_id=appointment.professional_id,
            starts_at=appointment.starts_at.astimezone(UTC),
            ends_at=appointment.ends_at.astimezone(UTC),
            status=appointment.status.value,
            cancel_reason=appointment.cancel_reason,
            created_by=appointment.created_by,
            origin="online" if appointment.created_by is None else "staff",
            pending_until=(
                None
                if appointment.pending_until is None
                else appointment.pending_until.astimezone(UTC)
            ),
        )


class AppointmentViewOut(AppointmentOut):
    """Turno con apellido y nombre del paciente (DD-79); solo listado y detalle."""

    patient_first_name: str
    patient_last_name: str

    @classmethod
    def from_view(cls, view: use_cases.AppointmentView) -> AppointmentViewOut:
        base = AppointmentOut.from_domain(view.appointment)
        return cls(
            **base.model_dump(),
            patient_first_name=view.patient_first_name,
            patient_last_name=view.patient_last_name,
        )


class SlotOut(BaseModel):
    starts_at: datetime
    ends_at: datetime
    status: Literal["FREE", "BUSY", "OUTSIDE_HOURS"]

    @classmethod
    def from_domain(cls, slot: Slot) -> SlotOut:
        return cls(
            starts_at=slot.starts_at.astimezone(UTC),
            ends_at=slot.ends_at.astimezone(UTC),
            status=slot.status.value,
        )


class BookRequest(BaseModel):
    patient_id: EntityId
    professional_id: EntityId
    starts_at: AwareDatetime


class CancelRequest(BaseModel):
    reason: Reason


class RescheduleRequest(BaseModel):
    starts_at: AwareDatetime


class AttendanceRequest(BaseModel):
    status: Literal["completed", "no_show"]


def _invalid_range(message: str) -> RequestValidationError:
    """422 con la forma de siempre (sin eco de los valores enviados)."""
    return RequestValidationError([{"loc": ("query", "to"), "msg": message, "type": "value_error"}])


@appointments_router.post("", status_code=201)
def book(body: BookRequest, deps: Agenda, principal: StaffUser) -> AppointmentOut:
    saved = use_cases.book_appointment(
        deps,
        principal,
        patient_id=body.patient_id,
        professional_id=body.professional_id,
        starts_at=body.starts_at.astimezone(UTC),
    )
    return AppointmentOut.from_domain(saved)


@appointments_router.get("")
def list_by_professional(
    deps: Agenda,
    principal: CurrentUser,
    professional_id: Annotated[EntityId, Query()],
    start: Annotated[AwareDatetime, Query(alias="from")],
    end: Annotated[AwareDatetime, Query(alias="to")],
) -> list[AppointmentViewOut]:
    if start >= end:
        raise _invalid_range("'from' debe ser anterior a 'to'")
    if end - start > timedelta(days=MAX_LIST_DAYS):
        raise _invalid_range(f"El rango no puede superar {MAX_LIST_DAYS} días")
    rows = use_cases.list_appointment_views(
        deps, principal, professional_id, start.astimezone(UTC), end.astimezone(UTC)
    )
    return [AppointmentViewOut.from_view(row) for row in rows]


@appointments_router.get("/{appointment_id}")
def detail(appointment_id: str, deps: Agenda, principal: CurrentUser) -> AppointmentViewOut:
    return AppointmentViewOut.from_view(
        use_cases.get_appointment_view(deps, principal, appointment_id)
    )


@appointments_router.post("/{appointment_id}/cancel")
def cancel(
    appointment_id: str, body: CancelRequest, deps: Agenda, principal: StaffUser
) -> AppointmentOut:
    return AppointmentOut.from_domain(
        use_cases.cancel_appointment(deps, appointment_id, body.reason)
    )


@appointments_router.post("/{appointment_id}/reschedule")
def reschedule(
    appointment_id: str, body: RescheduleRequest, deps: Agenda, principal: StaffUser
) -> AppointmentOut:
    return AppointmentOut.from_domain(
        use_cases.reschedule_appointment(deps, appointment_id, body.starts_at.astimezone(UTC))
    )


@appointments_router.post("/{appointment_id}/attendance")
def attendance(
    appointment_id: str, body: AttendanceRequest, deps: Agenda, principal: CurrentUser
) -> AppointmentOut:
    return AppointmentOut.from_domain(
        use_cases.record_attendance(deps, principal, appointment_id, AppointmentStatus(body.status))
    )


@professionals_router.get("/{professional_id}/slots")
def slots(
    professional_id: str,
    deps: Agenda,
    principal: CurrentUser,
    day: Annotated[date, Query(alias="date")],
) -> list[SlotOut]:
    return [
        SlotOut.from_domain(slot)
        for slot in use_cases.day_slots(deps, principal, professional_id, day)
    ]

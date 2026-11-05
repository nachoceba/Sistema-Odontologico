"""Endpoints de pacientes (spec patient-api, design D-6).

Las escrituras exigen administracion o recepcion en la ruta (``require_role``: 403 antes que
422, porque FastAPI resuelve las dependencias antes de validar el cuerpo) y ``DELETE`` solo
administracion. Las lecturas exigen sesion y el caso de uso vuelve a chequear el rol (RN-PR-02).
La fecha de nacimiento entra como texto ``AAAA-MM-DD`` (una fecha laxa de Pydantic aceptaria
numeros) y los instantes de los turnos salen en UTC. Ninguna respuesta de error repite datos.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
)

from app.api.dependencies import CurrentUser, Patients, require_role
from app.api.validators import Email, strip_text
from app.application import patients as use_cases
from app.domain.appointments import Appointment
from app.domain.auth import Principal, Role
from app.domain.patients.rules import clean_phone, normalize_document
from app.domain.patients.types import PatientRecord
from app.domain.professionals import UNSET, Unset

_staff_only = require_role(Role.ADMIN, Role.RECEPTIONIST)
_admin_only = require_role(Role.ADMIN)
StaffUser = Annotated[Principal, Depends(_staff_only)]
AdminUser = Annotated[Principal, Depends(_admin_only)]

router = APIRouter(prefix="/patients", tags=["patients"])


def _check_document(value: str) -> str:
    return normalize_document(value)


def _check_phone(value: str) -> str:
    clean_phone(value)
    return value


def _check_birth_date(value: str) -> str:
    date.fromisoformat(value)  # fecha imposible (2026-02-30) -> ValueError -> 422
    return value


Name = Annotated[str, BeforeValidator(strip_text), Field(min_length=1, max_length=100)]
Document = Annotated[
    str,
    BeforeValidator(strip_text),
    Field(min_length=1, max_length=40),
    AfterValidator(_check_document),
]
Phone = Annotated[
    str, BeforeValidator(strip_text), Field(max_length=30), AfterValidator(_check_phone)
]
BirthDate = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$"), AfterValidator(_check_birth_date)]
SearchText = Annotated[str | None, Query(max_length=100)]

_REQUIRED_ON_PATCH = ("first_name", "last_name", "document_number", "email")


class PatientOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    document_number: str
    email: str
    phone: str | None
    birth_date: str | None
    active: bool

    @classmethod
    def from_domain(cls, record: PatientRecord) -> PatientOut:
        return cls(
            id=record.id,
            first_name=record.first_name,
            last_name=record.last_name,
            document_number=record.document_number,
            email=record.email,
            phone=record.phone,
            birth_date=None if record.birth_date is None else record.birth_date.isoformat(),
            active=record.active,
        )


class PatientSearchOut(BaseModel):
    items: list[PatientOut]
    truncated: bool


class UpcomingAppointmentOut(BaseModel):
    id: str
    professional_id: str
    starts_at: datetime
    ends_at: datetime
    status: str

    @classmethod
    def from_domain(cls, appointment: Appointment) -> UpcomingAppointmentOut:
        return cls(
            id=appointment.id,
            professional_id=appointment.professional_id,
            starts_at=appointment.starts_at.astimezone(UTC),
            ends_at=appointment.ends_at.astimezone(UTC),
            status=appointment.status.value,
        )


class DeactivationOut(BaseModel):
    patient: PatientOut
    upcoming_appointments: list[UpcomingAppointmentOut]


class CreatePatientRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: Name
    last_name: Name
    document_number: Document
    email: Email
    phone: Phone | None = None
    birth_date: BirthDate | None = None


class UpdatePatientRequest(BaseModel):
    """Campo ausente = no cambia; ``phone`` y ``birth_date`` en ``null`` lo borran."""

    model_config = ConfigDict(extra="forbid")

    first_name: Name | None = None
    last_name: Name | None = None
    document_number: Document | None = None
    email: Email | None = None
    phone: Phone | None = None
    birth_date: BirthDate | None = None

    @model_validator(mode="after")
    def _required_fields_are_not_null(self) -> UpdatePatientRequest:
        for name in _REQUIRED_ON_PATCH:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError("El campo no puede ser nulo")
        return self


@router.get("")
def search_patients(
    deps: Patients,
    principal: CurrentUser,
    q: SearchText = None,
    include_inactive: bool = False,
) -> PatientSearchOut:
    result = use_cases.search_patients(deps, principal, text=q, include_inactive=include_inactive)
    return PatientSearchOut(
        items=[PatientOut.from_domain(record) for record in result.items],
        truncated=result.truncated,
    )


@router.get("/{patient_id}")
def get_patient(patient_id: str, deps: Patients, principal: CurrentUser) -> PatientOut:
    return PatientOut.from_domain(use_cases.get_patient(deps, principal, patient_id))


@router.post("", status_code=201)
def create_patient(body: CreatePatientRequest, deps: Patients, principal: StaffUser) -> PatientOut:
    saved = use_cases.create_patient(
        deps,
        principal,
        first_name=body.first_name,
        last_name=body.last_name,
        document_number=body.document_number,
        email=body.email,
        phone=body.phone,
        birth_date=None if body.birth_date is None else date.fromisoformat(body.birth_date),
    )
    return PatientOut.from_domain(saved)


@router.patch("/{patient_id}")
def update_patient(
    patient_id: str, body: UpdatePatientRequest, deps: Patients, principal: StaffUser
) -> PatientOut:
    sent = body.model_fields_set
    birth_date: date | None | Unset = UNSET
    if "birth_date" in sent:
        birth_date = None if body.birth_date is None else date.fromisoformat(body.birth_date)
    updated = use_cases.update_patient(
        deps,
        principal,
        patient_id,
        first_name=body.first_name,
        last_name=body.last_name,
        document_number=body.document_number,
        email=body.email,
        phone=body.phone if "phone" in sent else UNSET,
        birth_date=birth_date,
    )
    return PatientOut.from_domain(updated)


@router.post("/{patient_id}/deactivate")
def deactivate_patient(patient_id: str, deps: Patients, principal: StaffUser) -> DeactivationOut:
    result = use_cases.deactivate_patient(deps, principal, patient_id)
    return DeactivationOut(
        patient=PatientOut.from_domain(result.patient),
        upcoming_appointments=[
            UpcomingAppointmentOut.from_domain(a) for a in result.upcoming_appointments
        ],
    )


@router.post("/{patient_id}/reactivate")
def reactivate_patient(patient_id: str, deps: Patients, principal: StaffUser) -> PatientOut:
    return PatientOut.from_domain(use_cases.reactivate_patient(deps, principal, patient_id))


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: str, deps: Patients, principal: AdminUser) -> Response:
    use_cases.delete_patient(deps, principal, patient_id)
    return Response(status_code=204)

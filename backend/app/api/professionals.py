"""Endpoints de fichas, horarios semanales y licencias (spec professional-schedule-api).

Las escrituras exigen el rol admin en la ruta (require_role: 403 antes que 422, porque
FastAPI resuelve las dependencias antes de validar el cuerpo). Las lecturas exigen sesion y el
alcance del odontologo se aplica en el caso de uso (RN-AU-04, DD-53). Las horas entran como
HH:MM sin zona ni segundos; los instantes salen en UTC.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from app.api.appointments import EntityId
from app.api.dependencies import CurrentUser, Schedule, Treatments, require_role
from app.api.treatments import TreatmentOut
from app.api.validators import strip_text
from app.application import professionals as use_cases
from app.application import treatments as treatment_cases
from app.domain.appointments.types import WorkingHours
from app.domain.auth import Principal, Role
from app.domain.professionals import UNSET, Professional
from app.domain.schedules import TimeOffEntry
from app.domain.schedules.conflicts import ScheduleConflict

_admin_only = require_role(Role.ADMIN)
AdminUser = Annotated[Principal, Depends(_admin_only)]

router = APIRouter(prefix="/professionals", tags=["professionals"])

DisplayName = Annotated[str, BeforeValidator(strip_text), Field(min_length=1, max_length=200)]
LicenseNumber = Annotated[str, BeforeValidator(strip_text), Field(min_length=1, max_length=50)]
Reason = Annotated[str, BeforeValidator(strip_text), Field(max_length=500)]
# Solo HH:MM de 24 horas: rechaza segundos, zonas, numeros y "24:00" (design D-6).
ClockTime = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
# El dia fuera de 0 a 6 llega al dominio y responde INVALID_WORKING_HOURS (una sola fuente).
Weekday = Annotated[int, Field(strict=True)]


class ProfessionalOut(BaseModel):
    id: str
    display_name: str
    license_number: str | None
    active: bool

    @classmethod
    def from_domain(cls, professional: Professional) -> ProfessionalOut:
        return cls(
            id=professional.id,
            display_name=professional.display_name,
            license_number=professional.license_number,
            active=professional.active,
        )


class BlockBody(BaseModel):
    weekday: Weekday
    start_time: ClockTime
    end_time: ClockTime

    def to_domain(self) -> WorkingHours:
        return WorkingHours(
            weekday=self.weekday,
            start_time=time.fromisoformat(self.start_time),
            end_time=time.fromisoformat(self.end_time),
        )

    @classmethod
    def from_domain(cls, block: WorkingHours) -> BlockBody:
        return cls(
            weekday=block.weekday,
            start_time=block.start_time.strftime("%H:%M"),
            end_time=block.end_time.strftime("%H:%M"),
        )


class WorkingHoursBody(BaseModel):
    blocks: list[BlockBody]


class ConflictOut(BaseModel):
    appointment_id: str
    patient_id: str
    professional_id: str
    starts_at: datetime
    ends_at: datetime
    reason: str

    @classmethod
    def from_domain(cls, conflict: ScheduleConflict) -> ConflictOut:
        appointment = conflict.appointment
        return cls(
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            professional_id=appointment.professional_id,
            starts_at=appointment.starts_at.astimezone(UTC),
            ends_at=appointment.ends_at.astimezone(UTC),
            reason=conflict.reason.value,
        )


class WorkingHoursOut(BaseModel):
    blocks: list[BlockBody]


class WorkingHoursSavedOut(BaseModel):
    blocks: list[BlockBody]
    conflicts: list[ConflictOut]


class TimeOffOut(BaseModel):
    id: str
    starts_on: date
    ends_on: date
    reason: str | None

    @classmethod
    def from_domain(cls, entry: TimeOffEntry) -> TimeOffOut:
        return cls(
            id=entry.id, starts_on=entry.starts_on, ends_on=entry.ends_on, reason=entry.reason
        )


class TimeOffSavedOut(BaseModel):
    time_off: TimeOffOut
    conflicts: list[ConflictOut]


class UpdateProfessionalBody(BaseModel):
    """license_number null borra la matricula; un campo ausente no cambia (design D-4)."""

    display_name: DisplayName | None = None
    license_number: LicenseNumber | None = None


class ReplaceTreatmentsBody(BaseModel):
    """El conjunto completo asignado; como mucho 100 ids (spec treatment-api)."""

    model_config = ConfigDict(extra="forbid")

    treatment_ids: Annotated[list[EntityId], Field(max_length=100)]


class TimeOffBody(BaseModel):
    starts_on: date
    ends_on: date
    reason: Reason | None = None


@router.get("")
def list_files(deps: Schedule, principal: CurrentUser) -> list[ProfessionalOut]:
    return [ProfessionalOut.from_domain(p) for p in use_cases.list_professionals(deps, principal)]


@router.get("/{professional_id}")
def detail(professional_id: str, deps: Schedule, principal: CurrentUser) -> ProfessionalOut:
    return ProfessionalOut.from_domain(use_cases.get_professional(deps, principal, professional_id))


@router.patch("/{professional_id}")
def update(
    professional_id: str, body: UpdateProfessionalBody, deps: Schedule, principal: AdminUser
) -> ProfessionalOut:
    license_number = body.license_number if "license_number" in body.model_fields_set else UNSET
    updated = use_cases.update_professional(
        deps,
        principal,
        professional_id,
        display_name=body.display_name,
        license_number=license_number,
    )
    return ProfessionalOut.from_domain(updated)


@router.get("/{professional_id}/working-hours")
def read_working_hours(
    professional_id: str, deps: Schedule, principal: CurrentUser
) -> WorkingHoursOut:
    blocks = use_cases.get_working_hours(deps, principal, professional_id)
    return WorkingHoursOut(blocks=[BlockBody.from_domain(b) for b in blocks])


@router.put("/{professional_id}/working-hours")
def replace_working_hours(
    professional_id: str, body: WorkingHoursBody, deps: Schedule, principal: AdminUser
) -> WorkingHoursSavedOut:
    saved = use_cases.replace_working_hours(
        deps, principal, professional_id, [block.to_domain() for block in body.blocks]
    )
    return WorkingHoursSavedOut(
        blocks=[BlockBody.from_domain(b) for b in saved.blocks],
        conflicts=[ConflictOut.from_domain(c) for c in saved.conflicts],
    )


@router.get("/{professional_id}/time-off")
def list_time_off(professional_id: str, deps: Schedule, principal: CurrentUser) -> list[TimeOffOut]:
    return [
        TimeOffOut.from_domain(e) for e in use_cases.list_time_off(deps, principal, professional_id)
    ]


@router.post("/{professional_id}/time-off", status_code=201)
def add_time_off(
    professional_id: str, body: TimeOffBody, deps: Schedule, principal: AdminUser
) -> TimeOffSavedOut:
    saved = use_cases.add_time_off(
        deps, principal, professional_id, body.starts_on, body.ends_on, body.reason
    )
    return TimeOffSavedOut(
        time_off=TimeOffOut.from_domain(saved.time_off),
        conflicts=[ConflictOut.from_domain(c) for c in saved.conflicts],
    )


@router.delete("/{professional_id}/time-off/{time_off_id}", status_code=204)
def delete_time_off(
    professional_id: str, time_off_id: str, deps: Schedule, principal: AdminUser
) -> Response:
    use_cases.delete_time_off(deps, principal, professional_id, time_off_id)
    return Response(status_code=204)


@router.get("/{professional_id}/conflicts")
def conflicts(professional_id: str, deps: Schedule, principal: CurrentUser) -> list[ConflictOut]:
    return [
        ConflictOut.from_domain(c)
        for c in use_cases.list_conflicts(deps, principal, professional_id)
    ]


@router.get("/{professional_id}/treatments")
def read_treatments(
    professional_id: str, deps: Treatments, principal: CurrentUser
) -> list[TreatmentOut]:
    found = treatment_cases.list_professional_treatments(deps, principal, professional_id)
    return [TreatmentOut.from_domain(t) for t in found]


@router.put("/{professional_id}/treatments")
def replace_treatments(
    professional_id: str, body: ReplaceTreatmentsBody, deps: Treatments, principal: AdminUser
) -> list[TreatmentOut]:
    saved = treatment_cases.replace_professional_treatments(
        deps, principal, professional_id, body.treatment_ids
    )
    return [TreatmentOut.from_domain(t) for t in saved]

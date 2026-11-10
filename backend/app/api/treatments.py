"""Endpoints del catalogo de tratamientos (spec treatment-api, C-17).

Las lecturas exigen sesion (los tres roles); las escrituras exigen el rol admin en la ruta
(``require_role``: 403 antes que 422, porque FastAPI resuelve las dependencias antes de validar el
cuerpo). Los cuerpos rechazan campos desconocidos y el 422 no repite lo enviado.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.api.dependencies import CurrentUser, Treatments, require_role
from app.application import treatments as use_cases
from app.domain.auth import Principal, Role
from app.domain.treatments.rules import clean_treatment_name
from app.domain.treatments.types import Treatment

AdminUser = Annotated[Principal, Depends(require_role(Role.ADMIN))]

router = APIRouter(prefix="/treatments", tags=["treatments"])


def check_treatment_name(value: str) -> str:
    """Mismo largo y espacios que el dominio; el caso de uso guarda el nombre ya limpio."""
    clean_treatment_name(value)
    return value


TreatmentName = Annotated[str, Field(max_length=500), AfterValidator(check_treatment_name)]


class TreatmentOut(BaseModel):
    id: str
    name: str
    active: bool

    @classmethod
    def from_domain(cls, treatment: Treatment) -> TreatmentOut:
        return cls(id=treatment.id, name=treatment.name, active=treatment.active)


class CreateTreatmentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: TreatmentName


class UpdateTreatmentBody(BaseModel):
    """Un campo ausente no cambia (spec treatment-api)."""

    model_config = ConfigDict(extra="forbid")

    name: TreatmentName | None = None
    active: Annotated[bool | None, Field(strict=True)] = None


@router.get("")
def list_all(deps: Treatments, _principal: CurrentUser) -> list[TreatmentOut]:
    return [TreatmentOut.from_domain(t) for t in use_cases.list_treatments(deps)]


@router.post("", status_code=201)
def create(body: CreateTreatmentBody, deps: Treatments, principal: AdminUser) -> TreatmentOut:
    return TreatmentOut.from_domain(use_cases.create_treatment(deps, principal, name=body.name))


@router.patch("/{treatment_id}")
def update(
    treatment_id: str, body: UpdateTreatmentBody, deps: Treatments, principal: AdminUser
) -> TreatmentOut:
    updated = use_cases.update_treatment(
        deps, principal, treatment_id, name=body.name, active=body.active
    )
    return TreatmentOut.from_domain(updated)

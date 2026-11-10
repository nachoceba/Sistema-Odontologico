"""Casos de uso del catalogo de tratamientos y de lo que ofrece cada profesional (C-17, D-6).

Sin FastAPI ni SQLAlchemy. Las lecturas son de los tres roles (el odontologo solo ve la
asignacion propia, RN-AU-04); las escrituras son solo del administrador (DD-143), que ademas se
exige en la ruta con ``require_role`` (aca queda como defensa en profundidad).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.appointments.errors import ProfessionalNotFoundError
from app.domain.auth import ForbiddenError, Principal, Role, can_access_professional
from app.domain.professionals import ProfessionalRepository
from app.domain.treatments.errors import TreatmentNotFoundError
from app.domain.treatments.ports import TreatmentRepository
from app.domain.treatments.rules import clean_treatment_name
from app.domain.treatments.types import NewTreatment, Treatment


@dataclass(frozen=True)
class TreatmentDeps:
    treatments: TreatmentRepository
    professionals: ProfessionalRepository


def _require_admin(principal: Principal) -> None:
    if principal.role is not Role.ADMIN:
        raise ForbiddenError


def _require_professional(deps: TreatmentDeps, professional_id: str) -> None:
    if deps.professionals.get_by_id(professional_id) is None:
        raise ProfessionalNotFoundError


def list_treatments(deps: TreatmentDeps) -> list[Treatment]:
    """Todo el catalogo, activos e inactivos, ordenado por nombre."""
    return deps.treatments.list_all()


def create_treatment(deps: TreatmentDeps, principal: Principal, *, name: str) -> Treatment:
    """Alta de un tratamiento activo; nombre repetido sin mayusculas ni tildes: rechazado."""
    _require_admin(principal)
    return deps.treatments.add(NewTreatment(name=clean_treatment_name(name)))


def update_treatment(
    deps: TreatmentDeps,
    principal: Principal,
    treatment_id: str,
    *,
    name: str | None = None,
    active: bool | None = None,
) -> Treatment:
    """Cambia nombre y/o estado; un campo ausente no cambia. Nunca se borra un tratamiento."""
    _require_admin(principal)
    cleaned = None if name is None else clean_treatment_name(name)
    return deps.treatments.update(treatment_id, name=cleaned, active=active)


def list_professional_treatments(
    deps: TreatmentDeps, principal: Principal, professional_id: str
) -> list[Treatment]:
    """Los tratamientos asignados al profesional (activos e inactivos)."""
    if not can_access_professional(principal, professional_id):
        raise ForbiddenError
    _require_professional(deps, professional_id)
    return deps.treatments.list_for_professional(professional_id)


def replace_professional_treatments(
    deps: TreatmentDeps,
    principal: Principal,
    professional_id: str,
    treatment_ids: Sequence[str],
) -> list[Treatment]:
    """Reemplaza el conjunto completo; si algun id no existe no cambia nada (DD-141)."""
    _require_admin(principal)
    _require_professional(deps, professional_id)
    unique_ids = list(dict.fromkeys(treatment_ids))
    if any(deps.treatments.get(treatment_id) is None for treatment_id in unique_ids):
        raise TreatmentNotFoundError
    deps.treatments.replace_for_professional(professional_id, unique_ids)
    return deps.treatments.list_for_professional(professional_id)

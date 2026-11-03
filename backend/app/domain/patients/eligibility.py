"""Elegibilidad del paciente para recibir turnos nuevos. Solo libreria estandar."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EligibilityRejection(Enum):
    PATIENT_INACTIVE = "PATIENT_INACTIVE"


@dataclass(frozen=True)
class EligibilityResult:
    """Aceptado <=> reason ausente."""

    allowed: bool
    reason: EligibilityRejection | None = None

    @classmethod
    def accept(cls) -> EligibilityResult:
        return cls(allowed=True, reason=None)

    @classmethod
    def reject(cls, reason: EligibilityRejection) -> EligibilityResult:
        return cls(allowed=False, reason=reason)


def check_patient_can_book(active: bool) -> EligibilityResult:
    """RN-PA-04: un paciente inactivo (RN-PA-03) no recibe turnos nuevos.

    Independiente de las reglas de horario de validate_appointment. Decision P-5: el caso
    de uso (C-08) la aplica tambien al reprogramar; desactivar un paciente no cancela
    sus turnos futuros (se listan). ``active`` debe ser bool: otro tipo es un error del
    llamador (ValueError), para que el texto "false" no cuente como verdadero.
    """
    if not isinstance(active, bool):
        raise ValueError("active debe ser bool")
    if not active:
        return EligibilityResult.reject(EligibilityRejection.PATIENT_INACTIVE)
    return EligibilityResult.accept()

"""Repositorio de pacientes en memoria (solo lectura; el estado inicial se inyecta)."""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.patients.types import Patient


class InMemoryPatientRepository:
    def __init__(self, initial: Iterable[Patient] = ()) -> None:
        self._patients = {patient.id: patient for patient in initial}

    def get(self, patient_id: str) -> Patient | None:
        return self._patients.get(patient_id)

"""Repositorio de tratamientos en memoria: doble fiel del unico por ``name_key`` (C-17)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import replace
from uuid import uuid4

from app.domain.treatments.errors import TreatmentNameTakenError, TreatmentNotFoundError
from app.domain.treatments.rules import treatment_name_key
from app.domain.treatments.types import NewTreatment, Treatment


class InMemoryTreatmentRepository:
    def __init__(self) -> None:
        self._treatments: dict[str, Treatment] = {}
        self._assigned: dict[str, set[str]] = {}  # profesional -> ids de tratamientos

    def load(self, treatments: Iterable[Treatment]) -> None:
        """Carga tratamientos con id propio (para dejar ids conocidos en los tests)."""
        for treatment in treatments:
            self._treatments[treatment.id] = treatment

    def list_all(self) -> list[Treatment]:
        return self._sorted(self._treatments.values())

    def get(self, treatment_id: str) -> Treatment | None:
        return self._treatments.get(treatment_id)

    def add(self, new: NewTreatment) -> Treatment:
        self._require_free_name(new.name, except_id=None)
        saved = Treatment(id=str(uuid4()), name=new.name, active=True)
        self._treatments[saved.id] = saved
        return saved

    def update(
        self, treatment_id: str, *, name: str | None = None, active: bool | None = None
    ) -> Treatment:
        current = self._treatments.get(treatment_id)
        if current is None:
            raise TreatmentNotFoundError
        if name is not None:
            self._require_free_name(name, except_id=treatment_id)
            current = replace(current, name=name)
        if active is not None:
            current = replace(current, active=active)
        self._treatments[treatment_id] = current
        return current

    def list_for_professional(self, professional_id: str) -> list[Treatment]:
        return self._sorted(self._assigned_to(professional_id))

    def offered_ids(self, professional_id: str) -> frozenset[str]:
        return frozenset(t.id for t in self._assigned_to(professional_id) if t.active)

    def list_offered(self, professional_id: str) -> list[Treatment]:
        return self._sorted(t for t in self._assigned_to(professional_id) if t.active)

    def replace_for_professional(self, professional_id: str, treatment_ids: Sequence[str]) -> None:
        self._assigned[professional_id] = set(treatment_ids)

    def _assigned_to(self, professional_id: str) -> list[Treatment]:
        ids = self._assigned.get(professional_id, set())
        return [self._treatments[i] for i in ids if i in self._treatments]

    def _require_free_name(self, name: str, *, except_id: str | None) -> None:
        key = treatment_name_key(name)
        for other in self._treatments.values():
            if other.id != except_id and treatment_name_key(other.name) == key:
                raise TreatmentNameTakenError

    @staticmethod
    def _sorted(treatments: Iterable[Treatment]) -> list[Treatment]:
        return sorted(treatments, key=lambda t: (treatment_name_key(t.name), t.id))

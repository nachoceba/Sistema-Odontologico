"""Repositorios en memoria de horarios y licencias."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from uuid import uuid4

from app.domain.appointments.types import WorkingHours
from app.domain.schedules.types import TimeOffEntry


class InMemoryWorkingHoursRepository:
    def __init__(self) -> None:
        self._blocks: dict[str, list[WorkingHours]] = {}

    def list_for_professional(self, professional_id: str) -> list[WorkingHours]:
        blocks = self._blocks.get(professional_id, [])
        return sorted(blocks, key=lambda b: (b.weekday, b.start_time))

    def replace_for_professional(
        self, professional_id: str, blocks: Sequence[WorkingHours]
    ) -> None:
        self._blocks[professional_id] = list(blocks)


class InMemoryTimeOffRepository:
    def __init__(self) -> None:
        self._entries: list[TimeOffEntry] = []

    def add(
        self,
        professional_id: str,
        starts_on: date,
        ends_on: date,
        reason: str | None = None,
    ) -> TimeOffEntry:
        if ends_on < starts_on:
            raise ValueError("la licencia no puede terminar antes de empezar")
        entry = TimeOffEntry(
            id=str(uuid4()),
            professional_id=professional_id,
            starts_on=starts_on,
            ends_on=ends_on,
            reason=reason,
        )
        self._entries.append(entry)
        return entry

    def list_for_professional(self, professional_id: str) -> list[TimeOffEntry]:
        mine = [e for e in self._entries if e.professional_id == professional_id]
        return sorted(mine, key=lambda e: e.starts_on)

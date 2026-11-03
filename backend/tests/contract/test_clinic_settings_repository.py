"""Bateria de contrato de la configuracion del consultorio (spec clinic-settings-repository)."""

from __future__ import annotations

from datetime import date, time

from app.domain.appointments import SlotStatus, WorkingHours, compute_slots
from app.domain.settings.types import ClinicSettings
from tests.contract.conftest import RepositoryFactory


def test_defaults_when_nothing_is_configured(factory: RepositoryFactory) -> None:
    settings = factory.settings().get()
    assert settings.slot_minutes == 30
    assert settings.timezone == "America/Argentina/Buenos_Aires"
    assert settings.min_notice_hours == 6


def test_configured_values_are_returned(factory: RepositoryFactory) -> None:
    configured = ClinicSettings(slot_minutes=20, min_notice_hours=12)
    settings = factory.settings(configured).get()
    assert settings.slot_minutes == 20
    assert settings.min_notice_hours == 12
    assert settings.timezone == "America/Argentina/Buenos_Aires"


def test_configured_slot_changes_computed_slots(factory: RepositoryFactory) -> None:
    settings = factory.settings(ClinicSettings(slot_minutes=20)).get()
    slots = compute_slots(
        professional_id="dra-a",
        day=date(2026, 10, 5),
        working_hours=[WorkingHours(weekday=0, start_time=time(9), end_time=time(10))],
        time_off=[],
        existing_appointments=[],
        slot_minutes=settings.slot_minutes,
        timezone=settings.timezone,
    )
    free = [s for s in slots if s.status == SlotStatus.FREE]
    assert len(free) == 3
    assert [(s.ends_at - s.starts_at).total_seconds() for s in free] == [1200] * 3
    assert [s.starts_at.minute for s in free] == [0, 20, 40]

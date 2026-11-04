"""Reglas puras nuevas de C-08: precision de minutos (P-12b) y turno propio del paciente (P-3)."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.domain.appointments import Appointment, AppointmentStatus
from app.domain.appointments.rules import has_sub_minute_precision, patient_has_overlap
from tests.unit.domain.appointments.helpers import monday


def test_exact_minute_has_no_sub_minute_precision() -> None:
    assert not has_sub_minute_precision(monday(10, 0))


def test_seconds_count_as_sub_minute_precision() -> None:
    assert has_sub_minute_precision(monday(10, 0) + timedelta(seconds=30))


def test_fractions_of_a_second_count_as_sub_minute_precision() -> None:
    assert has_sub_minute_precision(monday(10, 0) + timedelta(milliseconds=500))


def _appointment(
    *,
    appointment_id: str = "t-1",
    patient_id: str = "pac-1",
    professional_id: str = "dra-a",
    starts_at: datetime,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
) -> Appointment:
    return Appointment(
        id=appointment_id,
        patient_id=patient_id,
        professional_id=professional_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=30),
        status=status,
        cancel_reason=None,
        created_by="rec-1",
    )


def _overlap(
    existing: list[Appointment], starts_at: datetime, exclude_id: str | None = None
) -> bool:
    return patient_has_overlap(
        "pac-1", starts_at, starts_at + timedelta(minutes=30), existing, exclude_id=exclude_id
    )


def test_same_time_with_another_professional_overlaps() -> None:
    existing = [_appointment(professional_id="dra-a", starts_at=monday(10))]
    assert _overlap(existing, monday(10))


def test_another_time_the_same_day_does_not_overlap() -> None:
    existing = [_appointment(starts_at=monday(10))]
    assert not _overlap(existing, monday(11))


def test_partial_overlap_counts() -> None:
    existing = [_appointment(starts_at=monday(10, 0))]
    assert _overlap(existing, monday(10, 15))


def test_cancelled_appointment_does_not_count() -> None:
    existing = [_appointment(starts_at=monday(10), status=AppointmentStatus.CANCELLED)]
    assert not _overlap(existing, monday(10))


def test_back_to_back_appointments_do_not_overlap() -> None:
    existing = [_appointment(starts_at=monday(9, 30))]
    assert not _overlap(existing, monday(10))


def test_another_patient_does_not_count() -> None:
    existing = [_appointment(patient_id="pac-2", starts_at=monday(10))]
    assert not _overlap(existing, monday(10))


def test_excluded_appointment_is_ignored_when_rescheduling() -> None:
    existing = [_appointment(appointment_id="t-1", starts_at=monday(10))]
    assert not _overlap(existing, monday(10, 15), exclude_id="t-1")
    assert _overlap(existing, monday(10, 15), exclude_id="otro")

"""Tipos con identidad y errores del repositorio de turnos (C-05d)."""

from __future__ import annotations

import dataclasses

import pytest

from app.domain.appointments import (
    Appointment,
    AppointmentNotFoundError,
    AppointmentStatus,
    ExistingAppointment,
    NewAppointment,
    SlotTakenError,
)
from tests.unit.domain.appointments.helpers import monday


def _appointment(status: AppointmentStatus = AppointmentStatus.SCHEDULED) -> Appointment:
    return Appointment(
        id="a-1",
        patient_id="pac-1",
        professional_id="dra-a",
        starts_at=monday(10),
        ends_at=monday(10, 30),
        status=status,
        cancel_reason=None,
        created_by="rec-1",
    )


@pytest.mark.parametrize("status", [AppointmentStatus.SCHEDULED, AppointmentStatus.CANCELLED])
def test_to_existing_keeps_professional_range_and_status(
    status: AppointmentStatus,
) -> None:
    assert _appointment(status).to_existing() == ExistingAppointment(
        professional_id="dra-a",
        starts_at=monday(10),
        ends_at=monday(10, 30),
        status=status,
    )


def test_appointment_and_new_appointment_are_immutable() -> None:
    new = NewAppointment(
        patient_id="pac-1",
        professional_id="dra-a",
        starts_at=monday(10),
        ends_at=monday(10, 30),
        created_by="rec-1",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        new.patient_id = "pac-2"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        _appointment().status = AppointmentStatus.CANCELLED  # type: ignore[misc]


def test_slot_taken_error_carries_professional_and_requested_start() -> None:
    error = SlotTakenError("dra-a", monday(10, 15))
    assert error.code == "SLOT_TAKEN"
    assert error.professional_id == "dra-a"
    assert error.starts_at == monday(10, 15)


def test_appointment_not_found_error_carries_id() -> None:
    error = AppointmentNotFoundError("a-9")
    assert error.code == "APPOINTMENT_NOT_FOUND"
    assert error.appointment_id == "a-9"
    assert "a-9" in str(error)

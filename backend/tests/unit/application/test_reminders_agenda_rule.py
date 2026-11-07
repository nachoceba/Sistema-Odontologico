"""Regla dura 6 con la tarea de recordatorios registrada: la agenda sigue sin superposiciones.

La pasada no escribe turnos y agendar dos veces el mismo horario sigue dando ``SlotTakenError``
(spec reminder-scheduling y notification-tasks).
"""

from __future__ import annotations

import pytest

from app.application.appointments import book_appointment
from app.application.reminders import send_reminders
from app.domain.appointments import AppointmentStatus
from app.domain.appointments.errors import SlotTakenError
from app.infrastructure.tasks.notifications import enviar_recordatorios
from tests.unit.application.agenda_helpers import PROF_A, PROF_B, RECEPTION
from tests.unit.application.reminder_helpers import ReminderWorld
from tests.unit.domain.appointments.helpers import monday


def book(scenario: ReminderWorld, patient_id: str, professional_id: str = PROF_A) -> str:
    saved = book_appointment(
        scenario.world.deps(),
        RECEPTION,
        patient_id=patient_id,
        professional_id=professional_id,
        starts_at=monday(10),
    )
    return saved.id


def test_with_the_reminder_task_registered_booking_the_same_slot_twice_is_slot_taken() -> None:
    assert enviar_recordatorios.name == "enviar_recordatorios"
    scenario = ReminderWorld()
    book(scenario, "pac-1")

    with pytest.raises(SlotTakenError):
        book(scenario, "pac-2")

    scheduled = [a for a in scenario.world.everything() if a.status is AppointmentStatus.SCHEDULED]
    assert len(scheduled) == 1


def test_another_professional_can_take_the_same_time_and_both_get_a_reminder() -> None:
    scenario = ReminderWorld()
    book(scenario, "pac-1", PROF_A)
    book(scenario, "pac-2", PROF_B)

    summary = send_reminders(scenario.deps())

    assert summary.sent == 2


def test_the_reminder_pass_writes_no_appointment_and_the_slot_stays_taken() -> None:
    scenario = ReminderWorld()
    book(scenario, "pac-1")
    before = scenario.world.everything()

    summary = send_reminders(scenario.deps())

    assert summary.sent == 1
    assert scenario.world.everything() == before
    with pytest.raises(SlotTakenError):
        book(scenario, "pac-2")
    assert scenario.world.everything() == before

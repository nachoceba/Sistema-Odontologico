"""Consulta de turnos en conflicto (spec professional-schedule-use-cases)."""

from __future__ import annotations

from datetime import time

import pytest

from app.application.appointments import cancel_appointment, reschedule_appointment
from app.application.professionals import list_conflicts
from app.domain.appointments import WorkingHours
from app.domain.appointments.errors import ProfessionalNotFoundError
from app.domain.auth import ForbiddenError
from app.domain.schedules.conflicts import ConflictReason
from tests.unit.application.agenda_helpers import (
    ADMIN,
    DENTIST_A,
    DENTIST_B,
    DENTIST_NO_FILE,
    PROF_A,
    PROF_B,
    RECEPTION,
    World,
)
from tests.unit.domain.appointments.helpers import monday

UNKNOWN = "99999999-9999-4999-8999-999999999999"


def world_with_late_appointment() -> World:
    """La Dra. A atiende los lunes 09:00-13:00 y tiene un turno futuro a las 16:00."""
    world = World()
    world.working_hours.replace_for_professional(PROF_A, [WorkingHours(0, time(9), time(13))])
    world.seed(monday(16))
    return world


def test_reception_sees_the_pending_conflicts_with_reason() -> None:
    world = world_with_late_appointment()
    conflicts = list_conflicts(world.schedule_deps(), RECEPTION, PROF_A)
    assert [(c.appointment.starts_at, c.reason) for c in conflicts] == [
        (monday(16), ConflictReason.OUTSIDE_WORKING_HOURS)
    ]


def test_admin_and_own_dentist_can_consult() -> None:
    deps = world_with_late_appointment().schedule_deps()
    assert len(list_conflicts(deps, ADMIN, PROF_A)) == 1
    assert len(list_conflicts(deps, DENTIST_A, PROF_A)) == 1


def test_cancelling_the_appointment_removes_it_from_the_list() -> None:
    world = world_with_late_appointment()
    appointment = world.everything()[0]
    cancel_appointment(world.deps(), appointment.id, "Cambio de horario")
    assert list_conflicts(world.schedule_deps(), RECEPTION, PROF_A) == []


def test_rescheduling_to_a_valid_slot_removes_it_from_the_list() -> None:
    world = world_with_late_appointment()
    appointment = world.everything()[0]
    reschedule_appointment(world.deps(), appointment.id, monday(10))
    assert list_conflicts(world.schedule_deps(), RECEPTION, PROF_A) == []


def test_professional_without_conflicts_returns_an_empty_list() -> None:
    world = world_with_late_appointment()
    world.seed(monday(10), professional_id=PROF_B, patient_id="pac-2")
    assert list_conflicts(world.schedule_deps(), RECEPTION, PROF_B) == []


@pytest.mark.parametrize("principal", [DENTIST_B, DENTIST_NO_FILE])
def test_a_dentist_cannot_consult_someone_elses_conflicts(principal: object) -> None:
    deps = world_with_late_appointment().schedule_deps()
    with pytest.raises(ForbiddenError):
        list_conflicts(deps, principal, PROF_A)  # type: ignore[arg-type]


def test_unknown_professional_is_not_found() -> None:
    with pytest.raises(ProfessionalNotFoundError):
        list_conflicts(World().schedule_deps(), ADMIN, UNKNOWN)

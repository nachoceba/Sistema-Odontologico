"""Caso de uso agendar con repositorios en memoria y reloj fijo (spec appointment-use-cases)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.application.appointments import book_appointment
from app.core.errors import DomainError
from app.domain.appointments import Appointment, AppointmentStatus, NotificationKind
from app.domain.appointments.errors import (
    InsufficientNoticeError,
    OffGridError,
    OutsideWorkingHoursError,
    PatientDoubleBookedError,
    PatientInactiveError,
    PatientNotFoundError,
    ProfessionalInactiveError,
    ProfessionalNotFoundError,
    ProfessionalTimeOffError,
    SlotTakenError,
)
from app.domain.treatments.errors import TreatmentNotAvailableError, TreatmentNotFoundError
from tests.unit.application.agenda_helpers import PROF_A, PROF_B, RECEPTION, World
from tests.unit.domain.appointments.helpers import monday

NIL_PROFESSIONAL = "99999999-9999-4999-8999-999999999999"
MONDAY_DATE = monday(10).date()  # 2026-10-05 (13:00 UTC es el mismo dia)


def _book(
    world: World,
    starts_at: datetime,
    *,
    patient_id: str = "pac-1",
    professional_id: str = PROF_A,
    treatment_id: str | None = None,
) -> Appointment:
    return book_appointment(
        world.deps(),
        RECEPTION,
        patient_id=patient_id,
        professional_id=professional_id,
        treatment_id=treatment_id or world.treatment_id,
        starts_at=starts_at,
    )


def _assert_rejected(
    world: World,
    error_class: type[DomainError],
    starts_at: datetime,
    *,
    patient_id: str = "pac-1",
    professional_id: str = PROF_A,
    treatment_id: str | None = None,
) -> None:
    before = world.everything(professional_id)
    with pytest.raises(error_class):
        _book(
            world,
            starts_at,
            patient_id=patient_id,
            professional_id=professional_id,
            treatment_id=treatment_id,
        )
    assert world.everything(professional_id) == before  # un rechazo no escribe nada


# --- Agendar un turno ----------------------------------------------------------------------


def test_books_a_free_slot_with_the_clinic_duration_and_the_creator() -> None:
    world = World()

    saved = _book(world, monday(10))

    assert saved.status is AppointmentStatus.SCHEDULED
    assert saved.starts_at == monday(10)
    assert saved.ends_at == monday(10, 30)
    assert saved.starts_at.utcoffset() == timedelta(0)
    assert saved.starts_at.hour == 13  # 10:00 hora del consultorio = 13:00 UTC
    assert saved.created_by == RECEPTION.user_id
    assert world.appointments.get(saved.id) == saved


def test_a_taken_slot_is_rejected_as_slot_taken() -> None:
    world = World()
    world.seed(monday(10), patient_id="pac-2")
    _assert_rejected(world, SlotTakenError, monday(10))


def test_a_partially_overlapping_slot_is_rejected_as_slot_taken() -> None:
    world = World()
    world.seed(monday(10, 0), patient_id="pac-2")
    _assert_rejected(world, SlotTakenError, monday(10, 0))


def test_a_slot_that_ends_after_the_working_block_is_rejected() -> None:
    world = World(slot_minutes=45)
    _assert_rejected(world, OutsideWorkingHoursError, monday(12, 45))


def test_a_start_between_blocks_is_rejected_as_outside_working_hours() -> None:
    world = World()
    _assert_rejected(world, OutsideWorkingHoursError, monday(13, 30))


def test_insufficient_notice_is_rejected() -> None:
    world = World(now=monday(8))
    _assert_rejected(world, InsufficientNoticeError, monday(10))


def test_a_start_in_the_past_is_rejected_as_insufficient_notice() -> None:
    world = World(now=monday(11))
    _assert_rejected(world, InsufficientNoticeError, monday(10))


def test_exactly_the_minimum_notice_is_accepted() -> None:
    world = World(now=monday(4))
    _book(world, monday(10))
    assert len(world.everything()) == 1


def test_one_minute_short_of_the_notice_is_rejected() -> None:
    world = World(now=monday(4, 1))
    _assert_rejected(world, InsufficientNoticeError, monday(10))


def test_a_time_off_day_is_rejected() -> None:
    world = World()
    world.time_off.add(PROF_A, MONDAY_DATE, MONDAY_DATE)
    _assert_rejected(world, ProfessionalTimeOffError, monday(10))


def test_off_grid_start_is_rejected() -> None:
    world = World()
    _assert_rejected(world, OffGridError, monday(10, 10))


def test_a_start_with_seconds_is_rejected_as_off_grid() -> None:
    world = World()
    _assert_rejected(world, OffGridError, monday(10) + timedelta(seconds=30))


def test_a_start_with_microseconds_is_rejected_as_off_grid() -> None:
    world = World()
    _assert_rejected(world, OffGridError, monday(10) + timedelta(microseconds=1))


def test_an_inactive_patient_is_rejected() -> None:
    world = World()
    _assert_rejected(world, PatientInactiveError, monday(10), patient_id="pac-off")


def test_an_inactive_professional_is_rejected() -> None:
    world = World()
    world.set_professional_active(PROF_A, False)
    _assert_rejected(world, ProfessionalInactiveError, monday(10))


def test_unknown_patient_and_unknown_professional_are_rejected() -> None:
    world = World()
    _assert_rejected(world, PatientNotFoundError, monday(10), patient_id="no-existe")
    _assert_rejected(world, ProfessionalNotFoundError, monday(10), professional_id=NIL_PROFESSIONAL)


def test_unknown_patient_wins_over_an_invalid_start() -> None:
    world = World()
    _assert_rejected(world, PatientNotFoundError, monday(10, 10), patient_id="no-existe")


def test_unknown_professional_wins_over_an_inactive_patient() -> None:
    world = World()
    _assert_rejected(
        world,
        ProfessionalNotFoundError,
        monday(10),
        patient_id="pac-off",
        professional_id=NIL_PROFESSIONAL,
    )


def test_back_to_back_appointments_are_accepted() -> None:
    world = World()
    world.seed(monday(10))
    _book(world, monday(10, 30), patient_id="pac-2")
    assert len(world.everything()) == 2


def test_a_cancelled_appointment_frees_the_slot() -> None:
    world = World()
    cancelled = world.seed(monday(10))
    world.appointments.change_status(cancelled.id, AppointmentStatus.CANCELLED, "aviso")
    _book(world, monday(10), patient_id="pac-2")
    scheduled = [a for a in world.everything() if a.status is AppointmentStatus.SCHEDULED]
    assert len(scheduled) == 1


def test_the_duration_comes_from_the_clinic_settings() -> None:
    world = World(slot_minutes=20)
    saved = _book(world, monday(9, 40))
    assert saved.ends_at == monday(10, 0)


def test_another_professional_uses_their_own_schedule() -> None:
    world = World()
    saved = _book(world, monday(9), professional_id=PROF_B)
    assert saved.professional_id == PROF_B
    # Dr. B no atiende por la tarde: su horario es solo de 09:00 a 13:00
    _assert_rejected(world, OutsideWorkingHoursError, monday(15), professional_id=PROF_B)


def test_a_start_given_in_another_zone_is_the_same_instant() -> None:
    world = World()
    plus_three = monday(10).astimezone(timezone(timedelta(hours=3)))
    assert plus_three.hour == 16
    saved = _book(world, plus_three)
    assert saved.starts_at == monday(10)


# --- Un paciente no tiene dos turnos superpuestos ------------------------------------------


def test_same_time_with_another_professional_is_double_booked() -> None:
    world = World()
    world.seed(monday(10), patient_id="pac-1", professional_id=PROF_A)
    _assert_rejected(
        world, PatientDoubleBookedError, monday(10), patient_id="pac-1", professional_id=PROF_B
    )


def test_same_day_in_another_time_is_accepted() -> None:
    world = World()
    world.seed(monday(10), patient_id="pac-1", professional_id=PROF_A)
    _book(world, monday(11), patient_id="pac-1", professional_id=PROF_B)
    assert len(world.everything(PROF_B)) == 1


def test_cancelled_or_back_to_back_turns_of_the_patient_do_not_block() -> None:
    world = World()
    cancelled = world.seed(monday(10), patient_id="pac-1", professional_id=PROF_A)
    world.appointments.change_status(cancelled.id, AppointmentStatus.CANCELLED, "aviso")
    world.seed(monday(9, 30), patient_id="pac-1", professional_id=PROF_B)

    _book(world, monday(10), patient_id="pac-1", professional_id=PROF_B)

    assert len(world.everything(PROF_B)) == 2


def test_the_taken_slot_wins_over_the_double_booking() -> None:
    world = World()
    world.seed(monday(10), patient_id="pac-1", professional_id=PROF_A)
    world.seed(monday(10), patient_id="pac-2", professional_id=PROF_B)
    _assert_rejected(world, SlotTakenError, monday(10), patient_id="pac-1", professional_id=PROF_B)


# --- Tratamiento (C-17, DD-142) ------------------------------------------------------------


def test_books_with_the_chosen_treatment_and_registers_the_confirmation() -> None:
    world = World()

    saved = _book(world, monday(10), treatment_id=world.limpieza.id)

    assert saved.treatment_id == world.limpieza.id
    assert world.appointments.get(saved.id) == saved
    kinds = [n.kind for n in world.notifications.list_for_appointment(saved.id)]
    assert kinds == [NotificationKind.CONFIRMATION]
    assert saved.ends_at - saved.starts_at == timedelta(minutes=30)  # la duracion no cambia


def test_two_treatments_book_consecutive_slots_of_the_same_duration() -> None:
    world = World()
    first = _book(world, monday(10), treatment_id=world.consulta.id)
    second = _book(world, monday(10, 30), treatment_id=world.limpieza.id)
    assert first.ends_at - first.starts_at == second.ends_at - second.starts_at
    assert first.ends_at == second.starts_at


def test_a_treatment_the_professional_does_not_offer_is_rejected() -> None:
    world = World()
    # "Limpieza dental" la ofrece solo la Dra. A.
    _assert_rejected(
        world,
        TreatmentNotAvailableError,
        monday(10),
        professional_id=PROF_B,
        treatment_id=world.limpieza.id,
    )


def test_an_inactive_treatment_is_rejected_even_when_assigned() -> None:
    world = World()
    world.treatments.update(world.limpieza.id, active=False)
    _assert_rejected(world, TreatmentNotAvailableError, monday(10), treatment_id=world.limpieza.id)


def test_an_unknown_treatment_is_rejected_as_not_found() -> None:
    world = World()
    _assert_rejected(world, TreatmentNotFoundError, monday(10), treatment_id="no-existe")


def test_the_treatment_is_checked_before_the_schedule() -> None:
    world = World()
    world.treatments.update(world.limpieza.id, active=False)
    # 10:10 esta fuera de la grilla, pero el tratamiento se chequea antes.
    _assert_rejected(
        world, TreatmentNotAvailableError, monday(10, 10), treatment_id=world.limpieza.id
    )


def test_inactive_patient_and_professional_are_rejected_before_the_treatment() -> None:
    world = World()
    world.set_patient_active("pac-1", False)
    _assert_rejected(world, PatientInactiveError, monday(10), treatment_id="no-existe")
    world.set_patient_active("pac-1", True)
    world.set_professional_active(PROF_A, False)
    _assert_rejected(world, ProfessionalInactiveError, monday(10), treatment_id="no-existe")


def test_a_taken_slot_with_another_treatment_is_still_slot_taken() -> None:
    world = World()
    world.seed(monday(10), patient_id="pac-2", treatment_id=world.consulta.id)
    _assert_rejected(world, SlotTakenError, monday(10), treatment_id=world.limpieza.id)


def test_the_treatment_is_checked_before_the_patient_overlap() -> None:
    world = World()
    world.seed(monday(10), patient_id="pac-1", professional_id=PROF_B)
    world.treatments.update(world.limpieza.id, active=False)
    # pac-1 ya tiene turno a esa hora (RN-TU-06 aparte), pero el tratamiento se chequea antes.
    _assert_rejected(world, TreatmentNotAvailableError, monday(10), treatment_id=world.limpieza.id)

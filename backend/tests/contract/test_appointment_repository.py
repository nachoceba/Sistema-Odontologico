"""Bateria de contrato del repositorio de turnos (spec appointment-repository)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.timezone import local_day_bounds
from app.domain.appointments import (
    Appointment,
    AppointmentNotFoundError,
    AppointmentRepository,
    AppointmentStatus,
    NewAppointment,
    RejectionReason,
    SlotTakenError,
    validate_appointment,
)
from tests.unit.domain.appointments.helpers import (
    DRA_A_HOURS,
    NOW,
    local,
    monday,
)

BA = "America/Argentina/Buenos_Aires"
SCHEDULED = AppointmentStatus.SCHEDULED
MONDAY_DATE = date(2026, 10, 5)


def book(
    repo: AppointmentRepository,
    start: datetime,
    end: datetime,
    *,
    professional: str = "dra-a",
    patient: str = "pac-1",
) -> Appointment:
    return repo.add(
        NewAppointment(
            patient_id=patient,
            professional_id=professional,
            starts_at=start,
            ends_at=end,
            created_by="rec-1",
        )
    )


def day_of(repo: AppointmentRepository, professional: str, day: date) -> list[Appointment]:
    start, end = local_day_bounds(day, BA)
    return repo.list_for_professional(professional, start, end)


# --- Guardar y buscar -------------------------------------------------------------


def test_add_returns_scheduled_appointment_retrievable_by_id(
    appointment_repo: AppointmentRepository,
) -> None:
    saved = book(appointment_repo, monday(10), monday(10, 30))
    assert saved.id
    assert saved.status == SCHEDULED
    assert saved.cancel_reason is None
    found = appointment_repo.get(saved.id)
    assert found == saved
    assert found is not None
    assert (found.patient_id, found.professional_id, found.created_by) == (
        "pac-1",
        "dra-a",
        "rec-1",
    )
    assert (found.starts_at, found.ends_at) == (monday(10), monday(10, 30))


def test_two_saved_appointments_get_distinct_ids(
    appointment_repo: AppointmentRepository,
) -> None:
    first = book(appointment_repo, monday(10), monday(10, 30))
    second = book(appointment_repo, monday(10, 30), monday(11))
    assert first.id != second.id


def test_same_instant_in_other_zone_is_retrieved_equal(
    appointment_repo: AppointmentRepository,
) -> None:
    tz = timezone(timedelta(hours=-3))
    saved = book(
        appointment_repo,
        datetime(2026, 10, 5, 10, 0, tzinfo=tz),
        datetime(2026, 10, 5, 10, 30, tzinfo=tz),
    )
    found = appointment_repo.get(saved.id)
    assert found is not None
    assert found.starts_at == monday(10)
    assert found.ends_at == monday(10, 30)


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(datetime(2026, 10, 5, 13, 0), monday(10, 30), id="inicio_sin_zona"),
        pytest.param(monday(10), datetime(2026, 10, 5, 13, 30), id="fin_sin_zona"),
        pytest.param(monday(10, 30), monday(10, 30), id="inicio_igual_fin"),
        pytest.param(monday(10, 30), monday(10), id="inicio_posterior_fin"),
    ],
)
def test_add_rejects_invalid_range_and_stays_empty(
    appointment_repo: AppointmentRepository, start: datetime, end: datetime
) -> None:
    with pytest.raises(ValueError):
        book(appointment_repo, start, end)
    assert day_of(appointment_repo, "dra-a", MONDAY_DATE) == []


def test_get_unknown_id_returns_none_without_error(
    appointment_repo: AppointmentRepository,
) -> None:
    book(appointment_repo, monday(10), monday(10, 30))
    assert appointment_repo.get("no-existe") is None


# --- No solapamiento (regla dura 6, RN-TU-01) -------------------------------------


def test_overlapping_second_appointment_is_rejected_and_listing_unchanged(
    appointment_repo: AppointmentRepository,
) -> None:
    book(appointment_repo, monday(10), monday(10, 30))
    with pytest.raises(SlotTakenError) as raised:
        book(appointment_repo, monday(10, 15), monday(10, 45))
    assert raised.value.professional_id == "dra-a"
    assert raised.value.starts_at == monday(10, 15)
    assert len(day_of(appointment_repo, "dra-a", MONDAY_DATE)) == 1


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(monday(10), monday(10, 30), id="mismo_horario"),
        pytest.param(monday(9, 30), monday(11), id="contiene_a_otro"),
        pytest.param(monday(10, 15), monday(10, 45), id="cruza_el_final"),
        pytest.param(monday(9, 45), monday(10, 15), id="cruza_el_inicio"),
    ],
)
def test_overlapping_ranges_are_rejected(
    appointment_repo: AppointmentRepository, start: datetime, end: datetime
) -> None:
    book(appointment_repo, monday(10), monday(10, 30), patient="pac-1")
    with pytest.raises(SlotTakenError):
        book(appointment_repo, start, end, patient="pac-2")


def test_overlap_across_midnight_is_compared_by_instants(
    appointment_repo: AppointmentRepository,
) -> None:
    book(appointment_repo, local(2026, 10, 5, 23, 45), local(2026, 10, 6, 0, 15))
    with pytest.raises(SlotTakenError):
        book(appointment_repo, local(2026, 10, 6, 0, 0), local(2026, 10, 6, 0, 30))


@pytest.mark.parametrize(
    ("start", "end", "professional", "patient"),
    [
        pytest.param(monday(9, 30), monday(10), "dra-a", "pac-2", id="pegado_antes"),
        pytest.param(monday(10, 30), monday(11), "dra-a", "pac-2", id="pegado_despues"),
        pytest.param(monday(10), monday(10, 30), "dr-b", "pac-2", id="otro_profesional"),
        pytest.param(
            monday(10),
            monday(10, 30),
            "dr-b",
            "pac-1",
            id="mismo_paciente_otro_profesional",
        ),
    ],
)
def test_non_conflicting_appointments_are_accepted(
    appointment_repo: AppointmentRepository,
    start: datetime,
    end: datetime,
    professional: str,
    patient: str,
) -> None:
    book(appointment_repo, monday(10), monday(10, 30), patient="pac-1")
    saved = book(appointment_repo, start, end, professional=professional, patient=patient)
    assert appointment_repo.get(saved.id) == saved


def test_cancelled_appointment_does_not_block(
    appointment_repo: AppointmentRepository,
) -> None:
    first = book(appointment_repo, monday(10), monday(10, 30))
    appointment_repo.change_status(first.id, AppointmentStatus.CANCELLED, "Aviso")
    book(appointment_repo, monday(10), monday(10, 30), patient="pac-2")
    statuses = [a.status.value for a in day_of(appointment_repo, "dra-a", MONDAY_DATE)]
    assert sorted(statuses) == ["cancelled", "scheduled"]


@pytest.mark.parametrize("status", [AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW])
def test_completed_or_no_show_appointments_do_not_block(
    appointment_repo: AppointmentRepository, status: AppointmentStatus
) -> None:
    first = book(appointment_repo, monday(10), monday(10, 30))
    appointment_repo.change_status(first.id, status)
    saved = book(appointment_repo, monday(10, 15), monday(10, 45), patient="pac-2")
    assert appointment_repo.get(saved.id) == saved


# --- Cambiar estado ---------------------------------------------------------------


def test_cancel_with_reason_frees_the_slot(
    appointment_repo: AppointmentRepository,
) -> None:
    saved = book(appointment_repo, monday(10), monday(10, 30))
    changed = appointment_repo.change_status(
        saved.id, AppointmentStatus.CANCELLED, "El paciente aviso por telefono"
    )
    assert changed.status == AppointmentStatus.CANCELLED
    found = appointment_repo.get(saved.id)
    assert found is not None
    assert found.status == AppointmentStatus.CANCELLED
    assert found.cancel_reason == "El paciente aviso por telefono"
    book(appointment_repo, monday(10), monday(10, 30), patient="pac-2")


def test_mark_completed_has_no_cancel_reason(
    appointment_repo: AppointmentRepository,
) -> None:
    saved = book(appointment_repo, monday(10), monday(10, 30))
    appointment_repo.change_status(saved.id, AppointmentStatus.COMPLETED)
    found = appointment_repo.get(saved.id)
    assert found is not None
    assert found.status == AppointmentStatus.COMPLETED
    assert found.cancel_reason is None


def test_back_to_scheduled_over_taken_slot_is_rejected_and_stays_cancelled(
    appointment_repo: AppointmentRepository,
) -> None:
    cancelled = book(appointment_repo, monday(10), monday(10, 30))
    appointment_repo.change_status(cancelled.id, AppointmentStatus.CANCELLED, "x")
    book(appointment_repo, monday(10), monday(10, 30), patient="pac-2")
    with pytest.raises(SlotTakenError):
        appointment_repo.change_status(cancelled.id, SCHEDULED)
    found = appointment_repo.get(cancelled.id)
    assert found is not None
    assert found.status == AppointmentStatus.CANCELLED


def test_change_status_of_unknown_appointment_raises_not_found(
    appointment_repo: AppointmentRepository,
) -> None:
    with pytest.raises(AppointmentNotFoundError) as raised:
        appointment_repo.change_status("no-existe", AppointmentStatus.CANCELLED, "x")
    assert raised.value.appointment_id == "no-existe"


# --- Reprogramar ------------------------------------------------------------------


def test_reschedule_to_free_slot_keeps_identity_and_frees_old_slot(
    appointment_repo: AppointmentRepository,
) -> None:
    saved = book(appointment_repo, monday(10), monday(10, 30))
    moved = appointment_repo.reschedule(saved.id, monday(11), monday(11, 30))
    assert moved.id == saved.id
    assert (moved.patient_id, moved.professional_id) == ("pac-1", "dra-a")
    found = appointment_repo.get(saved.id)
    assert found is not None
    assert (found.starts_at, found.ends_at) == (monday(11), monday(11, 30))
    book(appointment_repo, monday(10), monday(10, 30), patient="pac-2")


def test_reschedule_over_taken_slot_raises_and_leaves_original_untouched(
    appointment_repo: AppointmentRepository,
) -> None:
    mine = book(appointment_repo, monday(10), monday(10, 30), patient="pac-1")
    book(appointment_repo, monday(11), monday(11, 30), patient="pac-2")
    with pytest.raises(SlotTakenError):
        appointment_repo.reschedule(mine.id, monday(11), monday(11, 30))
    assert appointment_repo.get(mine.id) == mine


def test_reschedule_overlapping_own_previous_slot_is_accepted(
    appointment_repo: AppointmentRepository,
) -> None:
    saved = book(appointment_repo, monday(10), monday(10, 30))
    moved = appointment_repo.reschedule(saved.id, monday(10, 15), monday(10, 45))
    assert (moved.starts_at, moved.ends_at) == (monday(10, 15), monday(10, 45))


def test_reschedule_unknown_appointment_raises_not_found(
    appointment_repo: AppointmentRepository,
) -> None:
    with pytest.raises(AppointmentNotFoundError):
        appointment_repo.reschedule("no-existe", monday(11), monday(11, 30))


def test_reschedule_with_invalid_range_raises_value_error_and_keeps_original(
    appointment_repo: AppointmentRepository,
) -> None:
    saved = book(appointment_repo, monday(10), monday(10, 30))
    with pytest.raises(ValueError):
        appointment_repo.reschedule(saved.id, monday(11), monday(11))
    assert appointment_repo.get(saved.id) == saved


# --- Listados ---------------------------------------------------------------------


def test_professional_day_listing_includes_all_statuses_ordered_by_start(
    appointment_repo: AppointmentRepository,
) -> None:
    later = book(appointment_repo, monday(11), monday(11, 30))
    appointment_repo.change_status(later.id, AppointmentStatus.CANCELLED, "x")
    first = book(appointment_repo, monday(10), monday(10, 30))
    book(appointment_repo, local(2026, 10, 6, 10), local(2026, 10, 6, 10, 30))
    book(appointment_repo, monday(10), monday(10, 30), professional="dr-b")
    listed = day_of(appointment_repo, "dra-a", MONDAY_DATE)
    assert [a.id for a in listed] == [first.id, later.id]
    assert listed[1].status == AppointmentStatus.CANCELLED


def test_listing_range_is_half_open(appointment_repo: AppointmentRepository) -> None:
    book(appointment_repo, monday(9, 30), monday(10))
    inside = book(appointment_repo, monday(10), monday(10, 30))
    book(appointment_repo, monday(11), monday(11, 30))
    listed = appointment_repo.list_for_professional("dra-a", monday(10), monday(11))
    assert [a.id for a in listed] == [inside.id]


def test_midnight_crossing_appointment_appears_on_both_days(
    appointment_repo: AppointmentRepository,
) -> None:
    crossing = book(appointment_repo, local(2026, 10, 5, 23, 45), local(2026, 10, 6, 0, 15))
    monday_ids = [a.id for a in day_of(appointment_repo, "dra-a", date(2026, 10, 5))]
    tuesday_ids = [a.id for a in day_of(appointment_repo, "dra-a", date(2026, 10, 6))]
    assert monday_ids == [crossing.id]
    assert tuesday_ids == [crossing.id]


def test_listing_without_upper_bound_returns_future_appointments(
    appointment_repo: AppointmentRepository,
) -> None:
    book(appointment_repo, monday(10), monday(10, 30))
    friday = book(appointment_repo, local(2026, 10, 9, 10), local(2026, 10, 9, 10, 30))
    next_monday = book(appointment_repo, local(2026, 10, 12, 10), local(2026, 10, 12, 10, 30))
    listed = appointment_repo.list_for_professional("dra-a", local(2026, 10, 6, 0))
    assert [a.id for a in listed] == [friday.id, next_monday.id]


def test_listing_professional_without_appointments_is_empty(
    appointment_repo: AppointmentRepository,
) -> None:
    book(appointment_repo, monday(10), monday(10, 30), professional="dr-b")
    assert day_of(appointment_repo, "dra-a", MONDAY_DATE) == []


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(datetime(2026, 10, 5, 0, 0), None, id="desde_sin_zona"),
        pytest.param(monday(10), datetime(2026, 10, 5, 12, 0), id="hasta_sin_zona"),
        pytest.param(monday(10), monday(10), id="desde_igual_hasta"),
        pytest.param(monday(11), monday(10), id="desde_posterior_hasta"),
    ],
)
def test_listing_rejects_invalid_range(
    appointment_repo: AppointmentRepository, start: datetime, end: datetime | None
) -> None:
    with pytest.raises(ValueError):
        appointment_repo.list_for_professional("dra-a", start, end)
    with pytest.raises(ValueError):
        appointment_repo.list_for_patient("pac-1", start, end)


def test_returned_list_is_a_copy(appointment_repo: AppointmentRepository) -> None:
    book(appointment_repo, monday(10), monday(10, 30))
    listed = day_of(appointment_repo, "dra-a", MONDAY_DATE)
    listed.clear()
    assert len(day_of(appointment_repo, "dra-a", MONDAY_DATE)) == 1


def test_patient_listing_spans_professionals_ordered_by_start(
    appointment_repo: AppointmentRepository,
) -> None:
    afternoon = book(
        appointment_repo, monday(15), monday(15, 30), professional="dr-b", patient="pac-1"
    )
    morning = book(appointment_repo, monday(10), monday(10, 30), patient="pac-1")
    book(appointment_repo, monday(11), monday(11, 30), patient="pac-2")
    listed = appointment_repo.list_for_patient("pac-1", local(2026, 10, 5, 0))
    assert [a.id for a in listed] == [morning.id, afternoon.id]


def test_patient_without_appointments_lists_empty(
    appointment_repo: AppointmentRepository,
) -> None:
    book(appointment_repo, monday(10), monday(10, 30), patient="pac-2")
    assert appointment_repo.list_for_patient("pac-1", local(2026, 10, 5, 0)) == []


# --- Integracion con las reglas de dominio ----------------------------------------


def test_listing_feeds_validate_appointment_which_rejects_overlap(
    appointment_repo: AppointmentRepository,
) -> None:
    book(appointment_repo, monday(10), monday(10, 30))
    existing = [a.to_existing() for a in day_of(appointment_repo, "dra-a", MONDAY_DATE)]
    result = validate_appointment(
        professional_id="dra-a",
        starts_at=monday(10),
        now=NOW,
        working_hours=DRA_A_HOURS,
        time_off=[],
        existing_appointments=existing,
    )
    assert result.reason == RejectionReason.OVERLAPS_EXISTING

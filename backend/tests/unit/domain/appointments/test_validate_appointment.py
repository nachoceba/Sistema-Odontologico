from datetime import date, datetime, time, timezone

import pytest

from app.domain.appointments import (
    AppointmentStatus,
    RejectionReason,
    validate_appointment,
)

from app.domain.appointments import TimeOff, WorkingHours

from .helpers import (
    DR_B_HOURS,
    DRA_A_HOURS,
    MONDAY,
    NOW,
    appointment,
    local,
    monday,
    validate,
)


def test_accepts_free_slot_and_computes_ends_at() -> None:
    result = validate(monday(10, 0))

    assert result.accepted is True
    assert result.ends_at == local(2026, 10, 5, 10, 30)
    assert result.reason is None


def test_utc_instant_is_evaluated_in_clinic_local_time() -> None:
    # 13:00 UTC == 10:00 en Buenos Aires (UTC-3): cae dentro del horario 09-13.
    starts_at_utc = datetime(2026, 10, 5, 13, 0, tzinfo=timezone.utc)

    result = validate(starts_at_utc)

    assert result.accepted is True
    assert result.ends_at == datetime(2026, 10, 5, 13, 30, tzinfo=timezone.utc)


def test_naive_datetime_raises_value_error() -> None:
    naive_start = datetime(2026, 10, 5, 10, 0)  # sin zona: error de programacion

    with pytest.raises(ValueError):
        validate(naive_start)


def test_naive_now_raises_value_error() -> None:
    with pytest.raises(ValueError):
        validate_appointment(
            professional_id="dra-a",
            starts_at=monday(10, 0),
            now=datetime(2026, 10, 3, 10, 0),
            working_hours=DRA_A_HOURS,
            time_off=[],
            existing_appointments=[],
        )



# --- Anticipacion minima (RN-TU-12) -----------------------------------------


def test_rejects_insufficient_notice() -> None:
    result = validate(monday(10, 0), now=monday(5, 0))  # faltan 5 h

    assert result.accepted is False
    assert result.reason == RejectionReason.INSUFFICIENT_NOTICE
    assert result.ends_at is None


def test_accepts_exactly_min_notice() -> None:
    result = validate(monday(10, 0), now=monday(4, 0))  # faltan exactamente 6 h

    assert result.accepted is True
    assert result.ends_at == monday(10, 30)


def test_rejects_start_in_the_past() -> None:
    result = validate(monday(10, 0), now=monday(11, 0))

    assert result.accepted is False
    assert result.reason == RejectionReason.INSUFFICIENT_NOTICE


def test_rejects_with_configured_12h_notice() -> None:
    sunday_23 = local(2026, 10, 4, 23, 0)

    result = validate(monday(10, 0), now=sunday_23, min_notice_hours=12)  # faltan 11 h

    assert result.accepted is False
    assert result.reason == RejectionReason.INSUFFICIENT_NOTICE


# --- Grilla de slots (RN-TU-02) ----------------------------------------------


def test_rejects_off_grid_start() -> None:
    result = validate(monday(10, 10))

    assert result.accepted is False
    assert result.reason == RejectionReason.OFF_GRID


def test_rejects_off_grid_start_in_second_block() -> None:
    result = validate(monday(14, 20))

    assert result.accepted is False
    assert result.reason == RejectionReason.OFF_GRID


def test_grid_is_anchored_to_block_start() -> None:
    dr_b_offset_hours = [WorkingHours(MONDAY, time(9, 15), time(13, 15))]

    result = validate(
        monday(9, 45), professional_id="dr-b", working_hours=dr_b_offset_hours
    )

    assert result.accepted is True
    assert result.ends_at == monday(10, 15)


def test_hour_on_the_hour_is_off_grid_when_block_starts_at_09_15() -> None:
    dr_b_offset_hours = [WorkingHours(MONDAY, time(9, 15), time(13, 15))]

    result = validate(
        monday(10, 0), professional_id="dr-b", working_hours=dr_b_offset_hours
    )

    assert result.accepted is False
    assert result.reason == RejectionReason.OFF_GRID


# --- Horario de trabajo (RN-TU-03) -------------------------------------------


def test_rejects_before_working_hours() -> None:
    result = validate(monday(8, 30))

    assert result.accepted is False
    assert result.reason == RejectionReason.OUTSIDE_WORKING_HOURS


def test_rejects_gap_between_blocks() -> None:
    result = validate(monday(13, 0))

    assert result.accepted is False
    assert result.reason == RejectionReason.OUTSIDE_WORKING_HOURS


def test_accepts_last_slot_ending_at_block_end() -> None:
    result = validate(monday(12, 30))

    assert result.accepted is True
    assert result.ends_at == monday(13, 0)


def test_rejects_day_without_working_hours() -> None:
    tuesday_10 = local(2026, 10, 6, 10, 0)

    result = validate(tuesday_10)

    assert result.accepted is False
    assert result.reason == RejectionReason.OUTSIDE_WORKING_HOURS


def test_rejects_slot_that_would_end_after_block_end() -> None:
    short_block = [WorkingHours(MONDAY, time(9, 0), time(13, 15))]

    result = validate(monday(13, 0), working_hours=short_block)  # 13:00-13:30 > 13:15

    assert result.accepted is False
    assert result.reason == RejectionReason.OUTSIDE_WORKING_HOURS


# --- Licencias (RN-TU-03, RN-HO-03) ------------------------------------------


def test_rejects_on_last_day_of_time_off() -> None:
    leave = [TimeOff(starts_on=date(2026, 10, 1), ends_on=date(2026, 10, 5))]

    result = validate(monday(10, 0), time_off=leave)

    assert result.accepted is False
    assert result.reason == RejectionReason.PROFESSIONAL_TIME_OFF


def test_accepts_day_after_time_off_ends() -> None:
    leave = [TimeOff(starts_on=date(2026, 9, 28), ends_on=date(2026, 10, 4))]

    result = validate(monday(10, 0), time_off=leave)

    assert result.accepted is True
    assert result.ends_at == monday(10, 30)


def test_accepts_day_before_time_off_starts() -> None:
    leave = [TimeOff(starts_on=date(2026, 10, 6), ends_on=date(2026, 10, 8))]

    result = validate(monday(10, 0), time_off=leave)

    assert result.accepted is True


def test_rejects_on_first_day_of_time_off() -> None:
    leave = [TimeOff(starts_on=date(2026, 10, 5), ends_on=date(2026, 10, 9))]

    result = validate(monday(10, 0), time_off=leave)

    assert result.accepted is False
    assert result.reason == RejectionReason.PROFESSIONAL_TIME_OFF


# --- No solapamiento (RN-TU-01) ----------------------------------------------


def test_rejects_overlap_with_same_professional() -> None:
    booked = [appointment("dra-a", monday(10, 0), monday(10, 30))]

    result = validate(monday(10, 0), existing_appointments=booked)

    assert result.accepted is False
    assert result.reason == RejectionReason.OVERLAPS_EXISTING


def test_accepts_back_to_back_after_existing() -> None:
    booked = [appointment("dra-a", monday(10, 0), monday(10, 30))]

    result = validate(monday(10, 30), existing_appointments=booked)

    assert result.accepted is True
    assert result.ends_at == monday(11, 0)


def test_accepts_back_to_back_before_existing() -> None:
    booked = [appointment("dra-a", monday(10, 0), monday(10, 30))]

    result = validate(monday(9, 30), existing_appointments=booked)

    assert result.accepted is True
    assert result.ends_at == monday(10, 0)


def test_accepts_same_time_other_professional() -> None:
    booked = [appointment("dra-a", monday(10, 0), monday(10, 30))]

    result = validate(
        monday(10, 0),
        professional_id="dr-b",
        working_hours=DR_B_HOURS,
        existing_appointments=booked,
    )

    assert result.accepted is True
    assert result.ends_at == monday(10, 30)


def test_cancelled_appointment_does_not_block() -> None:
    booked = [
        appointment(
            "dra-a", monday(10, 0), monday(10, 30), status=AppointmentStatus.CANCELLED
        )
    ]

    result = validate(monday(10, 0), existing_appointments=booked)

    assert result.accepted is True
    assert result.ends_at == monday(10, 30)


@pytest.mark.parametrize(
    "status", [AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW]
)
def test_non_scheduled_statuses_do_not_block(status: AppointmentStatus) -> None:
    booked = [appointment("dra-a", monday(10, 0), monday(10, 30), status=status)]

    result = validate(monday(10, 0), existing_appointments=booked)

    assert result.accepted is True


@pytest.mark.parametrize("start", [(10, 0), (10, 30)])
def test_rejects_partial_overlap_with_misaligned_existing(start: tuple[int, int]) -> None:
    booked = [appointment("dra-a", monday(10, 15), monday(10, 45))]

    result = validate(monday(*start), existing_appointments=booked)

    assert result.accepted is False
    assert result.reason == RejectionReason.OVERLAPS_EXISTING


# --- Orden fijo de evaluacion ------------------------------------------------


def test_notice_wins_over_off_grid() -> None:
    result = validate(monday(10, 10), now=monday(8, 0))  # 2 h de anticipacion y 10:10

    assert result.accepted is False
    assert result.reason == RejectionReason.INSUFFICIENT_NOTICE


def test_time_off_wins_over_overlap() -> None:
    leave = [TimeOff(starts_on=date(2026, 10, 5), ends_on=date(2026, 10, 5))]
    booked = [appointment("dra-a", monday(10, 0), monday(10, 30))]

    result = validate(monday(10, 0), time_off=leave, existing_appointments=booked)

    assert result.accepted is False
    assert result.reason == RejectionReason.PROFESSIONAL_TIME_OFF


def test_off_grid_wins_over_time_off() -> None:
    leave = [TimeOff(starts_on=date(2026, 10, 5), ends_on=date(2026, 10, 5))]

    result = validate(monday(10, 10), time_off=leave)

    assert result.reason == RejectionReason.OFF_GRID

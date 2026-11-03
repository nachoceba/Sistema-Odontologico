"""Tests de compute_slots (spec slot-availability). Datos ficticios."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import pytest

from app.domain.appointments import (
    AppointmentStatus,
    ExistingAppointment,
    Slot,
    SlotStatus,
    TimeOff,
    WorkingHours,
    compute_slots,
    validate_appointment,
)

from .helpers import (
    DRA_A_HOURS,
    MONDAY,
    NOW,
    appointment,
    count_by_status,
    local,
    monday,
    slot_at,
)

FREE = SlotStatus.FREE
BUSY = SlotStatus.BUSY
OUT = SlotStatus.OUTSIDE_HOURS
MONDAY_DATE = date(2026, 10, 5)
TUESDAY_DATE = date(2026, 10, 6)


def slots_for_monday(
    *,
    working_hours: Sequence[WorkingHours] = DRA_A_HOURS,
    time_off: Sequence[TimeOff] = (),
    existing_appointments: Sequence[ExistingAppointment] = (),
    slot_minutes: int = 30,
    day: date = MONDAY_DATE,
    professional_id: str = "dra-a",
    timezone: str = "America/Argentina/Buenos_Aires",
) -> list[Slot]:
    return compute_slots(
        professional_id=professional_id,
        day=day,
        working_hours=working_hours,
        time_off=time_off,
        existing_appointments=existing_appointments,
        slot_minutes=slot_minutes,
        timezone=timezone,
    )


def hours(*ranges: tuple[tuple[int, int], tuple[int, int]]) -> list[WorkingHours]:
    return [WorkingHours(MONDAY, time(*start), time(*end)) for start, end in ranges]


def sched(
    start: tuple[int, int],
    end: tuple[int, int],
    who: str = "dra-a",
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
) -> ExistingAppointment:
    return appointment(who, monday(*start), monday(*end), status)


def assert_statuses(slots: Sequence[Slot], expected: dict[tuple[int, int], SlotStatus]) -> None:
    for (hour, minute), status in expected.items():
        assert slot_at(slots, hour, minute).status is status, (hour, minute)


# --- Franjas del dia local completo, ordenadas y en UTC ----------------------


def test_monday_without_appointments_returns_full_local_day() -> None:
    slots = slots_for_monday()

    assert len(slots) == 48
    assert count_by_status(slots) == {"FREE": 16, "OUTSIDE_HOURS": 32}
    assert_statuses(
        slots,
        {(9, 0): FREE, (12, 30): FREE, (13, 0): OUT, (14, 0): FREE, (17, 30): FREE, (18, 0): OUT},
    )


def test_slots_are_contiguous_and_in_utc() -> None:
    slots = slots_for_monday()

    assert slots[0].starts_at == local(2026, 10, 5, 0, 0)
    assert slots[0].ends_at == slots[0].starts_at + timedelta(minutes=30)
    nine = slot_at(slots, 9, 0)
    assert (nine.starts_at.hour, nine.starts_at.minute) == (12, 0)
    assert (nine.ends_at.hour, nine.ends_at.minute) == (12, 30)
    assert (slots[0].starts_at.day, slots[0].starts_at.hour) == (5, 3)
    assert slots[-1].ends_at == local(2026, 10, 6, 0, 0)
    assert (slots[-1].ends_at.day, slots[-1].ends_at.hour) == (6, 3)
    for slot in slots:
        assert slot.starts_at.utcoffset() == timedelta(0)
        assert slot.ends_at.utcoffset() == timedelta(0)
    for previous, following in zip(slots, slots[1:], strict=False):
        assert previous.ends_at == following.starts_at


# --- Grilla anclada al tramo y franja que no entra completa ------------------


@pytest.mark.parametrize(
    ("working_hours", "slot_minutes", "expected", "ends"),
    [
        pytest.param(
            hours(((14, 0), (15, 45))),
            30,
            {(14, 0): FREE, (14, 30): FREE, (15, 0): FREE, (15, 30): OUT, (15, 45): OUT},
            {(15, 30): (15, 45)},
            id="tramo_14_a_1545_resto_1530_outside",
        ),
        pytest.param(
            hours(((9, 15), (13, 15))),
            30,
            {(9, 0): OUT, (9, 15): FREE, (9, 45): FREE, (12, 45): FREE},
            {(9, 0): (9, 15), (12, 45): (13, 15)},
            id="dr_b_tramo_0915_grilla_anclada",
        ),
        pytest.param(
            hours(((9, 0), (13, 0))),
            45,
            {
                (9, 0): FREE,
                (9, 45): FREE,
                (10, 30): FREE,
                (11, 15): FREE,
                (12, 0): FREE,
                (12, 45): OUT,
            },
            {(12, 0): (12, 45), (12, 45): (13, 0)},
            id="slot_45_ultimo_libre_1200_resto_1245",
        ),
        pytest.param(
            hours(((9, 0), (13, 15)), ((13, 15), (17, 0))),
            30,
            {(12, 30): FREE, (13, 0): OUT, (13, 15): FREE},
            {(12, 30): (13, 0), (13, 0): (13, 15), (13, 15): (13, 45)},
            id="tramos_contiguos_1315_anclas_distintas",
        ),
    ],
)
def test_grid_and_partial_remainder(
    working_hours: list[WorkingHours],
    slot_minutes: int,
    expected: dict[tuple[int, int], SlotStatus],
    ends: dict[tuple[int, int], tuple[int, int]],
) -> None:
    slots = slots_for_monday(working_hours=working_hours, slot_minutes=slot_minutes)

    assert_statuses(slots, expected)
    for (hour, minute), (end_hour, end_minute) in ends.items():
        assert slot_at(slots, hour, minute).ends_at == monday(end_hour, end_minute)


def test_dr_b_has_eight_free_slots() -> None:
    slots = slots_for_monday(working_hours=hours(((9, 15), (13, 15))))

    assert count_by_status(slots)["FREE"] == 8


@pytest.mark.parametrize("slot_minutes", [30, 45])
def test_only_outside_hours_slots_can_be_shorter(slot_minutes: int) -> None:
    slots = slots_for_monday(
        working_hours=hours(((9, 15), (13, 20)), ((14, 0), (17, 0))),
        slot_minutes=slot_minutes,
    )

    for slot in slots:
        if slot.status is not OUT:
            assert slot.ends_at - slot.starts_at == timedelta(minutes=slot_minutes)


# --- Ocupacion ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("existing", "expected"),
    [
        pytest.param(
            [sched((10, 0), (10, 30))],
            {(10, 0): BUSY, (9, 30): FREE, (10, 30): FREE},
            id="scheduled_1000_busy_pegados_libres",
        ),
        pytest.param(
            [sched((10, 0), (10, 30), status=AppointmentStatus.CANCELLED)],
            {(10, 0): FREE},
            id="cancelado_libera_1000",
        ),
        pytest.param(
            [
                sched((10, 0), (10, 30), status=AppointmentStatus.COMPLETED),
                sched((11, 0), (11, 30), status=AppointmentStatus.NO_SHOW),
            ],
            {(10, 0): FREE, (11, 0): FREE},
            id="completed_y_no_show_no_ocupan",
        ),
        pytest.param(
            [sched((10, 0), (10, 30), who="dr-b")],
            {(10, 0): FREE},
            id="turno_de_dr_b_no_ocupa_dra_a",
        ),
        pytest.param(
            [sched((10, 15), (10, 45))],
            {(10, 0): BUSY, (10, 30): BUSY, (9, 30): FREE, (11, 0): FREE},
            id="desalineado_1015_ocupa_1000_y_1030",
        ),
        pytest.param(
            [sched((10, 0), (10, 30)), sched((10, 30), (11, 0))],
            {(10, 0): BUSY, (10, 30): BUSY, (9, 30): FREE, (11, 0): FREE},
            id="consecutivos_1000_y_1030_ambos_busy",
        ),
    ],
)
def test_occupancy(
    existing: list[ExistingAppointment], expected: dict[tuple[int, int], SlotStatus]
) -> None:
    assert_statuses(slots_for_monday(existing_appointments=existing), expected)


# --- Licencias ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("time_off", "day", "expected_counts"),
    [
        pytest.param(
            [TimeOff(date(2026, 10, 1), date(2026, 10, 5))],
            MONDAY_DATE,
            {"OUTSIDE_HOURS": 48},
            id="licencia_jueves_a_lunes_todo_outside",
        ),
        pytest.param(
            [TimeOff(MONDAY_DATE, MONDAY_DATE)],
            MONDAY_DATE,
            {"OUTSIDE_HOURS": 48},
            id="licencia_un_dia_lunes_5_sin_free",
        ),
        pytest.param(
            [TimeOff(MONDAY_DATE, MONDAY_DATE)],
            date(2026, 10, 12),
            {"FREE": 16, "OUTSIDE_HOURS": 32},
            id="licencia_un_dia_lunes_12_libre",
        ),
    ],
)
def test_time_off(time_off: list[TimeOff], day: date, expected_counts: dict[str, int]) -> None:
    slots = slots_for_monday(time_off=time_off, day=day)

    assert len(slots) == 48
    assert count_by_status(slots) == expected_counts


# --- Precedencia de estados --------------------------------------------------


@pytest.mark.parametrize(
    ("time_off", "existing", "expected"),
    [
        pytest.param(
            [TimeOff(MONDAY_DATE, MONDAY_DATE)],
            [sched((10, 0), (10, 30))],
            {(10, 0): OUT},
            id="licencia_prevalece_sobre_scheduled_1000",
        ),
        pytest.param(
            [],
            [sched((13, 0), (13, 30))],
            {(13, 0): OUT, (12, 30): FREE, (14, 0): FREE},
            id="scheduled_1300_en_hueco_queda_outside",
        ),
    ],
)
def test_state_precedence(
    time_off: list[TimeOff],
    existing: list[ExistingAppointment],
    expected: dict[tuple[int, int], SlotStatus],
) -> None:
    slots = slots_for_monday(time_off=time_off, existing_appointments=existing)

    assert_statuses(slots, expected)


# --- Dia sin tramos y limites del dia local ----------------------------------


@pytest.mark.parametrize(
    ("day", "expected_counts"),
    [
        pytest.param(TUESDAY_DATE, {"OUTSIDE_HOURS": 48}, id="martes_sin_tramos_48_outside"),
    ],
)
def test_day_without_working_hours(day: date, expected_counts: dict[str, int]) -> None:
    slots = slots_for_monday(day=day)

    assert len(slots) == 48
    assert count_by_status(slots) == expected_counts


def test_local_day_boundaries_utc_tuesday_is_local_monday() -> None:
    start_utc = datetime(2026, 10, 6, 0, 0, tzinfo=UTC)  # lunes 21:00 local
    existing = [appointment("dr-c", start_utc, start_utc + timedelta(minutes=30))]

    slots = slots_for_monday(
        professional_id="dr-c",
        working_hours=hours(((18, 0), (22, 0))),
        existing_appointments=existing,
    )

    assert start_utc.date() != MONDAY_DATE
    assert_statuses(slots, {(21, 0): BUSY, (20, 30): FREE})


def test_local_day_boundaries_tuesday_midnight_does_not_touch_monday() -> None:
    start_utc = datetime(2026, 10, 6, 3, 0, tzinfo=UTC)  # martes 00:00 local
    existing = [appointment("dr-c", start_utc, start_utc + timedelta(minutes=30))]

    slots = slots_for_monday(
        professional_id="dr-c",
        working_hours=hours(((18, 0), (22, 0))),
        existing_appointments=existing,
    )

    assert "BUSY" not in count_by_status(slots)
    assert slots[-1].ends_at == start_utc


def test_appointment_crossing_local_midnight() -> None:
    tuesday_hours = [WorkingHours(1, time(0, 0), time(2, 0))]
    crossing = appointment("dr-d", local(2026, 10, 5, 23, 45), local(2026, 10, 6, 0, 15))

    tuesday_slots = slots_for_monday(
        professional_id="dr-d",
        day=TUESDAY_DATE,
        working_hours=tuesday_hours,
        existing_appointments=[crossing],
    )
    monday_slots = slots_for_monday(
        professional_id="dr-d", working_hours=tuesday_hours, existing_appointments=[crossing]
    )

    assert slot_at(tuesday_slots, 0, 0, day=(2026, 10, 6)).status is BUSY
    assert slot_at(tuesday_slots, 0, 30, day=(2026, 10, 6)).status is FREE
    assert slot_at(monday_slots, 23, 30).status is OUT


# --- Sin anticipacion minima -------------------------------------------------


def test_slots_ignore_min_notice() -> None:
    now = monday(8, 0)

    slots = slots_for_monday()
    result = validate_appointment(
        professional_id="dra-a",
        starts_at=monday(10, 0),
        now=now,
        working_hours=DRA_A_HOURS,
        time_off=[],
        existing_appointments=[],
    )

    assert slot_at(slots, 10, 0).status is FREE
    assert result.accepted is False
    assert result.reason is not None and result.reason.name == "INSUFFICIENT_NOTICE"


# --- Entradas invalidas ------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"slot_minutes": 0}, id="slot_minutes_cero"),
        pytest.param({"slot_minutes": -30}, id="slot_minutes_negativo"),
        pytest.param({"day": "2026-10-05"}, id="day_texto"),
        pytest.param({"day": datetime(2026, 10, 5, 10, 0)}, id="day_datetime"),
    ],
)
def test_invalid_inputs_raise_value_error(overrides: dict[str, Any]) -> None:
    params: dict[str, Any] = {
        "professional_id": "dra-a",
        "day": MONDAY_DATE,
        "working_hours": DRA_A_HOURS,
        "time_off": [],
        "existing_appointments": [],
        **overrides,
    }
    with pytest.raises(ValueError):
        compute_slots(**params)


# --- Coherencia con validate_appointment ------------------------------------


def test_every_free_slot_is_accepted_by_validate_appointment() -> None:
    existing = [
        sched((10, 15), (10, 45)),
        sched((15, 0), (15, 30), status=AppointmentStatus.CANCELLED),
    ]

    slots = slots_for_monday(existing_appointments=existing)
    free = [slot for slot in slots if slot.status is FREE]

    assert len(free) == 14
    for slot in free:
        result = validate_appointment(
            professional_id="dra-a",
            starts_at=slot.starts_at,
            now=NOW,
            working_hours=DRA_A_HOURS,
            time_off=[],
            existing_appointments=existing,
        )
        assert result.accepted is True, slot
        assert result.ends_at == slot.ends_at

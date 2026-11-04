"""Endpoints de profesionales, horarios y licencias (spec professional-schedule-api)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.unit.api.conftest import ScheduleScene, bearer, login_token
from tests.unit.application.agenda_helpers import PROF_A, PROF_B
from tests.unit.domain.appointments.helpers import DRA_A_HOURS, monday

BASE_A = f"/api/v1/professionals/{PROF_A}"
BASE_B = f"/api/v1/professionals/{PROF_B}"


def admin_headers(client: TestClient) -> dict[str, str]:
    return bearer(login_token(client, "admin@example.com"))


def block(weekday: int, start: str, end: str) -> dict[str, Any]:
    return {"weekday": weekday, "start_time": start, "end_time": end}


# --- Fichas -----------------------------------------------------------------------------------


def test_list_returns_all_files_without_account_data(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    response = auth_client.get("/api/v1/professionals", headers=admin_headers(auth_client))
    assert response.status_code == 200
    rows = response.json()
    assert {row["id"] for row in rows} == {PROF_A, PROF_B}
    for row in rows:
        assert set(row) == {"id", "display_name", "license_number", "active"}


def test_detail_does_not_expose_the_account(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    headers = bearer(login_token(auth_client, "recepcion@example.com"))
    body = auth_client.get(BASE_A, headers=headers).json()
    assert body == {
        "id": PROF_A,
        "display_name": "u-dra-a",
        "license_number": None,
        "active": True,
    }
    assert "email" not in body
    assert "password_hash" not in body


def test_patch_changes_name_and_license_and_absent_field_keeps_the_value(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    headers = admin_headers(auth_client)
    first = auth_client.patch(
        BASE_A,
        json={"display_name": "  Dra. Ana Pérez ", "license_number": "MN-5"},
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["display_name"] == "Dra. Ana Pérez"
    assert first.json()["license_number"] == "MN-5"
    only_name = auth_client.patch(BASE_A, json={"display_name": "Dra. A"}, headers=headers).json()
    assert (only_name["display_name"], only_name["license_number"]) == ("Dra. A", "MN-5")
    cleared = auth_client.patch(BASE_A, json={"license_number": None}, headers=headers).json()
    assert (cleared["display_name"], cleared["license_number"]) == ("Dra. A", None)
    assert auth_client.get(BASE_A, headers=headers).json()["license_number"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"display_name": "   "},
        {"display_name": "x" * 201},
        {"license_number": ""},
        {"license_number": "y" * 51},
    ],
)
def test_patch_rejects_invalid_texts_with_422_and_changes_nothing(
    auth_client: TestClient, schedule: ScheduleScene, body: dict[str, Any]
) -> None:
    before = schedule.snapshot()
    response = auth_client.patch(BASE_A, json=body, headers=admin_headers(auth_client))
    assert response.status_code == 422
    assert schedule.snapshot() == before


# --- Horario ----------------------------------------------------------------------------------


def test_put_replaces_the_hours_and_returns_blocks_and_conflicts(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    turno = schedule.world.seed(monday(16))
    response = auth_client.put(
        f"{BASE_A}/working-hours",
        json={"blocks": [block(0, "09:00", "13:00")]},
        headers=admin_headers(auth_client),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["blocks"] == [block(0, "09:00", "13:00")]
    assert [(c["appointment_id"], c["reason"]) for c in body["conflicts"]] == [
        (turno.id, "OUTSIDE_WORKING_HOURS")
    ]
    conflict = body["conflicts"][0]
    assert conflict["patient_id"] == "pac-1"
    assert conflict["professional_id"] == PROF_A
    assert conflict["starts_at"].startswith("2026-10-05T19:00:00")
    assert conflict["ends_at"].startswith("2026-10-05T19:30:00")
    assert schedule.world.everything() == [turno]


def test_get_working_hours_returns_text_times_ordered(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    body = auth_client.get(f"{BASE_A}/working-hours", headers=admin_headers(auth_client)).json()
    assert body == {"blocks": [block(0, "09:00", "13:00"), block(0, "14:00", "18:00")]}
    assert len(DRA_A_HOURS) == 2


def test_put_with_an_empty_list_empties_the_week(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    response = auth_client.put(
        f"{BASE_B}/working-hours", json={"blocks": []}, headers=admin_headers(auth_client)
    )
    assert response.status_code == 200
    assert response.json() == {"blocks": [], "conflicts": []}


@pytest.mark.parametrize("value", ["09:00:30", "09:00Z", "24:00", "9:00", 900, "09:00+03:00", None])
def test_invalid_time_formats_are_422_without_echo(
    auth_client: TestClient, schedule: ScheduleScene, value: object
) -> None:
    before = schedule.snapshot()
    response = auth_client.put(
        f"{BASE_A}/working-hours",
        json={"blocks": [{"weekday": 0, "start_time": value, "end_time": "13:00"}]},
        headers=admin_headers(auth_client),
    )
    assert response.status_code == 422
    assert "09:00" not in response.text.replace("13:00", "")
    assert "input" not in response.text
    assert schedule.snapshot() == before


def test_put_without_blocks_is_422(auth_client: TestClient, schedule: ScheduleScene) -> None:
    response = auth_client.put(
        f"{BASE_A}/working-hours", json={}, headers=admin_headers(auth_client)
    )
    assert response.status_code == 422


def test_overlapping_blocks_are_400_naming_the_blocks_and_nothing_changes(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    before = schedule.snapshot()
    response = auth_client.put(
        f"{BASE_A}/working-hours",
        json={"blocks": [block(0, "09:00", "13:00"), block(0, "12:00", "15:00")]},
        headers=admin_headers(auth_client),
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_WORKING_HOURS"
    assert "Los tramos 1 y 2 se superponen" in error["message"]
    assert "12:00" not in error["message"]
    assert schedule.snapshot() == before


def test_weekday_seven_and_inverted_block_are_400(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    before = schedule.snapshot()
    headers = admin_headers(auth_client)
    for bad in (block(7, "09:00", "10:00"), block(1, "18:00", "09:00")):
        response = auth_client.put(
            f"{BASE_A}/working-hours", json={"blocks": [bad]}, headers=headers
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_WORKING_HOURS"
    assert schedule.snapshot() == before


def test_slots_endpoint_keeps_working_after_the_change(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    headers = admin_headers(auth_client)
    auth_client.put(
        f"{BASE_A}/working-hours", json={"blocks": [block(0, "09:00", "10:00")]}, headers=headers
    )
    slots = auth_client.get(
        f"{BASE_A}/slots", params={"date": "2026-10-05"}, headers=headers
    ).json()
    assert [s["status"] for s in slots if s["status"] == "FREE"] == ["FREE", "FREE"]


# --- Licencias --------------------------------------------------------------------------------


def test_post_time_off_returns_201_with_the_entry_and_conflicts(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    turno = schedule.world.seed(monday(10))
    response = auth_client.post(
        f"{BASE_A}/time-off",
        json={"starts_on": "2026-10-05", "ends_on": "2026-10-06", "reason": "  Congreso  "},
        headers=admin_headers(auth_client),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["time_off"]["id"]
    assert {k: body["time_off"][k] for k in ("starts_on", "ends_on", "reason")} == {
        "starts_on": "2026-10-05",
        "ends_on": "2026-10-06",
        "reason": "Congreso",
    }
    assert [(c["appointment_id"], c["reason"]) for c in body["conflicts"]] == [
        (turno.id, "TIME_OFF")
    ]


def test_post_time_off_without_reason_stores_null(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    body = auth_client.post(
        f"{BASE_B}/time-off",
        json={"starts_on": "2026-11-02", "ends_on": "2026-11-02", "reason": "   "},
        headers=admin_headers(auth_client),
    ).json()
    assert body["time_off"]["reason"] is None


def test_time_off_end_before_start_is_400(auth_client: TestClient, schedule: ScheduleScene) -> None:
    response = auth_client.post(
        f"{BASE_A}/time-off",
        json={"starts_on": "2026-10-16", "ends_on": "2026-10-12"},
        headers=admin_headers(auth_client),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_TIME_OFF"


@pytest.mark.parametrize(
    "body",
    [
        {"starts_on": "2026-10-12", "ends_on": "2026-10-16", "reason": "r" * 501},
        {"starts_on": "12/10/2026", "ends_on": "2026-10-16"},
        {"starts_on": "2026-10-12"},
    ],
)
def test_time_off_invalid_body_is_422_without_echo(
    auth_client: TestClient, schedule: ScheduleScene, body: dict[str, Any]
) -> None:
    before = schedule.snapshot()
    response = auth_client.post(f"{BASE_A}/time-off", json=body, headers=admin_headers(auth_client))
    assert response.status_code == 422
    assert "rrrrr" not in response.text
    assert schedule.snapshot() == before


def test_delete_time_off_returns_204_and_it_disappears(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    headers = admin_headers(auth_client)
    response = auth_client.delete(f"{BASE_A}/time-off/{schedule.time_off_a}", headers=headers)
    assert response.status_code == 204
    assert response.content == b""
    assert auth_client.get(f"{BASE_A}/time-off", headers=headers).json() == []


def test_delete_of_a_foreign_or_unknown_time_off_is_404(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    headers = admin_headers(auth_client)
    foreign = auth_client.delete(f"{BASE_A}/time-off/{schedule.time_off_b}", headers=headers)
    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "TIME_OFF_NOT_FOUND"
    assert (
        auth_client.delete(f"{BASE_A}/time-off/no-es-un-uuid", headers=headers).status_code == 404
    )
    assert len(schedule.world.time_off.list_for_professional(PROF_B)) == 1


def test_list_time_off_has_the_documented_shape(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    rows = auth_client.get(f"{BASE_A}/time-off", headers=admin_headers(auth_client)).json()
    assert rows == [
        {
            "id": schedule.time_off_a,
            "starts_on": "2026-10-12",
            "ends_on": "2026-10-16",
            "reason": "Congreso",
        }
    ]


# --- Conflictos -------------------------------------------------------------------------------


def test_conflicts_endpoint_lists_pending_ones_and_resolving_removes_them(
    auth_client: TestClient, schedule: ScheduleScene
) -> None:
    headers = admin_headers(auth_client)
    turno = schedule.world.seed(monday(16))
    auth_client.put(
        f"{BASE_A}/working-hours", json={"blocks": [block(0, "09:00", "13:00")]}, headers=headers
    )
    rows = auth_client.get(
        f"{BASE_A}/conflicts", headers=bearer(login_token(auth_client, "recepcion@example.com"))
    ).json()
    assert [r["appointment_id"] for r in rows] == [turno.id]
    cancelled = auth_client.post(
        f"/api/v1/appointments/{turno.id}/cancel", json={"reason": "Cambio"}, headers=headers
    )
    assert cancelled.status_code == 200
    assert auth_client.get(f"{BASE_A}/conflicts", headers=headers).json() == []

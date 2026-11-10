"""Endpoints del catalogo de tratamientos y de la asignacion (spec treatment-api, C-17)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.unit.api.conftest import bearer, login_token
from tests.unit.application.agenda_helpers import (
    CONSULTA_ID,
    LIMPIEZA_ID,
    PROF_A,
    PROF_B,
    World,
)

BASE = "/api/v1/treatments"
UNKNOWN = "99999999-9999-4999-8999-999999999999"


def headers(client: TestClient, email: str = "admin@example.com") -> dict[str, str]:
    return bearer(login_token(client, email))


def snapshot(world: World) -> tuple[object, object]:
    return world.treatments.list_all(), world.treatments.offered_ids(PROF_A)


# --- Catalogo -----------------------------------------------------------------------------------


def test_the_catalog_is_listed_with_its_state_ordered_by_name(
    auth_client: TestClient, treatments_world: World
) -> None:
    treatments_world.treatments.update(LIMPIEZA_ID, active=False)

    response = auth_client.get(BASE, headers=headers(auth_client, "recepcion@example.com"))

    assert response.status_code == 200
    assert response.json() == [
        {"id": CONSULTA_ID, "name": "Consulta", "active": True},
        {"id": LIMPIEZA_ID, "name": "Limpieza dental", "active": False},
    ]


def test_creating_answers_201_with_the_active_treatment_and_the_clean_name(
    auth_client: TestClient, treatments_world: World
) -> None:
    response = auth_client.post(
        BASE, json={"name": "  Tratamiento   de conducto "}, headers=headers(auth_client)
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["name"], body["active"]) == ("Tratamiento de conducto", True)
    assert set(body) == {"id", "name", "active"}
    assert treatments_world.treatments.get(body["id"]) is not None


def test_a_repeated_name_without_case_or_marks_is_409(
    auth_client: TestClient, treatments_world: World
) -> None:
    before = snapshot(treatments_world)

    response = auth_client.post(
        BASE, json={"name": "limpieza  DENTAL"}, headers=headers(auth_client)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TREATMENT_NAME_TAKEN"
    assert snapshot(treatments_world) == before


def test_invalid_names_are_422_without_echoing_the_input_and_create_nothing(
    auth_client: TestClient, treatments_world: World
) -> None:
    before = snapshot(treatments_world)
    for name in ("   ", "", "x" * 81, 7):
        response = auth_client.post(BASE, json={"name": name}, headers=headers(auth_client))
        assert response.status_code == 422, name
        assert "input" not in response.text
    assert snapshot(treatments_world) == before


def test_an_unknown_field_is_422_and_creates_nothing(
    auth_client: TestClient, treatments_world: World
) -> None:
    before = snapshot(treatments_world)

    response = auth_client.post(
        BASE, json={"name": "X", "duration": 60}, headers=headers(auth_client)
    )

    assert response.status_code == 422
    assert snapshot(treatments_world) == before


def test_deactivating_keeps_the_name(auth_client: TestClient, treatments_world: World) -> None:
    response = auth_client.patch(
        f"{BASE}/{LIMPIEZA_ID}", json={"active": False}, headers=headers(auth_client)
    )

    assert response.status_code == 200
    assert response.json() == {"id": LIMPIEZA_ID, "name": "Limpieza dental", "active": False}


def test_renaming_and_reactivating_in_one_call(
    auth_client: TestClient, treatments_world: World
) -> None:
    treatments_world.treatments.update(LIMPIEZA_ID, active=False)

    response = auth_client.patch(
        f"{BASE}/{LIMPIEZA_ID}",
        json={"name": "Profilaxis", "active": True},
        headers=headers(auth_client),
    )

    assert response.json() == {"id": LIMPIEZA_ID, "name": "Profilaxis", "active": True}


def test_an_empty_patch_changes_nothing(auth_client: TestClient, treatments_world: World) -> None:
    response = auth_client.patch(f"{BASE}/{CONSULTA_ID}", json={}, headers=headers(auth_client))

    assert response.status_code == 200
    assert response.json() == {"id": CONSULTA_ID, "name": "Consulta", "active": True}


def test_patch_rejects_unknown_fields_and_non_boolean_state(
    auth_client: TestClient, treatments_world: World
) -> None:
    for body in ({"duration": 5}, {"active": "false"}, {"active": 0}):
        response = auth_client.patch(
            f"{BASE}/{CONSULTA_ID}", json=body, headers=headers(auth_client)
        )
        assert response.status_code == 422, body
    current = treatments_world.treatments.get(CONSULTA_ID)
    assert current is not None and current.active is True


def test_patching_an_unknown_treatment_is_404(
    auth_client: TestClient, treatments_world: World
) -> None:
    response = auth_client.patch(
        f"{BASE}/{UNKNOWN}", json={"active": False}, headers=headers(auth_client)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TREATMENT_NOT_FOUND"


def test_renaming_to_the_name_of_another_treatment_is_409(
    auth_client: TestClient, treatments_world: World
) -> None:
    response = auth_client.patch(
        f"{BASE}/{LIMPIEZA_ID}", json={"name": "Consulta"}, headers=headers(auth_client)
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TREATMENT_NAME_TAKEN"


# --- Asignacion ---------------------------------------------------------------------------------


def assigned(client: TestClient, professional: str, email: str = "admin@example.com") -> Any:
    return client.get(
        f"/api/v1/professionals/{professional}/treatments", headers=headers(client, email)
    )


def test_the_assignment_lists_active_and_inactive_ordered_by_name(
    auth_client: TestClient, treatments_world: World
) -> None:
    treatments_world.treatments.update(LIMPIEZA_ID, active=False)

    response = assigned(auth_client, PROF_A)

    assert response.status_code == 200
    assert [(t["name"], t["active"]) for t in response.json()] == [
        ("Consulta", True),
        ("Limpieza dental", False),
    ]


def test_replacing_answers_200_with_the_new_list(
    auth_client: TestClient, treatments_world: World
) -> None:
    response = auth_client.put(
        f"/api/v1/professionals/{PROF_B}/treatments",
        json={"treatment_ids": [LIMPIEZA_ID, CONSULTA_ID, LIMPIEZA_ID]},
        headers=headers(auth_client),
    )

    assert response.status_code == 200
    assert [t["id"] for t in response.json()] == [CONSULTA_ID, LIMPIEZA_ID]
    assert treatments_world.treatments.offered_ids(PROF_B) == {CONSULTA_ID, LIMPIEZA_ID}


def test_replacing_with_an_unknown_id_is_404_and_keeps_the_assignment(
    auth_client: TestClient, treatments_world: World
) -> None:
    before = snapshot(treatments_world)

    response = auth_client.put(
        f"/api/v1/professionals/{PROF_A}/treatments",
        json={"treatment_ids": [CONSULTA_ID, UNKNOWN]},
        headers=headers(auth_client),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TREATMENT_NOT_FOUND"
    assert snapshot(treatments_world) == before


def test_replacing_for_an_unknown_professional_is_404(
    auth_client: TestClient, treatments_world: World
) -> None:
    response = auth_client.put(
        f"/api/v1/professionals/{UNKNOWN}/treatments",
        json={"treatment_ids": []},
        headers=headers(auth_client),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFESSIONAL_NOT_FOUND"


def test_an_empty_list_leaves_nothing_assigned(
    auth_client: TestClient, treatments_world: World
) -> None:
    response = auth_client.put(
        f"/api/v1/professionals/{PROF_B}/treatments",
        json={"treatment_ids": []},
        headers=headers(auth_client),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_more_than_one_hundred_ids_or_unknown_fields_are_422(
    auth_client: TestClient, treatments_world: World
) -> None:
    url = f"/api/v1/professionals/{PROF_A}/treatments"
    too_many = auth_client.put(
        url, json={"treatment_ids": [UNKNOWN] * 101}, headers=headers(auth_client)
    )
    extra = auth_client.put(
        url, json={"treatment_ids": [], "otro": 1}, headers=headers(auth_client)
    )

    assert too_many.status_code == 422
    assert extra.status_code == 422
    assert treatments_world.treatments.offered_ids(PROF_A) == {CONSULTA_ID, LIMPIEZA_ID}

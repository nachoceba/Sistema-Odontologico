"""Endpoints publicos de la reserva online (spec public-booking-api, C-15).

Casos de uso en memoria y limite de pedidos en memoria: sin base ni Redis.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_public_booking_deps, get_rate_limiter
from app.domain.patients.errors import DocumentTakenError
from app.domain.patients.types import NewPatient
from app.infrastructure.in_memory import InMemoryRateLimiter
from tests.unit.application.agenda_helpers import CONSULTA_ID, LIMPIEZA_ID, PROF_A, World
from tests.unit.domain.appointments.helpers import monday

JUAN_DOC = "30111222"
BASE = "/api/v1/public"


@dataclass
class Scene:
    app: FastAPI
    client: TestClient
    world: World
    limiter: InMemoryRateLimiter


@pytest.fixture
def make_scene(make_client: Callable[[], tuple[FastAPI, TestClient]]) -> Callable[[], Scene]:
    def build() -> Scene:
        app, client = make_client()
        world = World()
        world.patients.add(NewPatient("Juan", "Pérez", JUAN_DOC, "juan@example.com"))
        limiter = InMemoryRateLimiter(lambda: world.now)
        app.dependency_overrides[get_public_booking_deps] = lambda: world.public_deps()
        app.dependency_overrides[get_rate_limiter] = lambda: limiter
        return Scene(app, client, world, limiter)

    return build


@pytest.fixture
def scene(make_scene: Callable[[], Scene]) -> Scene:
    return make_scene()


def booking(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "professional_id": PROF_A,
        "treatment_id": CONSULTA_ID,
        "starts_at": monday(10).isoformat(),
        "document_number": "40999888",
        "first_name": "Lucía",
        "last_name": "Díaz",
        "email": "lucia@example.com",
        "phone": "11 5555-1234",
        "website": "",
    }
    data.update(overrides)
    return data


def post_booking(scene: Scene, **overrides: Any) -> Any:
    return scene.client.post(f"{BASE}/appointments", json=booking(**overrides))


# --- Lecturas ---------------------------------------------------------------------------------


def test_professionals_are_listed_without_a_session_with_only_id_and_name(scene: Scene) -> None:
    response = scene.client.get(f"{BASE}/professionals")

    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {
        PROF_A,
        "22222222-2222-4222-8222-222222222222",
    }
    assert all(set(item) == {"id", "display_name"} for item in response.json())


def test_slots_are_listed_in_utc_with_only_start_and_end(scene: Scene) -> None:
    response = scene.client.get(f"{BASE}/professionals/{PROF_A}/slots?date=2026-10-05")

    assert response.status_code == 200
    first = response.json()[0]
    assert set(first) == {"starts_at", "ends_at"}
    assert first["starts_at"].startswith("2026-10-05T12:00:00")  # 09:00 locales


def test_a_pending_booking_makes_its_slot_disappear(scene: Scene) -> None:
    post_booking(scene)

    starts = [
        s["starts_at"]
        for s in scene.client.get(f"{BASE}/professionals/{PROF_A}/slots?date=2026-10-05").json()
    ]

    assert not any(s.startswith("2026-10-05T13:00:00") for s in starts)


def test_slots_of_an_unknown_professional_are_404(scene: Scene) -> None:
    response = scene.client.get(
        f"{BASE}/professionals/99999999-9999-4999-8999-999999999999/slots?date=2026-10-05"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFESSIONAL_NOT_FOUND"


@pytest.mark.parametrize("value", ["2026-13-45", "mañana", ""])
def test_a_bad_date_is_422(scene: Scene, value: str) -> None:
    response = scene.client.get(f"{BASE}/professionals/{PROF_A}/slots?date={value}")

    assert response.status_code == 422


def test_a_junk_session_token_is_ignored_on_every_public_endpoint(scene: Scene) -> None:
    headers = {"Authorization": "Bearer basura"}

    assert scene.client.get(f"{BASE}/professionals", headers=headers).status_code == 200
    slots = f"{BASE}/professionals/{PROF_A}/slots?date=2026-10-05"
    assert scene.client.get(slots, headers=headers).status_code == 200
    booked = scene.client.post(f"{BASE}/appointments", json=booking(), headers=headers)
    assert booked.status_code == 202
    confirmed = scene.client.post(
        f"{BASE}/appointment-confirmations", json={"token": "tok-1"}, headers=headers
    )
    assert confirmed.status_code == 200


# --- Reservar -------------------------------------------------------------------------------


def test_booking_without_a_session_answers_202_with_the_minimum(scene: Scene) -> None:
    response = post_booking(scene)

    assert response.status_code == 202
    body = response.json()
    assert set(body) == {
        "starts_at",
        "ends_at",
        "professional_display_name",
        "confirm_before",
        "treatment_name",
    }
    assert body["treatment_name"] == "Consulta"
    assert body["starts_at"].startswith("2026-10-05T13:00:00")
    assert body["confirm_before"].startswith("2026-10-03T14:00:00")  # ahora + 60 minutos


def test_the_response_has_no_patient_data(scene: Scene) -> None:
    text = post_booking(scene).text

    for secret in ("lucia@example.com", "40999888", "Lucía", "Díaz", "5555-1234"):
        assert secret not in text


def test_new_and_existing_documents_get_identical_responses(
    make_scene: Callable[[], Scene],
) -> None:
    new_scene, existing_scene = make_scene(), make_scene()

    first = post_booking(new_scene)
    second = post_booking(
        existing_scene, document_number="30.111.222", first_name="juan", last_name="PEREZ"
    )

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()


GENERIC = {"error": {"code": "BOOKING_NOT_POSSIBLE", "message": "Verifique sus datos ingresados."}}


def test_a_wrong_name_is_the_generic_rejection(scene: Scene) -> None:
    response = post_booking(scene, document_number=JUAN_DOC, first_name="Pedro", last_name="Gómez")

    assert response.status_code == 409
    assert response.json() == GENERIC


def test_inactive_overlapping_and_race_rejections_are_byte_identical(
    make_scene: Callable[[], Scene], monkeypatch: pytest.MonkeyPatch
) -> None:
    mismatch = post_booking(
        make_scene(), document_number=JUAN_DOC, first_name="Pedro", last_name="Gómez"
    )

    inactive_scene = make_scene()
    juan = inactive_scene.world.patients.get_by_document(JUAN_DOC)
    assert juan is not None
    inactive_scene.world.patients.set_active(juan.id, False)
    inactive = post_booking(
        inactive_scene, document_number=JUAN_DOC, first_name="Juan", last_name="Pérez"
    )

    overlap_scene = make_scene()
    juan = overlap_scene.world.patients.get_by_document(JUAN_DOC)
    assert juan is not None
    overlap_scene.world.seed(
        monday(10), patient_id=juan.id, professional_id="22222222-2222-4222-8222-222222222222"
    )
    overlap = post_booking(
        overlap_scene, document_number=JUAN_DOC, first_name="Juan", last_name="Pérez"
    )

    race_scene = make_scene()

    def lose(_patient: NewPatient) -> None:
        raise DocumentTakenError

    monkeypatch.setattr(race_scene.world.patients, "add", lose)
    race = post_booking(race_scene)

    for response in (mismatch, inactive, overlap, race):
        assert response.status_code == 409
        assert response.content == mismatch.content
        assert response.json() == GENERIC


def test_a_taken_slot_is_409_slot_taken_and_creates_no_patient(scene: Scene) -> None:
    scene.world.seed(monday(10))

    response = post_booking(scene)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLOT_TAKEN"
    assert scene.world.patients.get_by_document("40999888") is None


def test_an_unbookable_start_is_409_slot_unavailable(scene: Scene) -> None:
    response = post_booking(scene, starts_at=monday(10, 15).isoformat())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLOT_UNAVAILABLE"


def test_an_unknown_professional_is_404(scene: Scene) -> None:
    response = post_booking(scene, professional_id="99999999-9999-4999-8999-999999999999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFESSIONAL_NOT_FOUND"


@pytest.mark.parametrize(
    "overrides",
    [
        {"email": "no-es-email"},
        {"starts_at": "2026-10-05T10:00:00"},
        {"document_number": "12"},
        {"first_name": ""},
        {"last_name": "x" * 101},
        {"phone": "abc"},
        {"active": False},
        {"professional_id": ""},
    ],
    ids=["email", "sin-zona", "documento", "nombre", "apellido-largo", "telefono", "extra", "id"],
)
def test_invalid_input_is_422_and_writes_nothing(scene: Scene, overrides: dict[str, Any]) -> None:
    response = post_booking(scene, **overrides)

    assert response.status_code == 422
    assert scene.world.patients.get_by_document("40999888") is None
    assert scene.world.everything() == []


def test_a_422_does_not_echo_the_values_sent(scene: Scene) -> None:
    response = post_booking(scene, email="no-es-email")

    assert "no-es-email" not in response.text


def test_the_phone_is_optional(scene: Scene) -> None:
    body = booking()
    del body["phone"]

    assert scene.client.post(f"{BASE}/appointments", json=body).status_code == 202


# --- Confirmar --------------------------------------------------------------------------------


def test_confirming_without_a_session_answers_200(scene: Scene) -> None:
    post_booking(scene)

    response = scene.client.post(f"{BASE}/appointment-confirmations", json={"token": "tok-1"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "starts_at",
        "ends_at",
        "professional_display_name",
        "treatment_name",
    }
    assert body["treatment_name"] == "Consulta"
    assert body["starts_at"].startswith("2026-10-05T13:00:00")


def test_a_used_unknown_or_expired_token_is_the_same_410(scene: Scene) -> None:
    post_booking(scene)

    def confirm(token: str) -> Any:
        return scene.client.post(f"{BASE}/appointment-confirmations", json={"token": token})

    assert confirm("tok-1").status_code == 200

    used = confirm("tok-1")
    unknown = confirm("otro")
    scene.world.now += timedelta(days=1)
    post_booking_again = post_booking(
        scene, document_number="40888777", starts_at=monday(11).isoformat()
    )
    assert post_booking_again.status_code == 202
    scene.world.now += timedelta(hours=2)
    expired = confirm("tok-2")

    for response in (used, unknown, expired):
        assert response.status_code == 410
        assert response.json() == {
            "error": {
                "code": "CONFIRMATION_LINK_INVALID",
                "message": "El enlace no es válido o ya venció.",
            }
        }


@pytest.mark.parametrize("body", [{"token": ""}, {"token": "x" * 129}, {}, {"token": "a", "x": 1}])
def test_a_bad_confirmation_body_is_422(scene: Scene, body: dict[str, Any]) -> None:
    assert scene.client.post(f"{BASE}/appointment-confirmations", json=body).status_code == 422


# --- Limite de pedidos y campo trampa ---------------------------------------------------------


def test_the_sixth_booking_in_an_hour_is_429_with_retry_after_and_creates_nothing(
    scene: Scene,
) -> None:
    statuses = [post_booking(scene).status_code for _ in range(5)]
    appointments_before = scene.world.everything()
    sixth = post_booking(scene, document_number="40777666", starts_at=monday(11).isoformat())

    assert statuses == [202, 409, 409, 409, 409]
    assert sixth.status_code == 429
    assert sixth.json()["error"]["code"] == "TOO_MANY_REQUESTS"
    assert int(sixth.headers["Retry-After"]) == 3600 - int(scene.world.now.timestamp()) % 3600
    assert scene.world.everything() == appointments_before
    assert scene.world.patients.get_by_document("40777666") is None


def test_the_eleventh_confirmation_in_an_hour_is_429(scene: Scene) -> None:
    statuses = [
        scene.client.post(f"{BASE}/appointment-confirmations", json={"token": f"t{n}"}).status_code
        for n in range(11)
    ]

    assert statuses == [410] * 10 + [429]


def test_the_61st_read_in_a_minute_is_429(scene: Scene) -> None:
    statuses = [scene.client.get(f"{BASE}/professionals").status_code for _ in range(61)]

    assert statuses == [200] * 60 + [429]


def test_groups_are_independent(scene: Scene) -> None:
    for _ in range(6):
        post_booking(scene)

    assert scene.client.get(f"{BASE}/professionals").status_code == 200
    assert (
        scene.client.post(f"{BASE}/appointment-confirmations", json={"token": "x"}).status_code
        == 410
    )


def test_x_forwarded_for_is_ignored(scene: Scene) -> None:
    for _ in range(5):
        post_booking(scene)

    response = scene.client.post(
        f"{BASE}/appointments", json=booking(), headers={"X-Forwarded-For": "203.0.113.77"}
    )

    assert response.status_code == 429


def test_the_rate_limit_key_has_no_document_or_token(scene: Scene) -> None:
    post_booking(scene)
    scene.client.post(f"{BASE}/appointment-confirmations", json={"token": "tok-1"})

    keys = [str(key) for key in scene.limiter._counts]  # noqa: SLF001
    assert keys
    assert not any("40999888" in key or "tok-1" in key for key in keys)


def test_the_honeypot_field_rejects_the_request_without_writing(scene: Scene) -> None:
    response = post_booking(scene, website="http://spam")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BOOKING_REJECTED"
    assert scene.world.patients.get_by_document("40999888") is None
    assert scene.world.everything() == []
    assert scene.world.verification.calls == []


def test_a_honeypot_request_still_counts_for_the_limit(scene: Scene) -> None:
    statuses = [post_booking(scene, website="x").status_code for _ in range(6)]

    assert statuses == [400] * 5 + [429]


def test_an_empty_honeypot_is_processed_normally(scene: Scene) -> None:
    assert post_booking(scene, website="").status_code == 202


# --- Los endpoints internos de turnos siguen protegidos ---------------------------------------


def test_the_internal_routes_still_require_a_session(scene: Scene) -> None:
    assert scene.client.post("/api/v1/appointments", json={}).status_code == 401
    assert (
        scene.client.get(f"/api/v1/professionals/{PROF_A}/slots?date=2026-10-05").status_code == 401
    )


# --- Tratamiento (C-17) ---------------------------------------------------------------------------


def treatments_url(professional: str = PROF_A) -> str:
    return f"{BASE}/professionals/{professional}/treatments"


def test_treatments_are_listed_without_a_session_with_only_id_and_name(scene: Scene) -> None:
    response = scene.client.get(treatments_url())

    assert response.status_code == 200
    assert response.json() == [
        {"id": CONSULTA_ID, "name": "Consulta"},
        {"id": LIMPIEZA_ID, "name": "Limpieza dental"},
    ]


def test_only_active_assigned_treatments_are_listed(scene: Scene) -> None:
    scene.world.treatments.update(LIMPIEZA_ID, active=False)

    assert scene.client.get(treatments_url()).json() == [{"id": CONSULTA_ID, "name": "Consulta"}]


def test_treatments_of_a_professional_not_offered_are_404(scene: Scene) -> None:
    scene.world.treatments.replace_for_professional(PROF_A, [])

    response = scene.client.get(treatments_url())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROFESSIONAL_NOT_FOUND"


def test_treatments_of_an_unknown_professional_are_404(scene: Scene) -> None:
    response = scene.client.get(treatments_url("99999999-9999-4999-8999-999999999999"))

    assert response.status_code == 404


def test_a_junk_session_token_is_ignored_on_the_treatments_endpoint(scene: Scene) -> None:
    response = scene.client.get(treatments_url(), headers={"Authorization": "Bearer basura"})

    assert response.status_code == 200


def test_the_61st_read_mixing_professionals_treatments_and_slots_is_429(scene: Scene) -> None:
    urls = [
        f"{BASE}/professionals",
        treatments_url(),
        f"{BASE}/professionals/{PROF_A}/slots?date=2026-10-05",
    ]
    statuses = [scene.client.get(urls[i % 3]).status_code for i in range(61)]

    assert statuses == [200] * 60 + [429]
    blocked = scene.client.get(treatments_url())
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_the_other_groups_stay_free_when_the_reads_are_exhausted(scene: Scene) -> None:
    for _ in range(61):
        scene.client.get(treatments_url())

    assert post_booking(scene).status_code == 202


def test_booking_without_a_treatment_is_422_and_writes_nothing(scene: Scene) -> None:
    body = booking()
    del body["treatment_id"]

    response = scene.client.post(f"{BASE}/appointments", json=body)

    assert response.status_code == 422
    assert scene.world.patients.get_by_document("40999888") is None
    assert scene.world.everything() == []


@pytest.mark.parametrize("value", ["", "   ", 7, None])
def test_a_blank_or_non_text_treatment_is_422(scene: Scene, value: Any) -> None:
    assert post_booking(scene, treatment_id=value).status_code == 422


def test_unknown_inactive_and_unoffered_treatments_get_the_same_409(
    make_scene: Callable[[], Scene],
) -> None:
    unknown = post_booking(make_scene(), treatment_id="no-existe")

    inactive_scene = make_scene()
    inactive_scene.world.treatments.update(LIMPIEZA_ID, active=False)
    inactive = post_booking(inactive_scene, treatment_id=LIMPIEZA_ID)

    unoffered_scene = make_scene()
    unoffered_scene.world.treatments.replace_for_professional(PROF_A, [CONSULTA_ID])
    unoffered = post_booking(unoffered_scene, treatment_id=LIMPIEZA_ID)

    for response in (unknown, inactive, unoffered):
        assert response.status_code == 409
        assert response.content == unknown.content
        assert response.json()["error"]["code"] == "TREATMENT_NOT_AVAILABLE"


def test_a_rejected_treatment_creates_no_patient_and_no_appointment(scene: Scene) -> None:
    post_booking(scene, treatment_id="no-existe")

    assert scene.world.patients.get_by_document("40999888") is None
    assert scene.world.everything() == []


def test_booking_with_another_offered_treatment_answers_with_its_name(scene: Scene) -> None:
    response = post_booking(scene, treatment_id=LIMPIEZA_ID)

    assert response.status_code == 202
    assert response.json()["treatment_name"] == "Limpieza dental"
    [saved] = scene.world.everything()
    assert saved.treatment_id == LIMPIEZA_ID

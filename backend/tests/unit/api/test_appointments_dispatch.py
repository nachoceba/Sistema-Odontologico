"""Agendar, reprogramar y cancelar con el despachador real de C-11: Redis caido no rompe nada
y no hay mas de una tarea por horario (spec notification-tasks; reglas duras 4 y 6)."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient
from kombu.exceptions import OperationalError

from app.domain.appointments import NotificationStatus
from app.infrastructure.tasks.dispatcher import CeleryNotificationDispatcher
from tests.unit.api.conftest import AgendaScene, bearer, login_token
from tests.unit.application.agenda_helpers import PROF_A
from tests.unit.domain.appointments.helpers import monday

BASE = "/api/v1/appointments"


class Queue:
    """Cola falsa: anota los ids publicados; con ``down`` imita un Redis caido."""

    def __init__(self) -> None:
        self.published: list[str] = []
        self.down = False

    def publish(self, notification_id: str) -> None:
        if self.down:
            raise OperationalError("Redis caido")
        self.published.append(notification_id)


@pytest.fixture
def queue(agenda: AgendaScene) -> Queue:
    fake = Queue()
    agenda.world.dispatcher.inner = CeleryNotificationDispatcher(fake.publish)
    return fake


@pytest.fixture
def reception(auth_client: TestClient) -> dict[str, str]:
    return bearer(login_token(auth_client, "recepcion@example.com"))


def body(starts_at: str, patient_id: str = "pac-1") -> dict[str, str]:
    return {"patient_id": patient_id, "professional_id": PROF_A, "starts_at": starts_at}


def test_booking_publishes_one_task_with_the_new_confirmation_id(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str], queue: Queue
) -> None:
    response = auth_client.post(BASE, json=body(monday(16).isoformat()), headers=reception)

    assert response.status_code == 201, response.text
    [row] = agenda.world.notifications.list_for_appointment(response.json()["id"])
    assert queue.published == [row.id]


def test_booking_with_redis_down_answers_201_keeps_the_pending_and_logs_without_patient_data(
    auth_client: TestClient,
    agenda: AgendaScene,
    reception: dict[str, str],
    queue: Queue,
    caplog: pytest.LogCaptureFixture,
) -> None:
    queue.down = True
    caplog.set_level(logging.WARNING)

    response = auth_client.post(BASE, json=body(monday(16).isoformat()), headers=reception)

    assert response.status_code == 201, response.text
    created = response.json()["id"]
    [row] = agenda.world.notifications.list_for_appointment(created)
    assert row.status is NotificationStatus.PENDING
    assert created in caplog.text
    assert "OperationalError" in caplog.text
    assert "juan@example.com" not in caplog.text


def test_rescheduling_with_redis_down_answers_200_and_leaves_the_new_pending(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str], queue: Queue
) -> None:
    queue.down = True

    response = auth_client.post(
        f"{BASE}/{agenda.future_a}/reschedule",
        json={"starts_at": monday(17).isoformat()},
        headers=reception,
    )

    assert response.status_code == 200, response.text
    rows = agenda.world.notifications.list_for_appointment(agenda.future_a)
    assert [(r.appointment_starts_at, r.status) for r in rows] == [
        (monday(17), NotificationStatus.PENDING)
    ]


def test_a_rejected_booking_publishes_nothing_and_the_same_slot_never_overlaps(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str], queue: Queue
) -> None:
    first = auth_client.post(BASE, json=body(monday(16).isoformat()), headers=reception)
    second = auth_client.post(
        BASE, json=body(monday(16).isoformat(), patient_id="pac-2"), headers=reception
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "SLOT_TAKEN"
    assert len(queue.published) == 1
    taken = [
        a
        for a in agenda.world.everything(PROF_A)
        if a.starts_at == monday(16) and a.status.value == "scheduled"
    ]
    assert len(taken) == 1


def test_cancelling_publishes_nothing(
    auth_client: TestClient, agenda: AgendaScene, reception: dict[str, str], queue: Queue
) -> None:
    response = auth_client.post(
        f"{BASE}/{agenda.future_a}/cancel", json={"reason": "aviso"}, headers=reception
    )

    assert response.status_code == 200
    assert queue.published == []

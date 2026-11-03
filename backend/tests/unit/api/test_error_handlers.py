"""Tests de la traduccion de errores a JSON (spec error-model)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import ClassVar

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import DomainError
from app.domain.appointments.errors import AppointmentNotFoundError, SlotTakenError


class CodigoSinEstadoError(DomainError):
    code: ClassVar[str] = "CODIGO_SIN_TABLA"


def _boom_not_found() -> None:
    raise AppointmentNotFoundError("apt-1")


def _boom_slot_taken() -> None:
    raise SlotTakenError("dra-a", datetime(2026, 10, 5, 13, 0, tzinfo=UTC))


def _boom_unmapped() -> None:
    raise CodigoSinEstadoError("sin estado asignado")


def _boom_internal() -> None:
    raise RuntimeError("secreto interno: password=hunter2")


@pytest.fixture
def raising_client(make_client: Callable[[], tuple[FastAPI, TestClient]]) -> TestClient:
    app, test_client = make_client()
    app.add_api_route("/__test__/not-found", _boom_not_found)
    app.add_api_route("/__test__/slot-taken", _boom_slot_taken)
    app.add_api_route("/__test__/unmapped", _boom_unmapped)
    app.add_api_route("/__test__/internal", _boom_internal)
    return test_client


def test_known_code_maps_to_404(raising_client: TestClient) -> None:
    response = raising_client.get("/__test__/not-found")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "APPOINTMENT_NOT_FOUND"
    assert body["error"]["message"]


def test_slot_taken_maps_to_409(raising_client: TestClient) -> None:
    response = raising_client.get("/__test__/slot-taken")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLOT_TAKEN"


def test_code_without_table_entry_maps_to_400(raising_client: TestClient) -> None:
    response = raising_client.get("/__test__/unmapped")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CODIGO_SIN_TABLA"


def test_unexpected_error_is_500_without_internal_details(raising_client: TestClient) -> None:
    response = raising_client.get("/__test__/internal")

    assert response.status_code == 500
    assert response.json() == {"error": {"code": "INTERNAL_ERROR", "message": "Error interno"}}
    assert "hunter2" not in response.text
    assert "Traceback" not in response.text

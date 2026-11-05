"""Tests de la traduccion de errores a JSON (spec error-model)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import ClassVar

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.errors import DomainError
from app.domain.appointments.errors import (
    AlreadyStartedError,
    AppointmentNotFoundError,
    AttendanceAlreadyRecordedError,
    CancelledIsFinalError,
    InsufficientNoticeError,
    NotStartedYetError,
    OffGridError,
    OutsideWorkingHoursError,
    PatientDoubleBookedError,
    PatientInactiveError,
    PatientNotFoundError,
    ProfessionalInactiveError,
    ProfessionalNotFoundError,
    ProfessionalTimeOffError,
    RescheduleSameTimeError,
    SlotTakenError,
)
from app.domain.auth import ForbiddenError, InvalidCredentialsError, NotAuthenticatedError
from app.domain.patients.errors import (
    DocumentTakenError,
    InvalidPatientDataError,
    PatientHasAppointmentsError,
)
from app.domain.schedules.errors import (
    InvalidTimeOffError,
    InvalidWorkingHoursError,
    TimeOffNotFoundError,
)
from app.domain.schedules.validation import ScheduleProblem, ScheduleProblemCode
from app.domain.users.errors import (
    EmailTakenError,
    RoleChangeNotAllowedError,
    SelfModificationError,
    UserNotFoundError,
)


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


def _boom_invalid_credentials() -> None:
    raise InvalidCredentialsError


def _boom_not_authenticated() -> None:
    raise NotAuthenticatedError


def _boom_forbidden() -> None:
    raise ForbiddenError


@pytest.fixture
def auth_client(make_client: Callable[[], tuple[FastAPI, TestClient]]) -> TestClient:
    app, test_client = make_client()
    app.add_api_route("/__test__/invalid-credentials", _boom_invalid_credentials)
    app.add_api_route("/__test__/not-authenticated", _boom_not_authenticated)
    app.add_api_route("/__test__/forbidden", _boom_forbidden)
    return test_client


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("/__test__/invalid-credentials", "INVALID_CREDENTIALS"),
        ("/__test__/not-authenticated", "NOT_AUTHENTICATED"),
    ],
)
def test_authentication_errors_are_401_with_www_authenticate(
    auth_client: TestClient, path: str, code: str
) -> None:
    response = auth_client.get(path)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["message"]


def test_forbidden_is_403_without_www_authenticate(auth_client: TestClient) -> None:
    response = auth_client.get("/__test__/forbidden")

    assert response.status_code == 403
    assert "www-authenticate" not in response.headers
    assert response.json() == {
        "error": {"code": "FORBIDDEN", "message": "No tenés permiso para esta acción"}
    }


def test_non_401_domain_errors_do_not_get_www_authenticate(raising_client: TestClient) -> None:
    response = raising_client.get("/__test__/slot-taken")

    assert response.status_code == 409
    assert "www-authenticate" not in response.headers


# --- Gestion de usuarios (C-04) ------------------------------------------------------------------


def _boom_user_not_found() -> None:
    raise UserNotFoundError


def _boom_email_taken() -> None:
    raise EmailTakenError


def _boom_role_change() -> None:
    raise RoleChangeNotAllowedError


def _boom_self_modification() -> None:
    raise SelfModificationError


class SecretBody(BaseModel):
    email: str = Field(pattern=r"^[^@]+@[^@]+$")
    password: str = Field(min_length=8, max_length=20)


def _echo(body: SecretBody) -> dict[str, str]:
    return {"email": body.email}


@pytest.fixture
def users_client(make_client: Callable[[], tuple[FastAPI, TestClient]]) -> TestClient:
    app, test_client = make_client()
    app.add_api_route("/__test__/user-not-found", _boom_user_not_found)
    app.add_api_route("/__test__/email-taken", _boom_email_taken)
    app.add_api_route("/__test__/role-change", _boom_role_change)
    app.add_api_route("/__test__/self-modification", _boom_self_modification)
    app.add_api_route("/__test__/echo", _echo, methods=["POST"])
    return test_client


def test_user_not_found_is_404(users_client: TestClient) -> None:
    response = users_client.get("/__test__/user-not-found")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("/__test__/email-taken", "EMAIL_TAKEN"),
        ("/__test__/role-change", "ROLE_CHANGE_NOT_ALLOWED"),
        ("/__test__/self-modification", "SELF_MODIFICATION_NOT_ALLOWED"),
    ],
)
def test_user_management_conflicts_are_409_without_www_authenticate(
    users_client: TestClient, path: str, code: str
) -> None:
    response = users_client.get(path)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["message"]
    assert "www-authenticate" not in response.headers


def test_validation_error_keeps_the_field_list_but_not_the_values_sent(
    users_client: TestClient,
) -> None:
    secret = "contrasena-valida-123"
    response = users_client.post("/__test__/echo", json={"email": "sin-arroba", "password": secret})

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert errors[0]["loc"] == ["body", "email"]
    assert errors[0]["msg"]
    assert errors[0]["type"]
    assert all("input" not in error and "ctx" not in error for error in errors)
    assert secret not in response.text
    assert "sin-arroba" not in response.text


def test_validation_error_on_the_password_itself_does_not_echo_it(
    users_client: TestClient,
) -> None:
    too_long = "x" * 21
    response = users_client.post("/__test__/echo", json={"email": "a@b", "password": too_long})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "password"]
    assert too_long not in response.text


# --- Errores de la agenda (C-08, spec error-model, design D-8) ---

AGENDA_ERRORS: list[tuple[type[DomainError], int]] = [
    (PatientNotFoundError, 404),
    (ProfessionalNotFoundError, 404),
    (PatientDoubleBookedError, 409),
    (PatientInactiveError, 409),
    (ProfessionalInactiveError, 409),
    (CancelledIsFinalError, 409),
    (AttendanceAlreadyRecordedError, 409),
    (AlreadyStartedError, 409),
    (NotStartedYetError, 409),
    (InsufficientNoticeError, 400),
    (OffGridError, 400),
    (OutsideWorkingHoursError, 400),
    (ProfessionalTimeOffError, 400),
    (RescheduleSameTimeError, 400),
]


@pytest.fixture
def agenda_client(make_client: Callable[[], tuple[FastAPI, TestClient]]) -> TestClient:
    app, test_client = make_client()
    for error_class, _ in AGENDA_ERRORS:

        def boom(error_class: type[DomainError] = error_class) -> None:
            raise error_class

        app.add_api_route(f"/__test__/{error_class.code}", boom)
    return test_client


@pytest.mark.parametrize(("error_class", "status"), AGENDA_ERRORS, ids=lambda v: str(v))
def test_agenda_errors_map_to_their_status_with_a_message(
    agenda_client: TestClient, error_class: type[DomainError], status: int
) -> None:
    response = agenda_client.get(f"/__test__/{error_class.code}")

    assert response.status_code == status
    body = response.json()["error"]
    assert body["code"] == error_class.code
    assert body["message"]
    assert "www-authenticate" not in response.headers


def test_slot_taken_message_is_a_friendly_spanish_text_without_internal_ids(
    raising_client: TestClient,
) -> None:
    message = raising_client.get("/__test__/slot-taken").json()["error"]["message"]
    assert message == "Ese horario acaba de ocuparse. Elegí otro."


# --- Errores de horarios y licencias (C-07) ---------------------------------------------------


def _raise_invalid_working_hours() -> None:
    raise InvalidWorkingHoursError(
        [ScheduleProblem(ScheduleProblemCode.OVERLAPPING_BLOCKS, (0, 1))]
    )


def _raise_invalid_time_off() -> None:
    raise InvalidTimeOffError


def _raise_time_off_not_found() -> None:
    raise TimeOffNotFoundError


@pytest.mark.parametrize(
    ("path", "handler", "code", "status"),
    [
        ("working-hours", _raise_invalid_working_hours, "INVALID_WORKING_HOURS", 400),
        ("time-off-range", _raise_invalid_time_off, "INVALID_TIME_OFF", 400),
        ("time-off-missing", _raise_time_off_not_found, "TIME_OFF_NOT_FOUND", 404),
    ],
)
def test_schedule_errors_map_to_their_status_with_a_message(
    make_client: Callable[[], tuple[FastAPI, TestClient]],
    path: str,
    handler: Callable[[], None],
    code: str,
    status: int,
) -> None:
    app, test_client = make_client()
    app.add_api_route(f"/__test__/{path}", handler)
    response = test_client.get(f"/__test__/{path}")
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["message"]
    assert "www-authenticate" not in response.headers


def test_overlap_message_names_the_blocks_in_the_response(
    make_client: Callable[[], tuple[FastAPI, TestClient]],
) -> None:
    app, test_client = make_client()
    app.add_api_route("/__test__/overlap", _raise_invalid_working_hours)
    message = test_client.get("/__test__/overlap").json()["error"]["message"]
    assert "Los tramos 1 y 2 se superponen" in message


def test_schedule_codes_are_explicit_in_the_status_table() -> None:
    from app.api.errors import STATUS_BY_CODE

    assert STATUS_BY_CODE["INVALID_WORKING_HOURS"] == 400
    assert STATUS_BY_CODE["INVALID_TIME_OFF"] == 400
    assert STATUS_BY_CODE["TIME_OFF_NOT_FOUND"] == 404


# --- Errores de la gestion de pacientes (C-06) ------------------------------------------------


def _raise_document_taken() -> None:
    raise DocumentTakenError


def _raise_patient_has_appointments() -> None:
    raise PatientHasAppointmentsError


def _raise_invalid_patient_data() -> None:
    raise InvalidPatientDataError


@pytest.mark.parametrize(
    ("path", "handler", "code", "status"),
    [
        ("document-taken", _raise_document_taken, "DOCUMENT_TAKEN", 409),
        ("has-appointments", _raise_patient_has_appointments, "PATIENT_HAS_APPOINTMENTS", 409),
        ("invalid-patient", _raise_invalid_patient_data, "INVALID_PATIENT_DATA", 400),
    ],
)
def test_patient_errors_map_to_their_status_with_a_message_without_patient_data(
    make_client: Callable[[], tuple[FastAPI, TestClient]],
    path: str,
    handler: Callable[[], None],
    code: str,
    status: int,
) -> None:
    app, test_client = make_client()
    app.add_api_route(f"/__test__/{path}", handler)
    response = test_client.get(f"/__test__/{path}")
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["message"]
    assert "www-authenticate" not in response.headers


def test_patient_codes_are_explicit_in_the_status_table() -> None:
    from app.api.errors import STATUS_BY_CODE

    assert STATUS_BY_CODE["DOCUMENT_TAKEN"] == 409
    assert STATUS_BY_CODE["PATIENT_HAS_APPOINTMENTS"] == 409
    assert STATUS_BY_CODE["INVALID_PATIENT_DATA"] == 400

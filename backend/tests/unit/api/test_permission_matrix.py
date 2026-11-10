"""Matriz unica de permisos ruta x rol (spec access-control, regla dura 4, R-6, DD-110).

Fuente: ``knowledge-base/03_actores_y_roles.md`` (matriz RBAC confirmada, DD-48). La tabla debe
ser exactamente el conjunto de rutas registradas. Para cada ruta protegida: 401 sin token, 403 con
cada rol no permitido y ni 401 ni 403 con cada rol permitido. El alcance "propio" del odontologo
(RN-AU-04) sigue probado en los tests por recurso.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_agenda_deps,
    get_patient_deps,
    get_public_booking_deps,
    get_rate_limiter,
    get_schedule_deps,
    get_treatment_deps,
)
from app.domain.auth import Role
from app.infrastructure.in_memory import InMemoryRateLimiter
from tests.unit.api.conftest import PROFESSIONAL_A, bearer, login_token
from tests.unit.api.route_helpers import api_routes, route_keys
from tests.unit.application.agenda_helpers import World

RouteKey = tuple[str, str]

ADMIN_ONLY = frozenset({Role.ADMIN})
STAFF = frozenset({Role.ADMIN, Role.RECEPTIONIST})
EVERYONE = frozenset({Role.ADMIN, Role.RECEPTIONIST, Role.DENTIST})

# None = ruta publica. Un rol permitido que ademas filtra por alcance ("propio") lo hace dentro
# del caso de uso y se prueba en los tests por recurso.
MATRIX: dict[RouteKey, frozenset[Role] | None] = {
    ("POST", "/api/v1/auth/login"): None,
    ("GET", "/api/v1/health"): None,
    # Reserva online sin cuenta (C-15, design D-10): unica excepcion publica a la regla dura 4.
    ("GET", "/api/v1/public/professionals"): None,
    ("GET", "/api/v1/public/professionals/{professional_id}/slots"): None,
    ("GET", "/api/v1/public/professionals/{professional_id}/treatments"): None,
    ("POST", "/api/v1/public/appointments"): None,
    ("POST", "/api/v1/public/appointment-confirmations"): None,
    ("GET", "/api/v1/auth/me"): EVERYONE,
    # Usuarios y roles: solo el administrador.
    ("GET", "/api/v1/users"): ADMIN_ONLY,
    ("POST", "/api/v1/users"): ADMIN_ONLY,
    ("PATCH", "/api/v1/users/{user_id}"): ADMIN_ONLY,
    ("POST", "/api/v1/users/{user_id}/deactivate"): ADMIN_ONLY,
    ("POST", "/api/v1/users/{user_id}/reactivate"): ADMIN_ONLY,
    ("PUT", "/api/v1/users/{user_id}/password"): ADMIN_ONLY,
    # Profesionales, horarios y licencias: lectura para todos (odontologo: propio), escritura admin.
    ("GET", "/api/v1/professionals"): EVERYONE,
    ("GET", "/api/v1/professionals/{professional_id}"): EVERYONE,
    ("PATCH", "/api/v1/professionals/{professional_id}"): ADMIN_ONLY,
    ("GET", "/api/v1/professionals/{professional_id}/working-hours"): EVERYONE,
    ("PUT", "/api/v1/professionals/{professional_id}/working-hours"): ADMIN_ONLY,
    ("GET", "/api/v1/professionals/{professional_id}/time-off"): EVERYONE,
    ("POST", "/api/v1/professionals/{professional_id}/time-off"): ADMIN_ONLY,
    ("DELETE", "/api/v1/professionals/{professional_id}/time-off/{time_off_id}"): ADMIN_ONLY,
    ("GET", "/api/v1/professionals/{professional_id}/conflicts"): EVERYONE,
    ("GET", "/api/v1/professionals/{professional_id}/slots"): EVERYONE,
    # Catalogo de tratamientos y asignacion por profesional (C-17): lectura todos, escritura admin.
    ("GET", "/api/v1/treatments"): EVERYONE,
    ("POST", "/api/v1/treatments"): ADMIN_ONLY,
    ("PATCH", "/api/v1/treatments/{treatment_id}"): ADMIN_ONLY,
    ("GET", "/api/v1/professionals/{professional_id}/treatments"): EVERYONE,
    ("PUT", "/api/v1/professionals/{professional_id}/treatments"): ADMIN_ONLY,
    # Pacientes: lectura para todos, escritura admin y recepcion, borrado fisico solo admin.
    ("GET", "/api/v1/patients"): EVERYONE,
    ("GET", "/api/v1/patients/{patient_id}"): EVERYONE,
    ("POST", "/api/v1/patients"): STAFF,
    ("PATCH", "/api/v1/patients/{patient_id}"): STAFF,
    ("POST", "/api/v1/patients/{patient_id}/deactivate"): STAFF,
    ("POST", "/api/v1/patients/{patient_id}/reactivate"): STAFF,
    ("DELETE", "/api/v1/patients/{patient_id}"): ADMIN_ONLY,
    # Turnos: escritura (agendar, cancelar, reprogramar) admin y recepcion; el resto, todos
    ("GET", "/api/v1/appointments"): EVERYONE,
    ("GET", "/api/v1/appointments/{appointment_id}"): EVERYONE,
    ("POST", "/api/v1/appointments"): STAFF,
    ("POST", "/api/v1/appointments/{appointment_id}/cancel"): STAFF,
    ("POST", "/api/v1/appointments/{appointment_id}/reschedule"): STAFF,
    ("POST", "/api/v1/appointments/{appointment_id}/attendance"): EVERYONE,
}

PUBLIC_KEYS = [key for key, roles in MATRIX.items() if roles is None]
PROTECTED = [(key, roles) for key, roles in MATRIX.items() if roles is not None]
ACCOUNT_BY_ROLE = {
    Role.ADMIN: "admin@example.com",
    Role.RECEPTIONIST: "recepcion@example.com",
    Role.DENTIST: "dra.a@example.com",
}
GENERIC_ID = "00000000-0000-4000-8000-000000000000"


def compare_route_sets(
    declared: set[RouteKey], registered: set[RouteKey]
) -> tuple[list[str], list[str]]:
    """(rutas registradas sin fila, filas de rutas que no existen), como ``METODO /ruta``."""
    missing = sorted(f"{method} {path}" for method, path in registered - declared)
    stale = sorted(f"{method} {path}" for method, path in declared - registered)
    return missing, stale


def concrete(path: str, *, professional_id: str = GENERIC_ID) -> str:
    """Rellena los parametros de ruta; el odontologo usa su propia ficha para pasar el alcance."""
    filled = path.replace("{professional_id}", professional_id)
    return re.sub(r"\{[^}]+\}", GENERIC_ID, filled)


def test_comparison_names_a_registered_route_without_a_row() -> None:
    declared = {("GET", "/a")}
    registered = {("GET", "/a"), ("POST", "/b")}

    assert compare_route_sets(declared, registered) == (["POST /b"], [])


def test_comparison_names_a_row_for_a_route_that_does_not_exist() -> None:
    declared = {("GET", "/a"), ("DELETE", "/vieja/{id}")}
    registered = {("GET", "/a")}

    assert compare_route_sets(declared, registered) == ([], ["DELETE /vieja/{id}"])


def test_comparison_is_empty_when_both_sets_are_equal() -> None:
    keys = {("GET", "/a"), ("POST", "/a")}

    assert compare_route_sets(keys, set(keys)) == ([], [])


def test_matrix_equals_the_registered_routes(
    make_client: Callable[[], tuple[FastAPI, TestClient]],
) -> None:
    app, _ = make_client()
    registered = {key for context in api_routes(app) for key in route_keys(context)}

    assert compare_route_sets(set(MATRIX), registered) == ([], [])


def test_a_new_route_without_a_row_is_named_by_the_matrix_test(
    make_client: Callable[[], tuple[FastAPI, TestClient]],
) -> None:
    app, _ = make_client()
    app.add_api_route("/api/v1/olvidada", lambda: {}, methods=["GET"])
    registered = {key for context in api_routes(app) for key in route_keys(context)}

    assert compare_route_sets(set(MATRIX), registered) == (["GET /api/v1/olvidada"], [])


def test_public_routes_in_the_matrix_are_login_health_and_the_online_booking_five() -> None:
    assert set(PUBLIC_KEYS) == {
        ("POST", "/api/v1/auth/login"),
        ("GET", "/api/v1/health"),
        ("GET", "/api/v1/public/professionals"),
        ("GET", "/api/v1/public/professionals/{professional_id}/slots"),
        ("GET", "/api/v1/public/professionals/{professional_id}/treatments"),
        ("POST", "/api/v1/public/appointments"),
        ("POST", "/api/v1/public/appointment-confirmations"),
    }


# --- Comportamiento por ruta y rol ---

_TOKENS: dict[Role, str] = {}


@pytest.fixture
def world_client(auth_app: tuple[FastAPI, TestClient]) -> tuple[TestClient, dict[Role, str]]:
    """Cliente con casos de uso en memoria (sin base) y un token por rol (cacheado)."""
    app, client = auth_app
    world = World()
    app.dependency_overrides[get_agenda_deps] = world.deps
    app.dependency_overrides[get_schedule_deps] = world.schedule_deps
    app.dependency_overrides[get_patient_deps] = world.patient_deps
    app.dependency_overrides[get_treatment_deps] = world.treatment_deps
    app.dependency_overrides[get_public_booking_deps] = world.public_deps
    app.dependency_overrides[get_rate_limiter] = lambda: InMemoryRateLimiter(lambda: world.now)
    if not _TOKENS:
        for role, email in ACCOUNT_BY_ROLE.items():
            _TOKENS[role] = login_token(client, email)
    return client, dict(_TOKENS)


def call(client: TestClient, key: RouteKey, token: str | None, *, own: bool = False) -> int:
    method, path = key
    url = concrete(path, professional_id=PROFESSIONAL_A if own else GENERIC_ID)
    headers = bearer(token) if token else {}
    status: int = client.request(method, url, headers=headers).status_code
    return status


@pytest.mark.parametrize("key", [key for key, _ in PROTECTED], ids=lambda k: f"{k[0]} {k[1]}")
def test_every_protected_route_answers_401_without_token(
    world_client: tuple[TestClient, dict[Role, str]], key: RouteKey
) -> None:
    client, _ = world_client
    method, path = key

    response = client.request(method, concrete(path))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


DENIED = [(key, role) for key, roles in PROTECTED for role in sorted(set(Role) - roles, key=str)]


@pytest.mark.parametrize("key,role", DENIED, ids=lambda v: str(getattr(v, "value", v)))
def test_every_disallowed_role_gets_403(
    world_client: tuple[TestClient, dict[Role, str]], key: RouteKey, role: Role
) -> None:
    client, tokens = world_client
    method, path = key

    response = client.request(method, concrete(path), headers=bearer(tokens[role]))

    assert response.status_code == 403, f"{method} {path} con {role.value}"
    assert response.json()["error"]["code"] == "FORBIDDEN"


ALLOWED = [(key, role) for key, roles in PROTECTED for role in sorted(roles, key=str)]


@pytest.mark.parametrize("key,role", ALLOWED, ids=lambda v: str(getattr(v, "value", v)))
def test_every_allowed_role_passes_the_role_check(
    world_client: tuple[TestClient, dict[Role, str]], key: RouteKey, role: Role
) -> None:
    client, tokens = world_client

    status = call(client, key, tokens[role], own=role is Role.DENTIST)

    assert status not in (401, 403), f"{key[0]} {key[1]} con {role.value} -> {status}"


def test_reception_cannot_create_users(world_client: tuple[TestClient, dict[Role, str]]) -> None:
    client, tokens = world_client

    assert call(client, ("POST", "/api/v1/users"), tokens[Role.RECEPTIONIST]) == 403


def test_dentist_cannot_book_appointments(
    world_client: tuple[TestClient, dict[Role, str]],
) -> None:
    client, tokens = world_client

    assert call(client, ("POST", "/api/v1/appointments"), tokens[Role.DENTIST]) == 403


def test_admin_and_reception_can_search_patients(
    world_client: tuple[TestClient, dict[Role, str]],
) -> None:
    client, tokens = world_client

    for role in (Role.ADMIN, Role.RECEPTIONIST):
        response = client.get("/api/v1/patients?q=ruiz", headers=bearer(tokens[role]))
        assert response.status_code not in (401, 403)


@pytest.mark.parametrize("key", PUBLIC_KEYS, ids=lambda k: f"{k[0]} {k[1]}")
def test_public_routes_answer_without_a_session(
    world_client: tuple[TestClient, dict[Role, str]], key: RouteKey
) -> None:
    client, _ = world_client
    method, path = key

    response = client.request(method, path, json={} if method == "POST" else None)

    assert response.status_code not in (401, 403)

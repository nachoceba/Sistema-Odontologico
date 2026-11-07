"""Inventario de rutas: ninguna ruta de negocio puede quedar sin autenticacion (design D-7).

Red de seguridad de la regla dura 4: todo endpoint nuevo depende de ``current_user`` (directa o
indirectamente, por ejemplo a traves de ``require_role``) salvo la lista blanca publica.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.testclient import TestClient

from app.api.dependencies import current_user
from tests.unit.api.route_helpers import api_routes, route_keys

PUBLIC_ROUTES = {("POST", "/api/v1/auth/login"), ("GET", "/api/v1/health")}


def depends_on_current_user(dependant: Dependant) -> bool:
    return any(
        child.call is current_user or depends_on_current_user(child)
        for child in dependant.dependencies
    )


def unprotected_routes(app: FastAPI) -> list[str]:
    """``METODO /ruta`` de cada APIRoute fuera de la lista blanca sin ``current_user``."""
    found: list[str] = []
    for context in api_routes(app):
        for method, path in route_keys(context):
            if (method, path) in PUBLIC_ROUTES:
                continue
            if not depends_on_current_user(context.dependant):
                found.append(f"{method} {path}")
    return found


def test_every_non_public_route_depends_on_current_user(
    make_client: Callable[[], tuple[FastAPI, TestClient]],
) -> None:
    app, _ = make_client()
    assert unprotected_routes(app) == []


def test_every_protected_route_answers_401_without_token(
    make_client: Callable[[], tuple[FastAPI, TestClient]],
) -> None:
    app, test_client = make_client()
    checked = 0
    for context in api_routes(app):
        for method, path in route_keys(context):
            if (method, path) in PUBLIC_ROUTES:
                continue
            concrete = re.sub(r"\{[^}]+\}", "x", path)
            response = test_client.request(method, concrete)
            assert response.status_code == 401, f"{method} {path} -> {response.status_code}"
            assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"
            checked += 1
    assert checked >= 1  # al menos GET /auth/me


def test_the_check_detects_and_names_an_unprotected_route(
    make_client: Callable[[], tuple[FastAPI, TestClient]],
) -> None:
    app, _ = make_client()

    def forgotten() -> dict[str, str]:
        return {"dato": "expuesto"}

    app.add_api_route("/api/v1/olvidada", forgotten)

    assert unprotected_routes(app) == ["GET /api/v1/olvidada"]


def test_the_inventory_sees_the_real_routes(
    make_client: Callable[[], tuple[FastAPI, TestClient]],
) -> None:
    app, _ = make_client()
    seen = {key for context in api_routes(app) for key in route_keys(context)}
    assert seen >= PUBLIC_ROUTES
    assert ("GET", "/api/v1/auth/me") in seen


def test_public_list_is_exactly_login_and_health() -> None:
    assert {("POST", "/api/v1/auth/login"), ("GET", "/api/v1/health")} == PUBLIC_ROUTES


FORBIDDEN_PATH_WORDS = ("notif", "email", "recordatorio", "reminder", "task", "tarea", "celery")


def test_there_is_no_http_route_to_trigger_notifications_reminders_or_tasks(
    make_client: Callable[[], tuple[FastAPI, TestClient]],
) -> None:
    _, client = make_client()

    paths = list(client.get("/openapi.json").json()["paths"])

    assert paths, "el OpenAPI no lista ninguna ruta"
    offenders = [p for p in paths if any(word in p.lower() for word in FORBIDDEN_PATH_WORDS)]
    assert offenders == []

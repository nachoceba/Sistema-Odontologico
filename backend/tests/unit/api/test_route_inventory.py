"""Inventario de rutas: ninguna ruta de negocio puede quedar sin autenticacion (design D-7).

Red de seguridad de la regla dura 4: todo endpoint nuevo depende de ``current_user`` (directa o
indirectamente, por ejemplo a traves de ``require_role``) salvo la lista blanca publica.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, RouteContext, iter_route_contexts
from fastapi.testclient import TestClient

from app.api.dependencies import current_user

PUBLIC_ROUTES = {("POST", "/api/v1/auth/login"), ("GET", "/api/v1/health")}


def depends_on_current_user(dependant: Dependant) -> bool:
    return any(
        child.call is current_user or depends_on_current_user(child)
        for child in dependant.dependencies
    )


def api_routes(app: FastAPI) -> list[RouteContext]:
    """Rutas efectivas con su prefijo (esta version de FastAPI anida los routers incluidos)."""
    return [
        context
        for context in iter_route_contexts(app.routes)
        if isinstance(context.original_route, APIRoute)
    ]


def route_keys(context: RouteContext) -> list[tuple[str, str]]:
    return [(method, str(context.path)) for method in sorted(context.methods or set())]


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

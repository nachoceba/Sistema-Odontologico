"""Rutas efectivas de la app, compartidas por el inventario y la matriz de permisos."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.routing import APIRoute, RouteContext, iter_route_contexts


def api_routes(app: FastAPI) -> list[RouteContext]:
    """Rutas efectivas con su prefijo (esta version de FastAPI anida los routers incluidos)."""
    return [
        context
        for context in iter_route_contexts(app.routes)
        if isinstance(context.original_route, APIRoute)
    ]


def route_keys(context: RouteContext) -> list[tuple[str, str]]:
    return [(method, str(context.path)) for method in sorted(context.methods or set())]

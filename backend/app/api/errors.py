"""Traduccion de excepciones a respuestas JSON uniformes (spec error-model)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import DomainError

logger = logging.getLogger(__name__)

DEFAULT_DOMAIN_STATUS = 400
HTTP_401 = 401
STATUS_BY_CODE: dict[str, int] = {
    "APPOINTMENT_NOT_FOUND": 404,
    "SLOT_TAKEN": 409,
    "INVALID_CREDENTIALS": 401,
    "NOT_AUTHENTICATED": 401,
    "FORBIDDEN": 403,
}


def _body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message}}


async def handle_domain_error(_request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, DomainError)
    status = STATUS_BY_CODE.get(error.code, DEFAULT_DOMAIN_STATUS)
    headers = {"WWW-Authenticate": "Bearer"} if status == HTTP_401 else None
    return JSONResponse(status_code=status, content=_body(error.code, str(error)), headers=headers)


async def handle_unexpected_error(_request: Request, error: Exception) -> JSONResponse:
    logger.error("Error inesperado", exc_info=error)
    return JSONResponse(status_code=500, content=_body("INTERNAL_ERROR", "Error interno"))


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(Exception, handle_unexpected_error)

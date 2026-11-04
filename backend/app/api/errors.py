"""Traduccion de excepciones a respuestas JSON uniformes (spec error-model)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import DomainError

logger = logging.getLogger(__name__)

DEFAULT_DOMAIN_STATUS = 400
HTTP_401 = 401
STATUS_BY_CODE: dict[str, int] = {
    "APPOINTMENT_NOT_FOUND": 404,
    "USER_NOT_FOUND": 404,
    "PATIENT_NOT_FOUND": 404,
    "PROFESSIONAL_NOT_FOUND": 404,
    "SLOT_TAKEN": 409,
    "PATIENT_DOUBLE_BOOKED": 409,
    "PATIENT_INACTIVE": 409,
    "PROFESSIONAL_INACTIVE": 409,
    "CANCELLED_IS_FINAL": 409,
    "ATTENDANCE_ALREADY_RECORDED": 409,
    "ALREADY_STARTED": 409,
    "NOT_STARTED_YET": 409,
    "EMAIL_TAKEN": 409,
    "ROLE_CHANGE_NOT_ALLOWED": 409,
    "SELF_MODIFICATION_NOT_ALLOWED": 409,
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


async def handle_validation_error(_request: Request, error: Exception) -> JSONResponse:
    """422 con la lista de errores por campo pero sin ``input`` ni ``ctx`` (design D-6).

    Pydantic v2 repite en ``input`` el valor enviado: en un alta o un login seria la contrasena.
    """
    assert isinstance(error, RequestValidationError)
    detail = [
        {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": detail})


async def handle_unexpected_error(_request: Request, error: Exception) -> JSONResponse:
    logger.error("Error inesperado", exc_info=error)
    return JSONResponse(status_code=500, content=_body("INTERNAL_ERROR", "Error interno"))


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)

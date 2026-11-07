"""Filtro del registro de accesos: sin la parte de consulta (spec access-logging, DD-77)."""

from __future__ import annotations

import logging

import pytest

from app.core.logging import AccessLogQueryFilter

# Mismo formato y argumentos que escribe uvicorn (h11_impl / httptools_impl).
UVICORN_FORMAT = '%s - "%s %s HTTP/%s" %d'


def access_record(
    path_with_query: str, status: int = 200, *, logger: str = "uvicorn.access"
) -> logging.LogRecord:
    return logging.LogRecord(
        name=logger,
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=UVICORN_FORMAT,
        args=("172.18.0.1:51234", "GET", path_with_query, "1.1", status),
        exc_info=None,
    )


def filtered_message(record: logging.LogRecord) -> str:
    assert AccessLogQueryFilter().filter(record) is True
    return record.getMessage()


def test_patient_search_keeps_method_path_and_status_but_not_the_query() -> None:
    message = filtered_message(access_record("/api/v1/patients?q=ruiz"))

    assert "GET" in message
    assert "/api/v1/patients" in message
    assert "200" in message
    assert "ruiz" not in message
    assert "q=" not in message
    assert "?" not in message


def test_search_by_document_number_is_not_logged() -> None:
    message = filtered_message(access_record("/api/v1/patients?q=40555666"))

    assert "40555666" not in message


def test_other_route_with_query_loses_its_parameters() -> None:
    path = "/api/v1/appointments?professional_id=abc&from=2026-11-09T00:00:00Z&to=2026-11-10"

    message = filtered_message(access_record(path))

    assert "/api/v1/appointments" in message
    assert "professional_id=" not in message
    assert "2026-11-09" not in message


def test_route_without_query_is_left_untouched() -> None:
    message = filtered_message(access_record("/api/v1/health"))

    assert message == '172.18.0.1:51234 - "GET /api/v1/health HTTP/1.1" 200'


def test_error_response_with_query_keeps_the_status_only() -> None:
    message = filtered_message(access_record("/api/v1/patients?q=ruiz", 401))

    assert "401" in message
    assert "ruiz" not in message


def test_record_from_another_logger_is_not_modified() -> None:
    record = access_record("/api/v1/patients?q=ruiz", logger="app.otro")

    message = filtered_message(record)

    assert "q=ruiz" in message


@pytest.mark.parametrize("args", [(), ("solo-uno",), ("a", "GET", 123, "1.1", 200)])
def test_unexpected_arguments_pass_through_without_error(args: tuple[object, ...]) -> None:
    record = access_record("/x?y=1")
    record.args = args

    assert AccessLogQueryFilter().filter(record) is True
    assert record.args == args

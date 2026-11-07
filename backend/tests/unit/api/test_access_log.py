"""``create_app()`` instala el filtro del registro de accesos (spec access-logging, D-5)."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logging import ACCESS_LOGGER_NAME, AccessLogQueryFilter

AppFactory = Callable[[], tuple[FastAPI, TestClient]]


def installed_filters() -> list[logging.Filter]:
    logger = logging.getLogger(ACCESS_LOGGER_NAME)
    return [f for f in logger.filters if isinstance(f, AccessLogQueryFilter)]


def test_create_app_installs_the_filter_once_even_if_called_twice(
    make_client: AppFactory,
) -> None:
    make_client()
    make_client()

    assert len(installed_filters()) == 1


def test_real_uvicorn_access_line_has_no_query(
    make_client: AppFactory, caplog: pytest.LogCaptureFixture
) -> None:
    app, _ = make_client()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=0, log_config=None, log_level="info")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    with caplog.at_level(logging.INFO, logger=ACCESS_LOGGER_NAME):
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and time.monotonic() < deadline:
                time.sleep(0.05)
            assert server.started, "uvicorn no arranco"
            port = server.servers[0].sockets[0].getsockname()[1]
            first = httpx.get(f"http://127.0.0.1:{port}/api/v1/patients?q=ruiz")
            second = httpx.get(f"http://127.0.0.1:{port}/api/v1/health")
        finally:
            server.should_exit = True
            thread.join(timeout=10)

    assert first.status_code == 401
    assert second.status_code == 200
    messages = [r.getMessage() for r in caplog.records if r.name == ACCESS_LOGGER_NAME]
    searched = [m for m in messages if "/api/v1/patients" in m]
    assert searched and all("401" in m and "ruiz" not in m and "q=" not in m for m in searched)
    assert any("/api/v1/health" in m and "200" in m for m in messages)

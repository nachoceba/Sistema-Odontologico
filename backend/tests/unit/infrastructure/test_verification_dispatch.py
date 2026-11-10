"""Despacho de la verificacion despues del commit, sin depender de Redis (C-15, D-7)."""

from __future__ import annotations

import logging

import pytest
from kombu.exceptions import OperationalError

from app.infrastructure.tasks.dispatcher import CeleryVerificationDispatcher


def test_it_publishes_the_appointment_and_the_token() -> None:
    published: list[tuple[str, str]] = []

    CeleryVerificationDispatcher(lambda a, t: published.append((a, t))).dispatch("turno-1", "tok")

    assert published == [("turno-1", "tok")]


def test_a_publish_error_is_swallowed_and_logged_without_token_or_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def publish(appointment_id: str, token: str) -> None:
        raise OperationalError("redis caido con lucia@example.com")

    caplog.set_level(logging.WARNING)

    CeleryVerificationDispatcher(publish).dispatch("turno-1", "tok-secreto")

    assert "turno-1" in caplog.text
    assert "OperationalError" in caplog.text
    assert "tok-secreto" not in caplog.text
    assert "lucia@example.com" not in caplog.text

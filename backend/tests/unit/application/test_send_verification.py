"""Envio del email de verificacion de una reserva online (spec notification-tasks, C-15)."""

from __future__ import annotations

import logging
from datetime import timedelta

import pytest

from app.application.notifications import RequeueDeps, requeue_pending
from app.application.public_booking import book_online
from app.application.verification import VerificationDeps, send_verification
from app.core.security import hash_confirmation_token
from app.domain.appointments import AppointmentStatus
from app.domain.notifications import DeliveryOutcome
from app.domain.settings.types import ClinicSettings
from app.infrastructure.in_memory import (
    InMemoryClinicSettingsRepository,
    InMemoryProfessionalRepository,
)
from tests.email_fakes import FakeEmailSender
from tests.unit.application.agenda_helpers import PROF_A, World
from tests.unit.domain.appointments.helpers import monday

BASE = "https://turnos.consultorio.example"


class Scenario:
    def __init__(self) -> None:
        self.world = World()
        self.sender = FakeEmailSender()
        book_online(
            self.world.public_deps(),
            professional_id=PROF_A,
            starts_at=monday(10),
            document_number="40999888",
            first_name="Lucía",
            last_name="Díaz",
            email="lucia@example.com",
            phone=None,
        )
        self.appointment_id, self.token = self.world.verification.calls[0]

    def deps(self) -> VerificationDeps:
        return VerificationDeps(
            appointments=self.world.appointments,
            patients=self.world.patients,
            professionals=InMemoryProfessionalRepository(self.world.accounts),
            settings=InMemoryClinicSettingsRepository(
                ClinicSettings(clinic_name="Consultorio Demo")
            ),
            sender=self.sender,
            clock=lambda: self.world.now,
            hash_token=hash_confirmation_token,
            public_app_url=BASE,
        )

    def send(self, token: str | None = None, *, attempt: int = 1) -> DeliveryOutcome:
        return send_verification(
            self.deps(), self.appointment_id, token or self.token, attempt=attempt
        )


def test_it_sends_the_link_to_the_email_of_the_record() -> None:
    scenario = Scenario()

    assert scenario.send() is DeliveryOutcome.SENT

    [email] = scenario.sender.sent
    assert email.recipient == "lucia@example.com"
    assert email.subject == "Confirmá tu turno en Consultorio Demo"
    assert f"{BASE}/turnos/confirmar#token={scenario.token}" in email.body


def test_it_sends_nothing_when_the_appointment_was_cancelled() -> None:
    scenario = Scenario()
    scenario.world.appointments.change_status(
        scenario.appointment_id, AppointmentStatus.CANCELLED, "motivo"
    )

    assert scenario.send() is DeliveryOutcome.SKIPPED
    assert scenario.sender.sent == []


def test_it_sends_nothing_when_the_appointment_is_already_confirmed() -> None:
    scenario = Scenario()
    scenario.world.appointments.confirm_by_token_hash(
        hash_confirmation_token(scenario.token), scenario.world.now
    )

    assert scenario.send() is DeliveryOutcome.SKIPPED


def test_it_sends_nothing_when_the_deadline_passed() -> None:
    scenario = Scenario()
    scenario.world.now += timedelta(hours=2)

    assert scenario.send() is DeliveryOutcome.SKIPPED
    assert scenario.sender.sent == []


def test_it_sends_nothing_when_the_token_does_not_match() -> None:
    scenario = Scenario()

    assert scenario.send("otro-token") is DeliveryOutcome.SKIPPED
    assert scenario.sender.sent == []


def test_a_temporary_smtp_failure_asks_for_a_retry_until_the_last_attempt() -> None:
    scenario = Scenario()
    scenario.sender.fail_next(2, temporary=True, code="TIMEOUT")

    assert scenario.send(attempt=1) is DeliveryOutcome.RETRY
    assert scenario.send(attempt=3) is DeliveryOutcome.FAILED
    assert scenario.sender.sent == []


def test_a_permanent_smtp_failure_is_failed_without_retry() -> None:
    scenario = Scenario()
    scenario.sender.fail_next(1, temporary=False, code="550")

    assert scenario.send() is DeliveryOutcome.FAILED


def test_the_log_has_only_the_appointment_id_and_the_result(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scenario = Scenario()
    caplog.set_level(logging.INFO)

    scenario.send()

    assert scenario.appointment_id in caplog.text
    assert scenario.token not in caplog.text
    assert "lucia@example.com" not in caplog.text


def test_the_requeue_pass_never_takes_a_verification() -> None:
    scenario = Scenario()
    published: list[str] = []
    deps = RequeueDeps(
        notifications=scenario.world.notifications,
        publish=published.append,
        clock=lambda: scenario.world.now + timedelta(days=1),
    )

    assert requeue_pending(deps) == 0
    assert published == []

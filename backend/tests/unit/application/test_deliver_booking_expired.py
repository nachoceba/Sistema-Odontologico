"""Envio del aviso de vencimiento (spec notification-sending, C-16, DD-140)."""

from __future__ import annotations

import logging

import pytest

from app.application.appointments import cancel_appointment
from app.application.notifications import deliver_notification
from app.domain.appointments import (
    AppointmentStatus,
    NotificationKind,
    NotificationStatus,
)
from app.domain.notifications import DeliveryOutcome
from app.domain.public_booking.rules import EXPIRED_BOOKING_REASON
from tests.unit.application.notification_helpers import SendWorld
from tests.unit.domain.appointments.helpers import local, monday

FRIDAY_9 = local(2026, 10, 2, 9)


def expired_scenario(*, reason: str | None = EXPIRED_BOOKING_REASON) -> tuple[SendWorld, str]:
    """El turno del lunes 10:00, cancelado, con su aviso de vencimiento pendiente."""
    scenario = SendWorld()
    scenario.world.now = FRIDAY_9
    scenario.world.appointments.change_status(
        scenario.appointment.id, AppointmentStatus.CANCELLED, reason
    )
    row = scenario.world.notifications.add_pending_booking_expired(
        scenario.appointment.id, scenario.appointment.starts_at
    )
    assert row is not None
    return scenario, row.id


def test_a_booking_expired_notice_of_an_expired_cancellation_is_sent_to_the_patient_file() -> None:
    scenario, notice = expired_scenario()

    outcome = deliver_notification(scenario.deps(), notice)

    assert outcome is DeliveryOutcome.SENT
    [email] = scenario.sender.sent
    assert email.recipient == "juan@example.com"
    assert "se canceló por falta de confirmación" in email.subject
    assert "Profesional: Dra. A" in email.body
    assert "lunes 05/10/2026 10:00" in email.body
    assert "/turnos." in email.body
    [expired] = [r for r in scenario.rows() if r.kind is NotificationKind.BOOKING_EXPIRED]
    assert expired.status is NotificationStatus.SENT
    assert expired.sent_at == FRIDAY_9


def test_the_link_uses_the_configured_public_url() -> None:
    scenario, notice = expired_scenario()
    deps = scenario.deps()

    deliver_notification(deps, notice)

    [email] = scenario.sender.sent
    assert deps.public_app_url
    assert f"{deps.public_app_url}/turnos." in email.body


def test_a_cancellation_with_another_reason_expires_the_notice_without_sending() -> None:
    scenario, notice = expired_scenario(reason="El paciente avisó por teléfono")

    outcome = deliver_notification(scenario.deps(), notice)

    assert outcome is DeliveryOutcome.EXPIRED
    assert scenario.sender.sent == []
    [expired] = [r for r in scenario.rows() if r.kind is NotificationKind.BOOKING_EXPIRED]
    assert (expired.status, expired.error) == (NotificationStatus.FAILED, "EXPIRED")
    assert expired.sent_at is None


def test_a_cancellation_without_reason_expires_the_notice() -> None:
    scenario, notice = expired_scenario(reason=None)

    assert deliver_notification(scenario.deps(), notice) is DeliveryOutcome.EXPIRED
    assert scenario.sender.sent == []


def test_a_confirmed_appointment_expires_the_notice_without_sending() -> None:
    scenario = SendWorld()
    scenario.world.now = FRIDAY_9
    row = scenario.world.notifications.add_pending_booking_expired(
        scenario.appointment.id, scenario.appointment.starts_at
    )
    assert row is not None

    outcome = deliver_notification(scenario.deps(), row.id)

    assert outcome is DeliveryOutcome.EXPIRED
    assert scenario.sender.sent == []


def test_a_notice_of_an_appointment_that_already_started_expires_without_sending() -> None:
    scenario, notice = expired_scenario()
    scenario.world.now = monday(10)  # justo en el inicio

    assert deliver_notification(scenario.deps(), notice) is DeliveryOutcome.EXPIRED
    assert scenario.sender.sent == []


def test_one_minute_before_the_start_it_is_still_sent() -> None:
    scenario, notice = expired_scenario()
    scenario.world.now = monday(9, 59)

    assert deliver_notification(scenario.deps(), notice) is DeliveryOutcome.SENT


def test_a_notice_for_a_previous_start_expires_without_sending() -> None:
    scenario, notice = expired_scenario()
    scenario.world.appointments.reschedule(scenario.appointment.id, monday(11), monday(11, 30))

    assert deliver_notification(scenario.deps(), notice) is DeliveryOutcome.EXPIRED
    assert scenario.sender.sent == []


def test_running_the_notice_twice_sends_one_email() -> None:
    scenario, notice = expired_scenario()

    first = deliver_notification(scenario.deps(), notice)
    second = deliver_notification(scenario.deps(), notice)

    assert (first, second) == (DeliveryOutcome.SENT, DeliveryOutcome.SKIPPED)
    assert len(scenario.sender.sent) == 1


def test_temporary_failures_use_the_retries_of_c11() -> None:
    scenario, notice = expired_scenario()
    scenario.sender.fail_next(1, temporary=True, code="TIMEOUT")

    first = deliver_notification(scenario.deps(), notice, attempt=1)
    second = deliver_notification(scenario.deps(), notice, attempt=2)

    assert (first, second) == (DeliveryOutcome.RETRY, DeliveryOutcome.SENT)
    assert len(scenario.sender.sent) == 1


def test_three_temporary_failures_end_failed() -> None:
    scenario, notice = expired_scenario()
    scenario.sender.fail_next(5, temporary=True, code="451")

    outcomes = [deliver_notification(scenario.deps(), notice, attempt=n) for n in (1, 2, 3)]

    assert outcomes == [DeliveryOutcome.RETRY, DeliveryOutcome.RETRY, DeliveryOutcome.FAILED]
    [expired] = [r for r in scenario.rows() if r.kind is NotificationKind.BOOKING_EXPIRED]
    assert expired.error == "SMTP_TEMPORARY 451"


def test_the_log_carries_ids_and_kind_but_not_the_recipient(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scenario, notice = expired_scenario()

    with caplog.at_level(logging.INFO):
        deliver_notification(scenario.deps(), notice)

    assert "booking_expired" in caplog.text
    assert "juan@example.com" not in caplog.text


def test_a_manual_cancellation_never_yields_a_sendable_expiry_notice() -> None:
    """Aunque alguien registrara el aviso, la regla de envio lo descarta si no fue por vencer."""
    scenario = SendWorld()
    scenario.world.now = FRIDAY_9
    cancel_appointment(scenario.world.deps(), scenario.appointment.id, "Cancela la recepción")
    row = scenario.world.notifications.add_pending_booking_expired(
        scenario.appointment.id, scenario.appointment.starts_at
    )
    assert row is not None

    assert deliver_notification(scenario.deps(), row.id) is DeliveryOutcome.EXPIRED


def test_the_expiry_notice_names_the_treatment() -> None:
    scenario = SendWorld(with_treatment=True)
    scenario.world.now = FRIDAY_9
    scenario.world.appointments.change_status(
        scenario.appointment.id, AppointmentStatus.CANCELLED, EXPIRED_BOOKING_REASON
    )
    row = scenario.world.notifications.add_pending_booking_expired(
        scenario.appointment.id, scenario.appointment.starts_at
    )
    assert row is not None

    deliver_notification(scenario.deps(), row.id)

    [email] = scenario.sender.sent
    assert "Tratamiento: Limpieza dental" in email.body


def test_the_expiry_notice_of_a_booking_without_treatment_has_no_line() -> None:
    scenario, notice = expired_scenario()

    deliver_notification(scenario.deps(), notice)

    [email] = scenario.sender.sent
    assert "Tratamiento" not in email.body

"""Enviar una notificacion pendiente (spec notification-sending, con repositorios en memoria)."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime

import pytest

from app.application.appointments import cancel_appointment, reschedule_appointment
from app.application.notifications import deliver_notification
from app.domain.appointments import (
    AppointmentStatus,
    NotificationKind,
    NotificationStatus,
)
from app.domain.notifications import DeliveryOutcome
from tests.unit.application.notification_helpers import SendWorld
from tests.unit.domain.appointments.helpers import local, monday

SENT = NotificationStatus.SENT
FAILED = NotificationStatus.FAILED
PENDING = NotificationStatus.PENDING
FRIDAY_9 = local(2026, 10, 2, 9)


def at(scenario: SendWorld, moment: datetime = FRIDAY_9) -> SendWorld:
    scenario.world.now = moment
    return scenario


# --- Enviar ------------------------------------------------------------------------------------


def test_a_pending_confirmation_is_sent_once_and_marked_sent_with_the_clock() -> None:
    scenario = at(SendWorld())

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.SENT
    [email] = scenario.sender.sent
    assert email.recipient == "juan@example.com"
    assert "Consultorio Demo" in email.subject
    assert "Hola, Juan Pérez:" in email.body
    assert "Dra. A" in email.body
    [row] = scenario.rows()
    assert row.status is SENT
    assert row.sent_at == FRIDAY_9
    assert row.error is None


def test_a_pending_reminder_is_sent_with_the_reminder_text() -> None:
    scenario = at(SendWorld())
    reminder = scenario.add_reminder()

    outcome = deliver_notification(scenario.deps(), reminder.id)

    assert outcome is DeliveryOutcome.SENT
    [email] = scenario.sender.sent
    assert email.subject.startswith("Recordatorio de turno")
    assert "Te recordamos tu turno." in email.body
    kinds = {row.kind: row.status for row in scenario.rows()}
    assert kinds == {NotificationKind.CONFIRMATION: PENDING, NotificationKind.REMINDER: SENT}


def test_a_deactivated_patient_with_a_current_appointment_still_gets_the_email() -> None:
    scenario = at(SendWorld())
    scenario.world.set_patient_active("pac-1", False)

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.SENT
    assert len(scenario.sender.sent) == 1


def test_processing_never_changes_the_appointment() -> None:
    scenario = at(SendWorld())
    before = scenario.world.appointments.get(scenario.appointment.id)

    deliver_notification(scenario.deps(), scenario.notification.id)

    assert scenario.world.appointments.get(scenario.appointment.id) == before


# --- Idempotencia ------------------------------------------------------------------------------


def test_an_already_sent_notification_sends_nothing_and_keeps_its_row() -> None:
    scenario = at(SendWorld())
    deliver_notification(scenario.deps(), scenario.notification.id)
    [sent_row] = scenario.rows()

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.SKIPPED
    assert len(scenario.sender.sent) == 1
    assert scenario.rows() == [sent_row]


def test_a_deleted_notification_is_skipped_without_error() -> None:
    scenario = at(SendWorld())
    scenario.world.notifications.delete_pending(scenario.appointment.id)

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.SKIPPED
    assert scenario.sender.sent == []


def test_a_notification_for_a_start_that_is_no_longer_the_appointments_is_skipped() -> None:
    scenario = at(SendWorld())
    moved = scenario.world.appointments.reschedule(
        scenario.appointment.id, monday(11), monday(11, 30)
    )
    assert moved.starts_at == monday(11)

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.SKIPPED
    assert scenario.sender.sent == []
    assert scenario.rows() == [scenario.notification]


def test_an_unknown_id_is_skipped() -> None:
    scenario = at(SendWorld())
    assert deliver_notification(scenario.deps(), "no-existe") is DeliveryOutcome.SKIPPED


# --- Avisos vencidos (P-4) ---------------------------------------------------------------------


def test_an_accumulated_confirmation_of_a_past_appointment_expires_without_sending() -> None:
    scenario = at(SendWorld(), monday(12))  # el turno fue hace dos horas

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.EXPIRED
    assert scenario.sender.sent == []
    [row] = scenario.rows()
    assert row.status is FAILED
    assert row.error == "EXPIRED"
    assert row.sent_at is None


def test_an_accumulated_confirmation_of_a_future_appointment_is_sent() -> None:
    scenario = at(SendWorld(), local(2026, 10, 3, 10))

    assert deliver_notification(scenario.deps(), scenario.notification.id) is DeliveryOutcome.SENT


def test_an_appointment_that_starts_exactly_now_expires() -> None:
    scenario = at(SendWorld(), monday(10))

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.EXPIRED
    assert scenario.rows()[0].error == "EXPIRED"


@pytest.mark.parametrize("status", [AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW])
def test_a_pending_confirmation_of_an_attended_appointment_expires(
    status: AppointmentStatus,
) -> None:
    scenario = at(SendWorld())
    scenario.world.appointments.change_status(scenario.appointment.id, status)

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.EXPIRED
    assert scenario.sender.sent == []
    assert scenario.rows()[0].status is FAILED


# --- Fallos y reintentos (P-5) -----------------------------------------------------------------


def test_a_permanent_failure_marks_failed_in_one_attempt_and_leaves_the_appointment() -> None:
    scenario = at(SendWorld())
    scenario.sender.fail_next(1, temporary=False, code="550 5.1.1 <juan@example.com> rejected")

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.FAILED
    assert scenario.sender.attempts == 1
    [row] = scenario.rows()
    assert row.status is FAILED
    assert row.error == "SMTP_PERMANENT 550"
    assert row.sent_at is None
    stored = scenario.world.appointments.get(scenario.appointment.id)
    assert stored is not None
    assert stored.status is AppointmentStatus.SCHEDULED
    assert stored.starts_at == monday(10)


def test_a_temporary_failure_keeps_the_row_pending_and_asks_for_a_retry() -> None:
    scenario = at(SendWorld())
    scenario.sender.fail_next(1, temporary=True, code="TIMEOUT")

    first = deliver_notification(scenario.deps(), scenario.notification.id, attempt=1)

    assert first is DeliveryOutcome.RETRY
    assert scenario.rows() == [scenario.notification]

    second = deliver_notification(scenario.deps(), scenario.notification.id, attempt=2)

    assert second is DeliveryOutcome.SENT
    assert len(scenario.sender.sent) == 1
    assert scenario.rows()[0].status is SENT


def test_three_temporary_failures_end_in_failed_with_the_last_error() -> None:
    scenario = at(SendWorld())
    scenario.sender.fail_next(2, temporary=True, code="TIMEOUT")
    scenario.sender.fail_next(1, temporary=True, code="451")

    outcomes = [
        deliver_notification(scenario.deps(), scenario.notification.id, attempt=n)
        for n in (1, 2, 3)
    ]

    assert outcomes == [DeliveryOutcome.RETRY, DeliveryOutcome.RETRY, DeliveryOutcome.FAILED]
    assert scenario.sender.attempts == 3
    [row] = scenario.rows()
    assert row.status is FAILED
    assert row.error == "SMTP_TEMPORARY 451"


def test_a_failed_notification_is_never_retried() -> None:
    scenario = at(SendWorld())
    scenario.sender.fail_next(1, temporary=False, code="550")
    deliver_notification(scenario.deps(), scenario.notification.id)

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.SKIPPED
    assert scenario.sender.attempts == 1


def test_after_a_failed_send_the_appointment_can_still_be_rescheduled_and_cancelled() -> None:
    scenario = at(SendWorld())
    scenario.sender.fail_next(1, temporary=False, code="550")
    deliver_notification(scenario.deps(), scenario.notification.id)
    agenda = scenario.world.deps()

    moved = reschedule_appointment(agenda, scenario.appointment.id, monday(11))
    cancelled = cancel_appointment(agenda, moved.id, "paciente avisa")

    assert moved.starts_at == monday(11)
    assert cancelled.status is AppointmentStatus.CANCELLED


# --- Registros (D-12) --------------------------------------------------------------------------


def test_the_logs_carry_no_email_nor_name(caplog: pytest.LogCaptureFixture) -> None:
    scenario = at(SendWorld())
    scenario.sender.fail_next(1, temporary=True, code="TIMEOUT")
    caplog.set_level(logging.DEBUG)

    deliver_notification(scenario.deps(), scenario.notification.id, attempt=1)
    deliver_notification(scenario.deps(), scenario.notification.id, attempt=2)

    text = caplog.text
    assert scenario.notification.id in text
    assert "SENT" in text
    assert "RETRY" in text
    assert "juan@example.com" not in text
    assert "Pérez" not in text
    assert "Juan" not in text


# --- Tratamiento (C-17, DD-147) ----------------------------------------------------------------


def test_the_confirmation_names_the_treatment_after_the_professional() -> None:
    scenario = at(SendWorld(with_treatment=True))

    deliver_notification(scenario.deps(), scenario.notification.id)

    [email] = scenario.sender.sent
    assert "Profesional: Dra. A" + chr(10) + "Tratamiento: Limpieza dental" in email.body


def test_the_reminder_names_the_treatment_too() -> None:
    scenario = at(SendWorld(with_treatment=True))
    reminder = scenario.add_reminder()

    deliver_notification(scenario.deps(), reminder.id)

    [email] = scenario.sender.sent
    assert "Tratamiento: Limpieza dental" in email.body


def test_the_treatment_name_is_the_current_one_at_send_time() -> None:
    scenario = at(SendWorld(with_treatment=True))
    scenario.world.treatments.update(scenario.world.limpieza.id, name="Profilaxis")

    deliver_notification(scenario.deps(), scenario.notification.id)

    [email] = scenario.sender.sent
    assert "Tratamiento: Profilaxis" in email.body
    assert "Limpieza dental" not in email.body


def test_a_deactivated_treatment_still_shows_its_name() -> None:
    scenario = at(SendWorld(with_treatment=True))
    scenario.world.treatments.update(scenario.world.limpieza.id, active=False)

    deliver_notification(scenario.deps(), scenario.notification.id)

    [email] = scenario.sender.sent
    assert "Tratamiento: Limpieza dental" in email.body


def test_an_appointment_without_treatment_is_sent_without_the_line() -> None:
    scenario = at(SendWorld())

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.SENT
    [email] = scenario.sender.sent
    assert "Tratamiento" not in email.body


def test_a_treatment_that_cannot_be_read_does_not_fail_the_send() -> None:
    scenario = at(SendWorld())
    scenario.world.appointments._appointments[scenario.appointment.id] = replace(  # noqa: SLF001
        scenario.appointment, treatment_id="tratamiento-fantasma"
    )

    outcome = deliver_notification(scenario.deps(), scenario.notification.id)

    assert outcome is DeliveryOutcome.SENT
    [email] = scenario.sender.sent
    assert "Tratamiento" not in email.body

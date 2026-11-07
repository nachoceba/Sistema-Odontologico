"""Pasada de recordatorios con repositorios en memoria (specs reminder-scheduling)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.application.notifications import deliver_notification
from app.application.reminders import ReminderDeps, send_reminders
from app.domain.appointments import (
    Appointment,
    AppointmentStatus,
    NotificationKind,
    NotificationStatus,
)
from app.domain.appointments.ports import AgendaUnitOfWork
from app.domain.notifications import (
    EmailSender,
    EmailSendError,
    OutgoingEmail,
    ReminderRunSummary,
)
from app.domain.patients.types import Patient
from app.infrastructure.in_memory import InMemoryAppointmentRepository, InMemoryPatientRepository
from tests.unit.application.agenda_helpers import PROF_A, PROF_B
from tests.unit.application.reminder_helpers import ReminderWorld
from tests.unit.domain.appointments.helpers import local, monday

SENT = NotificationStatus.SENT


def test_at_the_configured_hour_each_appointment_of_tomorrow_gets_a_reminder() -> None:
    scenario = ReminderWorld()
    dra_a = scenario.world.seed(monday(10), professional_id=PROF_A)
    dr_b = scenario.world.seed(monday(11), professional_id=PROF_B, patient_id="pac-2")

    summary = send_reminders(scenario.deps())

    assert (summary.processed, summary.sent, summary.failed, summary.pending) == (2, 2, 0, 0)
    assert sorted(email.recipient for email in scenario.sender.sent) == [
        "ana@example.com",
        "juan@example.com",
    ]
    for appointment in (dra_a, dr_b):
        [row] = scenario.rows(appointment.id)
        assert (row.kind, row.status) == (NotificationKind.REMINDER, SENT)


# --- Cuando actua ------------------------------------------------------------------------------


class CountingAppointments(InMemoryAppointmentRepository):
    """Cuenta cuantas veces la pasada pidio el listado global."""

    def __init__(self, inner: InMemoryAppointmentRepository) -> None:
        super().__init__()
        self.restore(inner.snapshot())
        self.global_listings = 0

    def list_scheduled_starting_between(self, start: datetime, end: datetime) -> list[Appointment]:
        self.global_listings += 1
        return super().list_scheduled_starting_between(start, end)


def test_outside_the_configured_hour_it_reads_nothing_registers_nothing_and_sends_nothing() -> None:
    scenario = ReminderWorld()
    appointment = scenario.world.seed(monday(10))
    scenario.world.now = local(2026, 10, 4, 10)  # 10:00 locales con hora configurada 9
    counting = CountingAppointments(scenario.world.appointments)
    deps = replace(scenario.deps(), appointments=counting)

    summary = send_reminders(deps)

    assert summary == ReminderRunSummary()
    assert counting.global_listings == 0
    assert scenario.rows(appointment.id) == []
    assert scenario.sender.sent == []


def test_just_before_the_hour_it_does_not_act_and_at_the_hour_it_does() -> None:
    scenario = ReminderWorld()
    appointment = scenario.world.seed(monday(10))

    scenario.world.now = local(2026, 10, 4, 8, 59)
    assert send_reminders(scenario.deps()).processed == 0
    assert scenario.sender.sent == []

    scenario.world.now = local(2026, 10, 4, 9, 59)
    assert send_reminders(scenario.deps()).processed == 1
    assert len(scenario.rows(appointment.id)) == 1


def test_a_change_of_the_configured_hour_takes_effect_on_the_next_pass() -> None:
    scenario = ReminderWorld()
    scenario.world.seed(monday(10))
    scenario.clinic = replace(scenario.clinic, reminder_send_hour=10)

    scenario.world.now = local(2026, 10, 4, 9)
    assert send_reminders(scenario.deps()).processed == 0

    scenario.world.now = local(2026, 10, 4, 10)
    assert send_reminders(scenario.deps()).processed == 1


def test_the_hour_is_taken_from_the_settings_zone_not_from_utc() -> None:
    scenario = ReminderWorld()
    scenario.world.seed(monday(10))
    scenario.world.now = datetime(2026, 10, 4, 9, 0, tzinfo=UTC)  # 06:00 locales

    assert send_reminders(scenario.deps()).processed == 0


# --- Que turnos --------------------------------------------------------------------------------


def test_cancelled_appointments_get_no_reminder_and_no_row() -> None:
    scenario = ReminderWorld()
    kept = scenario.world.seed(monday(10))
    cancelled = scenario.world.seed(monday(11), professional_id=PROF_B)
    scenario.world.appointments.change_status(cancelled.id, AppointmentStatus.CANCELLED, "motivo")

    summary = send_reminders(scenario.deps())

    assert summary.processed == 1
    assert len(scenario.rows(kept.id)) == 1
    assert scenario.rows(cancelled.id) == []


def test_the_local_day_limits_decide_which_appointments_are_included() -> None:
    scenario = ReminderWorld()
    sunday_late = scenario.world.seed(local(2026, 10, 4, 23, 30))  # 02:30 UTC del lunes
    monday_first = scenario.world.seed(local(2026, 10, 5, 0, 0))  # 03:00 UTC del lunes
    tuesday_first = scenario.world.seed(local(2026, 10, 6, 0, 0))

    send_reminders(scenario.deps())

    assert scenario.rows(sunday_late.id) == []
    assert len(scenario.rows(monday_first.id)) == 1
    assert scenario.rows(tuesday_first.id) == []


def test_an_appointment_that_crosses_midnight_belongs_to_the_day_it_starts() -> None:
    scenario = ReminderWorld()
    crossing = scenario.world.seed(local(2026, 10, 4, 23, 45))  # termina 00:15 del lunes

    assert send_reminders(scenario.deps()).processed == 0
    assert scenario.rows(crossing.id) == []


def test_appointments_of_a_deactivated_patient_still_get_the_reminder() -> None:
    scenario = ReminderWorld()
    appointment = scenario.world.seed(monday(10), patient_id="pac-off")
    scenario.world.set_patient_active("pac-off", False)

    summary = send_reminders(scenario.deps())

    assert summary.sent == 1
    assert [email.recipient for email in scenario.sender.sent] == ["paula@example.com"]
    assert len(scenario.rows(appointment.id)) == 1


def test_appointments_of_a_deactivated_professional_still_get_the_reminder() -> None:
    scenario = ReminderWorld()
    appointment = scenario.world.seed(monday(10))
    scenario.world.set_professional_active(PROF_A, False)

    summary = send_reminders(scenario.deps())

    assert summary.sent == 1
    assert len(scenario.rows(appointment.id)) == 1


def test_a_day_without_appointments_reports_zero_everywhere() -> None:
    scenario = ReminderWorld()

    summary = send_reminders(scenario.deps())

    assert (summary.processed, summary.sent, summary.failed, summary.pending) == (0, 0, 0, 0)
    assert scenario.sender.sent == []


# --- Un solo recordatorio por turno y horario --------------------------------------------------


def test_running_twice_in_the_same_hour_sends_and_registers_nothing_the_second_time() -> None:
    scenario = ReminderWorld()
    appointment = scenario.world.seed(monday(10))
    send_reminders(scenario.deps())
    [first_row] = scenario.rows(appointment.id)

    second = send_reminders(scenario.deps())

    assert second.processed == 0
    assert len(scenario.sender.sent) == 1
    assert scenario.rows(appointment.id) == [first_row]


def test_an_appointment_whose_reminder_already_failed_gets_no_other_one() -> None:
    scenario = ReminderWorld()
    appointment = scenario.world.seed(monday(10))
    failed = scenario.world.notifications.seed(
        appointment.id, NotificationKind.REMINDER, NotificationStatus.FAILED, monday(10)
    )

    summary = send_reminders(scenario.deps())

    assert summary.processed == 0
    assert scenario.sender.attempts == 0
    assert scenario.rows(appointment.id) == [failed]


def test_a_reminder_still_pending_from_before_is_not_registered_again_in_the_pass() -> None:
    scenario = ReminderWorld()
    appointment = scenario.world.seed(monday(10))
    pending = scenario.world.notifications.seed(
        appointment.id, NotificationKind.REMINDER, NotificationStatus.PENDING, monday(10)
    )

    summary = send_reminders(scenario.deps())

    assert summary.processed == 0
    assert scenario.sender.sent == []
    assert scenario.rows(appointment.id) == [pending]


class ChangesAfterListing(InMemoryAppointmentRepository):
    """Entrega el listado y enseguida modifica el turno, como recepcion durante la pasada."""

    def __init__(
        self, inner: InMemoryAppointmentRepository, change: Callable[[Appointment], object]
    ) -> None:
        super().__init__()
        self.restore(inner.snapshot())
        self.inner = inner
        self.change = change

    def list_scheduled_starting_between(self, start: datetime, end: datetime) -> list[Appointment]:
        listed = self.inner.list_scheduled_starting_between(start, end)
        for appointment in listed:
            self.change(appointment)
        return listed


def test_an_appointment_cancelled_between_the_listing_and_the_registration_gets_nothing() -> None:
    scenario = ReminderWorld()
    appointment = scenario.world.seed(monday(10))
    repo = scenario.world.appointments
    deps = replace(
        scenario.deps(),
        appointments=ChangesAfterListing(
            repo,
            lambda a: repo.change_status(a.id, AppointmentStatus.CANCELLED, "motivo"),
        ),
    )

    summary = send_reminders(deps)

    assert summary.processed == 0
    assert scenario.rows(appointment.id) == []
    assert scenario.sender.sent == []


def test_an_appointment_moved_between_the_listing_and_the_registration_gets_no_old_time() -> None:
    scenario = ReminderWorld()
    appointment = scenario.world.seed(monday(10))
    repo = scenario.world.appointments
    deps = replace(
        scenario.deps(),
        appointments=ChangesAfterListing(
            repo, lambda a: repo.reschedule(a.id, monday(11), monday(11, 30))
        ),
    )

    summary = send_reminders(deps)

    assert summary.processed == 0
    assert scenario.rows(appointment.id) == []
    assert scenario.sender.sent == []


def test_an_appointment_booked_before_the_pass_gets_the_confirmation_and_the_reminder() -> None:
    scenario = ReminderWorld()
    appointment = scenario.world.seed(monday(10))
    confirmation = scenario.world.notifications.add_pending_confirmation(
        appointment.id, appointment.starts_at
    )
    assert confirmation is not None
    deliver_notification(scenario.deps().notification_deps, confirmation.id)

    send_reminders(scenario.deps())

    rows = {row.kind: row.status for row in scenario.rows(appointment.id)}
    assert rows == {NotificationKind.CONFIRMATION: SENT, NotificationKind.REMINDER: SENT}
    assert len(scenario.sender.sent) == 2
    subjects = [email.subject for email in scenario.sender.sent]
    assert sum(subject.startswith("Recordatorio de turno") for subject in subjects) == 1
    assert len(set(subjects)) == 2


def test_an_appointment_booked_after_the_pass_gets_only_the_confirmation() -> None:
    scenario = ReminderWorld()
    send_reminders(scenario.deps())
    scenario.world.now = local(2026, 10, 4, 11)
    late = scenario.world.seed(monday(10))
    scenario.world.notifications.add_pending_confirmation(late.id, late.starts_at)

    send_reminders(scenario.deps())  # las 11:00 no es la hora configurada

    assert [row.kind for row in scenario.rows(late.id)] == [NotificationKind.CONFIRMATION]
    assert scenario.sender.sent == []


# --- Fallo parcial -----------------------------------------------------------------------------


class RejectingFor:
    """Remitente que rechaza a ciertos destinatarios y deja pasar a los demas."""

    def __init__(self, rejected: dict[str, EmailSendError]) -> None:
        self.rejected = rejected
        self.sent: list[OutgoingEmail] = []

    def send(self, email: OutgoingEmail) -> None:
        if email.recipient in self.rejected:
            raise self.rejected[email.recipient]
        self.sent.append(email)


def three_appointments(scenario: ReminderWorld) -> tuple[Appointment, Appointment, Appointment]:
    first = scenario.world.seed(monday(10), patient_id="pac-1")
    second = scenario.world.seed(monday(11), patient_id="pac-2")
    third = scenario.world.seed(monday(12), patient_id="pac-off")
    return first, second, third


def with_sender(deps: ReminderDeps, sender: EmailSender) -> ReminderDeps:
    return replace(deps, notification_deps=replace(deps.notification_deps, sender=sender))


def test_a_permanent_rejection_marks_only_that_reminder_failed_and_the_batch_goes_on() -> None:
    scenario = ReminderWorld()
    first, second, third = three_appointments(scenario)
    sender = RejectingFor({"ana@example.com": EmailSendError(temporary=False, code="550")})

    summary = send_reminders(with_sender(scenario.deps(), sender))

    assert (summary.processed, summary.sent, summary.failed, summary.pending) == (3, 2, 1, 0)
    [row_1], [row_2], [row_3] = (scenario.rows(a.id) for a in (first, second, third))
    assert (row_1.status, row_3.status) == (SENT, SENT)
    assert row_2.status is NotificationStatus.FAILED
    assert row_2.error == "SMTP_PERMANENT 550"
    for appointment in (first, second, third):
        stored = scenario.world.appointments.get(appointment.id)
        assert stored is not None
        assert stored.status is AppointmentStatus.SCHEDULED


def test_a_temporary_failure_leaves_the_reminder_pending_and_the_batch_goes_on() -> None:
    scenario = ReminderWorld()
    first, second, third = three_appointments(scenario)
    sender = RejectingFor({"ana@example.com": EmailSendError(temporary=True, code="CONNECTION")})

    summary = send_reminders(with_sender(scenario.deps(), sender))

    assert (summary.processed, summary.sent, summary.failed, summary.pending) == (3, 2, 0, 1)
    assert scenario.rows(second.id)[0].status is NotificationStatus.PENDING
    assert scenario.rows(first.id)[0].status is SENT
    assert scenario.rows(third.id)[0].status is SENT


def test_a_failed_reminder_is_not_retried_by_later_passes() -> None:
    scenario = ReminderWorld()
    scenario.world.seed(monday(10), patient_id="pac-2")
    rejecting = RejectingFor({"ana@example.com": EmailSendError(temporary=False, code="550")})
    send_reminders(with_sender(scenario.deps(), rejecting))

    again = send_reminders(scenario.deps())  # ahora con el remitente que si envia

    assert again.processed == 0
    assert scenario.sender.attempts == 0


class ExplodingPatients(InMemoryPatientRepository):
    """Falla con un error que no es de envio al leer a un paciente."""

    def get(self, patient_id: str) -> Patient | None:
        if patient_id == "pac-2":
            raise RuntimeError("juan@example.com Perez")
        return super().get(patient_id)


def test_an_unexpected_error_in_one_appointment_is_logged_without_data_and_the_batch_goes_on(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scenario = ReminderWorld()
    first, second, third = three_appointments(scenario)
    deps = scenario.deps()
    exploding = ExplodingPatients(scenario.world.patient_list)
    deps = replace(deps, notification_deps=replace(deps.notification_deps, patients=exploding))

    with caplog.at_level(logging.INFO):
        summary = send_reminders(deps)

    assert (summary.processed, summary.sent, summary.failed, summary.pending) == (3, 2, 1, 0)
    assert scenario.rows(first.id)[0].status is SENT
    assert scenario.rows(third.id)[0].status is SENT
    text = caplog.text
    assert second.id in text
    assert "RuntimeError" in text
    assert "juan@example.com" not in text
    assert "Perez" not in text


def test_an_error_while_registering_one_reminder_does_not_stop_the_others() -> None:
    scenario = ReminderWorld()
    first, second, _third = three_appointments(scenario)
    deps = scenario.deps()
    calls: list[int] = []

    def flaky_unit_of_work() -> AgendaUnitOfWork:
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionError("la base no respondio")
        return deps.unit_of_work()

    summary = send_reminders(replace(deps, unit_of_work=flaky_unit_of_work))

    assert summary.sent == 2
    assert scenario.rows(first.id) == []
    assert len(scenario.rows(second.id)) == 1


# --- Registro de la pasada ---------------------------------------------------------------------


def test_the_pass_logs_one_summary_line_with_the_four_counts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scenario = ReminderWorld()
    for hour, patient in ((10, "pac-1"), (11, "pac-2"), (12, "pac-off"), (13, "pac-1")):
        scenario.world.seed(monday(hour), patient_id=patient)
    sender = RejectingFor({"ana@example.com": EmailSendError(temporary=False, code="550")})

    with caplog.at_level(logging.INFO, logger="app.application.reminders"):
        send_reminders(with_sender(scenario.deps(), sender))

    assert [r.getMessage() for r in caplog.records] == [
        "recordatorios: processed=4 sent=3 failed=1 pending=0"
    ]


def test_outside_the_hour_the_pass_only_says_it_is_not_the_configured_hour(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scenario = ReminderWorld()
    scenario.world.seed(monday(10))
    scenario.world.now = local(2026, 10, 4, 14)

    with caplog.at_level(logging.INFO, logger="app.application.reminders"):
        send_reminders(scenario.deps())

    assert [r.getMessage() for r in caplog.records] == [
        "recordatorios: fuera de la hora configurada"
    ]


def test_no_log_line_of_the_pass_contains_the_patient_email_or_surname(
    caplog: pytest.LogCaptureFixture,
) -> None:
    scenario = ReminderWorld()
    scenario.world.seed(monday(10), patient_id="pac-1")

    with caplog.at_level(logging.DEBUG):
        send_reminders(scenario.deps())

    assert scenario.sender.sent  # el email salio; solo se revisa lo que se registro
    assert caplog.text
    assert "juan@example.com" not in caplog.text
    assert "Pérez" not in caplog.text
    assert "Juan" not in caplog.text


# --- Disparo manual ----------------------------------------------------------------------------


def test_force_acts_outside_the_hour_with_the_same_rules() -> None:
    scenario = ReminderWorld()
    kept = scenario.world.seed(monday(10))
    cancelled = scenario.world.seed(monday(11), professional_id=PROF_B)
    scenario.world.appointments.change_status(cancelled.id, AppointmentStatus.CANCELLED, "motivo")
    scenario.world.now = local(2026, 10, 4, 15)

    summary = send_reminders(scenario.deps(), force=True)

    assert summary.sent == 1
    assert len(scenario.rows(kept.id)) == 1
    assert scenario.rows(cancelled.id) == []


def test_forcing_twice_does_not_send_again() -> None:
    scenario = ReminderWorld()
    scenario.world.seed(monday(10))
    scenario.world.now = local(2026, 10, 4, 15)
    send_reminders(scenario.deps(), force=True)

    second = send_reminders(scenario.deps(), force=True)

    assert second.processed == 0
    assert len(scenario.sender.sent) == 1


def test_without_force_the_same_moment_does_not_act() -> None:
    scenario = ReminderWorld()
    scenario.world.seed(monday(10))
    scenario.world.now = local(2026, 10, 4, 15)

    assert send_reminders(scenario.deps()).processed == 0
    assert scenario.sender.sent == []

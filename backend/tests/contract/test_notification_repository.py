"""Bateria de contrato del registro de notificaciones (spec notification-registration)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.domain.appointments import (
    Appointment,
    AppointmentRepository,
    AppointmentStatus,
    NewAppointment,
    NotificationKind,
    NotificationRepository,
    NotificationStatus,
)
from tests.contract.conftest import Refs, RepositoryFactory
from tests.unit.domain.appointments.helpers import monday

PENDING = NotificationStatus.PENDING


@pytest.fixture
def notification_repo(factory: RepositoryFactory) -> NotificationRepository:
    return factory.notifications()


def make_appointment(
    repo: AppointmentRepository, ids: Refs, start: datetime, *, professional: str | None = None
) -> Appointment:
    return repo.add(
        NewAppointment(
            patient_id=ids.pac_1,
            professional_id=professional or ids.dra_a,
            starts_at=start,
            ends_at=start + timedelta(minutes=30),
            created_by=ids.rec_1,
        )
    )


def test_registers_a_pending_confirmation_without_send_date_or_error(
    notification_repo: NotificationRepository, appointment_repo: AppointmentRepository, ids: Refs
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))

    saved = notification_repo.add_pending_confirmation(appointment.id, appointment.starts_at)

    assert saved is not None
    assert saved.id
    assert saved.appointment_id == appointment.id
    assert saved.kind is NotificationKind.CONFIRMATION
    assert saved.status is PENDING
    assert saved.sent_at is None
    assert saved.error is None
    assert saved.appointment_starts_at == monday(10)
    assert notification_repo.list_for_appointment(appointment.id) == [saved]


def test_registering_the_same_confirmation_twice_keeps_a_single_one(
    notification_repo: NotificationRepository, appointment_repo: AppointmentRepository, ids: Refs
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    first = notification_repo.add_pending_confirmation(appointment.id, monday(10))

    second = notification_repo.add_pending_confirmation(appointment.id, monday(10))

    assert first is not None
    assert second is None
    assert notification_repo.list_for_appointment(appointment.id) == [first]


def test_a_different_start_is_a_different_notification(
    notification_repo: NotificationRepository, appointment_repo: AppointmentRepository, ids: Refs
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    notification_repo.add_pending_confirmation(appointment.id, monday(11))
    notification_repo.add_pending_confirmation(appointment.id, monday(10))

    listed = notification_repo.list_for_appointment(appointment.id)

    assert [n.appointment_starts_at for n in listed] == [monday(10), monday(11)]


def test_listing_only_returns_the_notifications_of_that_appointment(
    notification_repo: NotificationRepository, appointment_repo: AppointmentRepository, ids: Refs
) -> None:
    mine = make_appointment(appointment_repo, ids, monday(10))
    other = make_appointment(appointment_repo, ids, monday(10), professional=ids.dr_b)
    notification_repo.add_pending_confirmation(other.id, monday(10))

    assert notification_repo.list_for_appointment(mine.id) == []
    assert len(notification_repo.list_for_appointment(other.id)) == 1


def test_deleting_pending_removes_all_pending_of_the_appointment_and_counts_them(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    factory: RepositoryFactory,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    notification_repo.add_pending_confirmation(appointment.id, monday(10))
    factory.seed_notification(appointment.id, NotificationKind.REMINDER, PENDING, monday(10))

    removed = notification_repo.delete_pending(appointment.id)

    assert removed == 2
    assert notification_repo.list_for_appointment(appointment.id) == []


def test_deleting_pending_never_touches_sent_or_failed(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    factory: RepositoryFactory,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    sent = factory.seed_notification(
        appointment.id, NotificationKind.CONFIRMATION, NotificationStatus.SENT, monday(10)
    )
    failed = factory.seed_notification(
        appointment.id, NotificationKind.REMINDER, NotificationStatus.FAILED, monday(10)
    )
    notification_repo.add_pending_confirmation(appointment.id, monday(11))

    removed = notification_repo.delete_pending(appointment.id)

    assert removed == 1
    remaining = notification_repo.list_for_appointment(appointment.id)
    assert {n.id for n in remaining} == {sent.id, failed.id}
    assert {n.status for n in remaining} == {NotificationStatus.SENT, NotificationStatus.FAILED}


def test_deleting_pending_of_one_start_keeps_the_others(
    notification_repo: NotificationRepository, appointment_repo: AppointmentRepository, ids: Refs
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    notification_repo.add_pending_confirmation(appointment.id, monday(10))
    keep = notification_repo.add_pending_confirmation(appointment.id, monday(11))

    removed = notification_repo.delete_pending(appointment.id, starts_at=monday(10))

    assert removed == 1
    assert notification_repo.list_for_appointment(appointment.id) == [keep]


def test_deleting_pending_of_another_appointment_changes_nothing(
    notification_repo: NotificationRepository, appointment_repo: AppointmentRepository, ids: Refs
) -> None:
    mine = make_appointment(appointment_repo, ids, monday(10))
    other = make_appointment(appointment_repo, ids, monday(10), professional=ids.dr_b)
    notification_repo.add_pending_confirmation(mine.id, monday(10))

    assert notification_repo.delete_pending(other.id) == 0
    assert len(notification_repo.list_for_appointment(mine.id)) == 1


def test_a_sent_confirmation_blocks_registering_it_again_for_the_same_start(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    factory: RepositoryFactory,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    factory.seed_notification(
        appointment.id, NotificationKind.CONFIRMATION, NotificationStatus.SENT, monday(10)
    )

    assert notification_repo.add_pending_confirmation(appointment.id, monday(10)) is None
    assert len(notification_repo.list_for_appointment(appointment.id)) == 1


# --- Envio (C-11): tomar, marcar enviada o fallida -------------------------------------------


def _pending(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    hour: int = 10,
) -> tuple[Appointment, str]:
    appointment = make_appointment(appointment_repo, ids, monday(hour))
    saved = notification_repo.add_pending_confirmation(appointment.id, appointment.starts_at)
    assert saved is not None
    return appointment, saved.id


def test_claiming_a_pending_notification_returns_it(
    notification_repo: NotificationRepository, appointment_repo: AppointmentRepository, ids: Refs
) -> None:
    appointment, notification_id = _pending(notification_repo, appointment_repo, ids)

    claimed = notification_repo.claim_pending(notification_id)

    assert claimed is not None
    assert claimed.id == notification_id
    assert claimed.appointment_id == appointment.id
    assert claimed.status is PENDING


def test_claiming_nothing_when_the_id_does_not_exist(
    notification_repo: NotificationRepository,
) -> None:
    assert notification_repo.claim_pending("5b0a1c3e-7f64-4a0e-9d57-2f5c3a1d9e11") is None
    assert notification_repo.claim_pending("no-es-un-id") is None


def test_claiming_a_sent_notification_returns_nothing_and_changes_nothing(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    factory: RepositoryFactory,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    sent = factory.seed_notification(
        appointment.id, NotificationKind.CONFIRMATION, NotificationStatus.SENT, monday(10)
    )

    assert notification_repo.claim_pending(sent.id) is None
    assert notification_repo.list_for_appointment(appointment.id) == [sent]


def test_claiming_one_id_does_not_return_another_pending_notification(
    notification_repo: NotificationRepository, appointment_repo: AppointmentRepository, ids: Refs
) -> None:
    _, first = _pending(notification_repo, appointment_repo, ids, 10)
    _, second = _pending(notification_repo, appointment_repo, ids, 11)

    claimed = notification_repo.claim_pending(second)

    assert claimed is not None
    assert claimed.id == second != first


def test_marking_sent_stores_the_send_instant_and_no_error(
    notification_repo: NotificationRepository, appointment_repo: AppointmentRepository, ids: Refs
) -> None:
    appointment, notification_id = _pending(notification_repo, appointment_repo, ids)
    moment = monday(9)

    assert notification_repo.mark_sent(notification_id, moment) is True

    [row] = notification_repo.list_for_appointment(appointment.id)
    assert row.status is NotificationStatus.SENT
    assert row.sent_at == moment
    assert row.error is None


def test_marking_failed_stores_the_error_and_no_send_instant(
    notification_repo: NotificationRepository, appointment_repo: AppointmentRepository, ids: Refs
) -> None:
    appointment, notification_id = _pending(notification_repo, appointment_repo, ids)

    assert notification_repo.mark_failed(notification_id, "SMTP_PERMANENT 550") is True

    [row] = notification_repo.list_for_appointment(appointment.id)
    assert row.status is NotificationStatus.FAILED
    assert row.error == "SMTP_PERMANENT 550"
    assert row.sent_at is None


def test_marking_a_notification_that_is_not_pending_changes_nothing(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    factory: RepositoryFactory,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    sent = factory.seed_notification(
        appointment.id, NotificationKind.CONFIRMATION, NotificationStatus.SENT, monday(10)
    )
    failed = factory.seed_notification(
        appointment.id, NotificationKind.REMINDER, NotificationStatus.FAILED, monday(10)
    )

    assert notification_repo.mark_failed(sent.id, "X") is False
    assert notification_repo.mark_sent(failed.id, monday(9)) is False
    assert notification_repo.mark_sent("5b0a1c3e-7f64-4a0e-9d57-2f5c3a1d9e11", monday(9)) is False

    assert set(notification_repo.list_for_appointment(appointment.id)) == {sent, failed}


# --- Pendientes antiguas (C-11, reencolar_pendientes) ----------------------------------------


def test_old_pending_notifications_come_oldest_first_and_respect_the_limit(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    factory: RepositoryFactory,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    kind = NotificationKind.CONFIRMATION
    newest = factory.seed_notification(appointment.id, kind, PENDING, monday(12), monday(8, 20))
    oldest = factory.seed_notification(appointment.id, kind, PENDING, monday(10), monday(8, 0))
    middle = factory.seed_notification(appointment.id, kind, PENDING, monday(11), monday(8, 10))
    factory.seed_notification(
        appointment.id, NotificationKind.REMINDER, NotificationStatus.SENT, monday(10), monday(7)
    )

    only_one = notification_repo.list_pending_created_before(monday(8, 15), 1)
    both = notification_repo.list_pending_created_before(monday(8, 15), 10)

    assert [n.id for n in only_one] == [oldest.id]
    assert [n.id for n in both] == [oldest.id, middle.id]
    assert newest.id not in [n.id for n in both]


def test_old_pending_ignores_sent_failed_and_recent_ones(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    factory: RepositoryFactory,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    factory.seed_notification(
        appointment.id,
        NotificationKind.CONFIRMATION,
        NotificationStatus.SENT,
        monday(10),
        monday(1),
    )
    factory.seed_notification(
        appointment.id, NotificationKind.REMINDER, NotificationStatus.FAILED, monday(10), monday(1)
    )
    factory.seed_notification(
        appointment.id, NotificationKind.CONFIRMATION, PENDING, monday(11), monday(9)
    )

    assert notification_repo.list_pending_created_before(monday(8), 100) == []


def test_a_notification_created_exactly_at_the_limit_is_not_old_yet(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    factory: RepositoryFactory,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    factory.seed_notification(
        appointment.id, NotificationKind.CONFIRMATION, PENDING, monday(10), monday(8)
    )

    assert notification_repo.list_pending_created_before(monday(8), 10) == []
    assert len(notification_repo.list_pending_created_before(monday(8, 1), 10)) == 1


# --- Alta condicionada del recordatorio (C-12, D-4) ----------------------------------


def test_registers_a_pending_reminder_next_to_a_sent_confirmation(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    factory: RepositoryFactory,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    confirmation = factory.seed_notification(
        appointment.id, NotificationKind.CONFIRMATION, NotificationStatus.SENT, monday(10)
    )

    saved = notification_repo.add_pending_reminder(appointment.id, monday(10))

    assert saved is not None
    assert saved.kind is NotificationKind.REMINDER
    assert saved.status is PENDING
    assert saved.sent_at is None
    assert saved.error is None
    assert saved.appointment_starts_at == monday(10)
    listed = notification_repo.list_for_appointment(appointment.id)
    assert sorted((n.kind.value, n.status.value) for n in listed) == [
        ("confirmation", "sent"),
        ("reminder", "pending"),
    ]
    assert confirmation.id in [n.id for n in listed]


@pytest.mark.parametrize(
    "existing",
    [NotificationStatus.PENDING, NotificationStatus.SENT, NotificationStatus.FAILED],
)
def test_an_existing_reminder_in_any_status_is_never_registered_again(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    factory: RepositoryFactory,
    existing: NotificationStatus,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    seeded = factory.seed_notification(
        appointment.id, NotificationKind.REMINDER, existing, monday(10)
    )

    again = notification_repo.add_pending_reminder(appointment.id, monday(10))

    assert again is None
    assert notification_repo.list_for_appointment(appointment.id) == [seeded]


def test_a_reminder_for_another_start_of_the_same_appointment_is_a_new_row(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    factory: RepositoryFactory,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    factory.seed_notification(
        appointment.id, NotificationKind.REMINDER, NotificationStatus.SENT, monday(9)
    )

    saved = notification_repo.add_pending_reminder(appointment.id, monday(10))

    assert saved is not None
    assert [
        n.appointment_starts_at for n in notification_repo.list_for_appointment(appointment.id)
    ] == [
        monday(9),
        monday(10),
    ]


@pytest.mark.parametrize(
    "status",
    [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW],
)
def test_no_reminder_is_registered_for_an_appointment_that_is_not_scheduled(
    notification_repo: NotificationRepository,
    appointment_repo: AppointmentRepository,
    ids: Refs,
    status: AppointmentStatus,
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    appointment_repo.change_status(
        appointment.id, status, "motivo" if status is AppointmentStatus.CANCELLED else None
    )

    assert notification_repo.add_pending_reminder(appointment.id, monday(10)) is None
    assert notification_repo.list_for_appointment(appointment.id) == []


def test_no_reminder_is_registered_when_the_appointment_now_starts_at_another_time(
    notification_repo: NotificationRepository, appointment_repo: AppointmentRepository, ids: Refs
) -> None:
    appointment = make_appointment(appointment_repo, ids, monday(10))
    appointment_repo.reschedule(appointment.id, monday(11), monday(11, 30))

    assert notification_repo.add_pending_reminder(appointment.id, monday(10)) is None
    assert notification_repo.list_for_appointment(appointment.id) == []
    assert notification_repo.add_pending_reminder(appointment.id, monday(11)) is not None


def test_no_reminder_is_registered_for_an_unknown_appointment(
    notification_repo: NotificationRepository, ids: Refs
) -> None:
    unknown = "00000000-0000-0000-0000-000000000000"

    assert notification_repo.add_pending_reminder(unknown, monday(10)) is None
    assert notification_repo.add_pending_reminder("no-es-un-id", monday(10)) is None

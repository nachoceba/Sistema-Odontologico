"""Bateria de contrato del registro de notificaciones (spec notification-registration)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.domain.appointments import (
    Appointment,
    AppointmentRepository,
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

"""Bateria de contrato del vencimiento de reservas pendientes (C-16, DD-132).

Cada escenario corre en memoria y en PostgreSQL. Las notificaciones del aviso se registran en
la misma unidad de trabajo que la cancelacion (DD-140).
"""

from __future__ import annotations

from dataclasses import replace
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
    SlotTakenError,
)
from app.domain.public_booking.rules import EXPIRED_BOOKING_REASON
from tests.contract.conftest import Refs, RepositoryFactory
from tests.unit.domain.appointments.helpers import monday

HASH = "a" * 64
OTHER_HASH = "b" * 64


def online(ids: Refs, start: datetime, *, professional: str | None = None) -> NewAppointment:
    return NewAppointment(
        patient_id=ids.pac_1,
        professional_id=professional or ids.dra_a,
        starts_at=start,
        ends_at=start + timedelta(minutes=30),
        created_by=None,
    )


def staff(ids: Refs, start: datetime) -> NewAppointment:
    return NewAppointment(
        patient_id=ids.pac_1,
        professional_id=ids.dra_a,
        starts_at=start,
        ends_at=start + timedelta(minutes=30),
        created_by=ids.rec_1,
    )


@pytest.fixture
def repo(factory: RepositoryFactory) -> AppointmentRepository:
    return factory.appointments()


def pend(
    repo: AppointmentRepository,
    ids: Refs,
    start: datetime,
    until: datetime,
    token_hash: str = HASH,
) -> Appointment:
    return repo.add_pending(online(ids, start), token_hash, until)


def test_an_expired_pending_appointment_is_cancelled_with_the_reason_and_cleared(
    repo: AppointmentRepository, ids: Refs
) -> None:
    saved = pend(repo, ids, monday(12), monday(10))

    expired = repo.expire_pending(monday(10, 2), 200)

    assert [a.id for a in expired] == [saved.id]
    assert expired[0].starts_at == saved.starts_at
    stored = repo.get(saved.id)
    assert stored is not None
    assert stored.status is AppointmentStatus.CANCELLED
    assert stored.cancel_reason == EXPIRED_BOOKING_REASON == "Reserva online no confirmada"
    assert stored.pending_until is None
    # el hash quedo libre: no se puede confirmar y el valor se puede reutilizar
    assert repo.confirm_by_token_hash(HASH, monday(9)) is None
    pend(repo, ids, monday(13), monday(11), HASH)


def test_a_pending_appointment_that_is_still_valid_is_not_touched(
    repo: AppointmentRepository, ids: Refs
) -> None:
    saved = pend(repo, ids, monday(12), monday(10, 5))

    assert repo.expire_pending(monday(10), 200) == []
    assert repo.get(saved.id) == saved


def test_an_exact_expiry_instant_is_cancelled(repo: AppointmentRepository, ids: Refs) -> None:
    saved = pend(repo, ids, monday(12), monday(10))

    expired = repo.expire_pending(monday(10), 200)

    assert [a.id for a in expired] == [saved.id]


def test_confirmed_and_staff_appointments_are_never_touched(
    repo: AppointmentRepository, ids: Refs
) -> None:
    confirmed = pend(repo, ids, monday(11), monday(9), OTHER_HASH)
    repo.confirm_by_token_hash(OTHER_HASH, monday(8))
    walk_in = repo.add(staff(ids, monday(12)))

    assert repo.expire_pending(monday(20), 200) == []
    assert repo.get(confirmed.id) == replace(confirmed, pending_until=None)
    assert repo.get(walk_in.id) == walk_in


def test_a_second_pass_changes_nothing(repo: AppointmentRepository, ids: Refs) -> None:
    pend(repo, ids, monday(12), monday(10))
    assert len(repo.expire_pending(monday(10, 2), 200)) == 1

    assert repo.expire_pending(monday(10, 3), 200) == []


def test_the_limit_caps_one_pass_and_the_oldest_deadline_goes_first(
    repo: AppointmentRepository, ids: Refs
) -> None:
    late = pend(repo, ids, monday(12), monday(10, 20), HASH)
    early = pend(repo, ids, monday(13), monday(10, 10), OTHER_HASH)

    first = repo.expire_pending(monday(11), 1)
    second = repo.expire_pending(monday(11), 1)

    assert [a.id for a in first] == [early.id]
    assert [a.id for a in second] == [late.id]
    assert repo.expire_pending(monday(11), 1) == []


def test_an_expired_slot_can_be_booked_again_by_the_reception(
    repo: AppointmentRepository, ids: Refs
) -> None:
    """Regla dura 6: al vencer la franja se libera, y mientras vive sigue ocupada."""
    pend(repo, ids, monday(12), monday(10))
    with pytest.raises(SlotTakenError):
        repo.add(staff(ids, monday(12)))

    repo.expire_pending(monday(10), 200)

    assert repo.add(staff(ids, monday(12))).status is AppointmentStatus.SCHEDULED


def test_the_expiry_and_its_notice_commit_together(
    factory: RepositoryFactory, repo: AppointmentRepository, ids: Refs
) -> None:
    saved = pend(repo, ids, monday(12), monday(10))

    with factory.unit_of_work()() as uow:
        expired = uow.appointments.expire_pending(monday(10, 2), 200)
        for appointment in expired:
            uow.notifications.add_pending_booking_expired(appointment.id, appointment.starts_at)

    rows = factory.notifications().list_for_appointment(saved.id)
    assert [(r.kind, r.status) for r in rows] == [
        (NotificationKind.BOOKING_EXPIRED, NotificationStatus.PENDING)
    ]
    assert rows[0].appointment_starts_at == saved.starts_at


def test_a_failure_after_expiring_rolls_the_cancellation_back(
    factory: RepositoryFactory, repo: AppointmentRepository, ids: Refs
) -> None:
    saved = pend(repo, ids, monday(12), monday(10))

    with pytest.raises(RuntimeError), factory.unit_of_work()() as uow:
        uow.appointments.expire_pending(monday(10, 2), 200)
        raise RuntimeError

    assert repo.get(saved.id) == saved
    assert factory.notifications().list_for_appointment(saved.id) == []


def test_the_expiry_notice_is_registered_once_even_if_asked_twice(
    factory: RepositoryFactory, repo: AppointmentRepository, ids: Refs
) -> None:
    notifications: NotificationRepository = factory.notifications()
    saved = pend(repo, ids, monday(12), monday(10))
    repo.expire_pending(monday(10, 1), 200)

    first = notifications.add_pending_booking_expired(saved.id, saved.starts_at)
    second = notifications.add_pending_booking_expired(saved.id, saved.starts_at)

    assert first is not None
    assert first.kind is NotificationKind.BOOKING_EXPIRED
    assert first.status is NotificationStatus.PENDING
    assert second is None
    assert len(notifications.list_for_appointment(saved.id)) == 1


def test_the_expiry_notice_is_kept_apart_from_the_other_kinds(
    factory: RepositoryFactory, repo: AppointmentRepository, ids: Refs
) -> None:
    notifications = factory.notifications()
    saved = pend(repo, ids, monday(12), monday(10))
    assert notifications.add_pending_confirmation(saved.id, saved.starts_at) is not None

    assert notifications.add_pending_booking_expired(saved.id, saved.starts_at) is not None
    assert len(notifications.list_for_appointment(saved.id)) == 2

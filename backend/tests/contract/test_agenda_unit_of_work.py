"""Bateria de contrato de la unidad de trabajo de la agenda (spec appointment-unit-of-work).

Turno y notificaciones se confirman juntos o no se guarda nada, en memoria y en PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.domain.appointments import (
    Appointment,
    AppointmentRepository,
    AppointmentStatus,
    NewAppointment,
    NotificationRepository,
    SlotTakenError,
)
from tests.contract.conftest import Refs, RepositoryFactory
from tests.unit.domain.appointments.helpers import monday


class Boom(Exception):
    """Falla simulada en medio de una operacion."""


def new(ids: Refs, start: datetime, *, professional: str | None = None) -> NewAppointment:
    return NewAppointment(
        patient_id=ids.pac_1,
        professional_id=professional or ids.dra_a,
        starts_at=start,
        ends_at=start + timedelta(minutes=30),
        created_by=ids.rec_1,
    )


@pytest.fixture
def repos(factory: RepositoryFactory) -> tuple[AppointmentRepository, NotificationRepository]:
    return factory.appointments(), factory.notifications()


def test_commit_saves_the_appointment_and_its_notification_together(
    factory: RepositoryFactory,
    repos: tuple[AppointmentRepository, NotificationRepository],
    ids: Refs,
) -> None:
    appointments, notifications = repos

    with factory.unit_of_work()() as uow:
        saved = uow.appointments.add(new(ids, monday(10)))
        uow.notifications.add_pending_confirmation(saved.id, saved.starts_at)

    assert appointments.get(saved.id) == saved
    assert len(notifications.list_for_appointment(saved.id)) == 1


def test_inside_the_unit_the_repositories_see_their_own_writes(
    factory: RepositoryFactory, ids: Refs
) -> None:
    with factory.unit_of_work()() as uow:
        saved = uow.appointments.add(new(ids, monday(10)))
        notification = uow.notifications.add_pending_confirmation(saved.id, saved.starts_at)

        assert uow.appointments.get(saved.id) == saved
        assert uow.notifications.list_for_appointment(saved.id) == [notification]


def test_an_error_after_writing_both_leaves_neither(
    factory: RepositoryFactory,
    repos: tuple[AppointmentRepository, NotificationRepository],
    ids: Refs,
) -> None:
    appointments, notifications = repos
    created: list[Appointment] = []

    with pytest.raises(Boom), factory.unit_of_work()() as uow:
        saved = uow.appointments.add(new(ids, monday(10)))
        created.append(saved)
        uow.notifications.add_pending_confirmation(saved.id, saved.starts_at)
        raise Boom

    assert appointments.get(created[0].id) is None
    assert notifications.list_for_appointment(created[0].id) == []
    assert appointments.list_for_professional(ids.dra_a, monday(0), monday(23)) == []


def test_a_failed_reschedule_keeps_the_appointment_and_its_pending_notifications(
    factory: RepositoryFactory,
    repos: tuple[AppointmentRepository, NotificationRepository],
    ids: Refs,
) -> None:
    appointments, notifications = repos
    mine = appointments.add(new(ids, monday(10)))
    notifications.add_pending_confirmation(mine.id, mine.starts_at)
    appointments.add(new(ids, monday(11)))  # otro turno ocupa el destino

    with pytest.raises(SlotTakenError), factory.unit_of_work()() as uow:
        uow.notifications.delete_pending(mine.id, starts_at=mine.starts_at)
        uow.appointments.reschedule(mine.id, monday(11), monday(11, 30))

    assert appointments.get(mine.id) == mine
    assert len(notifications.list_for_appointment(mine.id)) == 1


def test_a_cancel_inside_the_unit_is_all_or_nothing_too(
    factory: RepositoryFactory,
    repos: tuple[AppointmentRepository, NotificationRepository],
    ids: Refs,
) -> None:
    appointments, notifications = repos
    mine = appointments.add(new(ids, monday(10)))
    notifications.add_pending_confirmation(mine.id, mine.starts_at)

    with pytest.raises(Boom), factory.unit_of_work()() as uow:
        uow.appointments.change_status(mine.id, AppointmentStatus.CANCELLED, "aviso")
        uow.notifications.delete_pending(mine.id)
        raise Boom

    stored = appointments.get(mine.id)
    assert stored is not None
    assert stored.status is AppointmentStatus.SCHEDULED
    assert len(notifications.list_for_appointment(mine.id)) == 1


def test_each_unit_is_independent_of_a_previous_rolled_back_one(
    factory: RepositoryFactory,
    repos: tuple[AppointmentRepository, NotificationRepository],
    ids: Refs,
) -> None:
    appointments, _ = repos
    open_unit = factory.unit_of_work()

    with pytest.raises(Boom), open_unit() as uow:
        uow.appointments.add(new(ids, monday(10)))
        raise Boom
    with open_unit() as uow:
        saved = uow.appointments.add(new(ids, monday(10)))  # el horario quedo libre

    assert appointments.get(saved.id) == saved

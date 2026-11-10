"""Bateria de contrato de las reservas online pendientes (C-15, DD-130, DD-131).

Cada escenario corre en memoria y en PostgreSQL. El hash del token nunca sale en el turno.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta

import pytest

from app.domain.appointments import (
    Appointment,
    AppointmentRepository,
    AppointmentStatus,
    NewAppointment,
    SlotTakenError,
)
from app.domain.patients.types import NewPatient, PatientRecord
from tests.contract.conftest import Refs, RepositoryFactory
from tests.unit.domain.appointments.helpers import monday

HASH = "a" * 64
OTHER_HASH = "b" * 64


def online(ids: Refs, start: datetime, *, patient: str | None = None) -> NewAppointment:
    return NewAppointment(
        patient_id=patient or ids.pac_1,
        professional_id=ids.dra_a,
        starts_at=start,
        ends_at=start + timedelta(minutes=30),
        created_by=None,
    )


def staff(ids: Refs, start: datetime) -> NewAppointment:
    return dataclasses.replace(online(ids, start), created_by=ids.rec_1)


@pytest.fixture
def repo(factory: RepositoryFactory) -> AppointmentRepository:
    return factory.appointments()


def pend(
    repo: AppointmentRepository, ids: Refs, start: datetime, token_hash: str = HASH
) -> Appointment:
    return repo.add_pending(online(ids, start), token_hash, start - timedelta(hours=2))


def test_a_pending_appointment_is_scheduled_without_creator_and_with_deadline(
    repo: AppointmentRepository, ids: Refs
) -> None:
    saved = pend(repo, ids, monday(10))

    assert saved.status is AppointmentStatus.SCHEDULED
    assert saved.created_by is None
    assert saved.pending_until == monday(8)
    assert repo.get(saved.id) == saved


def test_the_token_hash_never_leaves_the_repository(repo: AppointmentRepository, ids: Refs) -> None:
    saved = pend(repo, ids, monday(10))
    loaded = repo.get(saved.id)

    assert loaded is not None
    for appointment in (saved, loaded, *repo.list_for_professional(ids.dra_a, monday(0))):
        assert HASH not in [str(v) for v in dataclasses.asdict(appointment).values()]
    assert not any("hash" in field.name for field in dataclasses.fields(Appointment))


def test_a_pending_appointment_occupies_its_slot_for_staff_bookings(
    repo: AppointmentRepository, ids: Refs
) -> None:
    pend(repo, ids, monday(10))

    with pytest.raises(SlotTakenError):
        repo.add(staff(ids, monday(10)))


def test_a_pending_appointment_cannot_overlap_a_confirmed_one(
    repo: AppointmentRepository, ids: Refs
) -> None:
    repo.add(staff(ids, monday(10)))

    with pytest.raises(SlotTakenError):
        pend(repo, ids, monday(10), OTHER_HASH)


def test_confirming_with_the_hash_clears_the_pending_columns(
    repo: AppointmentRepository, ids: Refs
) -> None:
    saved = pend(repo, ids, monday(10))

    confirmed = repo.confirm_by_token_hash(HASH, monday(7))

    assert confirmed == dataclasses.replace(saved, pending_until=None)
    assert repo.get(saved.id) == confirmed


def test_the_token_serves_only_once(repo: AppointmentRepository, ids: Refs) -> None:
    pend(repo, ids, monday(10))
    assert repo.confirm_by_token_hash(HASH, monday(7)) is not None

    assert repo.confirm_by_token_hash(HASH, monday(7)) is None


def test_an_unknown_hash_finds_nothing(repo: AppointmentRepository, ids: Refs) -> None:
    pend(repo, ids, monday(10))

    assert repo.confirm_by_token_hash(OTHER_HASH, monday(7)) is None


def test_an_expired_pending_appointment_is_not_confirmed_and_stays_pending(
    repo: AppointmentRepository, ids: Refs
) -> None:
    saved = pend(repo, ids, monday(10))

    assert repo.confirm_by_token_hash(HASH, monday(8)) is None  # justo en el vencimiento
    assert repo.get(saved.id) == saved


def test_a_cancelled_appointment_clears_the_pending_data_and_cannot_be_confirmed(
    repo: AppointmentRepository, ids: Refs
) -> None:
    saved = pend(repo, ids, monday(10))

    cancelled = repo.change_status(saved.id, AppointmentStatus.CANCELLED, "no confirmo")

    assert cancelled.pending_until is None
    assert repo.confirm_by_token_hash(HASH, monday(7)) is None
    # el hash quedo libre: se puede reutilizar en otro turno pendiente
    pend(repo, ids, monday(11), HASH)


def test_cancelling_a_confirmed_online_appointment_keeps_it_cancelled(
    repo: AppointmentRepository, ids: Refs
) -> None:
    saved = pend(repo, ids, monday(10))
    repo.confirm_by_token_hash(HASH, monday(7))

    cancelled = repo.change_status(saved.id, AppointmentStatus.CANCELLED, "motivo")

    assert cancelled.status is AppointmentStatus.CANCELLED
    assert cancelled.created_by is None


def test_reminders_skip_pending_and_include_confirmed_online_appointments(
    repo: AppointmentRepository, ids: Refs
) -> None:
    pending = pend(repo, ids, monday(10), HASH)
    confirmed = pend(repo, ids, monday(11), OTHER_HASH)
    repo.confirm_by_token_hash(OTHER_HASH, monday(7))
    regular = repo.add(staff(ids, monday(12)))

    found = repo.list_scheduled_starting_between(monday(0), monday(23))

    assert pending.id not in [a.id for a in found]
    assert [a.id for a in found] == [confirmed.id, regular.id]


# --- Pacientes dentro de la unidad de trabajo ---

JUAN = PatientRecord(
    id="pac-1",
    first_name="Juan",
    last_name="Perez",
    document_number="30111222",
    email="juan@example.com",
    phone=None,
    birth_date=None,
    active=True,
)


def test_the_patient_and_the_pending_appointment_commit_together(
    factory: RepositoryFactory, ids: Refs
) -> None:
    with factory.unit_of_work()() as uow:
        patient = uow.patients.add(NewPatient("Lucia", "Diaz", "40999888", "lucia@example.com"))
        saved = uow.appointments.add_pending(
            online(ids, monday(10), patient=patient.id), HASH, monday(8)
        )

    assert factory.patients().get_by_document("40999888") is not None
    assert factory.appointments().get(saved.id) == saved


def test_a_colliding_appointment_leaves_no_new_patient(
    factory: RepositoryFactory, ids: Refs
) -> None:
    factory.appointments().add(staff(ids, monday(10)))

    with pytest.raises(SlotTakenError), factory.unit_of_work()() as uow:
        patient = uow.patients.add(NewPatient("Lucia", "Diaz", "40999888", "lucia@example.com"))
        uow.appointments.add_pending(online(ids, monday(10), patient=patient.id), HASH, monday(8))

    assert factory.patients().get_by_document("40999888") is None


def test_inside_the_unit_the_patient_is_found_by_document(factory: RepositoryFactory) -> None:
    with factory.unit_of_work()() as uow:
        assert uow.patients.get_by_document("40999888") is None
        created = uow.patients.add(NewPatient("Lucia", "Diaz", "40999888", "lucia@example.com"))
        assert uow.patients.get_by_document("40999888") == created


def test_get_by_document_finds_an_existing_record_and_nothing_else(
    factory: RepositoryFactory,
) -> None:
    repo = factory.patients([JUAN])

    found = repo.get_by_document("30111222")

    assert found is not None
    assert (found.first_name, found.last_name, found.email) == ("Juan", "Perez", "juan@example.com")
    assert repo.get_by_document("30111223") is None


def test_find_pending_returns_the_appointment_without_changing_it(
    repo: AppointmentRepository, ids: Refs
) -> None:
    saved = pend(repo, ids, monday(10))

    assert repo.find_pending_by_token_hash(HASH, monday(7)) == saved
    assert repo.find_pending_by_token_hash(HASH, monday(7)) == saved  # sigue pendiente


@pytest.mark.parametrize(
    ("token_hash", "hour"), [(OTHER_HASH, 7), (HASH, 8)], ids=["otro-hash", "vencido"]
)
def test_find_pending_finds_nothing_for_an_unknown_hash_or_after_the_deadline(
    repo: AppointmentRepository, ids: Refs, token_hash: str, hour: int
) -> None:
    pend(repo, ids, monday(10))

    assert repo.find_pending_by_token_hash(token_hash, monday(hour)) is None

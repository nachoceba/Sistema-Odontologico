"""Alta y edicion de pacientes: validacion, documento unico y datos opcionales
(spec patient-management)."""

from __future__ import annotations

from datetime import date

import pytest

from app.application.appointments import book_appointment
from app.application.patients import create_patient, update_patient
from app.domain.appointments.errors import PatientNotFoundError
from app.domain.patients.errors import DocumentTakenError, InvalidPatientDataError
from app.domain.patients.types import NewPatient, PatientRecord
from app.domain.professionals import UNSET
from tests.unit.application.agenda_helpers import PROF_A, RECEPTION, World
from tests.unit.domain.appointments.helpers import local, monday


def _snapshot(world: World) -> list[PatientRecord]:
    return world.patients.search(text="", include_inactive=True, limit=1000)


def _luis(world: World) -> PatientRecord:
    return world.patients.add(
        NewPatient(
            "Luis", "Fernández", "30111224", "luis@example.com", "011-5550-0001", date(1980, 1, 1)
        )
    )


# --- Alta ---


def test_create_normalizes_document_and_email_and_keeps_optional_data() -> None:
    world = World()
    saved = create_patient(
        world.patient_deps(),
        RECEPTION,
        first_name=" Laura ",
        last_name="Ruiz",
        document_number="40.222.333",
        email="Laura@Example.com",
        phone=" 011-5550-0002 ",
        birth_date=date(1990, 5, 10),
    )
    assert (saved.first_name, saved.document_number, saved.email) == (
        "Laura",
        "40222333",
        "laura@example.com",
    )
    assert (saved.phone, saved.birth_date, saved.active) == (
        "011-5550-0002",
        date(1990, 5, 10),
        True,
    )


def test_create_with_a_document_written_differently_is_taken_and_saves_nothing() -> None:
    world = World()
    world.patients.add(NewPatient("Otro", "Uno", "30111222", "uno@example.com"))
    before = _snapshot(world)
    with pytest.raises(DocumentTakenError):
        create_patient(
            world.patient_deps(),
            RECEPTION,
            first_name="Laura",
            last_name="Ruiz",
            document_number="30.111.222",
            email="laura@example.com",
        )
    assert _snapshot(world) == before


def test_create_with_a_future_birth_date_is_rejected_using_the_clinic_day() -> None:
    world = World(now=local(2026, 11, 4, 10))
    before = _snapshot(world)
    with pytest.raises(InvalidPatientDataError):
        create_patient(
            world.patient_deps(),
            RECEPTION,
            first_name="Laura",
            last_name="Ruiz",
            document_number="40222333",
            email="laura@example.com",
            birth_date=date(2027, 1, 1),
        )
    assert _snapshot(world) == before


def test_create_accepts_a_birth_date_of_the_clinic_today_even_late_at_night() -> None:
    world = World(now=local(2026, 11, 4, 22, 30))  # ya es 05/11 en UTC
    saved = create_patient(
        world.patient_deps(),
        RECEPTION,
        first_name="Bebé",
        last_name="Ruiz",
        document_number="40222334",
        email="bebe@example.com",
        birth_date=date(2026, 11, 4),
    )
    assert saved.birth_date == date(2026, 11, 4)


@pytest.mark.parametrize(
    "bad",
    [
        {"first_name": "   "},
        {"document_number": "123"},
        {"email": "sin-arroba"},
        {"phone": "llamar tarde"},
    ],
)
def test_create_with_invalid_text_data_saves_nothing(bad: dict[str, str]) -> None:
    world = World()
    before = _snapshot(world)
    data: dict[str, str] = {
        "first_name": "Laura",
        "last_name": "Ruiz",
        "document_number": "40222333",
        "email": "laura@example.com",
    } | bad
    with pytest.raises(ValueError):
        create_patient(
            world.patient_deps(),
            RECEPTION,
            first_name=data["first_name"],
            last_name=data["last_name"],
            document_number=data["document_number"],
            email=data["email"],
            phone=data.get("phone"),
        )
    assert _snapshot(world) == before


# --- Edición ---


def test_changing_the_email_does_not_touch_the_appointment_or_its_notification() -> None:
    world = World()
    appointment = book_appointment(
        world.deps(),
        RECEPTION,
        patient_id="pac-1",
        professional_id=PROF_A,
        treatment_id=world.treatment_id,
        starts_at=monday(10),
    )
    notifications_before = world.notifications.list_for_appointment(appointment.id)
    assert [n.status.value for n in notifications_before] == ["pending"]
    appointments_before = world.everything()
    updated = update_patient(world.patient_deps(), RECEPTION, "pac-1", email=" Nuevo@Example.com ")
    assert updated.email == "nuevo@example.com"
    assert world.patients.get_record("pac-1") == updated
    assert world.everything() == appointments_before
    assert world.notifications.list_for_appointment(appointment.id) == notifications_before


def test_editing_an_inactive_patient_keeps_it_inactive() -> None:
    world = World()
    world.set_patient_active("pac-2", False)
    updated = update_patient(world.patient_deps(), RECEPTION, "pac-2", phone="011-5550-0009")
    assert (updated.phone, updated.active) == ("011-5550-0009", False)


def test_editing_the_document_to_that_of_another_patient_is_taken_and_changes_nothing() -> None:
    world = World()
    luis = _luis(world)
    world.patients.add(NewPatient("Otro", "Uno", "30111222", "uno@example.com"))
    before = _snapshot(world)
    with pytest.raises(DocumentTakenError):
        update_patient(world.patient_deps(), RECEPTION, luis.id, document_number="30.111.222")
    assert _snapshot(world) == before


def test_editing_leaves_untouched_what_is_not_sent_and_clears_with_none() -> None:
    world = World()
    luis = _luis(world)
    same = update_patient(world.patient_deps(), RECEPTION, luis.id, first_name="Luisito")
    assert (same.phone, same.birth_date, same.first_name) == (
        "011-5550-0001",
        date(1980, 1, 1),
        "Luisito",
    )
    kept = update_patient(world.patient_deps(), RECEPTION, luis.id, phone=UNSET, birth_date=UNSET)
    assert kept == same
    cleared = update_patient(world.patient_deps(), RECEPTION, luis.id, phone=None, birth_date=None)
    assert (cleared.phone, cleared.birth_date) == (None, None)


def test_editing_with_a_blank_phone_clears_it() -> None:
    world = World()
    luis = _luis(world)
    assert update_patient(world.patient_deps(), RECEPTION, luis.id, phone="  ").phone is None


def test_editing_with_a_future_birth_date_is_rejected_and_changes_nothing() -> None:
    world = World(now=local(2026, 11, 4, 10))
    before = _snapshot(world)
    with pytest.raises(InvalidPatientDataError):
        update_patient(world.patient_deps(), RECEPTION, "pac-1", birth_date=date(2026, 11, 5))
    assert _snapshot(world) == before


def test_editing_an_unknown_patient_is_not_found() -> None:
    world = World()
    with pytest.raises(PatientNotFoundError):
        update_patient(world.patient_deps(), RECEPTION, "no-existe", first_name="X")


def test_a_rejected_edit_for_invalid_text_changes_nothing() -> None:
    world = World()
    before = _snapshot(world)
    with pytest.raises(ValueError):
        update_patient(
            world.patient_deps(), RECEPTION, "pac-1", first_name="Nuevo", email="sin-arroba"
        )
    assert _snapshot(world) == before

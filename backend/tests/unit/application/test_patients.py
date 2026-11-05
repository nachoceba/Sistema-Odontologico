"""Casos de uso de pacientes con repositorios en memoria y reloj fijo (spec patient-management)."""

from __future__ import annotations

import pytest

from app.application.patients import (
    MAX_SEARCH_RESULTS,
    create_patient,
    get_patient,
    search_patients,
    update_patient,
)
from app.domain.appointments.errors import PatientNotFoundError
from app.domain.auth import ForbiddenError
from app.domain.patients.types import NewPatient, PatientRecord
from tests.unit.application.agenda_helpers import (
    ADMIN,
    DENTIST_A,
    DENTIST_NO_FILE,
    RECEPTION,
    World,
)


def _add(world: World, last_name: str, document: str, *, first_name: str = "Paciente") -> str:
    return world.patients.add(
        NewPatient(
            first_name=first_name,
            last_name=last_name,
            document_number=document,
            email=f"{document}@example.com",
        )
    ).id


def _lopez(world: World) -> str:
    return _add(world, "López", "40222333", first_name="Marta")


def _snapshot(world: World) -> list[PatientRecord]:
    return world.patients.search(text="", include_inactive=True, limit=1000)


# --- Permisos por rol ---


def test_reception_creates_a_patient() -> None:
    world = World()
    saved = create_patient(
        world.patient_deps(),
        RECEPTION,
        first_name="Laura",
        last_name="Ruiz",
        document_number="40.222.333",
        email="laura@example.com",
    )
    assert saved.active is True
    assert world.patients.get_record(saved.id) == saved


def test_dentist_cannot_edit_and_nothing_changes() -> None:
    world = World()
    before = _snapshot(world)
    with pytest.raises(ForbiddenError):
        update_patient(world.patient_deps(), DENTIST_A, "pac-1", email="otro@example.com")
    assert _snapshot(world) == before


def test_dentist_cannot_create_and_nothing_changes() -> None:
    world = World()
    before = _snapshot(world)
    with pytest.raises(ForbiddenError):
        create_patient(
            world.patient_deps(),
            DENTIST_A,
            first_name="Laura",
            last_name="Ruiz",
            document_number="40222333",
            email="laura@example.com",
        )
    assert _snapshot(world) == before


def test_dentist_without_professional_file_searches_like_any_other() -> None:
    world = World()
    with_file = search_patients(world.patient_deps(), DENTIST_A, text="Pérez")
    without_file = search_patients(world.patient_deps(), DENTIST_NO_FILE, text="Pérez")
    assert [p.last_name for p in without_file.items] == ["Pérez"]
    assert without_file == with_file


def test_all_roles_can_read_a_patient() -> None:
    world = World()
    for principal in (ADMIN, RECEPTION, DENTIST_A, DENTIST_NO_FILE):
        assert get_patient(world.patient_deps(), principal, "pac-1").last_name == "Pérez"


# --- Buscar ---


def test_search_by_last_name_finds_one_and_no_more_results() -> None:
    world = World()
    _lopez(world)
    result = search_patients(world.patient_deps(), RECEPTION, text="lóp")
    assert [p.last_name for p in result.items] == ["López"]
    assert result.truncated is False


def test_search_with_more_than_the_maximum_returns_the_first_50_and_flags_it() -> None:
    world = World()
    for n in range(MAX_SEARCH_RESULTS + 1):
        _add(world, f"Apellido{n:03d}", f"6000{n:04d}")
    result = search_patients(world.patient_deps(), RECEPTION)
    assert len(result.items) == 50
    assert result.truncated is True
    assert result.items[0].last_name == "Apellido000"


def test_search_with_exactly_the_maximum_is_not_truncated() -> None:
    world = World()
    world.set_patient_active("pac-2", False)
    world.set_patient_active("pac-off", False)
    for n in range(MAX_SEARCH_RESULTS - 1):
        _add(world, f"Apellido{n:03d}", f"6000{n:04d}")
    result = search_patients(world.patient_deps(), RECEPTION)
    assert len(result.items) == 50
    assert result.truncated is False


def test_blank_text_is_the_same_as_no_text() -> None:
    world = World()
    deps = world.patient_deps()
    assert search_patients(deps, RECEPTION, text="   ") == search_patients(deps, RECEPTION)


def test_search_hides_inactive_by_default_and_includes_them_on_request() -> None:
    world = World()
    world.set_patient_active("pac-2", False)
    default = search_patients(world.patient_deps(), RECEPTION, text="Gómez")
    assert default.items == []
    with_inactive = search_patients(
        world.patient_deps(), RECEPTION, text="Gómez", include_inactive=True
    )
    assert [p.active for p in with_inactive.items] == [False]


# --- Ver ---


def test_view_of_an_inactive_patient_returns_the_full_record() -> None:
    world = World()
    world.set_patient_active("pac-2", False)
    record = get_patient(world.patient_deps(), RECEPTION, "pac-2")
    assert (record.first_name, record.last_name, record.active) == ("Ana", "Gómez", False)


def test_view_of_unknown_patient_is_not_found() -> None:
    world = World()
    with pytest.raises(PatientNotFoundError):
        get_patient(world.patient_deps(), RECEPTION, "no-existe")

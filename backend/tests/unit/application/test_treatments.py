"""Casos de uso del catalogo de tratamientos y su asignacion (spec treatment-management, C-17)."""

from __future__ import annotations

import pytest

from app.application.appointments import book_appointment
from app.application.treatments import (
    create_treatment,
    list_professional_treatments,
    list_treatments,
    replace_professional_treatments,
    update_treatment,
)
from app.domain.appointments.errors import ProfessionalNotFoundError
from app.domain.auth import ForbiddenError
from app.domain.treatments.errors import (
    InvalidTreatmentNameError,
    TreatmentNameTakenError,
    TreatmentNotFoundError,
)
from tests.unit.application.agenda_helpers import (
    ADMIN,
    DENTIST_A,
    DENTIST_B,
    PROF_A,
    PROF_B,
    RECEPTION,
    World,
)
from tests.unit.domain.appointments.helpers import monday

NIL = "99999999-9999-4999-8999-999999999999"


def _names(treatments: list) -> list[str]:  # type: ignore[type-arg]
    return [t.name for t in treatments]


# --- Catalogo -----------------------------------------------------------------------


def test_list_treatments_returns_the_catalog_ordered_by_name() -> None:
    world = World()
    create_treatment(world.treatment_deps(), ADMIN, name="Blanqueamiento")
    assert _names(list_treatments(world.treatment_deps())) == [
        "Blanqueamiento",
        "Consulta",
        "Limpieza dental",
    ]


def test_create_treatment_cleans_the_name_and_is_active() -> None:
    world = World()
    created = create_treatment(world.treatment_deps(), ADMIN, name="  Arreglo   de caries ")
    assert (created.name, created.active) == ("Arreglo de caries", True)
    assert world.treatments.get(created.id) == created


def test_create_treatment_with_a_repeated_name_is_rejected_and_writes_nothing() -> None:
    world = World()
    with pytest.raises(TreatmentNameTakenError):
        create_treatment(world.treatment_deps(), ADMIN, name="consulta")
    assert len(world.treatments.list_all()) == 2


@pytest.mark.parametrize("name", ["   ", "", "x" * 81])
def test_create_treatment_with_an_invalid_name_is_rejected(name: str) -> None:
    world = World()
    with pytest.raises(InvalidTreatmentNameError):
        create_treatment(world.treatment_deps(), ADMIN, name=name)
    assert len(world.treatments.list_all()) == 2


@pytest.mark.parametrize("principal", [RECEPTION, DENTIST_A])
def test_only_the_admin_creates_and_updates(principal) -> None:  # type: ignore[no-untyped-def]
    world = World()
    with pytest.raises(ForbiddenError):
        create_treatment(world.treatment_deps(), principal, name="Nuevo")
    with pytest.raises(ForbiddenError):
        update_treatment(world.treatment_deps(), principal, world.consulta.id, active=False)
    assert len(world.treatments.list_all()) == 2
    assert world.treatments.get(world.consulta.id) == world.consulta


def test_update_renames() -> None:
    world = World()
    updated = update_treatment(
        world.treatment_deps(), ADMIN, world.limpieza.id, name=" Profilaxis "
    )
    assert updated.name == "Profilaxis"
    assert world.treatments.get(world.limpieza.id) == updated


def test_update_deactivates_and_reactivates() -> None:
    world = World()
    off = update_treatment(world.treatment_deps(), ADMIN, world.limpieza.id, active=False)
    assert off.active is False
    on = update_treatment(world.treatment_deps(), ADMIN, world.limpieza.id, active=True)
    assert on.active is True


def test_update_accepts_the_same_name_with_another_case() -> None:
    world = World()
    updated = update_treatment(
        world.treatment_deps(), ADMIN, world.limpieza.id, name="LIMPIEZA dental"
    )
    assert updated.name == "LIMPIEZA dental"


def test_update_rejects_the_name_of_another_treatment() -> None:
    world = World()
    with pytest.raises(TreatmentNameTakenError):
        update_treatment(world.treatment_deps(), ADMIN, world.limpieza.id, name="consulta")
    assert world.treatments.get(world.limpieza.id) == world.limpieza


def test_update_unknown_treatment_is_not_found() -> None:
    world = World()
    with pytest.raises(TreatmentNotFoundError):
        update_treatment(world.treatment_deps(), ADMIN, NIL, active=False)


def test_update_with_an_invalid_name_is_rejected() -> None:
    world = World()
    with pytest.raises(InvalidTreatmentNameError):
        update_treatment(world.treatment_deps(), ADMIN, world.limpieza.id, name="  ")
    assert world.treatments.get(world.limpieza.id) == world.limpieza


# --- Asignacion a profesionales -----------------------------------------------------


def test_a_dentist_reads_only_their_own_assignment() -> None:
    world = World()
    own = list_professional_treatments(world.treatment_deps(), DENTIST_A, PROF_A)
    assert _names(own) == ["Consulta", "Limpieza dental"]
    with pytest.raises(ForbiddenError):
        list_professional_treatments(world.treatment_deps(), DENTIST_B, PROF_A)


def test_admin_and_reception_read_any_assignment() -> None:
    world = World()
    for principal in (ADMIN, RECEPTION):
        assert _names(list_professional_treatments(world.treatment_deps(), principal, PROF_B)) == [
            "Consulta"
        ]


def test_reading_the_assignment_of_an_unknown_professional_is_not_found() -> None:
    world = World()
    with pytest.raises(ProfessionalNotFoundError):
        list_professional_treatments(world.treatment_deps(), ADMIN, NIL)


def test_reading_the_assignment_includes_inactive_treatments() -> None:
    world = World()
    update_treatment(world.treatment_deps(), ADMIN, world.limpieza.id, active=False)
    listed = list_professional_treatments(world.treatment_deps(), ADMIN, PROF_A)
    assert [(t.name, t.active) for t in listed] == [("Consulta", True), ("Limpieza dental", False)]


def test_replace_assigns_the_whole_set() -> None:
    world = World()
    saved = replace_professional_treatments(
        world.treatment_deps(), ADMIN, PROF_B, [world.consulta.id, world.limpieza.id]
    )
    assert _names(saved) == ["Consulta", "Limpieza dental"]
    assert world.treatments.offered_ids(PROF_B) == {world.consulta.id, world.limpieza.id}


def test_replace_with_an_empty_list_leaves_nothing_assigned() -> None:
    world = World()
    assert replace_professional_treatments(world.treatment_deps(), ADMIN, PROF_B, []) == []
    assert world.treatments.list_for_professional(PROF_B) == []


def test_replace_counts_repeated_ids_once() -> None:
    world = World()
    saved = replace_professional_treatments(
        world.treatment_deps(), ADMIN, PROF_B, [world.limpieza.id, world.limpieza.id]
    )
    assert _names(saved) == ["Limpieza dental"]


def test_replace_with_an_unknown_id_is_rejected_and_keeps_the_previous_assignment() -> None:
    world = World()
    with pytest.raises(TreatmentNotFoundError):
        replace_professional_treatments(
            world.treatment_deps(), ADMIN, PROF_A, [world.consulta.id, NIL]
        )
    assert world.treatments.offered_ids(PROF_A) == {world.consulta.id, world.limpieza.id}


def test_replace_for_an_unknown_professional_is_rejected() -> None:
    world = World()
    with pytest.raises(ProfessionalNotFoundError):
        replace_professional_treatments(world.treatment_deps(), ADMIN, NIL, [world.consulta.id])


@pytest.mark.parametrize("principal", [RECEPTION, DENTIST_A])
def test_only_the_admin_replaces_the_assignment(principal) -> None:  # type: ignore[no-untyped-def]
    world = World()
    with pytest.raises(ForbiddenError):
        replace_professional_treatments(world.treatment_deps(), principal, PROF_A, [])
    assert world.treatments.offered_ids(PROF_A) == {world.consulta.id, world.limpieza.id}


def test_replace_accepts_an_inactive_treatment_and_it_is_not_offered() -> None:
    world = World()
    update_treatment(world.treatment_deps(), ADMIN, world.limpieza.id, active=False)
    saved = replace_professional_treatments(
        world.treatment_deps(), ADMIN, PROF_B, [world.consulta.id, world.limpieza.id]
    )
    assert len(saved) == 2
    assert world.treatments.offered_ids(PROF_B) == {world.consulta.id}


# --- Los turnos existentes no cambian -----------------------------------------------


def test_deactivating_and_unassigning_do_not_touch_existing_appointments() -> None:
    world = World()
    saved = book_appointment(
        world.deps(),
        RECEPTION,
        patient_id="pac-1",
        professional_id=PROF_A,
        treatment_id=world.limpieza.id,
        starts_at=monday(10),
    )

    update_treatment(world.treatment_deps(), ADMIN, world.limpieza.id, active=False)
    replace_professional_treatments(world.treatment_deps(), ADMIN, PROF_A, [world.consulta.id])

    stored = world.appointments.get(saved.id)
    assert stored == saved
    assert stored is not None
    assert stored.treatment_id == world.limpieza.id

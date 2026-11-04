"""Fichas de profesionales: listar, ver y editar (spec professional-schedule-use-cases)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.application.professionals import get_professional, list_professionals, update_professional
from app.domain.appointments.errors import ProfessionalNotFoundError
from app.domain.auth import ForbiddenError
from app.domain.professionals import UNSET
from tests.unit.application.agenda_helpers import (
    ADMIN,
    DENTIST_A,
    DENTIST_B,
    DENTIST_NO_FILE,
    PROF_A,
    PROF_B,
    RECEPTION,
    World,
)
from tests.unit.domain.appointments.helpers import monday

UNKNOWN = "99999999-9999-4999-8999-999999999999"


def named_world() -> World:
    world = World()
    for professional_id, name, license_number in [
        (PROF_A, "Dra. A", "MN-1"),
        (PROF_B, "Dr. B", "MN-2"),
    ]:
        world.accounts.professionals[professional_id] = replace(
            world.accounts.professionals[professional_id],
            display_name=name,
            license_number=license_number,
        )
    return world


# --- Listar y ver -----------------------------------------------------------------------------


def test_reception_lists_all_files_ordered_by_name_with_inactive_marked() -> None:
    world = named_world()
    world.set_professional_active(PROF_B, False)
    listed = list_professionals(world.schedule_deps(), RECEPTION)
    assert [(p.display_name, p.active) for p in listed] == [("Dr. B", False), ("Dra. A", True)]


def test_a_dentist_lists_only_their_own_file() -> None:
    world = named_world()
    assert [p.id for p in list_professionals(world.schedule_deps(), DENTIST_A)] == [PROF_A]


def test_a_dentist_without_file_lists_nothing() -> None:
    assert list_professionals(named_world().schedule_deps(), DENTIST_NO_FILE) == []


def test_admin_and_reception_get_any_file_even_inactive() -> None:
    world = named_world()
    world.set_professional_active(PROF_B, False)
    assert get_professional(world.schedule_deps(), ADMIN, PROF_B).display_name == "Dr. B"
    assert get_professional(world.schedule_deps(), RECEPTION, PROF_A).display_name == "Dra. A"


@pytest.mark.parametrize("professional_id", [PROF_B, "no-es-un-uuid"])
def test_a_dentist_asking_for_a_foreign_or_malformed_file_is_forbidden(
    professional_id: str,
) -> None:
    with pytest.raises(ForbiddenError):
        get_professional(named_world().schedule_deps(), DENTIST_A, professional_id)


def test_get_unknown_file_is_not_found_for_admin_and_reception() -> None:
    deps = named_world().schedule_deps()
    for principal in (ADMIN, RECEPTION):
        with pytest.raises(ProfessionalNotFoundError):
            get_professional(deps, principal, UNKNOWN)


# --- Editar -----------------------------------------------------------------------------------


def test_admin_corrects_the_display_name_and_nothing_else_changes() -> None:
    world = named_world()
    turno = world.seed(monday(10))
    updated = update_professional(
        world.schedule_deps(), ADMIN, PROF_A, display_name="  Dra. Ana Pérez  "
    )
    assert (updated.display_name, updated.license_number, updated.active) == (
        "Dra. Ana Pérez",
        "MN-1",
        True,
    )
    assert world.everything() == [turno]


def test_admin_clears_the_license_but_an_absent_field_keeps_it() -> None:
    world = named_world()
    deps = world.schedule_deps()
    kept = update_professional(deps, ADMIN, PROF_B, display_name="Dr. Beto")
    assert kept.license_number == "MN-2"
    cleared = update_professional(deps, ADMIN, PROF_B, license_number=None)
    assert (cleared.license_number, cleared.display_name) == (None, "Dr. Beto")
    assert (
        update_professional(deps, ADMIN, PROF_B, license_number=" MN-3 ").license_number == "MN-3"
    )


def test_admin_edits_an_inactive_file_and_it_stays_inactive() -> None:
    world = named_world()
    world.set_professional_active(PROF_B, False)
    updated = update_professional(world.schedule_deps(), ADMIN, PROF_B, license_number="MN-9")
    assert (updated.license_number, updated.active) == ("MN-9", False)


def test_editing_an_unknown_file_is_not_found_and_nothing_changes() -> None:
    world = named_world()
    before = world.accounts.professionals.copy()
    with pytest.raises(ProfessionalNotFoundError):
        update_professional(world.schedule_deps(), ADMIN, UNKNOWN, display_name="X")
    assert world.accounts.professionals == before


@pytest.mark.parametrize("principal", [RECEPTION, DENTIST_A, DENTIST_B, DENTIST_NO_FILE])
def test_only_admin_edits_files(principal: object) -> None:
    world = named_world()
    before = world.accounts.professionals.copy()
    with pytest.raises(ForbiddenError):
        update_professional(world.schedule_deps(), principal, PROF_A, display_name="Otro")  # type: ignore[arg-type]
    assert world.accounts.professionals == before


def test_forbidden_comes_before_validation_of_the_data() -> None:
    with pytest.raises(ForbiddenError):
        update_professional(named_world().schedule_deps(), RECEPTION, UNKNOWN, display_name="   ")


@pytest.mark.parametrize(
    ("display_name", "license_number"), [("   ", UNSET), (None, "   "), ("x" * 201, UNSET)]
)
def test_blank_or_too_long_texts_are_a_programming_error(
    display_name: str | None, license_number: object
) -> None:
    world = named_world()
    with pytest.raises(ValueError):
        update_professional(
            world.schedule_deps(),
            ADMIN,
            PROF_A,
            display_name=display_name,
            license_number=license_number,  # type: ignore[arg-type]
        )
    assert world.accounts.professionals[PROF_A].display_name == "Dra. A"

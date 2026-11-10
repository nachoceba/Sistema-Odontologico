"""Bateria de contrato del repositorio de tratamientos (spec treatment-management, C-17)."""

from __future__ import annotations

import pytest

from app.domain.treatments.errors import TreatmentNameTakenError, TreatmentNotFoundError
from app.domain.treatments.ports import TreatmentRepository
from app.domain.treatments.types import NewTreatment, Treatment
from tests.contract.conftest import Refs

MISSING_ID = "00000000-0000-0000-0000-000000000000"


def make(repo: TreatmentRepository, name: str, *, active: bool = True) -> Treatment:
    created = repo.add(NewTreatment(name=name))
    return created if active else repo.update(created.id, active=False)


# --- Catalogo -----------------------------------------------------------------------


def test_add_returns_an_active_treatment_retrievable_by_id(
    treatment_repo: TreatmentRepository,
) -> None:
    saved = treatment_repo.add(NewTreatment(name="Limpieza dental"))
    assert saved.id
    assert (saved.name, saved.active) == ("Limpieza dental", True)
    assert treatment_repo.get(saved.id) == saved


def test_get_unknown_or_malformed_id_returns_none(treatment_repo: TreatmentRepository) -> None:
    assert treatment_repo.get("no-existe") is None
    assert treatment_repo.get(MISSING_ID) is None


@pytest.mark.parametrize("repeated", ["Extracción", "EXTRACCION", " extraccion  "])
def test_add_rejects_a_name_with_the_same_key(
    treatment_repo: TreatmentRepository, repeated: str
) -> None:
    make(treatment_repo, "Extracción")
    with pytest.raises(TreatmentNameTakenError):
        treatment_repo.add(NewTreatment(name=repeated))
    assert [t.name for t in treatment_repo.list_all()] == ["Extracción"]


def test_add_accepts_a_different_name(treatment_repo: TreatmentRepository) -> None:
    make(treatment_repo, "Consulta")
    make(treatment_repo, "Consultas")
    assert len(treatment_repo.list_all()) == 2


def test_list_all_is_ordered_by_name_ignoring_case(
    treatment_repo: TreatmentRepository,
) -> None:
    for name in ["limpieza dental", "Blanqueamiento", "Extracción", "Arreglo de caries"]:
        make(treatment_repo, name)
    make(treatment_repo, "Consulta", active=False)
    assert [t.name for t in treatment_repo.list_all()] == [
        "Arreglo de caries",
        "Blanqueamiento",
        "Consulta",
        "Extracción",
        "limpieza dental",
    ]


def test_update_renames_and_deactivates(treatment_repo: TreatmentRepository) -> None:
    saved = make(treatment_repo, "Limpieza")
    renamed = treatment_repo.update(saved.id, name="Limpieza dental")
    assert (renamed.name, renamed.active) == ("Limpieza dental", True)
    off = treatment_repo.update(saved.id, active=False)
    assert (off.name, off.active) == ("Limpieza dental", False)
    assert treatment_repo.get(saved.id) == off
    assert treatment_repo.update(saved.id, active=True).active is True


def test_update_accepts_the_same_name_with_another_case(
    treatment_repo: TreatmentRepository,
) -> None:
    saved = make(treatment_repo, "limpieza dental")
    assert treatment_repo.update(saved.id, name="Limpieza dental").name == "Limpieza dental"


def test_update_rejects_the_name_of_another_treatment(
    treatment_repo: TreatmentRepository,
) -> None:
    make(treatment_repo, "Consulta")
    other = make(treatment_repo, "Extracción")
    with pytest.raises(TreatmentNameTakenError):
        treatment_repo.update(other.id, name="consulta")
    assert treatment_repo.get(other.id) == other


def test_update_unknown_treatment_raises_not_found(treatment_repo: TreatmentRepository) -> None:
    with pytest.raises(TreatmentNotFoundError):
        treatment_repo.update(MISSING_ID, active=False)
    with pytest.raises(TreatmentNotFoundError):
        treatment_repo.update("no-existe", name="Otro")


# --- Asignacion a profesionales -----------------------------------------------------


def test_a_professional_starts_with_nothing_assigned(
    treatment_repo: TreatmentRepository, ids: Refs
) -> None:
    assert treatment_repo.list_for_professional(ids.dra_a) == []
    assert treatment_repo.offered_ids(ids.dra_a) == frozenset()
    assert treatment_repo.list_offered(ids.dra_a) == []


def test_replace_for_professional_replaces_everything(
    treatment_repo: TreatmentRepository, ids: Refs
) -> None:
    consulta = make(treatment_repo, "Consulta")
    limpieza = make(treatment_repo, "Limpieza dental")
    caries = make(treatment_repo, "Arreglo de caries")
    treatment_repo.replace_for_professional(ids.dra_a, [consulta.id, limpieza.id, caries.id])
    assert [t.id for t in treatment_repo.list_for_professional(ids.dra_a)] == [
        caries.id,
        consulta.id,
        limpieza.id,
    ]

    treatment_repo.replace_for_professional(ids.dra_a, [consulta.id])
    assert [t.id for t in treatment_repo.list_for_professional(ids.dra_a)] == [consulta.id]

    treatment_repo.replace_for_professional(ids.dra_a, [])
    assert treatment_repo.list_for_professional(ids.dra_a) == []


def test_replace_for_professional_counts_repeated_ids_once(
    treatment_repo: TreatmentRepository, ids: Refs
) -> None:
    consulta = make(treatment_repo, "Consulta")
    treatment_repo.replace_for_professional(ids.dra_a, [consulta.id, consulta.id])
    assert [t.id for t in treatment_repo.list_for_professional(ids.dra_a)] == [consulta.id]


def test_assignments_are_independent_between_professionals(
    treatment_repo: TreatmentRepository, ids: Refs
) -> None:
    consulta = make(treatment_repo, "Consulta")
    blanqueamiento = make(treatment_repo, "Blanqueamiento")
    treatment_repo.replace_for_professional(ids.dra_a, [consulta.id, blanqueamiento.id])
    treatment_repo.replace_for_professional(ids.dr_b, [consulta.id])
    assert treatment_repo.offered_ids(ids.dra_a) == {consulta.id, blanqueamiento.id}
    assert treatment_repo.offered_ids(ids.dr_b) == {consulta.id}


def test_list_for_professional_includes_inactive_but_offered_only_active(
    treatment_repo: TreatmentRepository, ids: Refs
) -> None:
    consulta = make(treatment_repo, "Consulta")
    blanqueamiento = make(treatment_repo, "Blanqueamiento", active=False)
    treatment_repo.replace_for_professional(ids.dra_a, [consulta.id, blanqueamiento.id])

    assigned = treatment_repo.list_for_professional(ids.dra_a)
    assert [(t.name, t.active) for t in assigned] == [("Blanqueamiento", False), ("Consulta", True)]
    assert treatment_repo.offered_ids(ids.dra_a) == {consulta.id}
    assert [t.id for t in treatment_repo.list_offered(ids.dra_a)] == [consulta.id]


def test_reactivating_a_treatment_makes_it_offered_again(
    treatment_repo: TreatmentRepository, ids: Refs
) -> None:
    blanqueamiento = make(treatment_repo, "Blanqueamiento", active=False)
    treatment_repo.replace_for_professional(ids.dra_a, [blanqueamiento.id])
    assert treatment_repo.offered_ids(ids.dra_a) == frozenset()
    treatment_repo.update(blanqueamiento.id, active=True)
    assert treatment_repo.offered_ids(ids.dra_a) == {blanqueamiento.id}


def test_unknown_professional_has_nothing_assigned(treatment_repo: TreatmentRepository) -> None:
    assert treatment_repo.offered_ids("no-existe") == frozenset()
    assert treatment_repo.list_for_professional("no-existe") == []

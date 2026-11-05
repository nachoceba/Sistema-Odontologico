"""Bateria de contrato del repositorio de pacientes (spec patient-repository)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from app.domain.appointments.errors import PatientNotFoundError
from app.domain.patients import EligibilityRejection, check_patient_can_book
from app.domain.patients.errors import DocumentTakenError
from app.domain.patients.types import NewPatient, Patient, PatientChanges, PatientRecord
from tests.contract.conftest import RepositoryFactory

JUAN = Patient(
    id="pac-1",
    first_name="Juan",
    last_name="Perez",
    email="juan.perez@example.com",
    active=True,
)
ANA = Patient(
    id="pac-2",
    first_name="Ana",
    last_name="Gomez",
    email="ana.gomez@example.com",
    active=False,
)


def test_active_patient_is_found_with_all_fields(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN])
    juan_id = factory.patient("pac-1")
    found = repo.get(juan_id)
    assert found == replace(JUAN, id=juan_id)
    assert found is not None
    assert found.active is True


def test_inactive_patient_active_flag_feeds_eligibility_rule(
    factory: RepositoryFactory,
) -> None:
    repo = factory.patients([JUAN, ANA])
    found = repo.get(factory.patient("pac-2"))
    assert found is not None
    assert found.active is False
    result = check_patient_can_book(found.active)
    assert not result.allowed
    assert result.reason == EligibilityRejection.PATIENT_INACTIVE
    juan = repo.get(factory.patient("pac-1"))
    assert juan is not None
    assert check_patient_can_book(juan.active).allowed


def test_unknown_patient_returns_none_without_error(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN])
    assert repo.get("no-existe") is None


# --- Ficha completa y alta (C-06) ---

JUAN_R = PatientRecord(
    id="pac-1",
    first_name="Juan",
    last_name="Pérez",
    document_number="30111222",
    email="juan.perez@example.com",
    phone="011-5550-0001",
    birth_date=None,
    active=True,
)
ANA_R = PatientRecord(
    id="pac-2",
    first_name="Ana",
    last_name="Gómez",
    document_number="30111223",
    email="ana.gomez@example.com",
    phone=None,
    birth_date=date(1985, 3, 2),
    active=False,
)
LAURA = NewPatient(
    first_name="Laura",
    last_name="Ruiz",
    document_number="40222333",
    email="laura@example.com",
    phone="011-5550-0002",
    birth_date=date(1990, 5, 10),
)


def test_full_record_includes_optional_data(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R, ANA_R])
    juan_id, ana_id = factory.patient("pac-1"), factory.patient("pac-2")
    assert repo.get_record(juan_id) == replace(JUAN_R, id=juan_id)
    assert repo.get_record(ana_id) == replace(ANA_R, id=ana_id)


def test_full_record_of_unknown_or_malformed_id_is_none(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R])
    assert repo.get_record("no-existe") is None
    assert repo.get_record("00000000-0000-4000-8000-000000000000") is None


def test_minimal_lookup_is_unchanged_by_full_records(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R])
    juan_id = factory.patient("pac-1")
    assert repo.get(juan_id) == Patient(
        id=juan_id,
        first_name="Juan",
        last_name="Pérez",
        email="juan.perez@example.com",
        active=True,
    )


def test_add_saves_active_patient_and_returns_the_record(factory: RepositoryFactory) -> None:
    repo = factory.patients()
    saved = repo.add(LAURA)
    assert saved.id
    assert saved.active is True
    assert (saved.first_name, saved.last_name, saved.document_number) == (
        "Laura",
        "Ruiz",
        "40222333",
    )
    assert (saved.email, saved.phone, saved.birth_date) == (
        "laura@example.com",
        "011-5550-0002",
        date(1990, 5, 10),
    )
    assert repo.get_record(saved.id) == saved


def test_add_without_optional_data_keeps_them_absent(factory: RepositoryFactory) -> None:
    repo = factory.patients()
    saved = repo.add(replace(LAURA, phone=None, birth_date=None))
    assert (saved.phone, saved.birth_date) == (None, None)


def test_add_with_taken_document_is_rejected_and_changes_nothing(
    factory: RepositoryFactory,
) -> None:
    repo = factory.patients([JUAN_R])
    juan_id = factory.patient("pac-1")
    with pytest.raises(DocumentTakenError):
        repo.add(replace(LAURA, document_number="30111222"))
    assert repo.get_record(juan_id) == replace(JUAN_R, id=juan_id)


def test_add_with_document_of_an_inactive_patient_is_rejected(
    factory: RepositoryFactory,
) -> None:
    repo = factory.patients([ANA_R])
    with pytest.raises(DocumentTakenError):
        repo.add(replace(LAURA, document_number="30111223"))


# --- Buscar pacientes ---


def _person(
    ref: str, first: str, last: str, document: str, *, active: bool = True
) -> PatientRecord:
    return PatientRecord(
        id=ref,
        first_name=first,
        last_name=last,
        document_number=document,
        email=f"{ref}@example.com",
        phone=None,
        birth_date=None,
        active=active,
    )


MARTA = _person("pac-3", "Marta", "López", "40222333")
LUCIA = _person("pac-4", "Lucía", "Torres", "30111224")


def _names(found: list[PatientRecord]) -> list[str]:
    return [f"{p.first_name} {p.last_name}" for p in found]


def test_search_by_partial_last_name_ignores_case(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R, MARTA, LUCIA])
    assert _names(repo.search(text="pÉ", include_inactive=False, limit=10)) == ["Juan Pérez"]
    assert _names(repo.search(text="RE", include_inactive=False, limit=10)) == [
        "Juan Pérez",
        "Lucía Torres",
    ]


def test_search_by_start_of_document_accepts_dots_and_orders_by_last_name(
    factory: RepositoryFactory,
) -> None:
    repo = factory.patients([LUCIA, JUAN_R, MARTA])
    assert _names(repo.search(text="30.111", include_inactive=False, limit=10)) == [
        "Juan Pérez",
        "Lucía Torres",
    ]
    assert _names(repo.search(text="40222", include_inactive=False, limit=10)) == ["Marta López"]


def test_search_excludes_inactive_unless_asked(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R, ANA_R])
    assert _names(repo.search(text="", include_inactive=False, limit=10)) == ["Juan Pérez"]
    found = repo.search(text="", include_inactive=True, limit=10)
    assert _names(found) == ["Ana Gómez", "Juan Pérez"]
    assert [p.active for p in found] == [False, True]


def test_search_treats_wildcards_as_plain_text(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R, MARTA])
    assert repo.search(text="%", include_inactive=True, limit=10) == []
    assert repo.search(text="_", include_inactive=True, limit=10) == []
    assert repo.search(text="\\", include_inactive=True, limit=10) == []


def test_search_respects_the_maximum_in_last_name_order(factory: RepositoryFactory) -> None:
    people = [
        _person(f"pac-{n}", "Paciente", last, f"5000000{n}")
        for n, last in enumerate(["Echeverría", "Díaz", "Aguirre", "Castro", "Benítez"], start=5)
    ]
    repo = factory.patients(people)
    found = repo.search(text="", include_inactive=False, limit=3)
    assert [p.last_name for p in found] == ["Aguirre", "Benítez", "Castro"]


def test_search_with_the_same_last_name_orders_by_first_name(factory: RepositoryFactory) -> None:
    repo = factory.patients(
        [
            _person("pac-5", "Zoe", "Ruiz", "50000001"),
            _person("pac-6", "Abel", "Ruiz", "50000002"),
        ]
    )
    assert _names(repo.search(text="ruiz", include_inactive=False, limit=10)) == [
        "Abel Ruiz",
        "Zoe Ruiz",
    ]


def test_a_rejected_add_leaves_a_single_patient_with_that_document(
    factory: RepositoryFactory,
) -> None:
    repo = factory.patients([JUAN_R])
    with pytest.raises(DocumentTakenError):
        repo.add(replace(LAURA, document_number="30111222"))
    assert _names(repo.search(text="30111222", include_inactive=True, limit=10)) == ["Juan Pérez"]


# --- Editar, activar y desactivar ---

LUIS = _person("pac-5", "Luis", "Fernández", "30111224")


def test_update_changes_email_and_clears_phone_keeping_the_rest(
    factory: RepositoryFactory,
) -> None:
    repo = factory.patients([JUAN_R])
    juan_id = factory.patient("pac-1")
    updated = repo.update(juan_id, PatientChanges(email="nuevo@example.com", phone=None))
    assert updated == replace(JUAN_R, id=juan_id, email="nuevo@example.com", phone=None)
    assert repo.get_record(juan_id) == updated


def test_update_changes_name_document_and_birth_date(factory: RepositoryFactory) -> None:
    repo = factory.patients([ANA_R])
    ana_id = factory.patient("pac-2")
    updated = repo.update(
        ana_id,
        PatientChanges(
            first_name="Anita",
            last_name="Gómez Paz",
            document_number="30999888",
            birth_date=None,
        ),
    )
    assert updated == replace(
        ANA_R,
        id=ana_id,
        first_name="Anita",
        last_name="Gómez Paz",
        document_number="30999888",
        birth_date=None,
    )


def test_update_with_the_document_of_another_patient_is_rejected(
    factory: RepositoryFactory,
) -> None:
    repo = factory.patients([JUAN_R, LUIS])
    luis_id = factory.patient("pac-5")
    with pytest.raises(DocumentTakenError):
        repo.update(luis_id, PatientChanges(document_number="30111222", first_name="Otro"))
    assert repo.get_record(luis_id) == replace(LUIS, id=luis_id)


def test_update_resending_the_own_document_is_not_a_conflict(
    factory: RepositoryFactory,
) -> None:
    repo = factory.patients([JUAN_R])
    juan_id = factory.patient("pac-1")
    updated = repo.update(juan_id, PatientChanges(document_number="30111222", first_name="Juana"))
    assert updated.first_name == "Juana"
    assert updated.document_number == "30111222"


def test_update_of_unknown_patient_is_not_found(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R])
    with pytest.raises(PatientNotFoundError):
        repo.update("no-existe", PatientChanges(first_name="X"))


def test_deactivate_is_seen_by_the_eligibility_rule(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R])
    juan_id = factory.patient("pac-1")
    assert repo.set_active(juan_id, False).active is False
    found = repo.get(juan_id)
    assert found is not None
    assert found.active is False
    result = check_patient_can_book(found.active)
    assert result.reason == EligibilityRejection.PATIENT_INACTIVE


def test_reactivate_returns_the_active_record(factory: RepositoryFactory) -> None:
    repo = factory.patients([ANA_R])
    ana_id = factory.patient("pac-2")
    assert repo.set_active(ana_id, True) == replace(ANA_R, id=ana_id, active=True)


def test_deactivating_an_inactive_patient_is_not_an_error(factory: RepositoryFactory) -> None:
    repo = factory.patients([ANA_R])
    ana_id = factory.patient("pac-2")
    assert repo.set_active(ana_id, False) == replace(ANA_R, id=ana_id)


def test_set_active_of_unknown_patient_is_not_found(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R])
    with pytest.raises(PatientNotFoundError):
        repo.set_active("no-existe", False)


# --- Borrar ---


def test_delete_of_patient_without_appointments_removes_it(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R, ANA_R])
    juan_id = factory.patient("pac-1")
    assert repo.delete(juan_id) is True
    assert repo.get_record(juan_id) is None
    assert repo.get(juan_id) is None
    ana_id = factory.patient("pac-2")
    assert repo.get_record(ana_id) == replace(ANA_R, id=ana_id)


def test_delete_frees_the_document_for_a_new_add(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R])
    assert repo.delete(factory.patient("pac-1")) is True
    assert repo.add(replace(LAURA, document_number="30111222")).document_number == "30111222"


def test_delete_of_unknown_patient_reports_it_did_not_exist(factory: RepositoryFactory) -> None:
    repo = factory.patients([JUAN_R])
    assert repo.delete("no-existe") is False

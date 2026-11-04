"""Errores de los casos de uso de agenda y su traduccion desde motivos de dominio (D-1, D-8)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.errors import DomainError
from app.domain.appointments import RejectionReason, TransitionRejection
from app.domain.appointments.errors import (
    AlreadyStartedError,
    AttendanceAlreadyRecordedError,
    CancelledIsFinalError,
    InsufficientNoticeError,
    NotStartedYetError,
    OffGridError,
    OutsideWorkingHoursError,
    PatientDoubleBookedError,
    PatientInactiveError,
    PatientNotFoundError,
    ProfessionalInactiveError,
    ProfessionalNotFoundError,
    ProfessionalTimeOffError,
    RescheduleSameTimeError,
    SlotTakenError,
    error_for_rejection,
    error_for_transition,
)

START = datetime(2026, 10, 5, 13, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("error_class", "code"),
    [
        (PatientNotFoundError, "PATIENT_NOT_FOUND"),
        (ProfessionalNotFoundError, "PROFESSIONAL_NOT_FOUND"),
        (PatientInactiveError, "PATIENT_INACTIVE"),
        (ProfessionalInactiveError, "PROFESSIONAL_INACTIVE"),
        (PatientDoubleBookedError, "PATIENT_DOUBLE_BOOKED"),
        (RescheduleSameTimeError, "RESCHEDULE_SAME_TIME"),
        (InsufficientNoticeError, "INSUFFICIENT_NOTICE"),
        (OffGridError, "OFF_GRID"),
        (OutsideWorkingHoursError, "OUTSIDE_WORKING_HOURS"),
        (ProfessionalTimeOffError, "PROFESSIONAL_TIME_OFF"),
        (CancelledIsFinalError, "CANCELLED_IS_FINAL"),
        (AttendanceAlreadyRecordedError, "ATTENDANCE_ALREADY_RECORDED"),
        (AlreadyStartedError, "ALREADY_STARTED"),
        (NotStartedYetError, "NOT_STARTED_YET"),
    ],
)
def test_each_error_is_a_domain_error_with_its_code_and_a_spanish_message(
    error_class: type[DomainError], code: str
) -> None:
    error = error_class()
    assert isinstance(error, DomainError)
    assert error.code == code
    assert str(error).strip() != ""
    assert code not in str(error)  # el mensaje es para personas, no el codigo


def test_patient_double_booked_message_does_not_reveal_other_appointment_data() -> None:
    assert str(PatientDoubleBookedError()) == "El paciente ya tiene otro turno en ese horario"


@pytest.mark.parametrize(
    ("reason", "code"),
    [
        (RejectionReason.INSUFFICIENT_NOTICE, "INSUFFICIENT_NOTICE"),
        (RejectionReason.OFF_GRID, "OFF_GRID"),
        (RejectionReason.OUTSIDE_WORKING_HOURS, "OUTSIDE_WORKING_HOURS"),
        (RejectionReason.PROFESSIONAL_TIME_OFF, "PROFESSIONAL_TIME_OFF"),
    ],
)
def test_error_for_rejection_maps_each_rule_to_its_error(
    reason: RejectionReason, code: str
) -> None:
    assert error_for_rejection(reason, professional_id="dra-a", starts_at=START).code == code


def test_overlap_rejection_is_reported_as_slot_taken_like_the_database_race() -> None:
    error = error_for_rejection(
        RejectionReason.OVERLAPS_EXISTING, professional_id="dra-a", starts_at=START
    )
    assert isinstance(error, SlotTakenError)
    assert error.code == "SLOT_TAKEN"
    assert error.professional_id == "dra-a"
    assert error.starts_at == START


@pytest.mark.parametrize(
    ("reason", "code"),
    [
        (TransitionRejection.CANCELLED_IS_FINAL, "CANCELLED_IS_FINAL"),
        (TransitionRejection.ATTENDANCE_ALREADY_RECORDED, "ATTENDANCE_ALREADY_RECORDED"),
        (TransitionRejection.ALREADY_STARTED, "ALREADY_STARTED"),
        (TransitionRejection.NOT_STARTED_YET, "NOT_STARTED_YET"),
    ],
)
def test_error_for_transition_maps_each_used_rejection(
    reason: TransitionRejection, code: str
) -> None:
    assert error_for_transition(reason).code == code


def test_error_for_transition_rejects_a_target_status_it_never_expects() -> None:
    with pytest.raises(ValueError):
        error_for_transition(TransitionRejection.INVALID_TARGET_STATUS)

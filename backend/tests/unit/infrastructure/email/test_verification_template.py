"""Plantilla del email de verificacion de una reserva online (spec email-templates, C-15)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from app.infrastructure.email.templates import VerificationEmailData, render_verification_email

ZONE = "America/Argentina/Buenos_Aires"
URL = "https://turnos.consultorio.example/turnos/confirmar#token=abc_DEF-123"

DATA = VerificationEmailData(
    patient_first_name="Lucía",
    patient_last_name="Díaz",
    professional_name="Dra. A",
    starts_at=datetime(2026, 11, 9, 13, 30, tzinfo=UTC),  # lunes 10:30 locales
    confirm_before=datetime(2026, 11, 9, 16, 0, tzinfo=UTC),  # 13:00 locales
    timezone=ZONE,
    clinic_name="Consultorio Demo",
    address="Av. Siempre Viva 742",
    phone="011 4000-0000",
    confirm_url=URL,
)


def test_subject_names_the_clinic() -> None:
    subject, _ = render_verification_email(DATA)

    assert subject == "Confirmá tu turno en Consultorio Demo"


def test_body_has_patient_professional_local_date_link_deadline_and_clinic_in_order() -> None:
    _, body = render_verification_email(DATA)

    expected_in_order = [
        "Lucía Díaz",
        "Dra. A",
        "lunes 09/11/2026 10:30",
        URL,
        "hasta las 13:00",
        "el horario se libera",
        "si no pediste el turno",
        "Consultorio Demo",
        "Av. Siempre Viva 742",
        "011 4000-0000",
    ]
    position = -1
    for piece in expected_in_order:
        found = body.lower().find(piece.lower(), position + 1)
        assert found > position, f"{piece!r} no esta en orden"
        position = found


def test_the_body_never_contains_a_document_number() -> None:
    _, body = render_verification_email(DATA)

    assert "40999888" not in body
    assert "documento" not in body.lower()


def test_without_address_or_phone_those_lines_are_left_out() -> None:
    _, body = render_verification_email(replace(DATA, address="", phone=None))

    assert "Dirección" not in body
    assert "Teléfono" not in body


def test_the_deadline_uses_the_local_time_of_the_clinic() -> None:
    _, body = render_verification_email(
        replace(DATA, confirm_before=datetime(2026, 11, 9, 2, 5, tzinfo=UTC))
    )

    assert "hasta las 23:05" in body  # 02:05 UTC es 23:05 del domingo local

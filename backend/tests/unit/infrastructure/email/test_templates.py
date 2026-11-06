"""Plantillas de confirmacion y recordatorio (spec email-templates)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.domain.appointments import NotificationKind
from app.infrastructure.email.templates import EmailData, render_email

ZONE = "America/Argentina/Buenos_Aires"
INFO_LINE = (
    "Este email es informativo: para cambiar o cancelar el turno comunicate con el consultorio."
)

DATA = EmailData(
    patient_first_name="Juan",
    patient_last_name="Perez",
    professional_name="Dra. A",
    starts_at=datetime(2026, 11, 9, 13, 0, tzinfo=UTC),
    timezone=ZONE,
    clinic_name="Consultorio Demo",
    address="Av. Siempre Viva 742",
    phone="011 4000-0000",
)


def test_confirmation_subject_and_body_have_the_exact_text_and_order() -> None:
    subject, body = render_email(NotificationKind.CONFIRMATION, DATA)

    assert subject == ("Turno confirmado: lunes 9 de noviembre de 2026, 10:00 h - Consultorio Demo")
    expected_in_order = [
        "Hola, Juan Perez:",
        "Tu turno quedó agendado.",
        "lunes 9 de noviembre de 2026, 10:00 h",
        "Dra. A",
        "Consultorio Demo",
        "Av. Siempre Viva 742",
        "011 4000-0000",
        INFO_LINE,
    ]
    position = -1
    for piece in expected_in_order:
        found = body.find(piece, position + 1)
        assert found > position, f"{piece!r} no esta en orden"
        position = found


def test_confirmation_without_clinic_phone_has_no_phone_line_nor_empty_label() -> None:
    _, body = render_email(NotificationKind.CONFIRMATION, replace(DATA, phone=None))

    assert "Teléfono" not in body
    assert "011" not in body
    assert "Dirección: Av. Siempre Viva 742" in body


def test_confirmation_without_address_has_no_empty_address_label() -> None:
    _, body = render_email(NotificationKind.CONFIRMATION, replace(DATA, address=""))
    assert "Dirección" not in body


def test_a_start_near_utc_midnight_shows_the_clinic_local_day() -> None:
    late = replace(DATA, starts_at=datetime(2026, 11, 10, 2, 30, tzinfo=UTC))

    subject, body = render_email(NotificationKind.CONFIRMATION, late)

    assert "lunes 9 de noviembre de 2026, 23:30 h" in subject
    assert "lunes 9 de noviembre de 2026, 23:30 h" in body
    assert "martes" not in subject + body


def test_another_weekday_and_month_use_their_own_spanish_names() -> None:
    other = replace(DATA, starts_at=datetime(2027, 3, 3, 12, 5, tzinfo=UTC))  # miercoles 09:05

    subject, _ = render_email(NotificationKind.CONFIRMATION, other)

    assert "miércoles 3 de marzo de 2027, 09:05 h" in subject


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (datetime(2026, 12, 6, 15, 0, tzinfo=UTC), "domingo 6 de diciembre de 2026, 12:00 h"),
        (datetime(2026, 7, 4, 15, 0, tzinfo=UTC), "sábado 4 de julio de 2026, 12:00 h"),
    ],
)
def test_weekday_and_month_names_with_accents(moment: datetime, expected: str) -> None:
    subject, _ = render_email(NotificationKind.CONFIRMATION, replace(DATA, starts_at=moment))
    assert expected in subject


def test_the_email_uses_the_data_given_which_are_the_current_ones() -> None:
    renamed = replace(DATA, patient_last_name="Pérez")
    _, body = render_email(NotificationKind.CONFIRMATION, renamed)
    assert "Hola, Juan Pérez:" in body


def test_the_email_has_no_patient_document_phone_or_birth_date() -> None:
    # EmailData no tiene esos campos: lo que no se le pasa no puede aparecer.
    names = set(EmailData.__dataclass_fields__)
    assert not {"document_number", "patient_phone", "birth_date", "email"} & names
    subject, body = render_email(NotificationKind.CONFIRMATION, DATA)
    assert "@" not in subject + body


def test_reminder_changes_subject_and_phrase_and_keeps_the_rest() -> None:
    subject, body = render_email(NotificationKind.REMINDER, DATA)

    assert subject == (
        "Recordatorio de turno: lunes 9 de noviembre de 2026, 10:00 h - Consultorio Demo"
    )
    assert "Te recordamos tu turno." in body
    assert "Tu turno quedó agendado." not in body
    assert INFO_LINE in body
    assert "Dra. A" in body


@pytest.mark.parametrize("data", [DATA, replace(DATA, phone=None, address="")])
def test_the_reminder_never_uses_relative_words(data: EmailData) -> None:
    subject, body = render_email(NotificationKind.REMINDER, data)
    text = (subject + body).lower()
    assert "mañana" not in text
    assert "24 horas" not in text


def test_an_unknown_kind_is_rejected_as_a_programming_error() -> None:
    with pytest.raises(ValueError, match="tipo de email"):
        render_email("newsletter", DATA)  # type: ignore[arg-type]

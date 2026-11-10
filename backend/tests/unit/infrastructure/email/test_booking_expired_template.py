"""Email de cancelacion por falta de confirmacion (spec email-templates, C-16, DD-140)."""

from __future__ import annotations

from dataclasses import fields, replace
from datetime import UTC, datetime

import pytest

from app.domain.appointments import NotificationKind
from app.infrastructure.email.redirect import DEMO_LINE
from app.infrastructure.email.templates import EmailData, render_email

ZONE = "America/Argentina/Buenos_Aires"
CANCEL_LINE = "Su turno se canceló porque no fue confirmado a tiempo con el enlace que le enviamos."

DATA = EmailData(
    patient_first_name="Lucía",
    patient_last_name="Díaz",
    professional_name="Dra. A",
    starts_at=datetime(2026, 11, 9, 13, 30, tzinfo=UTC),
    timezone=ZONE,
    clinic_name="Consultorio Demo",
    address="Av. Siempre Viva 742",
    phone="011 4000-0000",
    public_app_url="https://turnos.example.test",
)


def render(data: EmailData = DATA) -> tuple[str, str]:
    return render_email(NotificationKind.BOOKING_EXPIRED, data)


def test_the_subject_says_the_appointment_was_cancelled_for_lack_of_confirmation() -> None:
    subject, _ = render()

    assert subject == "Tu turno en Consultorio Demo se canceló por falta de confirmación"


def test_the_body_has_name_professional_local_time_sentence_link_and_clinic_in_order() -> None:
    _, body = render()

    expected_in_order = [
        "Hola, Lucía Díaz:",
        "Profesional: Dra. A",
        "Fecha y hora: lunes 09/11/2026 10:30",
        CANCEL_LINE,
        "Si todavía lo necesita, puede volver a reservar en https://turnos.example.test/turnos.",
        "Consultorio: Consultorio Demo",
        "Dirección: Av. Siempre Viva 742",
        "Teléfono: 011 4000-0000",
    ]
    position = -1
    for piece in expected_in_order:
        found = body.find(piece, position + 1)
        assert found > position, f"{piece!r} no esta en orden"
        position = found


def test_the_hour_is_the_clinic_hour_and_not_utc() -> None:
    _, body = render()

    assert "10:30" in body
    assert "13:30" not in body


def test_another_zone_changes_the_local_day_and_hour() -> None:
    other = replace(
        DATA, timezone="America/New_York", starts_at=datetime(2026, 11, 10, 3, 30, tzinfo=UTC)
    )

    _, body = render(other)

    assert "lunes 09/11/2026 22:30" in body


def test_missing_address_and_phone_are_left_out() -> None:
    _, body = render(replace(DATA, address="", phone=None))

    assert "Dirección" not in body
    assert "Teléfono" not in body
    assert "Consultorio: Consultorio Demo" in body


def test_the_text_carries_no_document_reason_or_other_people() -> None:
    _, body = render()

    assert not any("document" in f.name or "reason" in f.name for f in fields(EmailData))
    assert "DNI" not in body
    assert "documento" not in body.lower()
    assert "motivo" not in body.lower()


def test_it_is_plain_text_without_html() -> None:
    _, body = render()

    assert "<" not in body
    assert body.endswith("\n")


@pytest.mark.parametrize("base", ["https://turnos.example.test", "http://localhost:5173"])
def test_the_link_points_at_the_public_booking_page_of_the_configured_site(base: str) -> None:
    _, body = render(replace(DATA, public_app_url=base))

    assert f"{base}/turnos." in body


def test_the_demo_line_is_added_by_the_redirecting_sender_not_by_the_template() -> None:
    _, body = render()

    assert DEMO_LINE not in body

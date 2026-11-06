"""Plantillas de los emails de turno, en texto plano (spec email-templates, design D-5).

Funciones puras: reciben los datos vigentes y devuelven asunto y cuerpo. Los dias y meses
van en castellano con tablas propias (``locale`` depende del sistema del contenedor) y la
hora sale de ``to_local`` (RN-GL-01). No reciben documento, telefono ni nacimiento del
paciente: lo que no entra no puede aparecer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.timezone import to_local
from app.domain.appointments.types import NotificationKind

_WEEKDAYS = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)
_MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
INFORMATIVE_LINE = (
    "Este email es informativo: para cambiar o cancelar el turno comunicate con el consultorio."
)
_HEADLINE = {
    NotificationKind.CONFIRMATION: "Tu turno quedó agendado.",
    NotificationKind.REMINDER: "Te recordamos tu turno.",
}
_SUBJECT_PREFIX = {
    NotificationKind.CONFIRMATION: "Turno confirmado",
    NotificationKind.REMINDER: "Recordatorio de turno",
}


@dataclass(frozen=True)
class EmailData:
    """Datos vigentes al momento del envio."""

    patient_first_name: str
    patient_last_name: str
    professional_name: str
    starts_at: datetime  # UTC
    timezone: str
    clinic_name: str
    address: str
    phone: str | None


def format_local_datetime(instant: datetime, timezone_name: str) -> str:
    """``lunes 9 de noviembre de 2026, 10:00 h`` en la hora del consultorio."""
    local = to_local(instant, timezone_name)
    return (
        f"{_WEEKDAYS[local.weekday()]} {local.day} de {_MONTHS[local.month - 1]} "
        f"de {local.year}, {local:%H:%M} h"
    )


def render_email(kind: NotificationKind, data: EmailData) -> tuple[str, str]:
    """Asunto y cuerpo del email del tipo pedido; un tipo desconocido es un error de codigo."""
    if kind not in _HEADLINE:
        raise ValueError("tipo de email desconocido")
    when = format_local_datetime(data.starts_at, data.timezone)
    subject = f"{_SUBJECT_PREFIX[kind]}: {when} - {data.clinic_name}"
    lines = [
        f"Hola, {data.patient_first_name} {data.patient_last_name}:",
        "",
        _HEADLINE[kind],
        "",
        f"Fecha y hora: {when}",
        f"Profesional: {data.professional_name}",
        f"Consultorio: {data.clinic_name}",
    ]
    if data.address:
        lines.append(f"Dirección: {data.address}")
    if data.phone:
        lines.append(f"Teléfono: {data.phone}")
    lines += ["", INFORMATIVE_LINE]
    return subject, "\n".join(lines) + "\n"

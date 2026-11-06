"""Configuracion de agenda del consultorio. Solo libreria estandar."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClinicSettings:
    """Valores por defecto del modelo de datos: DD-03, SU-01 y DD-14."""

    slot_minutes: int = 30
    timezone: str = "America/Argentina/Buenos_Aires"
    min_notice_hours: int = 6
    # Datos del consultorio para los emails y hora del recordatorio (C-11, D-10).
    clinic_name: str = "Consultorio"
    address: str = ""
    phone: str | None = None
    reminder_send_hour: int = 9

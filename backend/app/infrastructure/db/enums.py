"""Enumerados de infraestructura sin tipo de dominio todavia (design D-4).

``AppointmentStatus`` vive en el dominio y se reutiliza tal cual. Los valores de estos
enumerados son los que guarda PostgreSQL (``values_callable`` en los modelos).
"""

from __future__ import annotations

from enum import Enum


class UserRole(Enum):
    ADMIN = "admin"
    RECEPTIONIST = "receptionist"
    DENTIST = "dentist"


class NotificationKind(Enum):
    CONFIRMATION = "confirmation"
    REMINDER = "reminder"
    BOOKING_EXPIRED = "booking_expired"


class NotificationStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"

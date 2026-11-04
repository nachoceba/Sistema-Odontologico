"""Dominio de profesionales (C-04: solo lectura de fichas)."""

from app.domain.professionals.ports import ProfessionalRepository
from app.domain.professionals.types import Professional

__all__ = ["Professional", "ProfessionalRepository"]

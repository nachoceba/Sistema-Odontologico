"""Dominio de profesionales (C-04: lectura de fichas; C-07: edicion)."""

from app.domain.professionals.ports import ProfessionalRepository
from app.domain.professionals.types import UNSET, Professional, Unset

__all__ = ["UNSET", "Professional", "ProfessionalRepository", "Unset"]

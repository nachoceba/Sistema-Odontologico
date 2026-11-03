"""Validacion previa de rangos que comparten todos los repositorios (design D-6).

Funciones puras, solo libreria estandar. La implementacion en memoria y la de PostgreSQL las
llaman ANTES de tocar su almacenamiento, de modo que el tipo y el mensaje del error no dependan
de la implementacion (equivalen a los CHECK de la base).
"""

from __future__ import annotations

from datetime import date, datetime


def require_range(starts_at: datetime, ends_at: datetime) -> None:
    """Instantes con zona e inicio < fin (CHECK ``starts_at < ends_at``)."""
    if starts_at.tzinfo is None or ends_at.tzinfo is None:
        raise ValueError("inicio y fin deben tener zona horaria")
    if starts_at >= ends_at:
        raise ValueError("el inicio debe ser anterior al fin")


def require_query_range(start: datetime, end: datetime | None) -> None:
    """Rango de consulta ``[start, end)``: con zona y, si hay fin, ``start < end``."""
    if start.tzinfo is None or (end is not None and end.tzinfo is None):
        raise ValueError("desde y hasta deben tener zona horaria")
    if end is not None and start >= end:
        raise ValueError("desde debe ser anterior a hasta")


def require_time_off_range(starts_on: date, ends_on: date) -> None:
    """CHECK ``starts_on <= ends_on``: una licencia de un solo dia es valida."""
    if ends_on < starts_on:
        raise ValueError("la licencia no puede terminar antes de empezar")

"""Texto comparable: mayusculas, sin tildes y con un solo espacio (compartido con tratamientos)."""

from __future__ import annotations

import pytest

from app.domain.text import comparable_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  María   José ", "MARIA JOSE"),
        ("Extracción", "EXTRACCION"),
        ("ñandú", "NANDU"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_comparable_text_removes_marks_case_and_repeated_spaces(raw: str, expected: str) -> None:
    assert comparable_text(raw) == expected


def test_comparable_text_makes_equivalent_spellings_equal() -> None:
    assert comparable_text("limpieza  DENTAL") == comparable_text("Limpiéza dental")

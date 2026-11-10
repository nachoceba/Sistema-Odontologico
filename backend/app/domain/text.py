"""Comparacion de textos sin mayusculas, tildes ni espacios repetidos. Solo libreria estandar."""

from __future__ import annotations

import unicodedata


def comparable_text(text: str) -> str:
    """NFKD sin diacriticos, en mayusculas y con los espacios reducidos (DD-129)."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.upper().split())

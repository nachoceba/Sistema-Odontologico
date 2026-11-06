"""Fallo de envio clasificado (spec email-sending). Sin datos personales."""

from __future__ import annotations

import re

_SMTP_CODE = re.compile(r"^[1-5]\d\d(?!\d)")
_NETWORK_CODES = frozenset({"CONNECTION", "TIMEOUT"})
MAX_ERROR_LENGTH = 200


def _clean_code(raw: str) -> str:
    """Deja solo un codigo SMTP de tres cifras o una palabra de red conocida."""
    candidate = raw.strip()
    match = _SMTP_CODE.match(candidate)
    if match:
        return match.group(0)
    return candidate if candidate in _NETWORK_CODES else ""


class EmailSendError(Exception):
    """Un envio que no se completo; ``temporary`` decide si se reintenta (design D-4).

    ``code`` puede venir sucio (texto del servidor): solo se conserva lo seguro.
    """

    def __init__(self, *, temporary: bool, code: str = "") -> None:
        self.temporary = temporary
        self.code = _clean_code(code)
        super().__init__(sanitize_error(self))


def sanitize_error(error: EmailSendError) -> str:
    """Texto guardado en ``email_notifications.error``: ``SMTP_PERMANENT 550`` y similares."""
    kind = "SMTP_TEMPORARY" if error.temporary else "SMTP_PERMANENT"
    text = f"{kind} {error.code}" if error.code else kind
    return text[:MAX_ERROR_LENGTH]

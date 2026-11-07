"""Acceso a la API HTTP de Mailpit desde los tests que corren en el contenedor.

Lo comparten los tests de integracion de confirmacion y recordatorio (C-11/C-12) y el smoke
test de punta a punta (C-13). ``MAILPIT_URL`` permite apuntar a otro host; por defecto es el
servicio ``mailpit`` de Docker Compose.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any

MAILPIT_API = os.environ.get("MAILPIT_URL", "http://mailpit:8025/api/v1")


def mailpit(path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{MAILPIT_API}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
        payload = response.read()
    return json.loads(payload) if payload.startswith((b"{", b"[")) else payload


def messages_to(address: str) -> list[dict[str, Any]]:
    query = urllib.parse.quote(f"to:{address}")
    messages: list[dict[str, Any]] = mailpit(f"/search?query={query}")["messages"]
    return messages


def delete_messages(messages: list[dict[str, Any]]) -> None:
    ids = [message["ID"] for message in messages]
    if ids:
        mailpit("/messages", method="DELETE", body={"IDs": ids})

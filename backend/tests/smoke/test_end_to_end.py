"""Smoke test de punta a punta contra el entorno levantado (DD-108 y DD-109, end-to-end-smoke).

Se pide con ``docker compose exec api pytest -m smoke`` (desarrollo o demo). Habla HTTP con la
API (``SMOKE_API_URL``, por defecto ``http://api:8000/api/v1``) y con la API de Mailpit, y pide
la pasada de recordatorios al ``worker`` real por la cola. Usa las cuentas del seed (la
contrasena sale de ``SEED_DEMO_PASSWORD`` del entorno, nunca del codigo) y dos pacientes ficticios
propios que al terminar quedan desactivados y sin turnos agendados. Los pasos corren en orden y
comparten estado: si uno falla, los siguientes fallan avisando cual fue.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.infrastructure.email.templates import format_local_datetime
from app.infrastructure.tasks.celery_app import celery_app
from tests.mailpit_support import MAILPIT_API, delete_messages, mailpit, messages_to

API_URL = os.environ.get("SMOKE_API_URL", "http://api:8000/api/v1")
PASSWORD_VARIABLE = "SEED_DEMO_PASSWORD"
SEED_ACCOUNTS = {
    "admin": "admin@example.com",
    "receptionist": "recepcion@example.com",
    "dentist": "dra.a@example.com",
}
CONFIRMATION = "Turno confirmado"
REMINDER = "Recordatorio de turno"
WAIT_SECONDS = 30.0
SETTLE_SECONDS = 5.0
NEW_BLOCK = ("09:00", "12:00")  # horario agregado si mañana no atiende nadie (P-6)
SLOTS_NEEDED = 3


@dataclass
class Flow:
    """Estado compartido entre los pasos del recorrido."""

    client: httpx.Client
    timezone: ZoneInfo
    tokens: dict[str, str] = field(default_factory=dict)
    professional_id: str = ""
    original_blocks: list[dict[str, Any]] | None = None  # no es None si se agrego un tramo
    slots: list[datetime] = field(default_factory=list)
    patients: dict[str, dict[str, str]] = field(default_factory=dict)
    appointments: dict[str, str] = field(default_factory=dict)

    @property
    def tomorrow(self) -> date:
        return datetime.now(self.timezone).date() + timedelta(days=1)

    def token(self, role: str) -> str:
        if role not in self.tokens:
            response = self.client.post(
                "/auth/login",
                json={"email": SEED_ACCOUNTS[role], "password": os.environ[PASSWORD_VARIABLE]},
            )
            assert response.status_code == 200, f"login de {role}: {response.status_code}"
            self.tokens[role] = response.json()["access_token"]
        return self.tokens[role]

    def call(self, role: str, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self.token(role)}"}
        return self.client.request(method, path, headers=headers, **kwargs)

    def when(self, index: int) -> str:
        """El horario de la franja tal como aparece en el asunto de los emails."""
        return format_local_datetime(self.slots[index], str(self.timezone))

    def recipient(self, label: str) -> str:
        """Donde llegan los emails del paciente: ``EMAIL_REDIRECT_TO`` si esta definida."""
        return os.environ.get("EMAIL_REDIRECT_TO") or self.patients[label]["email"]

    def mail_count(self, prefix: str, when: str) -> int:
        """Emails del tipo y horario dados en los buzones de los pacientes del test."""
        recipients = {self.recipient(label) for label in self.patients}
        return sum(
            1
            for address in recipients
            for message in messages_to(address)
            if message["Subject"].startswith(prefix) and when in message["Subject"]
        )


def _require_environment() -> None:
    """Chequeo previo: contrasena del seed definida y API y Mailpit respondiendo."""
    if not os.environ.get(PASSWORD_VARIABLE):
        pytest.fail(f"Falta la variable de entorno {PASSWORD_VARIABLE}", pytrace=False)
    try:
        httpx.get(f"{API_URL}/health", timeout=5).raise_for_status()
    except httpx.HTTPError as error:
        pytest.fail(
            f"La API no responde en {API_URL}/health: {type(error).__name__}", pytrace=False
        )
    try:
        mailpit("/info")
    except OSError as error:
        pytest.fail(f"Mailpit no responde en {MAILPIT_API}: {type(error).__name__}", pytrace=False)


def _cleanup(flow: Flow) -> None:
    """Deja el entorno como estaba: turnos cancelados, pacientes desactivados, tramos originales."""
    for appointment_id in flow.appointments.values():
        detail = flow.call("receptionist", "GET", f"/appointments/{appointment_id}")
        if detail.status_code == 200 and detail.json()["status"] == "scheduled":
            flow.call(
                "receptionist",
                "POST",
                f"/appointments/{appointment_id}/cancel",
                json={"reason": "Limpieza del smoke test"},
            )
    for patient in flow.patients.values():
        flow.call("receptionist", "POST", f"/patients/{patient['id']}/deactivate")
    if flow.original_blocks is not None:
        flow.call(
            "admin",
            "PUT",
            f"/professionals/{flow.professional_id}/working-hours",
            json={"blocks": flow.original_blocks},
        )
    if not os.environ.get("EMAIL_REDIRECT_TO"):
        for patient in flow.patients.values():
            delete_messages(messages_to(patient["email"]))


@pytest.fixture(scope="module")
def flow() -> Iterator[Flow]:
    _require_environment()
    timezone = ZoneInfo(os.environ.get("CLINIC_TIMEZONE", "America/Argentina/Buenos_Aires"))
    with httpx.Client(base_url=API_URL, timeout=15) as client:
        state = Flow(client, timezone)
        try:
            yield state
        finally:
            _cleanup(state)


def wait_until(condition: Callable[[], bool], what: str) -> None:
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.5)
    pytest.fail(f"Tiempo agotado esperando: {what}", pytrace=False)


def free_slots(flow: Flow, professional_id: str) -> tuple[list[dict[str, Any]], list[datetime]]:
    response = flow.call(
        "receptionist",
        "GET",
        f"/professionals/{professional_id}/slots",
        params={"date": flow.tomorrow.isoformat()},
    )
    assert response.status_code == 200, f"franjas: {response.status_code}"
    rows: list[dict[str, Any]] = response.json()
    free = [datetime.fromisoformat(r["starts_at"]) for r in rows if r["status"] == "FREE"]
    return rows, free


def choose_professional_and_slots(flow: Flow) -> None:
    """Un profesional con franjas libres mañana; si nadie atiende, se le agrega un tramo (P-6)."""
    professionals = flow.call("receptionist", "GET", "/professionals").json()
    active = [p["id"] for p in professionals if p["active"]]
    assert active, "no hay profesionales activos"
    without_hours: str | None = None
    for professional_id in active:
        rows, free = free_slots(flow, professional_id)
        if len(free) >= SLOTS_NEEDED:
            flow.professional_id, flow.slots = professional_id, free[:SLOTS_NEEDED]
            return
        attends = any(row["status"] != "OUTSIDE_HOURS" for row in rows)
        if not attends and without_hours is None:
            without_hours = professional_id
    assert without_hours, "mañana ningun profesional tiene franjas libres suficientes"
    current = flow.call("admin", "GET", f"/professionals/{without_hours}/working-hours")
    blocks: list[dict[str, Any]] = current.json()["blocks"]
    added = {
        "weekday": flow.tomorrow.weekday(),
        "start_time": NEW_BLOCK[0],
        "end_time": NEW_BLOCK[1],
    }
    flow.professional_id = without_hours
    flow.original_blocks = blocks
    saved = flow.call(
        "admin",
        "PUT",
        f"/professionals/{without_hours}/working-hours",
        json={"blocks": [*blocks, added]},
    )
    assert saved.status_code == 200, f"agregar el tramo de mañana: {saved.status_code}"
    _, free = free_slots(flow, without_hours)
    assert len(free) >= SLOTS_NEEDED, "el tramo agregado no dejo franjas libres suficientes"
    flow.slots = free[:SLOTS_NEEDED]


def create_patient(flow: Flow, label: str) -> None:
    suffix = uuid.uuid4().hex[:10]
    body = {
        "first_name": f"Smoke{label}",
        "last_name": "Prueba",
        "document_number": f"SM{int(suffix, 16) % 10**10:010d}",
        "email": f"smoke-{suffix}@example.com",
    }
    response = flow.call("receptionist", "POST", "/patients", json=body)
    assert response.status_code == 201, f"crear paciente {label}: {response.status_code}"
    flow.patients[label] = {"id": response.json()["id"], "email": body["email"]}


def book(flow: Flow, label: str, slot_index: int, *, role: str = "receptionist") -> httpx.Response:
    return flow.call(
        role,
        "POST",
        "/appointments",
        json={
            "patient_id": flow.patients[label]["id"],
            "professional_id": flow.professional_id,
            "starts_at": flow.slots[slot_index].isoformat(),
        },
    )


def require_previous(flow: Flow, key: str, step: str) -> None:
    if key not in flow.appointments:
        pytest.fail(f"No se puede correr {step}: un paso anterior fallo (falta el turno {key})")


def test_step_1_each_seed_account_logs_in_and_me_returns_its_role(flow: Flow) -> None:
    for role in SEED_ACCOUNTS:
        me = flow.call(role, "GET", "/auth/me")

        assert me.status_code == 200
        assert me.json()["role"] == role


def test_step_2_booking_a_taken_slot_is_rejected_and_a_dentist_cannot_book(flow: Flow) -> None:
    choose_professional_and_slots(flow)
    create_patient(flow, "A")
    create_patient(flow, "B")

    first = book(flow, "A", 0)
    assert first.status_code == 201, first.text
    flow.appointments["A"] = first.json()["id"]

    taken = book(flow, "B", 0)
    assert taken.status_code == 409
    assert taken.json()["error"]["code"] == "SLOT_TAKEN"

    forbidden = book(flow, "B", 1, role="dentist")
    assert forbidden.status_code == 403


def test_step_3_the_confirmation_of_appointment_a_reaches_mailpit(flow: Flow) -> None:
    require_previous(flow, "A", "el paso 3")

    wait_until(
        lambda: flow.mail_count(CONFIRMATION, flow.when(0)) >= 1,
        "la confirmacion del turno A en Mailpit",
    )


def test_step_4_cancelling_appointment_a_frees_its_slot(flow: Flow) -> None:
    require_previous(flow, "A", "el paso 4")

    cancelled = flow.call(
        "receptionist",
        "POST",
        f"/appointments/{flow.appointments['A']}/cancel",
        json={"reason": "Cancelado por el smoke test"},
    )

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    _, free = free_slots(flow, flow.professional_id)
    assert flow.slots[0] in free


def test_step_5_appointment_b_is_booked_rescheduled_and_confirmed_again(flow: Flow) -> None:
    require_previous(flow, "A", "el paso 5")

    booked = book(flow, "B", 1)
    assert booked.status_code == 201, booked.text
    flow.appointments["B"] = booked.json()["id"]

    moved = flow.call(
        "receptionist",
        "POST",
        f"/appointments/{flow.appointments['B']}/reschedule",
        json={"starts_at": flow.slots[2].isoformat()},
    )

    assert moved.status_code == 200, moved.text
    wait_until(
        lambda: flow.mail_count(CONFIRMATION, flow.when(2)) >= 1,
        "la confirmacion del nuevo horario del turno B",
    )


def test_step_6_a_forced_pass_sends_one_reminder_for_b_and_a_second_adds_none(flow: Flow) -> None:
    require_previous(flow, "B", "el paso 6")
    before = {index: flow.mail_count(REMINDER, flow.when(index)) for index in range(SLOTS_NEEDED)}

    celery_app.send_task("enviar_recordatorios", kwargs={"forzar": True})

    wait_until(
        lambda: flow.mail_count(REMINDER, flow.when(2)) == before[2] + 1,
        "el recordatorio del turno B en Mailpit",
    )
    time.sleep(SETTLE_SECONDS)
    assert flow.mail_count(REMINDER, flow.when(2)) == before[2] + 1
    assert flow.mail_count(REMINDER, flow.when(0)) == before[0]  # A cancelado: sin recordatorio
    assert flow.mail_count(REMINDER, flow.when(1)) == before[1]  # horario anterior de B

    celery_app.send_task("enviar_recordatorios", kwargs={"forzar": True})
    time.sleep(SETTLE_SECONDS)

    assert flow.mail_count(REMINDER, flow.when(2)) == before[2] + 1


VERIFICATION = "Confirmá tu turno"
TOKEN_IN_LINK = re.compile(r"/turnos/confirmar#token=([\w-]+)")


def _verification_ids(mailbox: str) -> set[str]:
    return {m["ID"] for m in messages_to(mailbox) if m["Subject"].startswith(VERIFICATION)}


def test_step_7_an_online_booking_is_confirmed_from_the_email_link(flow: Flow) -> None:
    require_previous(flow, "B", "el paso 7")
    suffix = uuid.uuid4().hex[:10]
    document = f"SO{int(suffix, 16) % 10**10:010d}"
    typed_email = f"smoke-online-{suffix}@example.com"
    mailbox = os.environ.get("EMAIL_REDIRECT_TO") or typed_email
    known = _verification_ids(mailbox)
    public = httpx.Client(base_url=API_URL, timeout=15)

    listed = public.get("/public/professionals")
    assert listed.status_code == 200
    assert flow.professional_id in {p["id"] for p in listed.json()}
    booked = public.post(
        "/public/appointments",
        json={
            "professional_id": flow.professional_id,
            "starts_at": flow.slots[0].isoformat(),
            "document_number": document,
            "first_name": "SmokeOnline",
            "last_name": "Prueba",
            "email": typed_email,
        },
    )
    assert booked.status_code == 202, booked.text
    found = flow.call("receptionist", "GET", "/patients", params={"q": document}).json()["items"]
    assert len(found) == 1, "la reserva online debio crear la ficha"
    flow.patients["C"] = {"id": found[0]["id"], "email": typed_email}
    day = flow.tomorrow
    listing = flow.call(
        "receptionist",
        "GET",
        "/appointments",
        params={
            "professional_id": flow.professional_id,
            "from": datetime.combine(day, datetime.min.time(), flow.timezone).isoformat(),
            "to": datetime.combine(
                day + timedelta(days=1), datetime.min.time(), flow.timezone
            ).isoformat(),
        },
    ).json()
    pending = [a for a in listing if a["patient_id"] == found[0]["id"]]
    assert len(pending) == 1
    assert (pending[0]["origin"], pending[0]["pending_until"] is not None) == ("online", True)
    flow.appointments["C"] = pending[0]["id"]

    def new_message() -> bool:
        return bool(_verification_ids(mailbox) - known)

    wait_until(new_message, "el email de verificacion en Mailpit")
    [message_id] = _verification_ids(mailbox) - known
    body = mailpit(f"/message/{message_id}")["Text"]
    match = TOKEN_IN_LINK.search(body)
    assert match is not None, "el email no trae el enlace de confirmacion"

    confirmed = public.post("/public/appointment-confirmations", json={"token": match.group(1)})
    assert confirmed.status_code == 200, confirmed.text
    again = public.post("/public/appointment-confirmations", json={"token": match.group(1)})
    assert again.status_code == 410
    wait_until(
        lambda: flow.mail_count(CONFIRMATION, flow.when(0)) >= 1,
        "la confirmacion normal del turno online en Mailpit",
    )
    public.close()

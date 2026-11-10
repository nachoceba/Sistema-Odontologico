"""Fixtures de los tests de API: entorno valido y fabrica de clientes."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_user_repository
from app.core.config import get_settings
from app.core.security import hash_password
from app.domain.appointments import Appointment
from app.domain.auth import Role, UserAccount
from app.infrastructure.in_memory import InMemoryUserAccountRepository
from tests.unit.application.agenda_helpers import PROF_A, PROF_B, World
from tests.unit.domain.appointments.helpers import monday

API_ENV: dict[str, str] = {
    "DATABASE_URL": "postgresql+psycopg://odonto:odonto_dev@db-inexistente.invalid:5432/odonto",
    "REDIS_URL": "redis://redis-inexistente.invalid:6379/0",
    "JWT_SECRET_KEY": "k" * 48,
    "SMTP_HOST": "mailpit",
    "SMTP_PORT": "1025",
    "EMAIL_FROM": "turnos@consultorio.test",
    "CLINIC_TIMEZONE": "America/Argentina/Buenos_Aires",
    "CORS_ORIGINS": "http://localhost:5173",
}


@pytest.fixture(autouse=True)
def api_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name, value in API_ENV.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def make_client() -> Callable[[], tuple[FastAPI, TestClient]]:
    from app.main import create_app

    def build() -> tuple[FastAPI, TestClient]:
        app = create_app()
        return app, TestClient(app, raise_server_exceptions=False)

    return build


@pytest.fixture
def client(make_client: Callable[[], tuple[FastAPI, TestClient]]) -> TestClient:
    return make_client()[1]


# --- Autenticacion: repositorio en memoria sustituye al de PostgreSQL (design D-10) ---

AUTH_PASSWORD = "clave-ficticia-de-prueba"
PROFESSIONAL_A = "11111111-1111-4111-8111-111111111111"
PROFESSIONAL_B = "22222222-2222-4222-8222-222222222222"


def make_account(
    user_id: str,
    email: str,
    role: Role,
    *,
    active: bool = True,
    professional_id: str | None = None,
    full_name: str = "Usuario Demo",
) -> UserAccount:
    return UserAccount(
        id=user_id,
        email=email,
        full_name=full_name,
        password_hash=hash_password(AUTH_PASSWORD),
        role=role,
        active=active,
        professional_id=professional_id,
    )


@pytest.fixture(scope="session")
def seeded_accounts() -> list[UserAccount]:
    """Un usuario por rol, uno desactivado y un odontologo sin ficha (hash calculado una vez)."""
    return [
        make_account("u-admin", "admin@example.com", Role.ADMIN, full_name="Admin Demo"),
        make_account("u-rec", "recepcion@example.com", Role.RECEPTIONIST, full_name="Rec Demo"),
        make_account(
            "u-dra-a",
            "dra.a@example.com",
            Role.DENTIST,
            professional_id=PROFESSIONAL_A,
            full_name="Dra A",
        ),
        make_account("u-dr-sin-ficha", "sinficha@example.com", Role.DENTIST),
        make_account("u-baja", "baja@example.com", Role.RECEPTIONIST, active=False),
    ]


@pytest.fixture
def user_repo(seeded_accounts: list[UserAccount]) -> InMemoryUserAccountRepository:
    return InMemoryUserAccountRepository(seeded_accounts)


@pytest.fixture
def auth_app(
    make_client: Callable[[], tuple[FastAPI, TestClient]],
    user_repo: InMemoryUserAccountRepository,
) -> tuple[FastAPI, TestClient]:
    app, test_client = make_client()
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    return app, test_client


@pytest.fixture
def auth_client(auth_app: tuple[FastAPI, TestClient]) -> TestClient:
    return auth_app[1]


def login_token(test_client: TestClient, email: str) -> str:
    response = test_client.post(
        "/api/v1/auth/login", json={"email": email, "password": AUTH_PASSWORD}
    )
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- Agenda: casos de uso sobre repositorios en memoria (C-08, design D-10) ---


@dataclass
class AgendaScene:
    """Mundo en memoria con cuatro turnos conocidos: dos de la Dra. A y dos del Dr. B."""

    world: World
    started_a: str
    future_a: str
    started_b: str
    future_b: str

    def snapshot(self) -> list[Appointment]:
        return self.world.everything(PROF_A) + self.world.everything(PROF_B)


@pytest.fixture
def agenda(auth_app: tuple[FastAPI, TestClient]) -> AgendaScene:
    """Dependencias de agenda en memoria; reloj en lunes 10:10 y sin anticipacion minima."""
    from app.api.dependencies import get_agenda_deps

    world = World(now=monday(10, 10), min_notice_hours=0)
    scene = AgendaScene(
        world=world,
        started_a=world.seed(monday(10), patient_id="pac-1", professional_id=PROF_A).id,
        future_a=world.seed(monday(15), patient_id="pac-2", professional_id=PROF_A).id,
        started_b=world.seed(monday(10), patient_id="pac-2", professional_id=PROF_B).id,
        future_b=world.seed(monday(12), patient_id="pac-1", professional_id=PROF_B).id,
    )
    auth_app[0].dependency_overrides[get_agenda_deps] = world.deps
    return scene


# --- Profesionales, horarios y licencias: casos de uso en memoria (C-07) ---


@dataclass
class ScheduleScene:
    """Mundo en memoria con una licencia por profesional y el estado completo comparable."""

    world: World
    time_off_a: str
    time_off_b: str

    def snapshot(self) -> tuple[object, ...]:
        world = self.world
        return (
            dict(world.accounts.professionals),
            world.working_hours.list_for_professional(PROF_A),
            world.working_hours.list_for_professional(PROF_B),
            world.time_off.list_for_professional(PROF_A),
            world.time_off.list_for_professional(PROF_B),
            world.everything(PROF_A),
            world.everything(PROF_B),
        )


@pytest.fixture
def schedule(auth_app: tuple[FastAPI, TestClient]) -> ScheduleScene:
    """Dependencias de horarios en memoria; reloj fijo el sabado 3 de octubre de 2026."""
    from datetime import date

    from app.api.dependencies import get_agenda_deps, get_schedule_deps

    world = World()
    scene = ScheduleScene(
        world=world,
        time_off_a=world.time_off.add(
            PROF_A, date(2026, 10, 12), date(2026, 10, 16), "Congreso"
        ).id,
        time_off_b=world.time_off.add(PROF_B, date(2026, 10, 19), date(2026, 10, 20)).id,
    )
    auth_app[0].dependency_overrides[get_schedule_deps] = world.schedule_deps
    auth_app[0].dependency_overrides[get_agenda_deps] = world.deps
    return scene


# --- Pacientes: casos de uso en memoria (C-06) ---


@dataclass
class PatientScene:
    """Mundo en memoria con Juan (turno agendado), Ana (inactiva) y Laura (sin turnos)."""

    world: World
    laura_id: str
    appointment_id: str

    def snapshot(self) -> tuple[object, ...]:
        world = self.world
        return (
            world.patients.search(text="", include_inactive=True, limit=1000),
            world.everything(PROF_A),
            world.everything(PROF_B),
            world.notifications.snapshot(),
        )


@pytest.fixture
def patients_scene(auth_app: tuple[FastAPI, TestClient]) -> PatientScene:
    """Dependencias de pacientes y agenda en memoria; reloj en el sabado 3 de octubre."""
    from app.api.dependencies import get_agenda_deps, get_patient_deps
    from app.domain.patients.types import NewPatient

    world = World()
    world.set_patient_active("pac-2", False)
    laura = world.patients.add(NewPatient("Laura", "Ruiz", "40222333", "laura@example.com"))
    scene = PatientScene(
        world=world,
        laura_id=laura.id,
        appointment_id=world.seed(monday(10), patient_id="pac-1", professional_id=PROF_A).id,
    )
    auth_app[0].dependency_overrides[get_patient_deps] = world.patient_deps
    auth_app[0].dependency_overrides[get_agenda_deps] = world.deps
    return scene


# --- Tratamientos: casos de uso en memoria (C-17) ---


@pytest.fixture
def treatments_world(auth_app: tuple[FastAPI, TestClient]) -> World:
    """Catalogo en memoria con "Consulta" y "Limpieza dental"; los dos profesionales los ofrecen."""
    from app.api.dependencies import get_agenda_deps, get_treatment_deps

    world = World()
    auth_app[0].dependency_overrides[get_treatment_deps] = world.treatment_deps
    auth_app[0].dependency_overrides[get_agenda_deps] = world.deps
    return world

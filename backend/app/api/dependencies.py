"""Dependencias de FastAPI: repositorio de cuentas y configuracion del token."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.appointments import AgendaDeps
from app.application.auth import TokenConfig, resolve_principal
from app.application.professionals import ScheduleDeps
from app.core.config import get_settings
from app.domain.auth import (
    ForbiddenError,
    NotAuthenticatedError,
    Principal,
    Role,
    UserAccountRepository,
    can_access_professional,
)
from app.infrastructure.db.repositories import (
    SqlAlchemyAgendaUnitOfWork,
    SqlAlchemyAppointmentRepository,
    SqlAlchemyClinicSettingsRepository,
    SqlAlchemyPatientRepository,
    SqlAlchemyProfessionalRepository,
    SqlAlchemyTimeOffRepository,
    SqlAlchemyUserAccountRepository,
    SqlAlchemyWorkingHoursRepository,
)
from app.infrastructure.db.session import get_session_factory
from app.infrastructure.notifications import NoOpNotificationDispatcher


def get_user_repository() -> UserAccountRepository:
    """Fabrica sobreescribible en los tests (``app.dependency_overrides``, design D-10)."""
    return SqlAlchemyUserAccountRepository(get_session_factory())


def get_token_config() -> TokenConfig:
    return TokenConfig.from_settings(get_settings())


def get_clock() -> Callable[[], datetime]:
    """Reloj del sistema; los tests lo sobreescriben con uno fijo (design D-4)."""
    return lambda: datetime.now(UTC)


def get_agenda_deps(clock: Annotated[Callable[[], datetime], Depends(get_clock)]) -> AgendaDeps:
    """Casos de uso de agenda sobre PostgreSQL; sobreescribible en los tests (design D-10)."""
    sessions = get_session_factory()
    return AgendaDeps(
        appointments=SqlAlchemyAppointmentRepository(sessions),
        patients=SqlAlchemyPatientRepository(sessions),
        professionals=SqlAlchemyProfessionalRepository(sessions),
        working_hours=SqlAlchemyWorkingHoursRepository(sessions),
        time_off=SqlAlchemyTimeOffRepository(sessions),
        settings=SqlAlchemyClinicSettingsRepository(sessions),
        unit_of_work=lambda: SqlAlchemyAgendaUnitOfWork(sessions),
        dispatcher=NoOpNotificationDispatcher(),
        clock=clock,
    )


def get_schedule_deps(
    clock: Annotated[Callable[[], datetime], Depends(get_clock)],
) -> ScheduleDeps:
    """Casos de uso de profesionales y horarios sobre PostgreSQL; sobreescribible en tests."""
    sessions = get_session_factory()
    return ScheduleDeps(
        professionals=SqlAlchemyProfessionalRepository(sessions),
        working_hours=SqlAlchemyWorkingHoursRepository(sessions),
        time_off=SqlAlchemyTimeOffRepository(sessions),
        appointments=SqlAlchemyAppointmentRepository(sessions),
        settings=SqlAlchemyClinicSettingsRepository(sessions),
        clock=clock,
    )


UserRepository = Annotated[UserAccountRepository, Depends(get_user_repository)]
TokenSettings = Annotated[TokenConfig, Depends(get_token_config)]
Agenda = Annotated[AgendaDeps, Depends(get_agenda_deps)]
Schedule = Annotated[ScheduleDeps, Depends(get_schedule_deps)]


# auto_error=False: sin encabezado la dependencia devuelve None y respondemos con el cuerpo
# uniforme de error-model en lugar del ``{"detail": ...}`` de FastAPI (design D-4).
_bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    repo: UserRepository,
    config: TokenSettings,
) -> Principal:
    """El principal de la request; recarga la cuenta en cada llamada (design D-5)."""
    if credentials is None:
        raise NotAuthenticatedError
    return resolve_principal(credentials.credentials, repo, config)


CurrentUser = Annotated[Principal, Depends(current_user)]


def require_role(*roles: Role) -> Callable[[Principal], Principal]:
    """Dependencia que deja pasar solo a los roles dados (401 antes que 403, design D-6)."""
    allowed = frozenset(roles)

    def check(principal: CurrentUser) -> Principal:
        if principal.role not in allowed:
            raise ForbiddenError
        return principal

    return check


def require_professional_access(professional_id: str, principal: CurrentUser) -> Principal:
    """Aplica ``can_access_professional`` al parametro de ruta ``professional_id`` (D-8)."""
    if not can_access_professional(principal, professional_id):
        raise ForbiddenError
    return principal

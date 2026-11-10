"""Endpoints publicos de la reserva online, sin sesion (spec public-booking-api, C-15).

Son la unica excepcion a la regla dura 4 (design D-10): no exigen JWT y por eso se defienden con
un limite de pedidos por IP (``request.client.host``, nunca ``X-Forwarded-For``), un campo
trampa, esquemas estrictos y respuestas minimas. Ninguna respuesta devuelve email, telefono,
documento ni el nombre completo de una ficha, y los errores 422 no repiten lo enviado.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field

from app.api.appointments import EntityId
from app.api.dependencies import PublicBooking, RateLimiterDep
from app.api.patients import Document, Name, Phone
from app.api.validators import Email, strip_text
from app.application import public_booking as use_cases
from app.domain.public_booking.errors import BookingRejectedError, TooManyRequestsError

router = APIRouter(prefix="/public", tags=["public"])

READ_LIMIT = (60, 60)  # lecturas: 60 por minuto
BOOK_LIMIT = (5, 3600)  # reservas: 5 por hora
CONFIRM_LIMIT = (10, 3600)  # confirmaciones: 10 por hora


def rate_limited(group: str, limit: int, window_seconds: int) -> Callable[..., None]:
    """Dependencia que cuenta el pedido antes de validar el cuerpo (429 antes que 422)."""

    def check(request: Request, limiter: RateLimiterDep) -> None:
        client = request.client.host if request.client is not None else "unknown"
        decision = limiter.hit(group, client, limit=limit, window_seconds=window_seconds)
        if not decision.allowed:
            raise TooManyRequestsError(decision.retry_after)

    return check


_read_limit = Depends(rate_limited("read", *READ_LIMIT))
_book_limit = Depends(rate_limited("book", *BOOK_LIMIT))
_confirm_limit = Depends(rate_limited("confirm", *CONFIRM_LIMIT))

Token = Annotated[str, BeforeValidator(strip_text), Field(min_length=1, max_length=128)]


class ProfessionalOut(BaseModel):
    id: str
    display_name: str


class PublicSlotOut(BaseModel):
    starts_at: datetime
    ends_at: datetime


class BookingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    professional_id: EntityId
    starts_at: AwareDatetime
    document_number: Document
    first_name: Name
    last_name: Name
    email: Email
    phone: Phone | None = None
    website: Annotated[str, Field(max_length=500)] = ""  # campo trampa: un humano lo deja vacio


class BookingOut(BaseModel):
    starts_at: datetime
    ends_at: datetime
    professional_display_name: str
    confirm_before: datetime


class ConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: Token


class ConfirmationOut(BaseModel):
    starts_at: datetime
    ends_at: datetime
    professional_display_name: str


@router.get("/professionals", dependencies=[_read_limit])
def professionals(deps: PublicBooking) -> list[ProfessionalOut]:
    return [
        ProfessionalOut(id=p.id, display_name=p.display_name)
        for p in use_cases.list_public_professionals(deps)
    ]


@router.get("/professionals/{professional_id}/slots", dependencies=[_read_limit])
def slots(
    professional_id: str,
    deps: PublicBooking,
    day: Annotated[date, Query(alias="date")],
) -> list[PublicSlotOut]:
    return [
        PublicSlotOut(starts_at=s.starts_at.astimezone(UTC), ends_at=s.ends_at.astimezone(UTC))
        for s in use_cases.public_day_slots(deps, professional_id, day)
    ]


@router.post("/appointments", status_code=202, dependencies=[_book_limit])
def book(body: BookingRequest, deps: PublicBooking) -> BookingOut:
    if body.website:
        raise BookingRejectedError
    booked = use_cases.book_online(
        deps,
        professional_id=body.professional_id,
        starts_at=body.starts_at.astimezone(UTC),
        document_number=body.document_number,
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
    )
    return BookingOut(
        starts_at=booked.starts_at.astimezone(UTC),
        ends_at=booked.ends_at.astimezone(UTC),
        professional_display_name=booked.professional_display_name,
        confirm_before=booked.confirm_before.astimezone(UTC),
    )


@router.post("/appointment-confirmations", dependencies=[_confirm_limit])
def confirm(body: ConfirmationRequest, deps: PublicBooking) -> ConfirmationOut:
    confirmed = use_cases.confirm_online_booking(deps, body.token)
    return ConfirmationOut(
        starts_at=confirmed.starts_at.astimezone(UTC),
        ends_at=confirmed.ends_at.astimezone(UTC),
        professional_display_name=confirmed.professional_display_name,
    )

"""Toma simultanea de una notificacion contra PostgreSQL real (spec notification-registration).

La primera sesion toma la fila ``pending`` y no termina su transaccion; la segunda no obtiene
nada y no espera (``FOR UPDATE SKIP LOCKED``, design D-3). Las esperas tienen limite
(``lock_timeout`` y ``join`` con timeout) para que un fallo no cuelgue la suite.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.appointments import Notification
from app.infrastructure.db.repositories import (
    SqlAlchemyAgendaUnitOfWork,
    SqlAlchemyNotificationRepository,
)
from tests.integration.db.helpers import at, insert_appointment, make_world

JOIN_SECONDS = 20.0
LOCK_TIMEOUT = "-c lock_timeout=10000"
FAST_SECONDS = 5.0


@pytest.fixture
def sessions(engine: Engine) -> Iterator[sessionmaker[Session]]:
    limited = create_engine(engine.url, connect_args={"options": LOCK_TIMEOUT})
    yield sessionmaker(limited, expire_on_commit=False)
    limited.dispose()


@pytest.fixture
def pending_id(engine: Engine, sessions: sessionmaker[Session]) -> str:
    with engine.begin() as connection:
        world = make_world(connection)
        appointment = insert_appointment(connection, world, at(10), at(10, 30))
    saved = SqlAlchemyNotificationRepository(sessions).add_pending_confirmation(
        str(appointment), at(10)
    )
    assert saved is not None
    return saved.id


def test_a_second_session_gets_nothing_without_waiting_while_the_first_holds_the_row(
    sessions: sessionmaker[Session], pending_id: str
) -> None:
    results: list[Notification | None] = []
    elapsed: list[float] = []

    def second_take() -> None:
        started = time.monotonic()
        with SqlAlchemyAgendaUnitOfWork(sessions) as other:
            results.append(other.notifications.claim_pending(pending_id))
        elapsed.append(time.monotonic() - started)

    with SqlAlchemyAgendaUnitOfWork(sessions) as first:
        assert first.notifications.claim_pending(pending_id) is not None
        thread = threading.Thread(target=second_take, daemon=True)
        thread.start()
        thread.join(JOIN_SECONDS)
        assert not thread.is_alive(), "la segunda toma quedo esperando el lock"
        assert first.notifications.mark_sent(pending_id, datetime(2026, 11, 6, 12, tzinfo=UTC))

    assert results == [None]
    assert elapsed[0] < FAST_SECONDS


def test_after_the_first_commits_the_row_is_sent_and_cannot_be_taken_again(
    sessions: sessionmaker[Session], pending_id: str
) -> None:
    with SqlAlchemyAgendaUnitOfWork(sessions) as first:
        assert first.notifications.claim_pending(pending_id) is not None
        first.notifications.mark_sent(pending_id, datetime(2026, 11, 6, 12, tzinfo=UTC))

    with SqlAlchemyAgendaUnitOfWork(sessions) as second:
        assert second.notifications.claim_pending(pending_id) is None


def test_after_the_first_rolls_back_the_row_can_be_taken_again(
    sessions: sessionmaker[Session], pending_id: str
) -> None:
    with pytest.raises(RuntimeError), SqlAlchemyAgendaUnitOfWork(sessions) as first:
        first.notifications.claim_pending(pending_id)
        raise RuntimeError

    with SqlAlchemyAgendaUnitOfWork(sessions) as second:
        assert second.notifications.claim_pending(pending_id) is not None

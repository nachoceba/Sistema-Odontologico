"""Alcance de sesion de los repositorios SQL (design D-2).

Por defecto cada operacion abre su propia transaccion (DD-36). Dentro de una unidad de trabajo
los repositorios comparten una sesion: no confirman por su cuenta, solo hacen ``flush``; el que
confirma o revierte es la unidad, para que turno y notificaciones sean todo o nada.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session, sessionmaker


class SessionScope:
    """De donde sacan la sesion las operaciones de un repositorio."""

    def __init__(
        self,
        session_factory: sessionmaker[Session] | None = None,
        *,
        shared: Session | None = None,
    ) -> None:
        if (session_factory is None) == (shared is None):
            raise ValueError("indicar una fabrica de sesiones o una sesion compartida")
        self._factory = session_factory
        self._shared = shared

    @contextmanager
    def write(self) -> Iterator[Session]:
        """Transaccion propia (confirma al salir) o la sesion compartida (no confirma)."""
        if self._shared is not None:
            yield self._shared
        else:
            assert self._factory is not None
            with self._factory.begin() as session:
                yield session

    @contextmanager
    def read(self) -> Iterator[Session]:
        """Sesion de solo lectura propia o la compartida (ve las escrituras sin confirmar)."""
        if self._shared is not None:
            yield self._shared
        else:
            assert self._factory is not None
            with self._factory() as session:
                yield session

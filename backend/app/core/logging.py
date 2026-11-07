"""Registro de accesos sin la parte de consulta de la direccion (spec access-logging, DD-77).

La busqueda de pacientes viaja como ``?q=...`` y uvicorn escribe la direccion completa en cada
linea de acceso. ``AccessLogQueryFilter`` reescribe el argumento de la ruta del logger
``uvicorn.access`` y deja solo metodo, ruta y codigo de respuesta (DD-77, RN-PR-01). Si uvicorn
cambia el formato de los argumentos, el registro pasa sin tocar y el test del formato real falla.
"""

from __future__ import annotations

import logging

ACCESS_LOGGER_NAME = "uvicorn.access"
_PATH_ARG_INDEX = 2  # uvicorn: (cliente, metodo, ruta_con_consulta, version_http, codigo)
_MIN_ACCESS_ARGS = 5


class AccessLogQueryFilter(logging.Filter):
    """Quita desde ``?`` de la ruta en los registros de ``uvicorn.access``."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if record.name != ACCESS_LOGGER_NAME or not isinstance(args, tuple):
            return True
        if len(args) < _MIN_ACCESS_ARGS:
            return True
        path = args[_PATH_ARG_INDEX]
        if isinstance(path, str):
            without_query = path.partition("?")[0]
            record.args = (*args[:_PATH_ARG_INDEX], without_query, *args[_PATH_ARG_INDEX + 1 :])
        return True


def install_access_log_filter() -> None:
    """Instala el filtro una sola vez en el logger de accesos de uvicorn."""
    access_logger = logging.getLogger(ACCESS_LOGGER_NAME)
    if not any(isinstance(f, AccessLogQueryFilter) for f in access_logger.filters):
        access_logger.addFilter(AccessLogQueryFilter())

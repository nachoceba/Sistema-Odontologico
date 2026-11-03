"""Fixtures de integracion. Estos tests solo corren con ``pytest -m integration``.

Los marca como ``integration`` automaticamente; C-02 agrega aca la sesion de base real.
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/integration" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.integration)

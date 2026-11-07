"""Los tests de ``tests/smoke`` solo corren con ``pytest -m smoke`` (spec end-to-end-smoke)."""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/smoke" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.smoke)

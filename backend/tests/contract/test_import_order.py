"""Detecta ciclos de imports segun el orden de entrada (design D-2)."""

from __future__ import annotations

import subprocess
import sys

import pytest

PACKAGES = [
    "app.domain.schedules",
    "app.domain.appointments",
    "app.domain.patients",
    "app.domain.settings",
    "app.infrastructure.in_memory",
    "app.infrastructure.db.models",
    "app.infrastructure.db.repositories",
]


@pytest.mark.parametrize("package", PACKAGES)
def test_package_imports_first_in_fresh_interpreter(package: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", f"import {package}"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

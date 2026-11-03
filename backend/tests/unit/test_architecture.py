"""Regla dura 2: domain/ son funciones puras, sin imports de frameworks ni infraestructura."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

DOMAIN_DIR = Path(__file__).resolve().parents[2] / "app" / "domain"
FORBIDDEN = (
    "fastapi",
    "starlette",
    "sqlalchemy",
    "psycopg",
    "alembic",
    "celery",
    "redis",
    "app.infrastructure",
    "app.api",
)


def forbidden_imports(source: str) -> list[str]:
    """Modulos prohibidos importados por un codigo fuente (incluye imports dentro de funciones)."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        found += [
            name
            for name in names
            if any(name == root or name.startswith(root + ".") for root in FORBIDDEN)
        ]
    return found


def test_the_checker_detects_forbidden_imports() -> None:
    assert forbidden_imports("import sqlalchemy.orm\nfrom fastapi import APIRouter") == [
        "sqlalchemy.orm",
        "fastapi",
    ]
    assert forbidden_imports("def f():\n    from app.infrastructure.db import models") == [
        "app.infrastructure.db"
    ]


def test_the_checker_accepts_pure_imports() -> None:
    assert forbidden_imports("from datetime import datetime\nfrom app.core.errors import X") == []


@pytest.mark.parametrize(
    "path", sorted(DOMAIN_DIR.rglob("*.py")), ids=lambda p: p.relative_to(DOMAIN_DIR).as_posix()
)
def test_domain_module_imports_no_framework_or_infrastructure(path: Path) -> None:
    assert forbidden_imports(path.read_text(encoding="utf-8")) == []

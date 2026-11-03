"""Los modelos de la aplicacion y la migracion describen el mismo esquema (design D-8).

``compare_metadata`` de Alembic compara tablas, columnas, tipos, indices, UNIQUE y claves
foraneas, pero NO compara CHECK ni EXCLUDE ni valores por defecto del servidor. Por eso se
agrega una segunda comprobacion: todo constraint e indice con nombre de los modelos existe en
la base con ese nombre, y la base no tiene constraints propios que los modelos ignoren.
"""

from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, text
from sqlalchemy.dialects.postgresql import ENUM, ExcludeConstraint

from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base


def test_alembic_finds_no_differences_between_models_and_database(engine: Engine) -> None:
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, Base.metadata)
    assert differences == []


def test_every_named_constraint_and_index_of_the_models_exists_in_the_database(
    engine: Engine,
) -> None:
    expected_constraints: set[str] = set()
    expected_indexes: set[str] = set()
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            assert constraint.name, f"constraint sin nombre en {table.name}"
            expected_constraints.add(str(constraint.name))
        expected_indexes.update(str(index.name) for index in table.indexes)
    assert any(
        isinstance(c, ExcludeConstraint)
        for t in Base.metadata.tables.values()
        for c in t.constraints
    )

    with engine.connect() as connection:
        found_constraints = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT conname FROM pg_constraint WHERE connamespace = 'public'::regnamespace"
                )
            )
            if not row[0].startswith("alembic_version")
        }
        found_indexes = {
            row[0]
            for row in connection.execute(
                text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
            )
            if not row[0].startswith("alembic_version")
        }
    assert expected_constraints <= found_constraints
    assert found_constraints == expected_constraints
    # Los indices de la base incluyen los que respaldan PK, UNIQUE y EXCLUDE.
    assert expected_indexes <= found_indexes
    assert found_indexes - expected_indexes == (found_constraints & found_indexes)


def test_models_store_enum_values_not_names() -> None:
    status = Base.metadata.tables["appointments"].c.status.type
    assert isinstance(status, ENUM)
    assert list(status.enums) == ["scheduled", "cancelled", "completed", "no_show"]

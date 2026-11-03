"""Base declarativa y convencion de nombres de constraints (design D-1).

Todo constraint e indice lleva un nombre predecible (``pk_``, ``fk_``, ``uq_``, ``ck_``,
``ix_``; la exclusion usa ``ex_`` escrito a mano) para que la migracion y el ``downgrade``
puedan nombrarlos. Los CHECK se declaran con un nombre corto: la convencion le antepone
``ck_<tabla>_``.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

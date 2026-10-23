"""Generate the Postgres DDL from the SQLAlchemy models, so there is one source.

    python -m app.migrations.generate_ddl > migrations/001_extract_reference.sql
"""

from __future__ import annotations

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import Base

HEADER = """\
-- Generated from app/models.py by app.migrations.generate_ddl. Do not edit.
-- Provisional Postgres tables for the ACE extract reference loads. Names are
-- local to this app; engineering will map them onto the CHB schema.
-- Local development uses SQLAlchemy create_all() against SQLite.
"""


def render() -> str:
    dialect = postgresql.dialect()
    parts = [HEADER]
    for table in Base.metadata.sorted_tables:
        parts.append(str(CreateTable(table, if_not_exists=True).compile(dialect=dialect)).strip() + ";\n")
        for index in sorted(table.indexes, key=lambda i: i.name or ""):
            parts.append(str(CreateIndex(index, if_not_exists=True).compile(dialect=dialect)).strip() + ";\n")
    return "\n".join(parts)


if __name__ == "__main__":
    print(render(), end="")

"""Provisional Postgres tables for engineering to map onto the CHB schema.

The DDL is generated from app/models.py (see generate_ddl.py) so there is one
source. Local development uses SQLAlchemy create_all() against SQLite. Do not
run this script on SQLite.
"""

from app.migrations.generate_ddl import render

REVISION = 'add_extract_tables'
DOWN_REVISION = None

POSTGRES_UPGRADE = render()

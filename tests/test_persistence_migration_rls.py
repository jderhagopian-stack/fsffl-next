from __future__ import annotations

import re
from pathlib import Path


MIGRATIONS = Path("db/migrations")
_CREATE_TABLE = re.compile(
    r"create\s+table(?:\s+if\s+not\s+exists)?\s+fsffl\.([a-zA-Z0-9_]+)",
    re.IGNORECASE,
)
_ENABLE_RLS = re.compile(
    r"alter\s+table\s+fsffl\.([a-zA-Z0-9_]+)\s+enable\s+row\s+level\s+security",
    re.IGNORECASE,
)


def test_every_private_fsffl_table_has_row_level_security_migration() -> None:
    created: set[str] = set()
    protected: set[str] = set()

    for migration in sorted(MIGRATIONS.glob("*.sql")):
        source = migration.read_text(encoding="utf-8")
        created.update(_CREATE_TABLE.findall(source))
        protected.update(_ENABLE_RLS.findall(source))

    assert created
    assert created <= protected, (
        "private fsffl tables missing row-level-security coverage: "
        f"{sorted(created - protected)}"
    )

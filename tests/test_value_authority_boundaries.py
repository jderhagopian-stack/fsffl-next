from __future__ import annotations

import ast
from pathlib import Path


VALUE_ROOT = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "value"
ALLOWED_FSFFL_DEPENDENCIES = {"fsffl.value", "fsffl.state", "fsffl.forecast"}


def test_value_package_only_depends_on_upstream_fsffl_layers() -> None:
    violations: list[str] = []

    for path in sorted(VALUE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None and node.level == 0:
                names.append(node.module)

            for name in names:
                if not name.startswith("fsffl."):
                    continue
                parts = name.split(".")
                dependency = ".".join(parts[:2])
                if dependency not in ALLOWED_FSFFL_DEPENDENCIES:
                    relative = path.relative_to(VALUE_ROOT.parent.parent)
                    violations.append(f"{relative}: {name}")

    assert violations == [], (
        "NEXT-3 Value may depend only on State, Forecast, and Value itself; "
        "downstream authority imports found: " + ", ".join(violations)
    )

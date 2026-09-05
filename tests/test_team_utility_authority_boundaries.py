from __future__ import annotations

import ast
from pathlib import Path


TEAM_UTILITY_ROOT = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "team_utility"
ALLOWED_FSFFL_DEPENDENCIES = {
    "fsffl.team_utility",
    "fsffl.state",
    "fsffl.forecast",
    "fsffl.value",
}


def test_team_utility_depends_only_on_authoritative_upstream_layers() -> None:
    violations: list[str] = []

    for path in sorted(TEAM_UTILITY_ROOT.rglob("*.py")):
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
                dependency = ".".join(name.split(".")[:2])
                if dependency not in ALLOWED_FSFFL_DEPENDENCIES:
                    relative = path.relative_to(TEAM_UTILITY_ROOT.parent.parent)
                    violations.append(f"{relative}: {name}")

    assert violations == [], (
        "NEXT-4 Team Utility may consume only State, Forecast, Value, and its own "
        "authority; downstream Search/Trade/Analytics/Presentation imports found: "
        + ", ".join(violations)
    )

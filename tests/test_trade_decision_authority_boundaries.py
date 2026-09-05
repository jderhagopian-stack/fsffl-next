from __future__ import annotations

import ast
from pathlib import Path


TRADE_DECISION_ROOT = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "trade_decision"
ALLOWED_FSFFL_DEPENDENCIES = {
    "fsffl.trade_decision",
    "fsffl.state",
    "fsffl.team_utility",
    "fsffl.value",
}


def test_trade_decision_depends_only_on_authoritative_upstream_layers() -> None:
    violations: list[str] = []

    for path in sorted(TRADE_DECISION_ROOT.rglob("*.py")):
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
                    relative = path.relative_to(TRADE_DECISION_ROOT.parent.parent)
                    violations.append(f"{relative}: {name}")

    assert violations == [], (
        "NEXT-5 Trade Decision may consume only State, Value, Team Utility, and its "
        "own authority; downstream Search/Analytics/Presentation imports found: "
        + ", ".join(violations)
    )

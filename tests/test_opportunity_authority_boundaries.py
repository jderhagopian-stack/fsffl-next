from __future__ import annotations

import ast
from pathlib import Path


OPPORTUNITY_ROOT = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "opportunity"
ALLOWED_FSFFL_DEPENDENCIES = {
    "fsffl.opportunity",
    "fsffl.state",
    "fsffl.forecast",
    "fsffl.value",
    "fsffl.team_utility",
    "fsffl.trade_decision",
}


def test_opportunity_depends_only_on_authoritative_upstream_layers() -> None:
    violations: list[str] = []

    for path in sorted(OPPORTUNITY_ROOT.rglob("*.py")):
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
                    relative = path.relative_to(OPPORTUNITY_ROOT.parent.parent)
                    violations.append(f"{relative}: {name}")

    assert violations == [], (
        "NEXT-6 Opportunity may consume only authoritative upstream layers and its own "
        "search authority; downstream Analytics/Presentation imports found: "
        + ", ".join(violations)
    )

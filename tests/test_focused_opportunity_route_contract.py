from pathlib import Path

ROUTE = Path("src/fsffl/product/focused_opportunity_routes.py")
SEARCH = Path("src/fsffl/product/focused_opportunity_search.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_focused_route_preserves_search_vs_decision_authority() -> None:
    route = _read(ROUTE)
    search = _read(SEARCH)
    assert "posture_payload" in route
    assert "build_trade_spotlights(returned)" in route
    assert "acceptance_probability" not in route
    assert "apply_search_posture" in search
    assert "resolve_search_posture" in search
    assert "Value and Decision authority are unchanged" in search

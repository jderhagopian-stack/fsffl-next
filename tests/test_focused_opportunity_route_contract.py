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


def test_focused_route_spends_decision_budget_only_after_intent_admission() -> None:
    route = _read(ROUTE)

    assert "workspace_builder(runtime, bilateral_evaluation_limit=0)" in route
    assert "evaluation_limit=DEFAULT_PRELIMINARY_DECISION_BUDGET" in route
    assert "candidate_builder(runtime, browser, cardinal) if not intent else None" in route
    assert 'getattr(focused, "diagnostics", {})' in route

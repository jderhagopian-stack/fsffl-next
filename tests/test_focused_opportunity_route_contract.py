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
    assert "canonical = None" in route
    assert 'getattr(focused, "diagnostics", {})' in route
    assert "strategic_posture=effective" in search
    assert '"effective_posture": effective.value' in search


def test_focused_route_exposes_search_exhaustion_without_weakening_budget() -> None:
    route = _read(ROUTE)
    for token in (
        '"focus_outcome"',
        '"no_counterparty_admitted"',
        '"no_target_admitted"',
        '"no_package_neighborhood"',
        '"no_path_family_after_economic_screen"',
        '"no_final_path_after_screening"',
        '"packages_economic_incomplete"',
        '"preliminary_decision_errors"',
        '"counterparty_dominated_count"',
        '"focal_dominated_count"',
        '"changed_state_simulation_calls"',
    ):
        assert token in route
    assert "DEFAULT_PRELIMINARY_DECISION_BUDGET" in route
    assert "acceptance_probability" not in route

from pathlib import Path


POSTURE_UI = Path("src/fsffl/product/static/opportunity_posture_ui.js")
POSTURE_SERVER = Path("src/fsffl/product/opportunity_posture.py")
WORKSPACE = Path("src/fsffl/product/opportunity_workspace.py")
SEARCH = Path("src/fsffl/product/opportunity_search.py")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_market_exposes_consumer_owner_intent_control() -> None:
    source = _source(POSTURE_UI)

    assert "What are you trying to do?" in source
    assert "Best for my team" in source
    assert "Build for a Championship" in source
    assert "Balanced Trade" in source
    assert "Get Younger" in source
    assert "Rebuild" in source
    assert "Market focus" in source
    assert "How this changes suggestions" in source
    assert "deck.prepend(control)" in source


def test_owner_intent_uses_server_published_posture_ordering_not_ui_score() -> None:
    source = _source(POSTURE_UI)

    assert "posture_views" in source
    assert "candidate_indices" in source
    assert "applyServerPostureView" in source
    assert "fsffl.tradeFinderPosture" in source
    assert "localStorage" in source
    assert "This choice only changes the server-published Search ordering" in source


def test_default_market_focus_resolves_from_calculated_competitive_state() -> None:
    source = _source(POSTURE_SERVER)

    assert "OwnerStrategicPosture.DEFAULT_CALCULATED" in source
    assert "CalculatedCompetitiveState.CONTENDER: OwnerStrategicPosture.WIN_NOW" in source
    assert "CalculatedCompetitiveState.COMPETITIVE: OwnerStrategicPosture.BALANCED" in source
    assert "CalculatedCompetitiveState.DEVELOPING: OwnerStrategicPosture.RETOOL" in source
    assert "CalculatedCompetitiveState.REBUILDING: OwnerStrategicPosture.REBUILD" in source


def test_workspace_publishes_posture_views_over_one_canonical_candidate_collection() -> None:
    source = _source(WORKSPACE)

    assert '"posture_views"' in source
    assert '"candidate_indices"' in source
    assert "apply_search_posture(rows, effective)" in source
    assert '"owner_strategic_posture_is_search_lens_only": True' in source


def test_draft_capital_focus_waits_for_real_pick_target_search_support() -> None:
    source = _source(SEARCH)

    assert 'asset.asset_kind == "player"' in source
    assert "player_targets" in source

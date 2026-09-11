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
    for label in (
        "Use calculated / neutral",
        "Push in the chips / Win now",
        "Balanced",
        "Retool",
        "Rebuild",
        "Improve a position",
        "Shop a player",
        "Target a player",
        "Consolidate",
    ):
        assert label in source
    assert "Market focus" in source
    assert "How this changes suggestions" in source
    assert "deck.prepend(control)" in source


def test_strategic_owner_intent_uses_server_published_posture_ordering_not_ui_score() -> None:
    source = _source(POSTURE_UI)

    assert "posture_views" in source
    assert "candidate_indices" in source
    assert "applyServerPostureView" in source
    assert "fsffl.tradeFinderPosture" in source
    assert "Strategic choices change Trade Finder discovery order only" in source
    assert "server-published posture views" in source


def test_specific_market_tasks_only_narrow_already_returned_candidates() -> None:
    source = _source(POSTURE_UI)

    assert "fsffl.marketIntent" in source
    assert "fsffl.marketIntentValue" in source
    assert "Position, shop, target and consolidation choices only narrow" in source
    assert "already-returned candidate set" in source
    assert "fsffl:market-intent-changed" in source


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

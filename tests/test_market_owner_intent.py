from fsffl.product.focused_opportunity_search import candidate_matches_focus

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
        "Calculated / neutral",
        "Contend / Win now",
        "Balanced",
        "Retool",
        "Rebuild",
        "Target a position",
        "Shop a player",
        "Target a player",
        "Explore an owner / team",
        "Consolidate",
    ):
        assert label in source
    assert "Market focus" in source
    assert "How this changes suggestions" in source
    assert "nav.insertAdjacentElement('afterend',control)" in source
    assert "currentMarketMode()!=='opportunities'" in source


def test_strategic_owner_intent_uses_server_published_posture_ordering_not_ui_score() -> None:
    source = _source(POSTURE_UI)

    assert "posture_views" in source
    assert "candidate_indices" in source
    assert "applyServerPostureView" in source
    assert "fsffl.tradeFinderPosture" in source
    assert "Strategic choices constrain the submitted Trade Finder discovery neighborhood" in source
    assert "setPosture:value=>{rememberPosture(value||DEFAULT);broadcastIntent()" in source


def test_specific_market_tasks_use_server_focused_search_before_candidate_limit() -> None:
    posture = _source(POSTURE_UI)
    focused = _source(Path("src/fsffl/product/focused_opportunity_search.py"))
    routes = _source(Path("src/fsffl/product/focused_opportunity_routes.py"))

    assert "fsffl.marketIntent" in posture
    assert "fsffl.marketIntentValue" in posture
    assert "Position, shop, target, owner and consolidation choices use the server-owned focused Search path before the candidate limit." in posture
    assert "fsffl:market-intent-changed" in posture
    assert '"owner"' in focused.split("_VALID_INTENTS", 1)[1].split("\n", 1)[0]
    assert 'normalized_intent == "owner"' in focused
    assert '"applied_before_candidate_limit": True' in routes

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

    assert 'if target.asset_kind != "player":' in source
    assert "admitted_targets" in source


def test_specific_market_intent_predicate_is_semantically_exact() -> None:
    row = {
        "counterparty_team_id": "owner-a",
        "target_position": "WR",
        "send": [
            {"asset_ref": "player:shop-me", "asset_kind": "player"},
            {"asset_ref": "pick:2027-2", "asset_kind": "pick"},
        ],
        "receive": [{"asset_ref": "player:target-me", "asset_kind": "player"}],
    }

    assert candidate_matches_focus(row, intent="position", intent_value="WR")
    assert not candidate_matches_focus(row, intent="position", intent_value="RB")
    assert candidate_matches_focus(row, intent="owner", intent_value="owner-a")
    assert not candidate_matches_focus(row, intent="owner", intent_value="owner-b")
    assert candidate_matches_focus(row, intent="target", intent_value="player:target-me")
    assert not candidate_matches_focus(row, intent="target", intent_value="player:other")
    assert candidate_matches_focus(row, intent="shop", intent_value="player:shop-me")
    assert not candidate_matches_focus(row, intent="shop", intent_value="player:other")
    assert candidate_matches_focus(row, intent="consolidate", intent_value="")
    assert not candidate_matches_focus(row, intent="owner", intent_value="")

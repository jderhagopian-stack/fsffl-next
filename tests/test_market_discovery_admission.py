from types import SimpleNamespace

import fsffl.product.opportunity_search as search
from fsffl.product.focused_opportunity_search import build_focused_trade_candidates
from fsffl.product.opportunity_search import build_roster_aware_trade_candidates
from fsffl.state.models import Position
from fsffl.team_utility.utility import OwnerStrategicPosture


def _asset(player_id: str, position: Position):
    return SimpleNamespace(
        asset_ref=f"player:{player_id}",
        asset_kind="player",
        player_id=player_id,
        pick_id=None,
        label=player_id,
        detail=position.value,
        age_years=25.0,
        roster_slot=None,
    )


def _strength(team_id: str, position: Position, rank: int):
    return SimpleNamespace(
        team_id=team_id,
        position=position,
        league_rank=rank,
        team_count=4,
        strength_index=float(130 - rank * 15),
    )


def _fixture():
    positions = {
        "f-rb": Position.RB,
        "f-wr": Position.WR,
        "a-rb": Position.RB,
        "a-wr": Position.WR,
        "b-rb": Position.RB,
        "b-wr": Position.WR,
    }
    state = SimpleNamespace(
        state_id="state-1",
        players=tuple(
            SimpleNamespace(player_id=player_id, position=position)
            for player_id, position in positions.items()
        ),
    )
    views = (
        SimpleNamespace(
            team_id="me",
            position_strengths=(
                _strength("me", Position.QB, 1),
                _strength("me", Position.RB, 4),
                _strength("me", Position.WR, 3),
                _strength("me", Position.TE, 2),
            ),
            utility=None,
        ),
        SimpleNamespace(
            team_id="owner-a",
            position_strengths=(
                _strength("owner-a", Position.QB, 2),
                _strength("owner-a", Position.RB, 1),
                _strength("owner-a", Position.WR, 4),
                _strength("owner-a", Position.TE, 3),
            ),
            utility=None,
        ),
        SimpleNamespace(
            team_id="owner-b",
            position_strengths=(
                _strength("owner-b", Position.QB, 2),
                _strength("owner-b", Position.RB, 4),
                _strength("owner-b", Position.WR, 1),
                _strength("owner-b", Position.TE, 3),
            ),
            utility=None,
        ),
    )
    runtime = SimpleNamespace(
        league_state=state,
        selected_team_id="me",
        simulation_analytics=SimpleNamespace(
            team_views=views,
            simulation_result=SimpleNamespace(outcomes=()),
        ),
    )
    browser = SimpleNamespace(
        focal_team=SimpleNamespace(
            team_id="me",
            assets=(_asset("f-rb", Position.RB), _asset("f-wr", Position.WR)),
        ),
        counterparties=(
            SimpleNamespace(
                team_id="owner-a",
                display_name="Owner A",
                assets=(_asset("a-rb", Position.RB), _asset("a-wr", Position.WR)),
            ),
            SimpleNamespace(
                team_id="owner-b",
                display_name="Owner B",
                assets=(_asset("b-rb", Position.RB), _asset("b-wr", Position.WR)),
            ),
        ),
    )
    return runtime, browser


def _capture_prepackage(monkeypatch):
    seen_targets = []
    seen_send_sets = []

    def fake_catalog(focal_assets, cardinal, **kwargs):
        seen_send_sets.append(tuple(asset.asset_ref for asset in focal_assets))
        return {1: ()}

    def fake_neighborhood(**kwargs):
        seen_targets.append(kwargs["target"].asset_ref)
        return ()

    monkeypatch.setattr(search, "_build_package_catalog", fake_catalog)
    monkeypatch.setattr(search, "_nearest_packages_for_target", fake_neighborhood)
    return seen_targets, seen_send_sets


def test_automatic_improve_uses_need_plus_counterparty_supply_before_packages(monkeypatch) -> None:
    runtime, browser = _fixture()
    targets, sends = _capture_prepackage(monkeypatch)

    build_roster_aware_trade_candidates(runtime, browser, {})

    assert targets == ["player:a-rb", "player:b-wr"]
    assert sends == [("player:f-wr",), ("player:f-rb",)]


def test_position_owner_target_and_shop_create_distinct_early_neighborhoods(monkeypatch) -> None:
    runtime, browser = _fixture()

    targets, _ = _capture_prepackage(monkeypatch)
    build_focused_trade_candidates(
        runtime,
        browser,
        {},
        requested_posture=OwnerStrategicPosture.BALANCED,
        intent="position",
        intent_value="RB",
    )
    assert targets == ["player:a-rb", "player:b-rb"]

    targets.clear()
    build_focused_trade_candidates(
        runtime,
        browser,
        {},
        requested_posture=OwnerStrategicPosture.BALANCED,
        intent="owner",
        intent_value="owner-a",
    )
    assert targets == ["player:a-rb", "player:a-wr"]

    targets.clear()
    build_focused_trade_candidates(
        runtime,
        browser,
        {},
        requested_posture=OwnerStrategicPosture.BALANCED,
        intent="target",
        intent_value="player:b-wr",
    )
    assert targets == ["player:b-wr"]

    targets.clear()
    build_focused_trade_candidates(
        runtime,
        browser,
        {},
        requested_posture=OwnerStrategicPosture.BALANCED,
        intent="shop",
        intent_value="player:f-rb",
    )
    assert targets == ["player:b-wr"]

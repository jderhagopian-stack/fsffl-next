from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from fsffl.product.intrinsic_market_discovery import (
    INTRINSIC_MARKET_DISCOVERY_VERSION,
    _percentile_ranks,
    build_intrinsic_market_discovery,
)
from fsffl.product.runtime import UserRuntimeContext
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    Position,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)
from fsffl.value.current_runtime import CurrentMarketValueRuntimeResult
from fsffl.value.models import (
    MarketPriceEstimate,
    ValueAssetKind,
    ValueDistribution,
    ValueScale,
)
from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicAvailability


def _runtime() -> UserRuntimeContext:
    now = datetime(2026, 9, 20, 12, tzinfo=UTC)
    league_id = "league"
    players = (
        Player(player_id="p1", full_name="Alpha QB", position=Position.QB),
        Player(player_id="p2", full_name="Beta RB", position=Position.RB),
        Player(player_id="p3", full_name="Gamma WR", position=Position.WR),
        Player(player_id="p4", full_name="Delta TE", position=Position.TE),
    )
    state = LeagueState(
        league=League(
            league_id=league_id,
            name="Fixture",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=2, lineup=(), scoring=()),
        ),
        as_of=now,
        teams=(
            Team(team_id="a", league_id=league_id, display_name="Alpha Team"),
            Team(team_id="b", league_id=league_id, display_name="Beta Team"),
        ),
        team_states=(
            TeamState(
                team_id="a",
                roster=(
                    RosterEntry(player_id="p1", slot=RosterSlot.QB),
                    RosterEntry(player_id="p2", slot=RosterSlot.RB),
                ),
            ),
            TeamState(
                team_id="b",
                roster=(
                    RosterEntry(player_id="p3", slot=RosterSlot.WR),
                    RosterEntry(player_id="p4", slot=RosterSlot.TE),
                ),
            ),
        ),
        players=players,
    )
    scale = ValueScale(
        scale_id="dynasty-market-percentile",
        version="fixture-v1",
        unit_label="market percentile",
    )
    market = {
        "p1": 0.95,
        "p2": 0.15,
        "p3": 0.25,
        "p4": 0.85,
    }
    values = CurrentMarketValueRuntimeResult(
        league_state_id=state.state_id,
        estimates=tuple(
            MarketPriceEstimate(
                asset_id=player_id,
                asset_kind=ValueAssetKind.PLAYER,
                distribution=ValueDistribution(mean=value),
                scale=scale,
                as_of=now,
                market_context_id="fixture-market",
                model_version="fixture-market-v1",
            )
            for player_id, value in market.items()
        ),
        successful_source_ids=("fixture",),
        failed_sources=(),
        errors_by_source_id={},
        roster_player_count=4,
        valued_roster_player_count=4,
        market_context_id="fixture-market",
    )
    return UserRuntimeContext(
        user_id="u",
        league_state=state,
        selected_team_id="a",
        value_evidence=values,
    )


def _intrinsic() -> Any:
    # Raw Intrinsic values intentionally use unrelated units; only their ranks
    # are allowed to interact with Broad Market percentiles.
    values = {"p1": 10.0, "p2": 90.0, "p3": 80.0, "p4": 20.0}
    return cast(
        Any,
        SimpleNamespace(
            status=ShapleyIntrinsicAvailability.READY,
            status_reason=None,
            contract_version="intrinsic-contract-fixture",
            intrinsic_model_version="intrinsic-fixture-v1",
            forecast_model_version="forecast-fixture-v1",
            estimates=tuple(
                SimpleNamespace(player_id=player_id, raw_intrinsic_value=value)
                for player_id, value in values.items()
            ),
        ),
    )


def test_percentile_ranks_center_ties_without_inventing_common_units() -> None:
    ranks = _percentile_ranks((("a", 10.0), ("b", 20.0), ("c", 20.0), ("d", 40.0)))
    assert ranks == {"a": 0.125, "b": 0.5, "c": 0.5, "d": 0.875}


def test_discovery_uses_rank_only_and_preserves_action_boundaries() -> None:
    runtime = _runtime()
    payload = build_intrinsic_market_discovery(
        runtime,
        _intrinsic(),
        minimum_percentile_gap=0.10,
        limit=24,
    )

    assert payload["status"] == "ready"
    assert payload["model_version"] == INTRINSIC_MARKET_DISCOVERY_VERSION
    assert payload["league_state_id"] == runtime.league_state.state_id
    assert payload["focal_team_id"] == "a"
    authority = payload["authority"]
    assert authority["comparison_coordinate"] == "percentile_rank_presentation_only"
    assert authority["recommendation_authority"] is False
    assert authority["acceptance_probability"] is None
    assert authority["league_market_value_available"] is False
    assert authority["team_utility_included"] is False
    assert authority["raw_value_subtraction_used"] is False

    rows = {row["player_id"]: row for row in payload["rows"]}
    # p2 is on the focal team and Intrinsic ranks it much higher than market,
    # so the only workflow handoff is the existing shop-player Market Focus path.
    assert rows["p2"]["focus_intent"] == "shop"
    assert rows["p2"]["focus_value"] == "player:p2"
    assert rows["p2"]["action_authority"] == "diagnostic_only"
    assert rows["p2"]["acceptance_probability"] is None
    # p3 is owned by another team and is likewise a discovery-only target handoff.
    assert rows["p3"]["focus_intent"] == "target"
    assert rows["p3"]["focus_value"] == "player:p3"
    assert "not an automatic acquisition signal" in rows["p3"]["read"]


def test_discovery_fails_closed_without_market_evidence() -> None:
    runtime = _runtime()
    runtime = runtime.__class__(
        user_id=runtime.user_id,
        league_state=runtime.league_state,
        selected_team_id=runtime.selected_team_id,
    )
    payload = build_intrinsic_market_discovery(runtime, _intrinsic())
    assert payload["status"] == "unavailable"
    assert payload["rows"] == []
    assert payload["authority"]["recommendation_authority"] is False


def test_discovery_fails_closed_when_intrinsic_is_unavailable() -> None:
    intrinsic = _intrinsic()
    intrinsic.status = ShapleyIntrinsicAvailability.UNAVAILABLE
    intrinsic.status_reason = "fixture unavailable"
    payload = build_intrinsic_market_discovery(_runtime(), intrinsic)
    assert payload["status"] == "unavailable"
    assert payload["message"] == "fixture unavailable"
    assert payload["rows"] == []

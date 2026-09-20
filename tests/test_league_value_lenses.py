from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

from fsffl.product.league_value_lenses import (
    BROAD_MARKET_SCALE_ID,
    INTRINSIC_PRESENTATION_COORDINATE,
    LEAGUE_VALUE_LENS_CONTRACT_VERSION,
    build_league_value_lenses,
)
from fsffl.product.runtime import UserRuntimeContext
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
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


NOW = datetime(2026, 9, 20, 18, tzinfo=UTC)


def _state() -> LeagueState:
    league_id = "league"
    players = (
        Player(player_id="p1", full_name="Alpha QB", position=Position.QB),
        Player(player_id="p2", full_name="Beta RB", position=Position.RB),
        Player(player_id="p3", full_name="Gamma WR", position=Position.WR),
        Player(player_id="p4", full_name="Delta TE", position=Position.TE),
    )
    provenance = Provenance(
        source="fixture",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture-v1",
    )
    return LeagueState(
        league=League(
            league_id=league_id,
            name="Fixture",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=2, lineup=(), scoring=()),
        ),
        as_of=NOW,
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
        player_states=tuple(
            PlayerState(player_id=p.player_id, as_of=NOW, provenance=provenance)
            for p in players
        ),
    )


def _market(state: LeagueState) -> CurrentMarketValueRuntimeResult:
    scale = ValueScale(
        scale_id=BROAD_MARKET_SCALE_ID,
        version="fixture-v1",
        unit_label="market percentile",
    )
    values = {"p1": 0.90, "p2": 0.20, "p3": 0.30, "p4": 0.80}
    return CurrentMarketValueRuntimeResult(
        league_state_id=state.state_id,
        estimates=tuple(
            MarketPriceEstimate(
                asset_id=player_id,
                asset_kind=ValueAssetKind.PLAYER,
                distribution=ValueDistribution(mean=value),
                scale=scale,
                as_of=NOW,
                market_context_id="fixture-market",
                model_version="fixture-market-v1",
            )
            for player_id, value in values.items()
        ),
        successful_source_ids=("fixture",),
        failed_sources=(),
        errors_by_source_id={},
        roster_player_count=4,
        valued_roster_player_count=4,
        market_context_id="fixture-market",
    )


def _intrinsic(*, unavailable: bool = False) -> Any:
    values = {"p1": 10.0, "p2": 90.0, "p3": 80.0, "p4": 20.0}
    return cast(
        Any,
        SimpleNamespace(
            status=(
                ShapleyIntrinsicAvailability.UNAVAILABLE
                if unavailable
                else ShapleyIntrinsicAvailability.READY
            ),
            status_reason="fixture unavailable" if unavailable else None,
            contract_version="intrinsic-shapley-contract-fixture",
            quantity_semantics="raw_governed_shapley_marginal_fantasy_points",
            estimates=tuple(
                SimpleNamespace(player_id=player_id, raw_intrinsic_value=value)
                for player_id, value in values.items()
            ) if not unavailable else (),
        ),
    )


def test_league_value_lenses_keep_market_and_intrinsic_separate() -> None:
    state = _state()
    runtime = UserRuntimeContext(
        user_id="u",
        league_state=state,
        selected_team_id="a",
        value_evidence=_market(state),
    )
    payload = build_league_value_lenses(runtime, _intrinsic())

    assert payload["status"] == "ready"
    assert payload["contract_version"] == LEAGUE_VALUE_LENS_CONTRACT_VERSION
    assert payload["broad_market"]["scale_id"] == BROAD_MARKET_SCALE_ID
    assert payload["fsffl_intrinsic"]["display_coordinate"] == INTRINSIC_PRESENTATION_COORDINATE
    assert payload["broad_market"]["team_total_authority"] is False
    assert payload["fsffl_intrinsic"]["team_total_authority"] is False

    authority = payload["authority"]
    assert authority["broad_market_and_intrinsic_are_distinct_lenses"] is True
    assert authority["raw_value_subtraction_used"] is False
    assert authority["team_value_total_created"] is False
    assert authority["team_value_rank_created"] is False
    assert authority["league_market_value_available"] is False
    assert authority["team_utility_included"] is False
    assert authority["fsffl_cardinal_value_included"] is False
    assert authority["recommendation_authority"] is False
    assert authority["acceptance_probability"] is None

    rows = {row["player_id"]: row for row in payload["players"]}
    assert rows["p1"]["broad_market_percentile"] == 0.90
    assert rows["p2"]["intrinsic_percentile"] > rows["p2"]["broad_market_percentile"]
    assert rows["p3"]["intrinsic_percentile"] > rows["p3"]["broad_market_percentile"]


def test_market_failure_does_not_replace_intrinsic_lens() -> None:
    state = _state()
    runtime = UserRuntimeContext(user_id="u", league_state=state, selected_team_id="a")
    payload = build_league_value_lenses(runtime, _intrinsic())

    assert payload["status"] == "degraded"
    assert payload["broad_market"]["status"] == "unavailable"
    assert payload["fsffl_intrinsic"]["status"] == "ready"
    assert all(row["broad_market_percentile"] is None for row in payload["players"])
    assert any(row["intrinsic_percentile"] is not None for row in payload["players"])


def test_intrinsic_failure_does_not_replace_broad_market_lens() -> None:
    state = _state()
    runtime = UserRuntimeContext(
        user_id="u",
        league_state=state,
        selected_team_id="a",
        value_evidence=_market(state),
    )
    payload = build_league_value_lenses(runtime, _intrinsic(unavailable=True))

    assert payload["status"] == "degraded"
    assert payload["broad_market"]["status"] == "ready"
    assert payload["fsffl_intrinsic"]["status"] == "unavailable"
    assert all(row["intrinsic_percentile"] is None for row in payload["players"])
    assert any(row["broad_market_percentile"] is not None for row in payload["players"])


def test_team_groups_are_coverage_only_not_value_totals_or_ranks() -> None:
    state = _state()
    runtime = UserRuntimeContext(
        user_id="u",
        league_state=state,
        selected_team_id="a",
        value_evidence=_market(state),
    )
    payload = build_league_value_lenses(runtime, _intrinsic())
    team = payload["teams"][0]

    assert team["rostered_player_count"] == 2
    assert team["broad_market_covered_players"] == 2
    assert team["intrinsic_covered_players"] == 2
    assert team["comparable_players"] == 2
    assert "total_value" not in team
    assert "rank" not in team
    assert "score" not in team

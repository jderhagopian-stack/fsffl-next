from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from fsffl.forecast.future_contract import (
    ForecastUncertaintyKind,
    FutureForecastScenario,
)
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.product.player_intelligence import (
    PlayerHistoryService,
    build_player_intelligence_overview,
)
from fsffl.product.runtime import UserRuntimeContext
from fsffl.providers.sleeper_weekly_stats import SleeperWeeklyStatLine
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
    ScoringRule,
    Team,
    TeamState,
)


NOW = datetime(2026, 9, 21, 12, tzinfo=UTC)


def _rules() -> LeagueRules:
    return LeagueRules(
        team_count=2,
        roster_size=4,
        lineup=(),
        scoring=(
            ScoringRule(stat="pass_yd", points=0.04),
            ScoringRule(stat="pass_td", points=4.0),
            ScoringRule(stat="pass_int", points=-2.0),
            ScoringRule(stat="rush_yd", points=0.1),
            ScoringRule(stat="rush_td", points=6.0),
            ScoringRule(stat="rec", points=0.5),
            ScoringRule(stat="rec_yd", points=0.1),
            ScoringRule(stat="rec_td", points=6.0),
        ),
    )


def _state() -> LeagueState:
    league_id = "league"
    players = (
        Player(
            player_id="sleeper:player:101",
            full_name="Fixture QB",
            position=Position.QB,
            nfl_team="AAA",
        ),
        Player(
            player_id="sleeper:player:102",
            full_name="Fixture RB",
            position=Position.RB,
            nfl_team="BBB",
        ),
        Player(
            player_id="sleeper:player:103",
            full_name="Fixture WR",
            position=Position.WR,
            nfl_team="CCC",
        ),
        Player(
            player_id="sleeper:player:104",
            full_name="Fixture TE",
            position=Position.TE,
            nfl_team="DDD",
        ),
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
            rules=_rules(),
        ),
        as_of=NOW,
        teams=(
            Team(team_id="a", league_id=league_id, display_name="Alpha"),
            Team(team_id="b", league_id=league_id, display_name="Beta"),
        ),
        team_states=(
            TeamState(
                team_id="a",
                roster=tuple(
                    RosterEntry(player_id=player.player_id, slot=RosterSlot.BENCH)
                    for player in players
                ),
            ),
            TeamState(team_id="b", roster=()),
        ),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=player.player_id,
                as_of=NOW,
                age_years=25.0,
                nfl_team=player.nfl_team,
                provenance=provenance,
            )
            for player in players
        ),
    )


def _forecast_observation(player_id: str, points: float) -> ForecastObservation:
    provenance = Provenance(
        source="fixture-forecast",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture-forecast-v1",
    )
    return ForecastObservation(
        player_id=player_id,
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=datetime(2027, 2, 1, tzinfo=UTC),
        distribution=ForecastDistribution(mean=points, stddev=30.0, p10=250.0, p50=300.0, p90=350.0),
        source="fsffl:fixture",
        model_version="fixture-y1-v1",
        as_of=NOW,
        provenance=provenance,
    )


class _FutureContract:
    def rows_for_player(self, player_id: str):
        assert player_id == "sleeper:player:101"
        return (
            SimpleNamespace(
                year_index=2,
                target_season=2027,
                central_expectation=280.0,
                uncertainty_kind=ForecastUncertaintyKind.DISCRETE_SCENARIOS,
                stddev=None,
                p10=None,
                p50=None,
                p90=None,
                scenarios=(
                    FutureForecastScenario(
                        scenario_id="down",
                        probability=0.25,
                        fantasy_points=180.0,
                    ),
                    FutureForecastScenario(
                        scenario_id="base",
                        probability=0.50,
                        fantasy_points=280.0,
                    ),
                    FutureForecastScenario(
                        scenario_id="up",
                        probability=0.25,
                        fantasy_points=380.0,
                    ),
                ),
                evidence_path="fixture-y2",
                source="fsffl:future-fixture",
                model_version="fixture-y2-v1",
            ),
            SimpleNamespace(
                year_index=3,
                target_season=2028,
                central_expectation=240.0,
                uncertainty_kind=ForecastUncertaintyKind.DISCRETE_SCENARIOS,
                stddev=None,
                p10=None,
                p50=None,
                p90=None,
                scenarios=(
                    FutureForecastScenario(
                        scenario_id="down",
                        probability=0.25,
                        fantasy_points=120.0,
                    ),
                    FutureForecastScenario(
                        scenario_id="base",
                        probability=0.50,
                        fantasy_points=240.0,
                    ),
                    FutureForecastScenario(
                        scenario_id="up",
                        probability=0.25,
                        fantasy_points=360.0,
                    ),
                ),
                evidence_path="fixture-y3",
                source="fsffl:future-fixture",
                model_version="fixture-y3-v1",
            ),
        )


class _FutureCache:
    def get(self, runtime):
        assert runtime.league_state is not None
        return _FutureContract()


def test_player_overview_uses_forecast_owned_y1_y2_y3_and_fails_ppg_closed() -> None:
    state = _state()
    y1 = _forecast_observation("sleeper:player:101", 310.0)
    forecast = SimpleNamespace(
        league_scored_forecasts=(y1,),
        raw_forecasts=(),
        evidence_basis="preseason_baseline",
        model_version="next8-live-forecast-evidence-v5:revision-agnostic-source-health",
        successful_source_ids=("preserved_preseason_baseline",),
        runtime_result=SimpleNamespace(evaluation_as_of=NOW),
    )
    runtime = UserRuntimeContext(
        user_id="u",
        league_state=state,
        selected_team_id="a",
        forecast_evidence=forecast,
    )

    payload = build_player_intelligence_overview(
        runtime,
        "sleeper:player:101",
        intrinsic=None,
        future_cache=_FutureCache(),
    )

    rows = payload["forecast"]["rows"]
    assert [row["year_index"] for row in rows] == [1, 2, 3]
    assert [row["fantasy_points"] for row in rows] == [310.0, 280.0, 240.0]
    assert rows[0]["evidence_basis"] == "preseason_baseline"
    assert rows[1]["evidence_basis"] == "governed_future_forecast_contract"
    assert rows[1]["uncertainty"]["kind"] == "discrete_scenarios"
    assert [scenario["fantasy_points"] for scenario in rows[1]["uncertainty"]["scenarios"]] == [
        180.0,
        280.0,
        380.0,
    ]
    assert all(row["fantasy_ppg"] is None for row in rows)
    assert all(
        row["ppg_basis"]
        == "unavailable: Forecast contract does not expose expected player games"
        for row in rows
    )
    assert payload["value"]["raw_shapley_marginal_points"] is None


class _HistorySource:
    provider_name = "sleeper_stats"
    source_version = "fixture-sleeper-weekly-v1"

    _stats = {
        "101": {
            "gp": 1,
            "pass_yd": 300,
            "pass_td": 2,
            "pass_int": 1,
            "rush_yd": 20,
            "rush_td": 1,
        },
        "102": {
            "gp": 1,
            "rush_yd": 80,
            "rush_td": 1,
            "rec": 4,
            "rec_yd": 30,
            "rec_td": 0,
        },
        "103": {
            "gp": 1,
            "rush_yd": 5,
            "rush_td": 0,
            "rec": 7,
            "rec_yd": 100,
            "rec_td": 1,
        },
        "104": {
            "gp": 1,
            "rush_yd": 0,
            "rush_td": 0,
            "rec": 5,
            "rec_yd": 60,
            "rec_td": 1,
        },
    }

    def fetch_week(self, *, season: int, week: int):
        if week != 1:
            return ()
        return tuple(
            SleeperWeeklyStatLine(
                player_id=f"sleeper:player:{external_id}",
                season=season,
                week=week,
                stats=stats,
                captured_at=NOW,
                source_company="fixture",
            )
            for external_id, stats in self._stats.items()
        )


@pytest.mark.parametrize(
    ("player_id", "expected_keys"),
    (
        ("sleeper:player:101", {"pass_yd", "pass_td", "pass_int", "rush_yd", "rush_td"}),
        ("sleeper:player:102", {"rush_yd", "rush_td", "rec", "rec_yd", "rec_td"}),
        ("sleeper:player:103", {"rush_yd", "rush_td", "rec", "rec_yd", "rec_td"}),
        ("sleeper:player:104", {"rush_yd", "rush_td", "rec", "rec_yd", "rec_td"}),
    ),
)
def test_history_reuses_sleeper_actuals_with_current_scoring_and_provenance(
    player_id: str,
    expected_keys: set[str],
) -> None:
    runtime = UserRuntimeContext(user_id="u", league_state=_state(), selected_team_id="a")
    service = PlayerHistoryService(source=_HistorySource(), max_workers=1)

    rows = service.player_history(runtime, player_id)

    assert [row.season for row in rows] == [2023, 2024, 2025]
    assert all(row.games_played == 1 for row in rows)
    assert all(row.fantasy_points > 0 for row in rows)
    assert all(row.fantasy_ppg == pytest.approx(row.fantasy_points) for row in rows)
    assert all(set(row.stats) == expected_keys for row in rows)
    assert all(row.scoring_basis == "scored under current league rules" for row in rows)
    assert all(row.source == "sleeper_stats" for row in rows)
    assert all(row.source_version == "fixture-sleeper-weekly-v1" for row in rows)
    assert all(row.position_rank is None for row in rows)
    assert all("complete point-in-time historical position population" in (row.rank_basis or "") for row in rows)

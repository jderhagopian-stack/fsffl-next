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
from fsffl.providers.sleeper_weekly_stats import (
    SleeperSeasonStatLine,
    SleeperWeeklyStatLine,
    SleeperWeeklyStatsSource,
)
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
        distribution=ForecastDistribution(mean=points, stddev=30.0, p10=250.0, p25=280.0, p50=300.0, p75=325.0, p90=350.0),
        source="fsffl:fixture",
        model_version="fixture-y1-v1",
        as_of=NOW,
        provenance=provenance,
    )


def _stat_forecast_observation(
    player_id: str,
    metric: ForecastMetric,
    mean: float,
) -> ForecastObservation:
    provenance = Provenance(
        source="fixture-raw-y1",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture-raw-y1-v1",
    )
    return ForecastObservation(
        player_id=player_id,
        position=Position.QB,
        horizon=ForecastHorizon.SEASON,
        metric=metric,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=datetime(2027, 2, 1, tzinfo=UTC),
        distribution=ForecastDistribution(mean=mean, stddev=0.0),
        source="fsffl:fixture-raw-y1",
        model_version="fixture-raw-y1-v1",
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
                p10=120.0,
                p25=210.0,
                p50=280.0,
                p75=335.0,
                p90=380.0,
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
                p10=120.0,
                p25=210.0,
                p50=280.0,
                p75=335.0,
                p90=380.0,
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
    raw_y1 = (
        _stat_forecast_observation(
            "sleeper:player:101",
            ForecastMetric.PASS_YARDS,
            4050.0,
        ),
        _stat_forecast_observation(
            "sleeper:player:101",
            ForecastMetric.PASS_TD,
            29.0,
        ),
        _stat_forecast_observation(
            "sleeper:player:101",
            ForecastMetric.INTERCEPTIONS,
            9.0,
        ),
        _stat_forecast_observation(
            "sleeper:player:101",
            ForecastMetric.RUSH_YARDS,
            720.0,
        ),
    )
    forecast = SimpleNamespace(
        league_scored_forecasts=(y1,),
        raw_forecasts=raw_y1,
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
    assert rows[0]["uncertainty"]["p25"] == 280.0
    assert rows[0]["uncertainty"]["p75"] == 325.0
    assert rows[1]["uncertainty"]["p25"] == 210.0
    assert rows[1]["uncertainty"]["p50"] == 280.0
    assert rows[1]["uncertainty"]["p75"] == 335.0
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


    projected = payload["forecast"]["current_projected_stats"]
    assert projected["season"] == 2026
    assert projected["label"] == "PROJECTED"
    assert projected["evidence_basis"] == "preseason_baseline"
    assert projected["stats"] == {
        "pass_yd": 4050.0,
        "pass_td": 29.0,
        "pass_int": 9.0,
        "rush_yd": 720.0,
    }
    assert projected["fantasy_points"] == 310.0
    assert projected["fantasy_ppg"] is None
    assert projected["games_played"] is None
    assert "pass_att" not in projected["stats"]
    assert "pass_cmp" not in projected["stats"]
    assert "rush_att" not in projected["stats"]
    assert set(projected["field_provenance"]) == {
        "pass_yd",
        "pass_td",
        "pass_int",
        "rush_yd",
    }
    assert projected["source_ids"] == ["fsffl:fixture-raw-y1"]
    assert projected["model_versions"] == ["fixture-raw-y1-v1"]


def test_player_overview_projected_stats_fail_closed_when_y1_raw_fields_are_absent() -> None:
    state = _state()
    y1 = _forecast_observation("sleeper:player:101", 310.0)
    forecast = SimpleNamespace(
        league_scored_forecasts=(y1,),
        raw_forecasts=(),
        evidence_basis="preseason_baseline",
        model_version="fixture",
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

    projected = payload["forecast"]["current_projected_stats"]
    assert projected["stats"] == {}
    assert projected["field_provenance"] == {}
    assert projected["source_ids"] == []
    assert projected["model_versions"] == []
    assert projected["fantasy_points"] == 310.0
    assert projected["games_played"] is None


class _HistorySource:
    provider_name = "sleeper_stats"
    source_version = "fixture-sleeper-season-v2"

    _stats = {
        "101": {
            "gp": 17,
            "pass_att": 550,
            "pass_cmp": 365,
            "pass_yd": 4300,
            "pass_td": 31,
            "pass_int": 10,
            "rush_att": 54,
            "rush_yd": 320,
            "rush_td": 4,
            "fum": 5,
            "fum_lost": 2,
        },
        "102": {
            "gp": 16,
            "rush_att": 245,
            "rush_yd": 1080,
            "rush_td": 9,
            "rec_tgt": 61,
            "rec": 48,
            "rec_yd": 390,
            "rec_td": 3,
            "fum": 2,
            "fum_lost": 1,
        },
        "103": {
            "gp": 17,
            "rec_tgt": 132,
            "rec": 88,
            "rec_yd": 1240,
            "rec_td": 9,
            "rush_att": 7,
            "rush_yd": 46,
            "rush_td": 1,
            "fum": 1,
            "fum_lost": 0,
        },
        "104": {
            "gp": 15,
            "rec_tgt": 98,
            "rec": 70,
            "rec_yd": 760,
            "rec_td": 7,
            "rush_att": 1,
            "rush_yd": 4,
            "rush_td": 0,
            "fum": 1,
            "fum_lost": 1,
        },
    }
    _first_season = {"101": 2020, "102": 2021, "103": 2022, "104": 2024}

    def __init__(self):
        self.season_calls: list[int] = []

    def fetch_season(self, *, season: int):
        self.season_calls.append(season)
        rows = []
        for external_id, stats in self._stats.items():
            if season < self._first_season[external_id]:
                continue
            rows.append(
                SleeperSeasonStatLine(
                    player_id=f"sleeper:player:{external_id}",
                    season=season,
                    stats=stats,
                    captured_at=NOW,
                    source_company="fixture",
                )
            )
        return tuple(rows)


@pytest.mark.parametrize(
    ("player_id", "expected_keys"),
    (
        (
            "sleeper:player:101",
            {
                "pass_att",
                "pass_cmp",
                "pass_yd",
                "pass_td",
                "pass_int",
                "rush_att",
                "rush_yd",
                "rush_td",
                "fum",
                "fum_lost",
            },
        ),
        (
            "sleeper:player:102",
            {
                "rush_att",
                "rush_yd",
                "rush_td",
                "rec_tgt",
                "rec",
                "rec_yd",
                "rec_td",
                "fum",
                "fum_lost",
            },
        ),
        (
            "sleeper:player:103",
            {
                "rec_tgt",
                "rec",
                "rec_yd",
                "rec_td",
                "rush_att",
                "rush_yd",
                "rush_td",
                "fum",
                "fum_lost",
            },
        ),
        (
            "sleeper:player:104",
            {
                "rec_tgt",
                "rec",
                "rec_yd",
                "rec_td",
                "rush_att",
                "rush_yd",
                "rush_td",
                "fum",
                "fum_lost",
            },
        ),
    ),
)
def test_history_exposes_source_supported_position_box_stats(
    player_id: str,
    expected_keys: set[str],
) -> None:
    runtime = UserRuntimeContext(user_id="u", league_state=_state(), selected_team_id="a")
    source = _HistorySource()
    service = PlayerHistoryService(source=source, max_workers=4, minimum_season=2020)

    rows = service.player_history(runtime, player_id)

    assert rows
    assert all(set(row.stats) == expected_keys for row in rows)
    assert all(row.more_stats == {} for row in rows)
    assert all(row.games_played > 0 for row in rows)
    assert all(row.fantasy_ppg == pytest.approx(row.fantasy_points / row.games_played) for row in rows)
    assert all(row.scoring_basis == "scored under current league rules" for row in rows)
    assert all(row.source == "sleeper_stats" for row in rows)
    assert all(row.source_version == "fixture-sleeper-season-v2" for row in rows)
    assert all(row.games_played_basis == "provider season aggregate gp" for row in rows)
    assert all(row.position_rank is None for row in rows)


def test_full_career_history_is_not_capped_at_three_and_does_not_fabricate_young_seasons() -> None:
    runtime = UserRuntimeContext(user_id="u", league_state=_state(), selected_team_id="a")
    service = PlayerHistoryService(source=_HistorySource(), max_workers=4, minimum_season=2020)

    veteran = service.player_history(runtime, "sleeper:player:101")
    young = service.player_history(runtime, "sleeper:player:104")

    assert [row.season for row in veteran] == [2020, 2021, 2022, 2023, 2024, 2025]
    assert len(veteran) > 3
    assert [row.season for row in young] == [2024, 2025]


def test_historical_fantasy_points_reconcile_to_current_league_scoring() -> None:
    runtime = UserRuntimeContext(user_id="u", league_state=_state(), selected_team_id="a")
    service = PlayerHistoryService(source=_HistorySource(), max_workers=2, minimum_season=2025)

    row = service.player_history(runtime, "sleeper:player:101")[0]

    expected = 4300 * 0.04 + 31 * 4.0 - 10 * 2.0 + 320 * 0.1 + 4 * 6.0
    assert row.fantasy_points == pytest.approx(expected)
    assert row.games_played == 17


def test_repeat_player_history_reuses_compatible_season_aggregates() -> None:
    runtime = UserRuntimeContext(user_id="u", league_state=_state(), selected_team_id="a")
    source = _HistorySource()
    service = PlayerHistoryService(source=source, max_workers=4, minimum_season=2020)

    first = service.player_history(runtime, "sleeper:player:101")
    call_count = len(source.season_calls)
    second = service.player_history(runtime, "sleeper:player:102")

    assert first and second
    assert call_count == 6
    assert len(source.season_calls) == call_count


class _ArtifactStore:
    def __init__(self):
        self.records = {}

    def get_reusable_artifact(self, key):
        return self.records.get(key)

    def put_artifact(self, record):
        self.records[record.key] = record


def test_history_season_aggregates_are_durably_reusable_across_service_instances() -> None:
    runtime = UserRuntimeContext(user_id="u", league_state=_state(), selected_team_id="a")
    store = _ArtifactStore()
    first_source = _HistorySource()
    first_service = PlayerHistoryService(
        source=first_source,
        max_workers=2,
        minimum_season=2025,
        persistence_store=store,
    )
    assert first_service.player_history(runtime, "sleeper:player:101")
    assert first_source.season_calls == [2025]

    second_source = _HistorySource()
    second_service = PlayerHistoryService(
        source=second_source,
        max_workers=2,
        minimum_season=2025,
        persistence_store=store,
    )
    assert second_service.player_history(runtime, "sleeper:player:102")
    assert second_source.season_calls == []


class _WeeklyNoGpSource:
    provider_name = "sleeper_stats"
    source_version = "fixture-weekly-no-gp"

    def fetch_week(self, *, season: int, week: int):
        stats = {"pass_yd": 0.0} if week == 1 else ({"pass_yd": 100.0} if week == 2 else None)
        if stats is None:
            return ()
        return (
            SleeperWeeklyStatLine(
                player_id="sleeper:player:101",
                season=season,
                week=week,
                stats=stats,
                captured_at=NOW,
                source_company="fixture",
            ),
        )


def test_weekly_fallback_does_not_count_zero_non_participation_rows_as_games() -> None:
    runtime = UserRuntimeContext(user_id="u", league_state=_state(), selected_team_id="a")
    service = PlayerHistoryService(
        source=_WeeklyNoGpSource(),
        max_workers=4,
        minimum_season=2025,
    )

    row = service.player_history(runtime, "sleeper:player:101")[0]

    assert row.games_played == 1
    assert "non-zero measured-production fallback" in row.games_played_basis


def test_sleeper_season_stats_source_preserves_provider_box_score_keys_and_gp() -> None:
    seen = []

    def getter(url):
        seen.append(url)
        return {
            "101": {
                "season": 2025,
                "gp": 17,
                "pass_att": 550,
                "pass_cmp": 365,
                "pass_yd": 4300,
                "rush_att": 54,
                "rec_tgt": 1,
                "fum": 5,
                "fum_lost": 2,
            }
        }

    source = SleeperWeeklyStatsSource(http_get_json=getter, clock=lambda: NOW)
    rows = source.fetch_season(season=2025)

    assert seen == ["https://api.sleeper.app/v1/stats/nfl/regular/2025"]
    assert len(rows) == 1
    assert rows[0].stats["gp"] == 17
    assert rows[0].stats["pass_att"] == 550
    assert rows[0].stats["pass_cmp"] == 365
    assert rows[0].stats["rush_att"] == 54
    assert rows[0].stats["rec_tgt"] == 1
    assert rows[0].stats["fum"] == 5
    assert rows[0].stats["fum_lost"] == 2


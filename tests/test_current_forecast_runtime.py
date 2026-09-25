from datetime import UTC, datetime, timedelta
from threading import Barrier

from fsffl.forecast.current_runtime import NamedCurrentProjectionFetcher, build_current_live_forecasts
from fsffl.forecast.models import ForecastMetric
from fsffl.providers.current_projection_rows import CurrentProjectionRow, CurrentProjectionSnapshot
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    Position,
    Provenance,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)

NOW = datetime(2026, 9, 5, 20, tzinfo=UTC)


def state() -> LeagueState:
    provenance = Provenance(source="test", retrieved_at=NOW, effective_at=NOW)
    league = League(
        league_id="l1",
        name="League",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=1,
            lineup=(),
            scoring=(
                ScoringRule(stat="pass_yd", points=0.04),
                ScoringRule(stat="pass_td", points=4.0),
                ScoringRule(stat="pass_int", points=-2.0),
                ScoringRule(stat="rush_yd", points=0.1),
                ScoringRule(stat="rush_td", points=6.0),
            ),
        ),
    )
    return LeagueState(
        league=league,
        as_of=NOW,
        teams=(Team(team_id="a", league_id="l1", display_name="A"), Team(team_id="b", league_id="l1", display_name="B")),
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=(Player(player_id="p1", full_name="Lamar Jackson", position=Position.QB, nfl_team="BAL"),),
        player_states=(PlayerState(player_id="p1", as_of=NOW, nfl_team="BAL", provenance=provenance),),
    )


def snapshot(provider: str, yards: float, *, captured_at: datetime = NOW) -> CurrentProjectionSnapshot:
    return CurrentProjectionSnapshot(
        provider=provider,
        captured_at=captured_at,
        effective_at=(captured_at if provider == "cbs" else datetime(2026, 9, 4, 12, tzinfo=UTC)),
        rows=(CurrentProjectionRow(provider=provider, external_id=provider, player_name="Lamar Jackson", position=Position.QB, nfl_team="BAL", stats={"pass_yd": yards, "pass_td": 30.0, "pass_int": 10.0, "rush_yd": 800.0, "rush_td": 5.0}),),
        source_version=f"{provider}-v1",
        usage_class="beta-personal-research-requires-commercial-review",
    )


def test_current_runtime_ensembles_before_league_scoring() -> None:
    fetchers = (
        NamedCurrentProjectionFetcher("fftoday", lambda season: snapshot("fftoday", 4000.0)),
        NamedCurrentProjectionFetcher("cbs", lambda season: snapshot("cbs", 4200.0)),
    )
    result = build_current_live_forecasts(state(), fetchers=fetchers, clock=lambda: NOW)
    pass_yards = [item for item in result.raw_ensemble if item.metric == ForecastMetric.PASS_YARDS]
    assert len(pass_yards) == 1
    assert pass_yards[0].source == "fsffl:live_equal_weight"
    assert pass_yards[0].distribution.mean == 4100.0
    assert len(result.fantasy_point_forecasts) == 1
    assert result.fantasy_point_forecasts[0].source == "fsffl:live_league_scored"
    assert result.fantasy_point_forecasts[0].distribution.mean == 374.0
    assert result.fantasy_regular_season_forecasts == ()
    # Provider disagreement alone would yield only a few fantasy points of
    # dispersion here. The live runtime must instead expose the empirical
    # historical-error calibration required for downstream simulation.
    assert result.fantasy_point_forecasts[0].distribution.stddev > 200.0
    assert "next2-live-season-fp-uncertainty-v1" in result.fantasy_point_forecasts[0].model_version


def test_runtime_cutoff_advances_past_provider_retrieval_timestamp() -> None:
    captured_after_initial_clock = NOW + timedelta(seconds=2)
    fetchers = (
        NamedCurrentProjectionFetcher("fftoday", lambda season: snapshot("fftoday", 4000.0)),
        NamedCurrentProjectionFetcher("cbs", lambda season: snapshot("cbs", 4200.0, captured_at=captured_after_initial_clock)),
    )
    result = build_current_live_forecasts(state(), fetchers=fetchers, clock=lambda: NOW)
    assert result.evaluation_as_of == captured_after_initial_clock
    assert result.successful_source_ids == ("cbs", "fftoday")


def test_independent_provider_fetches_overlap_instead_of_running_serially() -> None:
    barrier = Barrier(2, timeout=2.0)

    def fetch(provider: str, yards: float):
        def run(season: int) -> CurrentProjectionSnapshot:
            assert season == 2026
            barrier.wait()
            return snapshot(provider, yards)
        return run

    result = build_current_live_forecasts(
        state(),
        fetchers=(
            NamedCurrentProjectionFetcher("fftoday", fetch("fftoday", 4000.0)),
            NamedCurrentProjectionFetcher("cbs", fetch("cbs", 4200.0)),
        ),
        clock=lambda: NOW,
    )
    assert result.successful_source_ids == ("cbs", "fftoday")
    assert result.model_version == "next2-current-runtime-v7:revision-agnostic-source-health"
    assert {event.provider for event in result.source_health_events} == {"cbs", "fftoday"}
    assert all(event.disposition == "accepted" for event in result.source_health_events)



def hodor_style_state() -> LeagueState:
    base = state()
    rules = LeagueRules(
        team_count=2,
        roster_size=4,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.K, count=1),
            LineupRequirement(slot=RosterSlot.DST, count=1),
        ),
        scoring=(
            ScoringRule(stat="pass_yd", points=0.04),
            ScoringRule(stat="pass_td", points=4.0),
            ScoringRule(stat="pass_int", points=-2.0),
            ScoringRule(stat="rush_yd", points=0.1),
            ScoringRule(stat="rush_td", points=6.0),
            ScoringRule(stat="fgm_50p", points=5.0),
            ScoringRule(stat="sack", points=1.0),
            ScoringRule(stat="pts_allow_0", points=10.0),
        ),
    )
    return base.model_copy(
        update={
            "league": base.league.model_copy(update={"rules": rules}),
        }
    )


def test_hodor_k_dst_rules_do_not_reject_shared_offensive_source_health_or_raw_ensemble() -> None:
    fetchers = (
        NamedCurrentProjectionFetcher("fftoday", lambda season: snapshot("fftoday", 4000.0)),
        NamedCurrentProjectionFetcher("cbs", lambda season: snapshot("cbs", 4200.0)),
    )

    result = build_current_live_forecasts(
        hodor_style_state(),
        fetchers=fetchers,
        clock=lambda: NOW,
    )

    assert result.successful_source_ids == ("cbs", "fftoday")
    assert not any("unsupported" in failure.lower() for failure in result.failed_sources)
    assert len(result.raw_ensemble) == 5
    assert len(result.fantasy_point_forecasts) == 1
    assert result.fantasy_point_forecasts[0].player_id == "p1"
    assert result.partial_fantasy_point_forecasts == ()

    families = {item.family: item for item in result.family_coverage}
    assert families["player_offense"].status == "FULL"
    assert families["kicker"].status == "UNSUPPORTED"
    assert families["dst"].status == "UNSUPPORTED"
    assert set(result.simulation_authority_blockers) == {
        "separate_k_dst_forecast_authority_required"
    }
    assert all(
        event.health_contract_version
        == "current-projection-health-v4:league-agnostic-offense-scale-integrity"
        for event in result.source_health_events
    )


def test_unknown_player_scoring_keeps_shared_raw_forecast_and_exposes_partial_subtotal() -> None:
    base = state()
    rules = base.league.rules.model_copy(
        update={
            "scoring": base.league.rules.scoring
            + (ScoringRule(stat="mystery_bonus", points=3.0),)
        }
    )
    custom = base.model_copy(
        update={"league": base.league.model_copy(update={"rules": rules})}
    )
    fetchers = (
        NamedCurrentProjectionFetcher("fftoday", lambda season: snapshot("fftoday", 4000.0)),
        NamedCurrentProjectionFetcher("cbs", lambda season: snapshot("cbs", 4200.0)),
    )

    result = build_current_live_forecasts(
        custom,
        fetchers=fetchers,
        clock=lambda: NOW,
    )

    assert len(result.raw_ensemble) == 5
    assert result.fantasy_point_forecasts == ()
    assert len(result.partial_fantasy_point_forecasts) == 1
    partial = result.partial_fantasy_point_forecasts[0]
    assert partial.player_id == "p1"
    assert partial.omitted_rule_stats == ("mystery_bonus",)
    assert "partial_player_scoring_coordinates_present" in result.simulation_authority_blockers
    assert "unsupported_player_offense_rules" in result.simulation_authority_blockers

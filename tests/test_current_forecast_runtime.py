from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest

from fsffl.forecast.current_runtime import (
    LiveForecastSourceHealthFailure,
    NamedCurrentProjectionFetcher,
    build_current_live_forecasts,
)
from fsffl.forecast.fumbles_lost_first_party import (
    FIRST_PARTY_FUMBLES_LOST_SOURCE,
    FirstPartyFumblesLostEvidenceTier,
    FirstPartyFumblesLostPlayerEvidence,
    FirstPartyFumblesLostSupplement,
)
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
    ProviderRef,
    RosterEntry,
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


def snapshot(
    provider: str,
    yards: float,
    *,
    captured_at: datetime = NOW,
    effective_at: datetime | None = None,
) -> CurrentProjectionSnapshot:
    resolved_effective_at = effective_at or (
        captured_at
        if provider == "cbs"
        else datetime(2026, 9, 4, 12, tzinfo=UTC)
    )
    return CurrentProjectionSnapshot(
        provider=provider,
        captured_at=captured_at,
        effective_at=resolved_effective_at,
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


def test_runtime_cutoff_is_canonical_state_even_when_retrieval_finishes_later() -> None:
    captured_after_state = NOW + timedelta(seconds=2)
    effective_before_state = NOW - timedelta(hours=1)
    fetchers = (
        NamedCurrentProjectionFetcher(
            "fftoday",
            lambda season: snapshot(
                "fftoday",
                4000.0,
                captured_at=captured_after_state,
                effective_at=effective_before_state,
            ),
        ),
        NamedCurrentProjectionFetcher(
            "cbs",
            lambda season: snapshot(
                "cbs",
                4200.0,
                captured_at=captured_after_state,
                effective_at=effective_before_state,
            ),
        ),
    )
    result = build_current_live_forecasts(
        state(),
        fetchers=fetchers,
        clock=lambda: captured_after_state,
    )
    assert result.evaluation_as_of == NOW
    assert result.successful_source_ids == ("cbs", "fftoday")
    assert all(row.as_of == NOW for row in result.raw_ensemble)
    assert all(
        row.provenance.retrieved_at == captured_after_state
        for row in result.raw_ensemble
    )


def test_provider_effective_after_canonical_state_fails_closed() -> None:
    after_state = NOW + timedelta(seconds=2)
    fetchers = (
        NamedCurrentProjectionFetcher(
            "fftoday",
            lambda season: snapshot(
                "fftoday",
                4000.0,
                captured_at=after_state,
                effective_at=NOW - timedelta(hours=1),
            ),
        ),
        NamedCurrentProjectionFetcher(
            "cbs",
            lambda season: snapshot(
                "cbs",
                4200.0,
                captured_at=after_state,
                effective_at=after_state,
            ),
        ),
    )
    with pytest.raises(LiveForecastSourceHealthFailure):
        build_current_live_forecasts(
            state(),
            fetchers=fetchers,
            clock=lambda: after_state,
        )


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
    assert result.model_version == "next2-current-runtime-v9:first-party-fumbles-lost"
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



def _synthetic_sleeper_state(
    *,
    external_id: str,
    scoring: tuple[ScoringRule, ...],
    lineup: tuple[LineupRequirement, ...],
) -> LeagueState:
    base = state()
    league_id = f"sleeper:{external_id}"
    rules = LeagueRules(
        team_count=2,
        roster_size=4,
        lineup=lineup,
        scoring=scoring,
    )
    league = base.league.model_copy(
        update={
            "league_id": league_id,
            "name": f"Synthetic {external_id}",
            "rules": rules,
            "provider_refs": (
                ProviderRef(provider="sleeper", external_id=external_id),
            ),
        }
    )
    teams = tuple(
        team.model_copy(update={"league_id": league_id})
        for team in base.teams
    )
    return base.model_copy(update={"league": league, "teams": teams})


def test_shared_forecast_pipeline_is_generic_across_unrelated_sleeper_leagues() -> None:
    fetchers = (
        NamedCurrentProjectionFetcher("fftoday", lambda season: snapshot("fftoday", 4000.0)),
        NamedCurrentProjectionFetcher("cbs", lambda season: snapshot("cbs", 4200.0)),
    )
    offense_only = _synthetic_sleeper_state(
        external_id="900000000000000001",
        lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
        scoring=(
            ScoringRule(stat="pass_yd", points=0.05),
            ScoringRule(stat="pass_td", points=6.0),
            ScoringRule(stat="pass_int", points=-1.0),
            ScoringRule(stat="rush_yd", points=0.1),
            ScoringRule(stat="rush_td", points=6.0),
        ),
    )
    k_dst_league = _synthetic_sleeper_state(
        external_id="900000000000000777",
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

    offense_result = build_current_live_forecasts(
        offense_only,
        fetchers=fetchers,
        clock=lambda: NOW,
    )
    k_dst_result = build_current_live_forecasts(
        k_dst_league,
        fetchers=fetchers,
        clock=lambda: NOW,
    )

    # Canonical raw player/stat Forecast truth is league-agnostic.
    assert [
        (item.player_id, item.metric, item.distribution.mean)
        for item in offense_result.raw_ensemble
    ] == [
        (item.player_id, item.metric, item.distribution.mean)
        for item in k_dst_result.raw_ensemble
    ]
    assert offense_result.successful_source_ids == ("cbs", "fftoday")
    assert k_dst_result.successful_source_ids == ("cbs", "fftoday")

    # League rules are applied only downstream and therefore produce the
    # appropriate scored result/capability without ID- or name-specific behavior.
    assert offense_result.fantasy_point_forecasts[0].distribution.mean == pytest.approx(485.0)
    assert k_dst_result.fantasy_point_forecasts[0].distribution.mean == pytest.approx(374.0)
    assert offense_result.simulation_authority_blockers == ()
    assert k_dst_result.simulation_authority_blockers == (
        "separate_k_dst_forecast_authority_required",
    )

    offense_families = {item.family: item for item in offense_result.family_coverage}
    k_dst_families = {item.family: item for item in k_dst_result.family_coverage}
    assert offense_families["player_offense"].status == "FULL"
    assert offense_families["kicker"].status == "NOT_APPLICABLE"
    assert offense_families["dst"].status == "NOT_APPLICABLE"
    assert k_dst_families["player_offense"].status == "FULL"
    assert k_dst_families["kicker"].status == "UNSUPPORTED"
    assert k_dst_families["dst"].status == "UNSUPPORTED"



def _fake_fumbles_lost_supplement(
    league_state: LeagueState,
    observations,
) -> FirstPartyFumblesLostSupplement:
    first = next(
        row
        for row in observations
        if row.player_id == "p1"
        and row.horizon.value == "season"
        and row.metric != ForecastMetric.FANTASY_POINTS
    )
    supplement_observation = first.model_copy(
        update={
            "metric": ForecastMetric.FUMBLES_LOST,
            "distribution": first.distribution.model_copy(
                update={"mean": 1.0, "stddev": 1.0}
            ),
            "source": FIRST_PARTY_FUMBLES_LOST_SOURCE,
            "model_version": "next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate",
            "provenance": first.provenance.model_copy(
                update={
                    "source": FIRST_PARTY_FUMBLES_LOST_SOURCE,
                    "source_version": "next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate",
                }
            ),
        }
    )
    evidence = FirstPartyFumblesLostPlayerEvidence(
        player_id="p1",
        position=Position.QB,
        historical_gsis_id="00-test",
        identity_method="retained_gsis",
        evidence_tier=FirstPartyFumblesLostEvidenceTier.HISTORY_PLUS_CURRENT,
        history_games=17,
        history_opportunities=500.0,
        current_games=2,
        current_opportunities=70.0,
        historical_role_opportunities_per_game=500.0 / 17.0,
        role_opportunities_per_game=32.0,
        position_lost_fumble_per_opportunity=0.005,
        mean_fumbles_lost=1.0,
        predictive_stddev=1.0,
    )
    return FirstPartyFumblesLostSupplement(
        season=2026,
        league_state_id=league_state.state_id,
        completed_through_week=2,
        current_input_captured_at=NOW,
        built_at=NOW,
        authority_valid_from=NOW,
        observed_schema_keys=("pass_att", "rec", "rush_att", "sack"),
        current_input_sha256="a" * 64,
        player_evidence=(evidence,),
        observations=(supplement_observation,),
    )


def test_fumbles_lost_supplement_promotes_material_player_scoring_to_full() -> None:
    base = state()
    state_with_cutoff = base.model_copy(
        update={
            "completed_through_week": 2,
            "league": base.league.model_copy(
                update={
                    "rules": base.league.rules.model_copy(
                        update={
                            "scoring": base.league.rules.scoring
                            + (ScoringRule(stat="fum_lost", points=-2.0),)
                        }
                    )
                }
            ),
        }
    )
    fetchers = (
        NamedCurrentProjectionFetcher("fftoday", lambda season: snapshot("fftoday", 4000.0)),
        NamedCurrentProjectionFetcher("cbs", lambda season: snapshot("cbs", 4200.0)),
    )

    without = build_current_live_forecasts(
        state_with_cutoff,
        fetchers=fetchers,
        clock=lambda: NOW,
        fumbles_lost_supplement_builder=lambda _state, _raw: (_ for _ in ()).throw(
            ValueError("no supplement")
        ),
    )
    assert without.fantasy_point_forecasts == ()
    assert len(without.partial_fantasy_point_forecasts) == 1
    assert without.partial_fantasy_point_forecasts[0].omitted_rule_stats == ("fum_lost",)
    # p1 is not rostered in this fixture, so its unresolved coordinate cannot
    # affect the Simulation consumer and must not create a league-wide blocker.
    assert without.simulation_material_partial_player_ids == ()
    assert "partial_player_scoring_coordinates_present" not in without.simulation_authority_blockers

    with_supplement = build_current_live_forecasts(
        state_with_cutoff,
        fetchers=fetchers,
        clock=lambda: NOW,
        fumbles_lost_supplement_builder=_fake_fumbles_lost_supplement,
    )
    assert len(with_supplement.fantasy_point_forecasts) == 1
    assert with_supplement.partial_fantasy_point_forecasts == ()
    assert with_supplement.fantasy_point_forecasts[0].distribution.mean == pytest.approx(372.0)
    assert with_supplement.fumbles_lost_supplement_player_count == 1
    assert with_supplement.fumbles_lost_supplement_failure is None
    assert with_supplement.fumbles_lost_supplement_authority_fingerprint
    assert "supplemental_mixed_vintage_current" in with_supplement.fantasy_point_forecasts[0].model_version
    assert FIRST_PARTY_FUMBLES_LOST_SOURCE in with_supplement.fantasy_point_forecasts[0].provenance.source

    # The canonical raw provider ensemble is not rebased by the supplement.
    assert with_supplement.raw_ensemble == without.raw_ensemble
    assert all(
        row.metric != ForecastMetric.FUMBLES_LOST
        for row in with_supplement.raw_ensemble
    )


def test_league_not_scoring_fumbles_lost_never_invokes_first_party_model() -> None:
    calls = []

    def unexpected(_state, _raw):
        calls.append(True)
        raise AssertionError("non-consuming league invoked FUMBLES_LOST supplement")

    fetchers = (
        NamedCurrentProjectionFetcher("fftoday", lambda season: snapshot("fftoday", 4000.0)),
        NamedCurrentProjectionFetcher("cbs", lambda season: snapshot("cbs", 4200.0)),
    )
    result = build_current_live_forecasts(
        state(),
        fetchers=fetchers,
        clock=lambda: NOW,
        fumbles_lost_supplement_builder=unexpected,
    )
    assert calls == []
    assert result.fumbles_lost_supplement_player_count == 0
    assert result.fumbles_lost_supplement_authority_fingerprint is None
    assert result.fumbles_lost_supplement_failure is None
    assert result.fantasy_point_forecasts[0].distribution.mean == pytest.approx(374.0)



def test_unresolved_fumbles_lost_blocks_simulation_only_for_active_roster_subject() -> None:
    base = state()
    active_state = base.model_copy(
        update={
            "completed_through_week": 2,
            "league": base.league.model_copy(
                update={
                    "rules": base.league.rules.model_copy(
                        update={
                            "scoring": base.league.rules.scoring
                            + (ScoringRule(stat="fum_lost", points=-2.0),)
                        }
                    )
                }
            ),
            "team_states": (
                TeamState(
                    team_id="a",
                    roster=(RosterEntry(player_id="p1", slot=RosterSlot.BENCH),),
                ),
                TeamState(team_id="b", roster=()),
            ),
        }
    )
    fetchers = (
        NamedCurrentProjectionFetcher("fftoday", lambda season: snapshot("fftoday", 4000.0)),
        NamedCurrentProjectionFetcher("cbs", lambda season: snapshot("cbs", 4200.0)),
    )

    result = build_current_live_forecasts(
        active_state,
        fetchers=fetchers,
        clock=lambda: NOW,
        fumbles_lost_supplement_builder=lambda _state, _raw: (_ for _ in ()).throw(
            ValueError("unresolved subject evidence")
        ),
    )

    assert len(result.partial_fantasy_point_forecasts) == 1
    assert result.partial_fantasy_point_forecasts[0].player_id == "p1"
    assert result.simulation_material_partial_player_ids == ("p1",)
    assert "partial_player_scoring_coordinates_present" in result.simulation_authority_blockers


def test_taxi_or_ir_partial_subject_does_not_block_simulation_consumer() -> None:
    base = state()
    scoped_state = base.model_copy(
        update={
            "completed_through_week": 2,
            "league": base.league.model_copy(
                update={
                    "rules": base.league.rules.model_copy(
                        update={
                            "scoring": base.league.rules.scoring
                            + (ScoringRule(stat="fum_lost", points=-2.0),)
                        }
                    )
                }
            ),
            "team_states": (
                TeamState(
                    team_id="a",
                    roster=(RosterEntry(player_id="p1", slot=RosterSlot.TAXI),),
                ),
                TeamState(team_id="b", roster=()),
            ),
        }
    )
    fetchers = (
        NamedCurrentProjectionFetcher("fftoday", lambda season: snapshot("fftoday", 4000.0)),
        NamedCurrentProjectionFetcher("cbs", lambda season: snapshot("cbs", 4200.0)),
    )

    result = build_current_live_forecasts(
        scoped_state,
        fetchers=fetchers,
        clock=lambda: NOW,
        fumbles_lost_supplement_builder=lambda _state, _raw: (_ for _ in ()).throw(
            ValueError("unresolved taxi subject evidence")
        ),
    )

    assert len(result.partial_fantasy_point_forecasts) == 1
    assert result.simulation_material_partial_player_ids == ()
    assert "partial_player_scoring_coordinates_present" not in result.simulation_authority_blockers

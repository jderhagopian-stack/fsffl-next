from __future__ import annotations

import copy
from collections import Counter
from datetime import UTC, datetime

import pytest

from fsffl.forecast.fumbles_lost_first_party import (
    FIRST_PARTY_FUMBLES_LOST_SOURCE,
    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
    FirstPartyFumblesLostEvidenceTier,
    FirstPartyFumblesLostPointAuthorityUnavailable,
    FirstPartyFumblesLostPlayerEvidence,
    FirstPartyFumblesLostSupplement,
    build_first_party_fumbles_lost_supplement,
)
from fsffl.forecast.fumbles_lost_rolling_authority import (
    FumblesLostProductionTable,
    ROLLING_FUMBLES_LOST_MODEL_VERSION,
    frozen_fumbles_lost_production_table_2026,
    production_table_payload_fingerprint,
    validate_annual_rollover_candidate,
)
from fsffl.forecast.fumbles_lost_first_party_priors import (
    CALIBRATION_SCALAR_2026,
    COLD_START_STDDEV_FLOOR,
    MODEL_VERSION,
    PLAYER_PRIORS,
    POSITION_LOST_FUMBLE_PER_OPPORTUNITY,
    POSITION_OPPORTUNITY_PER_GAME,
    POSITION_RESIDUAL_STDDEV_FLOOR,
    REQUIRED_COMPLETED_THROUGH_WEEK,
    TRAINING_SEASONS,
)
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.persistence.annual_preseason_snapshot import (
    ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
)
from fsffl.persistence.runtime_cache import (
    FORECAST_ARTIFACT_KIND,
    PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
)
from fsffl.persistence.supplemental_coordinate import (
    SUPPLEMENTAL_COORDINATE_ENSEMBLE_ARTIFACT_KIND,
    decode_first_party_fumbles_lost_supplement,
    first_party_fumbles_lost_supplement_artifact,
)
from fsffl.providers.sleeper_weekly_stats import (
    SleeperNflState,
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
    ScoringRule,
    Team,
    TeamState,
)


CAPTURED = datetime(2026, 9, 26, 3, 0, tzinfo=UTC)
PERIOD_START = datetime(2026, 9, 10, 0, 0, tzinfo=UTC)
PERIOD_END = datetime(2027, 1, 5, 0, 0, tzinfo=UTC)


def test_weekly_stats_nfl_state_uses_same_strongest_week_coordinate_as_canonical_state() -> None:
    source = SleeperWeeklyStatsSource(
        http_get_json=lambda _url: {
            "season": "2026",
            "week": 3,
            "display_week": 4,
            "leg": 4,
            "season_type": "regular",
        },
        clock=lambda: CAPTURED,
    )

    provider_state = source.fetch_nfl_state()

    assert provider_state.week == 3
    assert provider_state.display_week == 4
    assert provider_state.leg == 4
    assert provider_state.completed_through_week == 3


class FakeSleeperStats:
    def __init__(self, rows_by_week, *, completed_through_week: int = 2):
        self.rows_by_week = rows_by_week
        self.completed_through_week = completed_through_week
        self.nfl_state_calls = 0
        self.requested_weeks = []

    def fetch_nfl_state(self):
        self.nfl_state_calls += 1
        return SleeperNflState(
            season=2026,
            week=self.completed_through_week + 1,
            season_type="regular",
            captured_at=CAPTURED,
        )

    def fetch_week(self, *, season: int, week: int):
        assert season == 2026
        self.requested_weeks.append(week)
        return self.rows_by_week.get(week, ())


def _state(
    player_id: str,
    position: Position,
    *,
    completed_through_week: int = 2,
) -> LeagueState:
    provenance = Provenance(
        source="test",
        retrieved_at=CAPTURED,
        effective_at=CAPTURED,
    )
    league = League(
        league_id="sleeper:test",
        name="Test",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=1,
            lineup=(),
            scoring=(
                ScoringRule(stat="rush_yd", points=0.1),
                ScoringRule(stat="fum_lost", points=-2.0),
            ),
        ),
    )
    return LeagueState(
        league=league,
        as_of=CAPTURED,
        teams=(
            Team(team_id="a", league_id=league.league_id, display_name="A"),
            Team(team_id="b", league_id=league.league_id, display_name="B"),
        ),
        team_states=(
            TeamState(team_id="a", roster=()),
            TeamState(team_id="b", roster=()),
        ),
        players=(
            Player(
                player_id=player_id,
                full_name="Test Player",
                position=position,
                nfl_team="BUF",
            ),
        ),
        player_states=(
            PlayerState(
                player_id=player_id,
                as_of=CAPTURED,
                nfl_team="BUF",
                provenance=provenance,
            ),
        ),
        completed_through_week=completed_through_week,
    )


def _base(player_id: str, position: Position) -> tuple[ForecastObservation, ...]:
    provenance = Provenance(
        source="immutable-ordinary",
        retrieved_at=CAPTURED,
        effective_at=CAPTURED,
    )
    return (
        ForecastObservation(
            player_id=player_id,
            position=position,
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.RUSH_YARDS,
            period_start=PERIOD_START,
            period_end=PERIOD_END,
            distribution=ForecastDistribution(mean=500.0, stddev=100.0),
            source="fsffl:live_equal_weight",
            model_version="ordinary-v1",
            as_of=CAPTURED,
            provenance=provenance,
        ),
    )


def _line(player_id: str, week: int, **stats: float) -> SleeperWeeklyStatLine:
    required = {"pass_att": 0.0, "sack": 0.0, "rush_att": 0.0, "rec": 0.0}
    required.update(stats)
    return SleeperWeeklyStatLine(
        player_id=player_id,
        season=2026,
        week=week,
        stats=required,
        captured_at=CAPTURED,
    )


def test_frozen_priors_and_rolling_contract_match_accepted_research() -> None:
    assert MODEL_VERSION == "next2-fumbles-lost-first-party-v1:calibrated-position-opportunity-rate"
    assert CALIBRATION_SCALAR_2026 == 0.6158756078393594
    assert REQUIRED_COMPLETED_THROUGH_WEEK == 2
    assert TRAINING_SEASONS == (2021, 2022, 2023, 2024, 2025)
    assert len(PLAYER_PRIORS) == 335

    tiers = Counter(row[3] for row in PLAYER_PRIORS.values())
    assert tiers == {
        "history_plus_current": 258,
        "history_only": 40,
        "current_only": 28,
        "cold_start": 1,
        "unmapped": 8,
    }
    assert all(value > 0 for value in POSITION_RESIDUAL_STDDEV_FLOOR.values())
    assert COLD_START_STDDEV_FLOOR > 0
    table = frozen_fumbles_lost_production_table_2026()
    assert table.contract_version == ROLLING_FUMBLES_LOST_MODEL_VERSION
    assert table.supported_completed_through_weeks == tuple(range(2, 18))
    assert table.calibration_scalar(2) == CALIBRATION_SCALAR_2026
    assert table.calibration_scalar(3) == 0.6183406074632098
    assert table.role_prior_games == 4.0


def test_wr_shadow_formula_reproduces_accepted_week2_output() -> None:
    player_id = "sleeper:player:10213"
    source = FakeSleeperStats(
        {
            1: (_line(player_id, 1, rush_att=1.0, rec=3.0),),
            2: (_line(player_id, 2, rec=3.0),),
        }
    )
    base = _base(player_id, Position.WR)
    supplement = build_first_party_fumbles_lost_supplement(
        _state(player_id, Position.WR),
        base_observations=base,
        stats_source=source,  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    )

    assert supplement.calibration_scalar == 0.6158756078393594
    assert supplement.completed_through_week == 2
    assert supplement.observations[0].distribution.mean == pytest.approx(
        0.19742278, abs=2e-7
    )
    assert supplement.observations[0].distribution.stddev == pytest.approx(
        0.44432283, abs=2e-7
    )
    evidence = supplement.player_evidence[0]
    assert evidence.current_games == 2
    assert evidence.current_opportunities == pytest.approx(7.0)
    assert evidence.evidence_tier == FirstPartyFumblesLostEvidenceTier.HISTORY_PLUS_CURRENT


def test_qb_opportunity_uses_offensive_sack_not_idp_sack() -> None:
    player_id = "sleeper:player:11256"
    source = FakeSleeperStats(
        {
            1: (
                _line(
                    player_id,
                    1,
                    pass_att=6.0,
                    sack=2.0,
                    rush_att=2.0,
                    idp_sack=99.0,
                ),
            ),
            2: (),
        }
    )
    supplement = build_first_party_fumbles_lost_supplement(
        _state(player_id, Position.QB),
        base_observations=_base(player_id, Position.QB),
        stats_source=source,  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    )
    assert supplement.player_evidence[0].current_opportunities == pytest.approx(10.0)
    assert supplement.observations[0].distribution.mean == pytest.approx(
        0.8827901, abs=3e-7
    )


def test_cutoff_mismatch_fails_closed_and_total_fumbles_are_not_a_substitute() -> None:
    player_id = "sleeper:player:10213"
    source = FakeSleeperStats(
        {
            1: (_line(player_id, 1, fum=4.0, fum_lost=1.0, rec=3.0),),
            2: (_line(player_id, 2, rec=4.0),),
        },
        completed_through_week=3,
    )
    with pytest.raises(ValueError, match="cutoff does not match canonical State"):
        build_first_party_fumbles_lost_supplement(
            _state(player_id, Position.WR),
            base_observations=_base(player_id, Position.WR),
            stats_source=source,  # type: ignore[arg-type]
            clock=lambda: CAPTURED,
        )

    good = FakeSleeperStats(
        {
            1: (_line(player_id, 1, fum=99.0, rec=3.0),),
            2: (_line(player_id, 2, rec=4.0),),
        }
    )
    supplement = build_first_party_fumbles_lost_supplement(
        _state(player_id, Position.WR),
        base_observations=_base(player_id, Position.WR),
        stats_source=good,  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    )
    # Total fumbles are not an input to the model; identical opportunities imply
    # the same prediction regardless of a bogus/high total-fumbles field.
    assert supplement.observations[0].distribution.mean == pytest.approx(
        0.19742278, abs=2e-7
    )


def test_missing_required_current_schema_fails_closed_not_zero() -> None:
    player_id = "sleeper:player:10213"
    row = SleeperWeeklyStatLine(
        player_id=player_id,
        season=2026,
        week=1,
        stats={"rush_att": 1.0, "rec": 2.0},
        captured_at=CAPTURED,
    )
    source = FakeSleeperStats({1: (row,), 2: ()})
    with pytest.raises(ValueError, match="lacks accepted opportunity semantics"):
        build_first_party_fumbles_lost_supplement(
            _state(player_id, Position.WR),
            base_observations=_base(player_id, Position.WR),
            stats_source=source,  # type: ignore[arg-type]
            clock=lambda: CAPTURED,
        )


def test_identity_light_and_cold_start_never_receive_zero_uncertainty() -> None:
    identity_light_id = "sleeper:player:13269"
    identity_light = build_first_party_fumbles_lost_supplement(
        _state(identity_light_id, Position.QB),
        base_observations=_base(identity_light_id, Position.QB),
        stats_source=FakeSleeperStats(
            {
                1: (_line(identity_light_id, 1),),
                2: (_line(identity_light_id, 2),),
            }
        ),  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    ).player_evidence[0]
    assert identity_light.evidence_tier == FirstPartyFumblesLostEvidenceTier.IDENTITY_LIGHT
    assert identity_light.predictive_stddev >= COLD_START_STDDEV_FLOOR

    cold_id = "sleeper:player:12511"
    # A different player proves feed schema while the cold-start target has no
    # current Week-1/2 row of its own.
    cold = build_first_party_fumbles_lost_supplement(
        _state(cold_id, Position.QB),
        base_observations=_base(cold_id, Position.QB),
        stats_source=FakeSleeperStats(
            {
                1: (_line("sleeper:player:other", 1),),
                2: (),
            }
        ),  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    ).player_evidence[0]
    assert cold.evidence_tier == FirstPartyFumblesLostEvidenceTier.COLD_START
    assert cold.predictive_stddev >= COLD_START_STDDEV_FLOOR
    assert cold.predictive_stddev > 0


def test_first_party_artifact_is_current_only_and_preserves_raw_forecast() -> None:
    player_id = "sleeper:player:10213"
    base = _base(player_id, Position.WR)
    supplement = build_first_party_fumbles_lost_supplement(
        _state(player_id, Position.WR),
        base_observations=base,
        stats_source=FakeSleeperStats(
            {
                1: (_line(player_id, 1, rec=3.0),),
                2: (_line(player_id, 2, rec=4.0),),
            }
        ),  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    )
    assert base == _base(player_id, Position.WR)
    assert supplement.preseason_eligible is False
    assert supplement.annual_preseason_snapshot_eligible is False
    assert supplement.historical_pit_eligible is False
    assert supplement.backfill_allowed is False
    assert supplement.authority_valid_from == CAPTURED

    record = first_party_fumbles_lost_supplement_artifact(supplement)
    assert record.key.artifact_kind == SUPPLEMENTAL_COORDINATE_ENSEMBLE_ARTIFACT_KIND
    assert record.key.model_version == FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
    assert record.key.artifact_kind != FORECAST_ARTIFACT_KIND
    assert record.key.artifact_kind != PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND
    assert record.key.artifact_kind != ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND
    assert decode_first_party_fumbles_lost_supplement(dict(record.payload)) == supplement


def test_builder_refuses_to_overwrite_existing_fumbles_lost_truth() -> None:
    player_id = "sleeper:player:10213"
    base = _base(player_id, Position.WR)
    existing = base[0].model_copy(
        update={
            "metric": ForecastMetric.FUMBLES_LOST,
            "distribution": ForecastDistribution(mean=1.0, stddev=0.5),
        }
    )
    with pytest.raises(ValueError, match="cannot replace ordinary raw Forecast"):
        build_first_party_fumbles_lost_supplement(
            _state(player_id, Position.WR),
            base_observations=base + (existing,),
            stats_source=FakeSleeperStats(
                {1: (_line(player_id, 1, rec=3.0),), 2: (_line(player_id, 2, rec=4.0),)}
            ),  # type: ignore[arg-type]
            clock=lambda: CAPTURED,
        )



def test_prior_absent_state_subject_with_current_input_uses_current_only_tier() -> None:
    player_id = "sleeper:player:99999991"
    assert player_id not in PLAYER_PRIORS
    supplement = build_first_party_fumbles_lost_supplement(
        _state(player_id, Position.WR),
        base_observations=(),
        stats_source=FakeSleeperStats(
            {
                1: (_line(player_id, 1, rec=2.0),),
                2: (_line(player_id, 2, rec=3.0),),
            }
        ),  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    )

    assert supplement.subject_universe_player_ids == (player_id,)
    assert supplement.provider_absent_player_ids == (player_id,)
    assert supplement.frozen_prior_absent_player_ids == (player_id,)
    assert supplement.omitted_player_ids == ()
    assert len(supplement.observations) == 1
    evidence = supplement.player_evidence[0]
    assert evidence.identity_method == "canonical_sleeper_current_input"
    assert evidence.evidence_tier == FirstPartyFumblesLostEvidenceTier.CURRENT_ONLY
    assert evidence.history_games == 0
    assert evidence.history_opportunities == 0.0
    assert evidence.current_games == 2
    assert evidence.current_opportunities == pytest.approx(5.0)
    assert evidence.mean_fumbles_lost > 0
    assert evidence.predictive_stddev >= POSITION_RESIDUAL_STDDEV_FLOOR["WR"]
    assert supplement.observations[0].distribution.stddev > 0
    assert supplement.observations[0].period_start == datetime(2026, 9, 1, tzinfo=UTC)
    assert supplement.observations[0].period_end == datetime(2027, 3, 1, tzinfo=UTC)


def test_prior_absent_provider_target_is_not_omitted_or_silently_zeroed() -> None:
    player_id = "sleeper:player:99999992"
    assert player_id not in PLAYER_PRIORS
    supplement = build_first_party_fumbles_lost_supplement(
        _state(player_id, Position.WR),
        base_observations=_base(player_id, Position.WR),
        stats_source=FakeSleeperStats(
            {
                1: (_line(player_id, 1, rush_att=1.0, rec=4.0),),
                2: (_line(player_id, 2, rec=2.0),),
            }
        ),  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    )

    assert supplement.provider_absent_player_ids == ()
    assert supplement.frozen_prior_absent_player_ids == (player_id,)
    assert supplement.omitted_player_ids == ()
    assert supplement.observations[0].player_id == player_id
    assert supplement.observations[0].distribution.mean > 0
    assert supplement.player_evidence[0].evidence_tier == FirstPartyFumblesLostEvidenceTier.CURRENT_ONLY


def test_prior_absent_subject_without_current_row_is_identity_light_with_nonzero_uncertainty() -> None:
    player_id = "sleeper:player:99999993"
    assert player_id not in PLAYER_PRIORS
    supplement = build_first_party_fumbles_lost_supplement(
        _state(player_id, Position.TE),
        base_observations=(),
        stats_source=FakeSleeperStats(
            {
                1: (_line("sleeper:player:other", 1, rec=1.0),),
                2: (),
            }
        ),  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    )

    assert supplement.frozen_prior_absent_player_ids == (player_id,)
    assert supplement.omitted_player_ids == ()
    evidence = supplement.player_evidence[0]
    assert evidence.identity_method == "unmapped"
    assert evidence.evidence_tier == FirstPartyFumblesLostEvidenceTier.IDENTITY_LIGHT
    assert evidence.current_games == 0
    assert evidence.mean_fumbles_lost > 0
    assert evidence.predictive_stddev >= COLD_START_STDDEV_FLOOR
    assert supplement.observations[0].distribution.stddev >= COLD_START_STDDEV_FLOOR



def test_2027_governed_table_builds_and_consumes_refreshed_role_rate_inputs() -> None:
    prior = frozen_fumbles_lost_production_table_2026()
    payload = copy.deepcopy(dict(prior.payload))
    payload["target_season"] = 2027

    player_priors = {
        player_id: {
            "position": row[0],
            "historical_gsis_id": row[1],
            "identity_method": row[2],
            "accepted_tier": row[3],
            "history_games": row[4],
            "history_opportunities": row[5],
        }
        for player_id, row in PLAYER_PRIORS.items()
    }
    player_id = "sleeper:player:10213"
    player_priors[player_id] = {
        **player_priors[player_id],
        "history_games": 10,
        "history_opportunities": 100.0,
    }
    rates = dict(POSITION_LOST_FUMBLE_PER_OPPORTUNITY)
    roles = dict(POSITION_OPPORTUNITY_PER_GAME)
    rates["WR"] = 0.006
    roles["WR"] = 3.25
    for cutoff in (0, 1):
        row = payload["season_start"]["cutoffs"][str(cutoff)]
        row["fallback_eligibility"] = {
            tier: {
                position.value: (
                    bool(row["cold_start_fallback_eligible"][position.value])
                    if tier in {"cold_start", "identity_light"}
                    else True
                )
                for position in (Position.QB, Position.RB, Position.WR, Position.TE)
            }
            for tier in (
                "history_plus_current",
                "history_only",
                "current_only",
                "cold_start",
                "identity_light",
            )
        }

    payload["annual_freeze"] = {
        "exact_source_hashes": {"2026_weekly_exact_lost_fumbles": "a" * 64},
        "exact_source_urls": {
            "2026_weekly_exact_lost_fumbles": "https://example.invalid/2026-exact-weekly"
        },
        "source_captured_at": {
            "2026_weekly_exact_lost_fumbles": "2027-02-15T12:00:00+00:00"
        },
        "built_at": "2027-02-15T13:00:00+00:00",
        "training_seasons": [2021, 2022, 2023, 2024, 2025, 2026],
        "calibration_pseudo_current_seasons": [2022, 2023, 2024, 2025, 2026],
        "chronology_validation_passed": True,
        "position_lost_fumble_per_opportunity": rates,
        "position_opportunity_per_game": roles,
        "player_role_priors": player_priors,
        "player_prior_sufficient_statistics_fingerprint": (
            production_table_payload_fingerprint(
                {"player_role_priors": player_priors}
            )
        ),
    }
    candidate = FumblesLostProductionTable(
        payload=payload,
        fingerprint=production_table_payload_fingerprint(payload),
    )
    validate_annual_rollover_candidate(
        candidate,
        prior=prior,
        newly_completed_heldout_rmse={
            position.value: {cutoff: 0.0 for cutoff in range(2, 18)}
            for position in (Position.QB, Position.RB, Position.WR, Position.TE)
        },
        newly_completed_materiality_event_max={
            position.value: {cutoff: 0.0 for cutoff in range(0, 18)}
            for position in (Position.QB, Position.RB, Position.WR, Position.TE)
        },
        observed_population_coverage={
            position.value: {
                cutoff: {
                    tier: 1.0
                    for tier in (
                        "history_plus_current",
                        "history_only",
                        "current_only",
                        "cold_start",
                    )
                }
                for cutoff in range(0, 18)
            }
            for position in (Position.QB, Position.RB, Position.WR, Position.TE)
        },
        newly_completed_rolling_adequacy={
            "heldout_season": 2026,
            "cutoffs": {
                cutoff: {
                    "pooled_rolling_rmse": 0.5,
                    "pooled_zero_rmse": 1.0,
                    "heldout_season_rmse": 0.5,
                    "heldout_season_zero_rmse": 1.0,
                    "pooled_bias": 0.0,
                    "pooled_zero_gap": 0.0,
                }
                for cutoff in range(2, 18)
            },
        },
    )

    captured_2027 = datetime(2027, 9, 28, 3, 0, tzinfo=UTC)
    base_state = _state(
        player_id,
        Position.WR,
        completed_through_week=3,
    )
    state_2027 = base_state.model_copy(
        update={
            "as_of": captured_2027,
            "league": base_state.league.model_copy(update={"season": 2027}),
            "player_states": (
                base_state.player_states[0].model_copy(
                    update={"as_of": captured_2027}
                ),
            ),
        }
    )

    class FutureStats:
        requested_weeks: list[int]

        def __init__(self) -> None:
            self.requested_weeks = []

        def fetch_nfl_state(self):
            return SleeperNflState(
                season=2027,
                week=4,
                season_type="regular",
                captured_at=captured_2027,
            )

        def fetch_week(self, *, season: int, week: int):
            assert season == 2027
            self.requested_weeks.append(week)
            return (
                SleeperWeeklyStatLine(
                    player_id=player_id,
                    season=2027,
                    week=week,
                    stats={
                        "pass_att": 0.0,
                        "sack": 0.0,
                        "rush_att": 0.0,
                        "rec": 2.0,
                    },
                    captured_at=captured_2027,
                ),
            )

    source = FutureStats()
    supplement = build_first_party_fumbles_lost_supplement(
        state_2027,
        base_observations=(),
        stats_source=source,  # type: ignore[arg-type]
        clock=lambda: captured_2027,
        production_table=candidate,
    )

    # Historical role = 100 / 10 = 10. Current = 6 opportunities / 3 games.
    expected_role = (6.0 + 4.0 * 10.0) / (3.0 + 4.0)
    expected_mean = (
        candidate.calibration_scalar(3)
        * candidate.target_games
        * expected_role
        * rates["WR"]
    )
    assert source.requested_weeks == [1, 2, 3]
    assert supplement.production_table_target_season == 2027
    assert supplement.production_table_fingerprint == candidate.fingerprint
    assert supplement.annual_freeze_source_hashes == (
        ("2026_weekly_exact_lost_fumbles", "a" * 64),
    )
    assert supplement.training_seasons[-1] == 2026
    assert supplement.player_evidence[0].historical_role_opportunities_per_game == pytest.approx(10.0)
    assert supplement.player_evidence[0].position_lost_fumble_per_opportunity == pytest.approx(0.006)
    assert supplement.observations[0].distribution.mean == pytest.approx(expected_mean)
    assert supplement.observations[0].distribution.stddev > 0
    record = first_party_fumbles_lost_supplement_artifact(supplement)
    assert decode_first_party_fumbles_lost_supplement(dict(record.payload)) == supplement


def test_week0_and_week1_are_explicit_omission_without_provider_fetch() -> None:
    player_id = "sleeper:player:10213"
    for cutoff in (0, 1):
        source = FakeSleeperStats({}, completed_through_week=cutoff)
        with pytest.raises(
            FirstPartyFumblesLostPointAuthorityUnavailable,
            match="explicitly omitted before completed Week 2",
        ):
            build_first_party_fumbles_lost_supplement(
                _state(player_id, Position.WR, completed_through_week=cutoff),
                base_observations=_base(player_id, Position.WR),
                stats_source=source,  # type: ignore[arg-type]
                clock=lambda: CAPTURED,
            )
        assert source.nfl_state_calls == 0
        assert source.requested_weeks == []


def test_week3_uses_exact_frozen_scalar_floor_and_fetches_only_weeks_1_through_3() -> None:
    player_id = "sleeper:player:10213"
    source = FakeSleeperStats(
        {
            1: (_line(player_id, 1, rec=3.0),),
            2: (_line(player_id, 2, rec=4.0),),
            3: (_line(player_id, 3, rush_att=1.0, rec=2.0),),
            4: (_line(player_id, 4, rec=99.0),),
        },
        completed_through_week=3,
    )
    supplement = build_first_party_fumbles_lost_supplement(
        _state(player_id, Position.WR, completed_through_week=3),
        base_observations=_base(player_id, Position.WR),
        stats_source=source,  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    )
    table = frozen_fumbles_lost_production_table_2026()
    assert source.requested_weeks == [1, 2, 3]
    assert supplement.current_input_weeks == (1, 2, 3)
    assert supplement.calibration_scalar == 0.6183406074632098
    assert supplement.calibration_scalar == table.calibration_scalar(3)
    assert supplement.player_evidence[0].current_games == 3
    assert supplement.player_evidence[0].current_opportunities == pytest.approx(10.0)
    assert supplement.player_evidence[0].predictive_stddev >= table.uncertainty_floor(
        3, Position.WR
    )
    assert supplement.production_table_fingerprint == table.fingerprint
    assert "cutoff=3" in supplement.observations[0].provenance.source_version


def test_all_rolling_cutoff_scalars_and_uncertainty_floors_are_frozen_positive() -> None:
    table = frozen_fumbles_lost_production_table_2026()
    for cutoff in range(2, 18):
        assert table.calibration_scalar(cutoff) > 0
        for position in (Position.QB, Position.RB, Position.WR, Position.TE):
            assert table.uncertainty_floor(cutoff, position) > 0


def test_cutoff_advance_changes_authority_fingerprint_and_never_reads_future_week() -> None:
    player_id = "sleeper:player:10213"
    source2 = FakeSleeperStats(
        {
            1: (_line(player_id, 1, rec=3.0),),
            2: (_line(player_id, 2, rec=4.0),),
            3: (_line(player_id, 3, rec=50.0),),
        },
        completed_through_week=2,
    )
    week2 = build_first_party_fumbles_lost_supplement(
        _state(player_id, Position.WR, completed_through_week=2),
        base_observations=_base(player_id, Position.WR),
        stats_source=source2,  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    )
    assert source2.requested_weeks == [1, 2]

    source3 = FakeSleeperStats(
        {
            1: (_line(player_id, 1, rec=3.0),),
            2: (_line(player_id, 2, rec=4.0),),
            3: (_line(player_id, 3, rec=2.0),),
            4: (_line(player_id, 4, rec=50.0),),
        },
        completed_through_week=3,
    )
    week3 = build_first_party_fumbles_lost_supplement(
        _state(player_id, Position.WR, completed_through_week=3),
        base_observations=_base(player_id, Position.WR),
        stats_source=source3,  # type: ignore[arg-type]
        clock=lambda: CAPTURED,
    )
    assert source3.requested_weeks == [1, 2, 3]
    assert week2.authority_fingerprint != week3.authority_fingerprint
    assert week2.current_input_sha256 != week3.current_input_sha256


def test_week18_has_no_point_authority_and_never_fetches_provider_weeks() -> None:
    player_id = "sleeper:player:10213"
    source = FakeSleeperStats({}, completed_through_week=18)
    with pytest.raises(
        FirstPartyFumblesLostPointAuthorityUnavailable,
        match="Week 18 has no remaining-season rolling point authority",
    ):
        build_first_party_fumbles_lost_supplement(
            _state(player_id, Position.WR, completed_through_week=18),
            base_observations=_base(player_id, Position.WR),
            stats_source=source,  # type: ignore[arg-type]
            clock=lambda: CAPTURED,
        )
    assert source.nfl_state_calls == 0
    assert source.requested_weeks == []

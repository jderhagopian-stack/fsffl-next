from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

import pytest

from fsffl.forecast.fumbles_lost_first_party import (
    FIRST_PARTY_FUMBLES_LOST_SOURCE,
    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
    FirstPartyFumblesLostEvidenceTier,
    FirstPartyFumblesLostPlayerEvidence,
    FirstPartyFumblesLostSupplement,
    build_first_party_fumbles_lost_supplement,
)
from fsffl.forecast.fumbles_lost_first_party_priors import (
    CALIBRATION_SCALAR_2026,
    COLD_START_STDDEV_FLOOR,
    MODEL_VERSION,
    PLAYER_PRIORS,
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
from fsffl.providers.sleeper_weekly_stats import SleeperNflState, SleeperWeeklyStatLine
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


class FakeSleeperStats:
    def __init__(self, rows_by_week, *, completed_through_week: int = 2):
        self.rows_by_week = rows_by_week
        self.completed_through_week = completed_through_week

    def fetch_nfl_state(self):
        return SleeperNflState(
            season=2026,
            week=self.completed_through_week + 1,
            season_type="regular",
            captured_at=CAPTURED,
        )

    def fetch_week(self, *, season: int, week: int):
        assert season == 2026
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


def test_frozen_model_contract_matches_accepted_research() -> None:
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
    with pytest.raises(ValueError, match="completed Week 2"):
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

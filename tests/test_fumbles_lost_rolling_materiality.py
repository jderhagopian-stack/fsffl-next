from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest

from fsffl.forecast.fumbles_lost_first_party import FirstPartyFumblesLostEvidenceTier
from fsffl.forecast.fumbles_lost_materiality import (
    assess_fumbles_lost_non_material_partial,
)
from fsffl.forecast.fumbles_lost_rolling_authority import (
    FumblesLostProductionTable,
    NON_MATERIAL_PARTIAL_AUTHORITY,
    frozen_fumbles_lost_production_table_2026,
    resolve_fumbles_lost_production_table,
    validate_annual_rollover_candidate,
)
from fsffl.forecast.league_scoring import PartialFantasyPointForecast
from fsffl.forecast.models import ForecastDistribution, ForecastHorizon
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    Position,
    Provenance,
    ScoringRule,
    Team,
    TeamState,
)


NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
END = datetime(2027, 3, 1, tzinfo=UTC)


def _state(
    *,
    position: Position = Position.WR,
    cutoff: int = 3,
    coefficient: float = -1.0,
    canonical_position: Position | None = None,
) -> LeagueState:
    player_position = canonical_position or position
    league = League(
        league_id="sleeper:materiality",
        name="Materiality",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=1,
            lineup=(),
            scoring=(
                ScoringRule(stat="rush_yd", points=0.1),
                ScoringRule(stat="fum_lost", points=coefficient),
            ),
        ),
    )
    return LeagueState(
        league=league,
        as_of=NOW,
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
                player_id="sleeper:player:materiality",
                full_name="Materiality Player",
                position=player_position,
                nfl_team="BUF",
            ),
        ),
        player_states=(),
        completed_through_week=cutoff,
    )


def _partial(position: Position) -> PartialFantasyPointForecast:
    provenance = Provenance(
        source="test-supported-subtotal",
        retrieved_at=NOW,
        effective_at=NOW,
    )
    return PartialFantasyPointForecast(
        player_id="sleeper:player:materiality",
        position=position,
        horizon=ForecastHorizon.SEASON,
        period_start=datetime(2026, 9, 1, tzinfo=UTC),
        period_end=END,
        distribution=ForecastDistribution(mean=100.0, stddev=10.0),
        supported_rule_stats=("rush_yd",),
        omitted_rule_stats=("fum_lost",),
        omission_reasons=("FUMBLES_LOST remains explicitly omitted",),
        source="test",
        model_version="test-partial",
        as_of=NOW,
        provenance=provenance,
    )


def test_materiality_uses_corrected_all_population_bound_and_passes_at_exact_inequality() -> None:
    table = frozen_fumbles_lost_production_table_2026()
    threshold = table.payload["cutoffs"]["3"][  # type: ignore[index]
        "minimum_supported_fp_stddev_for_non_material_fsffl"
    ]["WR"]
    assessment = assess_fumbles_lost_non_material_partial(
        _state(position=Position.WR, cutoff=3),
        partial=_partial(Position.WR),
        supported_fantasy_point_stddev=float(threshold),
        supplement=None,
    )
    assert assessment.evidence_tier == FirstPartyFumblesLostEvidenceTier.IDENTITY_LIGHT
    assert assessment.eligible is True
    assert assessment.status == NON_MATERIAL_PARTIAL_AUTHORITY
    assert assessment.event_bound_90 == pytest.approx(3.642857142857143)
    assert assessment.impact_bound_90 == pytest.approx(3.642857142857143)
    assert assessment.impact_bound_90 <= assessment.allowed_impact_90


def test_materiality_fails_immediately_below_frozen_uncertainty_threshold() -> None:
    table = frozen_fumbles_lost_production_table_2026()
    threshold = float(
        table.payload["cutoffs"]["3"][  # type: ignore[index]
            "minimum_supported_fp_stddev_for_non_material_fsffl"
        ]["WR"]
    )
    assessment = assess_fumbles_lost_non_material_partial(
        _state(position=Position.WR, cutoff=3),
        partial=_partial(Position.WR),
        supported_fantasy_point_stddev=threshold - 1e-6,
        supplement=None,
    )
    assert assessment.eligible is True
    assert assessment.status == "MATERIAL_PARTIAL"
    assert assessment.impact_bound_90 > assessment.allowed_impact_90


@pytest.mark.parametrize("cutoff", [13, 14, 15, 16, 17])
def test_late_qb_identity_light_fallback_is_ineligible_even_with_huge_uncertainty(
    cutoff: int,
) -> None:
    assessment = assess_fumbles_lost_non_material_partial(
        _state(position=Position.QB, cutoff=cutoff),
        partial=_partial(Position.QB),
        supported_fantasy_point_stddev=10_000.0,
        supplement=None,
    )
    assert assessment.evidence_tier == FirstPartyFumblesLostEvidenceTier.IDENTITY_LIGHT
    assert assessment.eligible is False
    assert assessment.status == "MATERIAL_PARTIAL"
    assert "eligibility fails closed" in assessment.reason


def test_unknown_or_conflicting_position_fails_closed() -> None:
    assessment = assess_fumbles_lost_non_material_partial(
        _state(
            position=Position.QB,
            canonical_position=Position.WR,
            cutoff=3,
        ),
        partial=_partial(Position.QB),
        supported_fantasy_point_stddev=10_000.0,
        supplement=None,
    )
    assert assessment.eligible is False
    assert assessment.status == "MATERIAL_PARTIAL"
    assert "missing or conflicting" in assessment.reason


@pytest.mark.parametrize("cutoff", [0, 1])
def test_season_start_materiality_exists_without_point_authority(cutoff: int) -> None:
    table = frozen_fumbles_lost_production_table_2026()
    threshold = float(
        table.payload["season_start"]["cutoffs"][str(cutoff)][  # type: ignore[index]
            "minimum_supported_fp_stddev_for_non_material_fsffl"
        ]["WR"]
    )
    assessment = assess_fumbles_lost_non_material_partial(
        _state(position=Position.WR, cutoff=cutoff),
        partial=_partial(Position.WR),
        supported_fantasy_point_stddev=threshold,
        supplement=None,
    )
    assert assessment.status == NON_MATERIAL_PARTIAL_AUTHORITY
    assert assessment.event_bound_90 == pytest.approx(
        3.0 if cutoff == 0 else 3.1875
    )


def _annual_candidate() -> FumblesLostProductionTable:
    prior = frozen_fumbles_lost_production_table_2026()
    payload = copy.deepcopy(dict(prior.payload))
    payload["target_season"] = 2027
    payload["annual_freeze"] = {
        "exact_source_hashes": {"2026_weekly_exact_lost_fumbles": "a" * 64},
        "training_seasons": [2021, 2022, 2023, 2024, 2025, 2026],
        "player_prior_sufficient_statistics_fingerprint": "b" * 64,
    }
    return FumblesLostProductionTable(
        payload=payload,
        fingerprint="c" * 64,
    )


def test_annual_rollover_requires_explicit_target_season_freeze_and_monotone_floors() -> None:
    prior = frozen_fumbles_lost_production_table_2026()
    with pytest.raises(ValueError, match="annual governed freeze is unavailable"):
        resolve_fumbles_lost_production_table(2027)

    candidate = _annual_candidate()
    validate_annual_rollover_candidate(
        candidate,
        prior=prior,
        newly_completed_heldout_rmse={
            position.value: {cutoff: 0.0 for cutoff in range(2, 18)}
            for position in (Position.QB, Position.RB, Position.WR, Position.TE)
        },
    )

    with pytest.raises(ValueError, match="monotone prefix freeze"):
        validate_annual_rollover_candidate(
            candidate,
            prior=prior,
            newly_completed_heldout_rmse={
                "QB": {2: candidate.uncertainty_floor(2, Position.QB) + 0.01}
            },
        )


def test_annual_table_cannot_be_reused_for_wrong_target_season() -> None:
    candidate = _annual_candidate()
    with pytest.raises(ValueError, match="target season does not match State"):
        resolve_fumbles_lost_production_table(2028, table=candidate)

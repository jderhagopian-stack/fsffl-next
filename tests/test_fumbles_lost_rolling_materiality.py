from __future__ import annotations

import copy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from fsffl.forecast.fumbles_lost_first_party import FirstPartyFumblesLostEvidenceTier
from fsffl.forecast.fumbles_lost_first_party_priors import (
    PLAYER_PRIORS,
    POSITION_LOST_FUMBLE_PER_OPPORTUNITY,
    POSITION_OPPORTUNITY_PER_GAME,
)
from fsffl.forecast.fumbles_lost_materiality import (
    assess_fumbles_lost_non_material_partial,
)
from fsffl.forecast.fumbles_lost_rolling_authority import (
    FumblesLostProductionTable,
    NON_MATERIAL_PARTIAL_AUTHORITY,
    frozen_fumbles_lost_production_table_2026,
    production_table_payload_fingerprint,
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
    PlayerState,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
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
    roster_slot: RosterSlot | None = None,
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
    provenance = Provenance(
        source="test-materiality-state",
        retrieved_at=NOW,
        effective_at=NOW,
    )
    player_id = "sleeper:player:materiality"
    return LeagueState(
        league=league,
        as_of=NOW,
        teams=(
            Team(team_id="a", league_id=league.league_id, display_name="A"),
            Team(team_id="b", league_id=league.league_id, display_name="B"),
        ),
        team_states=(
            TeamState(
                team_id="a",
                roster=(
                    (RosterEntry(player_id=player_id, slot=roster_slot),)
                    if roster_slot is not None
                    else ()
                ),
            ),
            TeamState(team_id="b", roster=()),
        ),
        players=(
            Player(
                player_id=player_id,
                full_name="Materiality Player",
                position=player_position,
                nfl_team="BUF",
            ),
        ),
        player_states=(
            PlayerState(
                player_id=player_id,
                as_of=NOW,
                nfl_team="BUF",
                provenance=provenance,
            ),
        ),
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
    threshold = table.materiality_event_bound(3, Position.WR) / (0.10 * 1.645)
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
    threshold = table.materiality_event_bound(3, Position.WR) / (0.10 * 1.645)
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


def test_materiality_compatibility_is_bound_to_current_simulation_scope() -> None:
    from fsffl.forecast.fumbles_lost_materiality import (
        fumbles_lost_runtime_authority_compatible,
    )
    from fsffl.forecast.fumbles_lost_first_party import (
        FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
    )

    active = _state(
        position=Position.WR,
        cutoff=3,
        roster_slot=RosterSlot.WR,
    )
    partial = _partial(Position.WR)
    assessment = assess_fumbles_lost_non_material_partial(
        active,
        partial=partial,
        supported_fantasy_point_stddev=1_000.0,
        supplement=None,
    )
    assert assessment.status == NON_MATERIAL_PARTIAL_AUTHORITY

    runtime_result = SimpleNamespace(
        fumbles_lost_supplement_authority_fingerprint=None,
        fumbles_lost_materiality_assessments=(assessment,),
        partial_fantasy_point_forecasts=(partial,),
        fumbles_lost_simulation_relevant_player_ids=(
            "sleeper:player:materiality",
        ),
    )
    assert fumbles_lost_runtime_authority_compatible(
        active,
        runtime_result,
        expected_supplement_version=FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
    )

    taxi = _state(
        position=Position.WR,
        cutoff=3,
        roster_slot=RosterSlot.TAXI,
    )
    assert not fumbles_lost_runtime_authority_compatible(
        taxi,
        runtime_result,
        expected_supplement_version=FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
    )

    supplement_with_residual_partial = SimpleNamespace(
        **{
            **runtime_result.__dict__,
            "fumbles_lost_supplement_authority_fingerprint": "a" * 64,
            "fumbles_lost_supplement_model_version": (
                FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
            ),
            "fumbles_lost_supplement_league_state_id": active.state_id,
        }
    )
    assert fumbles_lost_runtime_authority_compatible(
        active,
        supplement_with_residual_partial,
        expected_supplement_version=FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
    )
    material = assessment.model_copy(
        update={"status": "MATERIAL_PARTIAL", "eligible": False}
    )
    supplement_with_material_residual = SimpleNamespace(
        **{
            **supplement_with_residual_partial.__dict__,
            "fumbles_lost_materiality_assessments": (material,),
        }
    )
    assert not fumbles_lost_runtime_authority_compatible(
        active,
        supplement_with_material_residual,
        expected_supplement_version=FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
    )

    replayed_scope = SimpleNamespace(
        **{
            **runtime_result.__dict__,
            "fumbles_lost_simulation_relevant_player_ids": (),
        }
    )
    assert fumbles_lost_runtime_authority_compatible(
        taxi,
        replayed_scope,
        expected_supplement_version=FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
    )


def _annual_player_priors() -> dict[str, dict[str, object]]:
    return {
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


def _annual_candidate() -> FumblesLostProductionTable:
    prior = frozen_fumbles_lost_production_table_2026()
    payload = copy.deepcopy(dict(prior.payload))
    payload["target_season"] = 2027
    player_priors = _annual_player_priors()
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
        "position_lost_fumble_per_opportunity": dict(
            POSITION_LOST_FUMBLE_PER_OPPORTUNITY
        ),
        "position_opportunity_per_game": dict(POSITION_OPPORTUNITY_PER_GAME),
        "player_role_priors": player_priors,
        "player_prior_sufficient_statistics_fingerprint": (
            production_table_payload_fingerprint(
                {"player_role_priors": player_priors}
            )
        ),
    }
    return FumblesLostProductionTable(
        payload=payload,
        fingerprint=production_table_payload_fingerprint(payload),
    )


def _annual_rmse() -> dict[str, dict[int, float]]:
    return {
        position.value: {cutoff: 0.0 for cutoff in range(2, 18)}
        for position in (Position.QB, Position.RB, Position.WR, Position.TE)
    }


def _annual_materiality_maxima() -> dict[str, dict[int, float]]:
    return {
        position.value: {cutoff: 0.0 for cutoff in range(0, 18)}
        for position in (Position.QB, Position.RB, Position.WR, Position.TE)
    }


def _annual_population_coverage() -> dict[str, dict[int, dict[str, float]]]:
    return {
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
    }


def _annual_rolling_adequacy() -> dict[str, object]:
    return {
        "heldout_season": 2026,
        "cutoffs": {
            cutoff: {
                "rolling_rmse": 0.5,
                "zero_rmse": 1.0,
                "bias": 0.0,
                "zero_gap": 0.0,
            }
            for cutoff in range(2, 18)
        },
    }


def test_annual_rollover_requires_explicit_target_season_freeze_and_monotone_floors() -> None:
    prior = frozen_fumbles_lost_production_table_2026()
    with pytest.raises(ValueError, match="annual governed freeze is unavailable"):
        resolve_fumbles_lost_production_table(2027)

    candidate = _annual_candidate()
    validate_annual_rollover_candidate(
        candidate,
        prior=prior,
        newly_completed_heldout_rmse=_annual_rmse(),
        newly_completed_materiality_event_max=_annual_materiality_maxima(),
        observed_population_coverage=_annual_population_coverage(),
        newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
    )

    with pytest.raises(ValueError, match="RMSE matrix is incomplete"):
        validate_annual_rollover_candidate(
            candidate,
            prior=prior,
            newly_completed_heldout_rmse={"QB": {2: 0.0}},
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )

    complete = {
        position.value: {cutoff: 0.0 for cutoff in range(2, 18)}
        for position in (Position.QB, Position.RB, Position.WR, Position.TE)
    }
    complete["QB"][2] = candidate.uncertainty_floor(2, Position.QB) + 0.01
    with pytest.raises(ValueError, match="monotone prefix freeze"):
        validate_annual_rollover_candidate(
            candidate,
            prior=prior,
            newly_completed_heldout_rmse=complete,
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )


def test_annual_rollover_structural_gate_rejects_other_incomplete_cutoff_fields() -> None:
    prior = frozen_fumbles_lost_production_table_2026()

    broken_floor = _annual_candidate()
    payload = copy.deepcopy(dict(broken_floor.payload))
    del payload["cutoffs"]["4"]["uncertainty_floor"]["TE"]
    broken_floor = FumblesLostProductionTable(
        payload=payload,
        fingerprint=production_table_payload_fingerprint(payload),
    )
    with pytest.raises(ValueError, match="uncertainty floor matrix is incomplete"):
        validate_annual_rollover_candidate(
            broken_floor,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )

    broken_bound = _annual_candidate()
    payload = copy.deepcopy(dict(broken_bound.payload))
    del payload["season_start"]["cutoffs"]["1"]["materiality_event_bound_90"]["RB"]
    broken_bound = FumblesLostProductionTable(
        payload=payload,
        fingerprint=production_table_payload_fingerprint(payload),
    )
    with pytest.raises(
        ValueError,
        match="season-start materiality matrix is incomplete",
    ):
        validate_annual_rollover_candidate(
            broken_bound,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )

    mismatched_fingerprint = _annual_candidate()
    mismatched_fingerprint = FumblesLostProductionTable(
        payload=mismatched_fingerprint.payload,
        fingerprint="0" * 64,
    )
    with pytest.raises(ValueError, match="fingerprint does not match payload"):
        validate_annual_rollover_candidate(
            mismatched_fingerprint,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )


def test_annual_rollover_rejects_incomplete_fallback_matrix_and_player_priors() -> None:
    prior = frozen_fumbles_lost_production_table_2026()
    complete_rmse = {
        position.value: {cutoff: 0.0 for cutoff in range(2, 18)}
        for position in (Position.QB, Position.RB, Position.WR, Position.TE)
    }

    broken_matrix = _annual_candidate()
    payload = copy.deepcopy(dict(broken_matrix.payload))
    del payload["cutoffs"]["3"]["fallback_eligibility"]["cold_start"]["WR"]
    broken_matrix = FumblesLostProductionTable(
        payload=payload,
        fingerprint=production_table_payload_fingerprint(payload),
    )
    with pytest.raises(ValueError, match="eligibility matrix is incomplete"):
        validate_annual_rollover_candidate(
            broken_matrix,
            prior=prior,
            newly_completed_heldout_rmse=complete_rmse,
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )

    broken_prior = _annual_candidate()
    payload = copy.deepcopy(dict(broken_prior.payload))
    player_priors = payload["annual_freeze"]["player_role_priors"]
    first_id = next(iter(player_priors))
    player_priors[first_id] = {"position": "WR"}
    payload["annual_freeze"]["player_prior_sufficient_statistics_fingerprint"] = (
        production_table_payload_fingerprint(
            {"player_role_priors": player_priors}
        )
    )
    broken_prior = FumblesLostProductionTable(
        payload=payload,
        fingerprint=production_table_payload_fingerprint(payload),
    )
    with pytest.raises(ValueError, match="player role prior is incomplete"):
        validate_annual_rollover_candidate(
            broken_prior,
            prior=prior,
            newly_completed_heldout_rmse=complete_rmse,
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )


def test_annual_rollover_requires_new_materiality_maxima_and_population_coverage() -> None:
    prior = frozen_fumbles_lost_production_table_2026()
    candidate = _annual_candidate()

    incomplete_max = _annual_materiality_maxima()
    del incomplete_max["WR"][3]
    with pytest.raises(ValueError, match="materiality maximum matrix is incomplete"):
        validate_annual_rollover_candidate(
            candidate,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=incomplete_max,
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )

    widened_max = _annual_materiality_maxima()
    widened_max["WR"][3] = candidate.materiality_event_bound(3, Position.WR) + 1.0
    with pytest.raises(ValueError, match="omits newly completed maximum"):
        validate_annual_rollover_candidate(
            candidate,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=widened_max,
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )

    failing_coverage = _annual_population_coverage()
    failing_coverage["WR"][3]["cold_start"] = 0.89
    assert candidate.fallback_eligible(3, Position.WR, "cold_start")
    with pytest.raises(ValueError, match="misses 90% coverage gate"):
        validate_annual_rollover_candidate(
            candidate,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=failing_coverage,
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )


def test_annual_rollover_requires_governed_rolling_adequacy_proof() -> None:
    prior = frozen_fumbles_lost_production_table_2026()
    candidate = _annual_candidate()

    with pytest.raises(ValueError, match="rolling adequacy proof is incomplete"):
        validate_annual_rollover_candidate(
            candidate,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy={},
        )

    wrong_season = _annual_rolling_adequacy()
    wrong_season["heldout_season"] = 2025
    with pytest.raises(ValueError, match="wrong held-out season"):
        validate_annual_rollover_candidate(
            candidate,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=wrong_season,
        )

    worse_than_omission = _annual_rolling_adequacy()
    worse_than_omission["cutoffs"][3]["rolling_rmse"] = 1.01  # type: ignore[index]
    with pytest.raises(ValueError, match="RMSE-vs-omission gate"):
        validate_annual_rollover_candidate(
            candidate,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=worse_than_omission,
        )

    biased = _annual_rolling_adequacy()
    biased["cutoffs"][8]["bias"] = 0.150001  # type: ignore[index]
    with pytest.raises(ValueError, match="absolute-bias gate"):
        validate_annual_rollover_candidate(
            candidate,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=biased,
        )

    miscalibrated = _annual_rolling_adequacy()
    miscalibrated["cutoffs"][12]["zero_gap"] = 0.050001  # type: ignore[index]
    with pytest.raises(ValueError, match="zero-calibration gate"):
        validate_annual_rollover_candidate(
            candidate,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=miscalibrated,
        )


@pytest.mark.parametrize("invalid_floor", [0.0, -0.1, float("inf"), float("nan")])
def test_annual_rollover_rejects_nonpositive_or_nonfinite_cold_start_floor(
    invalid_floor: float,
) -> None:
    prior = frozen_fumbles_lost_production_table_2026()
    candidate = _annual_candidate()
    payload = copy.deepcopy(dict(candidate.payload))
    payload["cold_start_floor"] = invalid_floor
    invalid = FumblesLostProductionTable(
        payload=payload,
        fingerprint=production_table_payload_fingerprint(payload),
    )

    with pytest.raises(ValueError, match="must be finite and positive"):
        validate_annual_rollover_candidate(
            invalid,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )


def test_annual_rollover_cannot_reduce_cold_start_uncertainty_floor() -> None:
    prior = frozen_fumbles_lost_production_table_2026()
    candidate = _annual_candidate()
    payload = copy.deepcopy(dict(candidate.payload))
    payload["cold_start_floor"] = prior.cold_start_floor - 0.01
    reduced = FumblesLostProductionTable(
        payload=payload,
        fingerprint=production_table_payload_fingerprint(payload),
    )

    with pytest.raises(ValueError, match="cannot decrease"):
        validate_annual_rollover_candidate(
            reduced,
            prior=prior,
            newly_completed_heldout_rmse=_annual_rmse(),
            newly_completed_materiality_event_max=_annual_materiality_maxima(),
            observed_population_coverage=_annual_population_coverage(),
            newly_completed_rolling_adequacy=_annual_rolling_adequacy(),
        )


def test_annual_table_cannot_be_reused_for_wrong_target_season() -> None:
    candidate = _annual_candidate()
    with pytest.raises(ValueError, match="target season does not match State"):
        resolve_fumbles_lost_production_table(2028, table=candidate)

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.forecast.league_scoring import derive_league_scoring_result
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.forecast.supplemental_coordinate import (
    SupplementalCoordinateEvidencePackage,
    SupplementalCoordinateSourceEvidence,
    SupplementalCoordinateSourceRow,
    SupplementalCoordinateUncertainty,
    SupplementalTargetPeriod,
    SupplementalTargetPlayerExposure,
    SupplementalTargetSemantics,
    SupplementalUncertaintyRow,
    apply_certified_supplemental_coordinate,
    build_certified_supplemental_coordinate,
)
from fsffl.persistence.annual_preseason_snapshot import (
    ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND,
)
from fsffl.persistence.runtime_cache import (
    FORECAST_ARTIFACT_KIND,
    PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND,
    SIMULATION_ARTIFACT_KIND,
    VALUE_ARTIFACT_KIND,
)
from fsffl.persistence.supplemental_coordinate import (
    SUPPLEMENTAL_COORDINATE_EVIDENCE_ARTIFACT_KIND,
    SUPPLEMENTAL_COORDINATE_SCOPE_KIND,
    apply_fumbles_lost_supplement_invalidation,
    decode_supplemental_coordinate_package,
    plan_fumbles_lost_supplement_invalidation,
    supplemental_coordinate_evidence_artifact,
    supplemental_coordinate_ensemble_artifact,
)
from fsffl.state.models import LeagueRules, Position, Provenance, ScoringRule


ACQUIRED = datetime(2026, 9, 26, 14, 0, tzinfo=UTC)
EFFECTIVE = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)
SOURCE_START = datetime(2026, 9, 27, 0, 0, tzinfo=UTC)
SOURCE_END = datetime(2027, 1, 5, 0, 0, tzinfo=UTC)
TARGET_START = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
TARGET_END = datetime(2027, 3, 1, 0, 0, tzinfo=UTC)


def _source(
    provider: str,
    *,
    group: str | None = None,
    projected_events: float,
    projected_games: float = 10.0,
    private_beta_eligible: bool = True,
    hash_char: str = "a",
) -> SupplementalCoordinateSourceEvidence:
    return SupplementalCoordinateSourceEvidence(
        provider=provider,
        independence_group=group or provider,
        source_id=f"{provider}:ros:2026-09-26",
        season=2026,
        captured_at=ACQUIRED,
        effective_at=EFFECTIVE,
        source_period_start=SOURCE_START,
        source_period_end=SOURCE_END,
        source_version=f"{provider}-v1",
        source_locator=f"provider://{provider}/ros",
        content_sha256=hash_char * 64,
        private_beta_eligible=private_beta_eligible,
        commercial_recheck_required=True,
        rights_basis="private-beta terms reviewed",
        rows=(
            SupplementalCoordinateSourceRow(
                player_id="p1",
                position=Position.RB,
                projected_events=projected_events,
                projected_games=projected_games,
            ),
        ),
    )


def _package(
    *,
    source_one: SupplementalCoordinateSourceEvidence | None = None,
    source_two: SupplementalCoordinateSourceEvidence | None = None,
) -> SupplementalCoordinateEvidencePackage:
    return SupplementalCoordinateEvidencePackage(
        season=2026,
        sources=tuple(
            item
            for item in (
                source_one or _source("one", projected_events=1.0, hash_char="a"),
                source_two or _source("two", projected_events=2.0, hash_char="b"),
            )
            if item is not None
        ),
    )


def _target() -> SupplementalTargetPeriod:
    return SupplementalTargetPeriod(
        horizon=ForecastHorizon.SEASON,
        period_start=TARGET_START,
        period_end=TARGET_END,
        evaluation_as_of=ACQUIRED,
        semantics=SupplementalTargetSemantics.SEASON_EQUIVALENT_CURRENT_RATE,
        player_exposures=(
            SupplementalTargetPlayerExposure(player_id="p1", target_games=17.0),
        ),
    )


def _uncertainty(*, compatible: bool = True) -> SupplementalCoordinateUncertainty:
    return SupplementalCoordinateUncertainty(
        target_horizon=ForecastHorizon.SEASON,
        target_period_start=TARGET_START,
        target_period_end=TARGET_END,
        evidence_id="research:future-certified-fumbles-lost-uncertainty",
        model_version="future-source-compatible-v1",
        source_compatible=compatible,
        rows=(SupplementalUncertaintyRow(player_id="p1", stddev_events=0.8),),
    )


def _base_observation() -> ForecastObservation:
    return ForecastObservation(
        player_id="p1",
        position=Position.RB,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.RUSH_YARDS,
        period_start=TARGET_START,
        period_end=TARGET_END,
        distribution=ForecastDistribution(mean=1000.0, stddev=100.0),
        source="fsffl:existing-ordinary-offense",
        model_version="existing-ordinary-offense-v1",
        as_of=ACQUIRED,
        provenance=Provenance(
            source="provider-existing",
            retrieved_at=ACQUIRED,
            effective_at=EFFECTIVE,
            source_version="existing-v1",
        ),
    )


def _rules(*rules: ScoringRule) -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(),
        scoring=rules,
    )


def test_staged_package_preserves_ros_provenance_and_cannot_claim_preseason_authority() -> None:
    package = _package()

    assert package.production_authority_promoted is False
    assert package.preseason_eligible is False
    assert package.historical_pit_eligible is False
    assert package.source_horizon == ForecastHorizon.REST_OF_SEASON
    assert all(source.captured_at == ACQUIRED for source in package.sources)
    assert all(source.effective_at == EFFECTIVE for source in package.sources)

    record = supplemental_coordinate_evidence_artifact(package)
    assert record.key.artifact_kind == SUPPLEMENTAL_COORDINATE_EVIDENCE_ARTIFACT_KIND
    assert record.key.scope_kind == SUPPLEMENTAL_COORDINATE_SCOPE_KIND
    assert record.key.scope_id == "2026:fumbles_lost"
    assert decode_supplemental_coordinate_package(dict(record.payload)) == package


def test_certified_builder_requires_two_independent_private_beta_eligible_sources() -> None:
    shared = _package(
        source_one=_source("one", group="shared", projected_events=1.0, hash_char="a"),
        source_two=_source("two", group="shared", projected_events=2.0, hash_char="b"),
    )
    with pytest.raises(ValueError, match="two independent"):
        build_certified_supplemental_coordinate(
            shared,
            target=_target(),
            uncertainty=_uncertainty(),
        )

    ineligible = _package(
        source_two=_source(
            "two",
            projected_events=2.0,
            private_beta_eligible=False,
            hash_char="b",
        ),
    )
    with pytest.raises(ValueError, match="two independent"):
        build_certified_supplemental_coordinate(
            ineligible,
            target=_target(),
            uncertainty=_uncertainty(),
        )


def test_target_period_normalization_is_explicit_and_keeps_source_horizon_separate() -> None:
    ensemble = build_certified_supplemental_coordinate(
        _package(),
        target=_target(),
        uncertainty=_uncertainty(),
    )

    by_source = {item.source_id: item for item in ensemble.normalized_source_values}
    assert by_source["one:ros:2026-09-26"].source_projected_events == pytest.approx(1.0)
    assert by_source["one:ros:2026-09-26"].source_projected_games == pytest.approx(10.0)
    assert by_source["one:ros:2026-09-26"].target_games == pytest.approx(17.0)
    assert by_source["one:ros:2026-09-26"].normalized_events == pytest.approx(1.7)
    assert by_source["two:ros:2026-09-26"].normalized_events == pytest.approx(3.4)

    observation = ensemble.observations[0]
    assert observation.distribution.mean == pytest.approx(2.55)
    assert observation.distribution.stddev == pytest.approx(0.8)
    assert observation.horizon == ForecastHorizon.SEASON
    assert ensemble.source_horizon == ForecastHorizon.REST_OF_SEASON.value
    assert ensemble.target_horizon == ForecastHorizon.SEASON
    assert ensemble.preseason_eligible is False
    assert ensemble.historical_pit_eligible is False
    assert ensemble.lineage_class == "supplemental_mixed_vintage_current"


def test_target_compatible_nonzero_uncertainty_is_mandatory() -> None:
    with pytest.raises(ValueError, match="not source-compatible"):
        build_certified_supplemental_coordinate(
            _package(),
            target=_target(),
            uncertainty=_uncertainty(compatible=False),
        )

    with pytest.raises(ValueError):
        SupplementalUncertaintyRow(player_id="p1", stddev_events=0.0)


def test_overlay_changes_only_fumbles_lost_and_makes_scoring_complete_when_consumed() -> None:
    base = (_base_observation(),)
    rules = _rules(
        ScoringRule(stat="rush_yd", points=0.1),
        ScoringRule(stat="fum_lost", points=-2.0),
    )
    before = derive_league_scoring_result(base, rules=rules)
    assert before.authoritative_forecasts == ()
    assert len(before.partial_forecasts) == 1
    assert before.partial_forecasts[0].omitted_rule_stats == ("fum_lost",)

    ensemble = build_certified_supplemental_coordinate(
        _package(),
        target=_target(),
        uncertainty=_uncertainty(),
    )
    applied = apply_certified_supplemental_coordinate(
        base,
        supplement=ensemble,
        rules=rules,
    )

    unrelated = tuple(
        item for item in applied.observations if item.metric != ForecastMetric.FUMBLES_LOST
    )
    assert unrelated == base
    supplement_rows = tuple(
        item for item in applied.observations if item.metric == ForecastMetric.FUMBLES_LOST
    )
    assert len(supplement_rows) == 1
    assert supplement_rows[0].source == "fsffl:current_supplement:fumbles_lost"
    assert applied.lineage.consumed is True
    assert applied.lineage.preseason_eligible is False
    assert applied.lineage.historical_pit_eligible is False

    after = derive_league_scoring_result(applied.observations, rules=rules)
    assert len(after.authoritative_forecasts) == 1
    assert after.partial_forecasts == ()
    assert after.authoritative_forecasts[0].distribution.mean == pytest.approx(94.9)


def test_league_without_fumbles_lost_rule_is_byte_for_byte_semantically_unchanged() -> None:
    base = (_base_observation(),)
    rules = _rules(ScoringRule(stat="rush_yd", points=0.1))
    ensemble = build_certified_supplemental_coordinate(
        _package(),
        target=_target(),
        uncertainty=_uncertainty(),
    )

    applied = apply_certified_supplemental_coordinate(
        base,
        supplement=ensemble,
        rules=rules,
    )

    assert applied.observations == base
    assert applied.lineage.consumed is False
    before = derive_league_scoring_result(base, rules=rules)
    after = derive_league_scoring_result(applied.observations, rules=rules)
    assert after == before


def test_certified_overlay_refuses_to_replace_existing_fumbles_lost_truth() -> None:
    base_fumble = ForecastObservation(
        **{
            **_base_observation().model_dump(),
            "metric": ForecastMetric.FUMBLES_LOST,
            "distribution": ForecastDistribution(mean=1.0, stddev=0.5),
        }
    )
    ensemble = build_certified_supplemental_coordinate(
        _package(),
        target=_target(),
        uncertainty=_uncertainty(),
    )
    with pytest.raises(ValueError, match="cannot overwrite"):
        apply_certified_supplemental_coordinate(
            (_base_observation(), base_fumble),
            supplement=ensemble,
            rules=_rules(ScoringRule(stat="fum_lost", points=-2.0)),
        )


def test_invalidation_is_selective_and_preserves_preseason_and_independent_value() -> None:
    consuming = _rules(ScoringRule(stat="fum_lost", points=-2.0))
    plan = plan_fumbles_lost_supplement_invalidation(
        consuming,
        previous_authority_fingerprint="old",
        new_authority_fingerprint="new",
    )
    assert plan.invalidate_artifact_kinds == (
        FORECAST_ARTIFACT_KIND,
        SIMULATION_ARTIFACT_KIND,
    )
    assert plan.rebuild_layers == (
        "current_forecast",
        "simulation",
        "forecast_derived_team_intelligence",
    )
    assert PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND in plan.preserve_artifact_kinds
    assert ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND in plan.preserve_artifact_kinds
    assert VALUE_ARTIFACT_KIND in plan.preserve_artifact_kinds

    unchanged = plan_fumbles_lost_supplement_invalidation(
        consuming,
        previous_authority_fingerprint="same",
        new_authority_fingerprint="same",
    )
    assert unchanged.invalidate_artifact_kinds == ()

    nonconsuming = plan_fumbles_lost_supplement_invalidation(
        _rules(ScoringRule(stat="rush_yd", points=0.1)),
        previous_authority_fingerprint="old",
        new_authority_fingerprint="new",
    )
    assert nonconsuming.invalidate_artifact_kinds == ()
    assert nonconsuming.reason_codes == ("league_does_not_score_fumbles_lost",)


def test_invalidation_hook_only_calls_store_for_affected_current_artifacts() -> None:
    calls = []

    class Store:
        def invalidate_scope(self, **kwargs):
            calls.append(kwargs)

    plan = plan_fumbles_lost_supplement_invalidation(
        _rules(ScoringRule(stat="fum_lost", points=-2.0)),
        previous_authority_fingerprint=None,
        new_authority_fingerprint="certified-v1",
    )
    apply_fumbles_lost_supplement_invalidation(
        Store(),  # type: ignore[arg-type]
        league_state_id="state-1",
        plan=plan,
        observed_at=ACQUIRED,
    )
    assert len(calls) == 1
    assert calls[0]["scope_id"] == "state-1"
    assert calls[0]["artifact_kinds"] == (
        FORECAST_ARTIFACT_KIND,
        SIMULATION_ARTIFACT_KIND,
    )
    assert calls[0]["cause_ref"] == "certified-v1"


def test_certified_ensemble_artifact_is_separate_from_forecast_and_preseason_artifacts() -> None:
    ensemble = build_certified_supplemental_coordinate(
        _package(),
        target=_target(),
        uncertainty=_uncertainty(),
    )
    record = supplemental_coordinate_ensemble_artifact(ensemble)

    assert record.key.artifact_kind == "current_supplemental_coordinate_ensemble"
    assert record.key.artifact_kind != FORECAST_ARTIFACT_KIND
    assert record.key.artifact_kind != PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND
    assert record.key.artifact_kind != ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND

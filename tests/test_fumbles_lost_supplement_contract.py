from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.league_scoring import derive_league_scoring_result
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.forecast.supplemental_coordinate import (
    FUMBLES_LOST_EMPIRICAL_STDDEV_FLOOR,
    SUPPLEMENTAL_COORDINATE_SOURCE,
    SupplementalCoordinateEvidencePackage,
    SupplementalCoordinateSourceEvidence,
    SupplementalCoordinateSourceRow,
    SupplementalTargetPeriod,
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
    SUPPLEMENTAL_COORDINATE_ENSEMBLE_ARTIFACT_KIND,
    SUPPLEMENTAL_COORDINATE_EVIDENCE_ARTIFACT_KIND,
    SUPPLEMENTAL_COORDINATE_SCOPE_KIND,
    apply_fumbles_lost_supplement_invalidation,
    decode_supplemental_coordinate_package,
    plan_fumbles_lost_supplement_invalidation,
    supplemental_coordinate_evidence_artifact,
    supplemental_coordinate_ensemble_artifact,
)
from fsffl.state.models import LeagueRules, Position, Provenance, ScoringRule


PRESEASON_AS_OF = datetime(2026, 9, 9, 23, 23, tzinfo=UTC)
CAPTURED = datetime(2026, 9, 26, 14, 0, tzinfo=UTC)
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
    source_games: int = 14,
    canonical_games: int = 14,
    private_beta_eligible: bool = True,
    source_health_passed: bool = True,
    exact_semantics: bool = True,
    hash_char: str = "a",
    player_id: str = "p1",
) -> SupplementalCoordinateSourceEvidence:
    return SupplementalCoordinateSourceEvidence(
        provider=provider,
        independence_group=group or provider,
        source_id=f"{provider}:ros:2026-09-26",
        captured_at=CAPTURED,
        effective_at=EFFECTIVE,
        source_period_start=SOURCE_START,
        source_period_end=SOURCE_END,
        source_version=f"{provider}-v1",
        source_locator=f"provider://{provider}/ros",
        content_sha256=hash_char * 64,
        private_beta_eligible=private_beta_eligible,
        commercial_recheck_required=True,
        rights_basis="private-beta terms reviewed",
        source_health_passed=source_health_passed,
        exact_lost_fumble_semantics=exact_semantics,
        rows=(
            SupplementalCoordinateSourceRow(
                player_id=player_id,
                position=Position.RB,
                nfl_team="BUF",
                projected_events=projected_events,
                source_games_represented=source_games,
                canonical_remaining_games_at_capture=canonical_games,
            ),
        ),
    )


def _package(
    *,
    one: SupplementalCoordinateSourceEvidence | None = None,
    two: SupplementalCoordinateSourceEvidence | None = None,
    include_two: bool = True,
) -> SupplementalCoordinateEvidencePackage:
    sources = [one or _source("one", projected_events=1.4, hash_char="a")]
    if include_two:
        sources.append(two or _source("two", projected_events=2.8, hash_char="b"))
    return SupplementalCoordinateEvidencePackage(sources=tuple(sources))


def _target(*, required: tuple[str, ...] = ("p1",)) -> SupplementalTargetPeriod:
    return SupplementalTargetPeriod(
        period_start=TARGET_START,
        period_end=TARGET_END,
        evaluation_as_of=CAPTURED,
        required_player_ids=required,
    )


def _base_observation(
    *,
    metric: ForecastMetric = ForecastMetric.RUSH_YARDS,
    mean: float = 1000.0,
    stddev: float = 100.0,
) -> ForecastObservation:
    return ForecastObservation(
        player_id="p1",
        position=Position.RB,
        horizon=ForecastHorizon.SEASON,
        metric=metric,
        period_start=TARGET_START,
        period_end=TARGET_END,
        distribution=ForecastDistribution(mean=mean, stddev=stddev),
        source="fsffl:immutable-ordinary-offense",
        model_version="immutable-ordinary-offense-v1",
        as_of=PRESEASON_AS_OF,
        provenance=Provenance(
            source="preseason-two-source-ensemble",
            retrieved_at=PRESEASON_AS_OF,
            effective_at=PRESEASON_AS_OF,
            source_version="immutable-v1",
        ),
    )


def _rules(*rules: ScoringRule) -> LeagueRules:
    return LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(),
        scoring=rules,
    )


def test_staged_package_is_current_only_and_cannot_claim_preseason_authority() -> None:
    package = _package()

    assert package.production_authority_promoted is False
    assert package.preseason_eligible is False
    assert package.annual_preseason_snapshot_eligible is False
    assert package.historical_pit_eligible is False
    assert package.backfill_allowed is False
    assert package.source_horizon == ForecastHorizon.REST_OF_SEASON
    assert all(source.captured_at == CAPTURED for source in package.sources)

    record = supplemental_coordinate_evidence_artifact(package)
    assert record.key.artifact_kind == SUPPLEMENTAL_COORDINATE_EVIDENCE_ARTIFACT_KIND
    assert record.key.scope_kind == SUPPLEMENTAL_COORDINATE_SCOPE_KIND
    assert record.key.scope_id == "2026:fumbles_lost"
    assert decode_supplemental_coordinate_package(dict(record.payload)) == package


def test_builder_requires_exactly_two_independent_eligible_healthy_exact_sources() -> None:
    with pytest.raises(ValueError, match="exactly two"):
        build_certified_supplemental_coordinate(
            _package(include_two=False),
            target=_target(),
        )

    shared = _package(
        one=_source("one", group="shared", projected_events=1.4, hash_char="a"),
        two=_source("two", group="shared", projected_events=2.8, hash_char="b"),
    )
    with pytest.raises(ValueError, match="two independent"):
        build_certified_supplemental_coordinate(shared, target=_target())

    ineligible = _package(
        two=_source(
            "two",
            projected_events=2.8,
            private_beta_eligible=False,
            hash_char="b",
        )
    )
    with pytest.raises(ValueError, match="private-beta"):
        build_certified_supplemental_coordinate(ineligible, target=_target())

    unhealthy = _package(
        two=_source(
            "two",
            projected_events=2.8,
            source_health_passed=False,
            hash_char="b",
        )
    )
    with pytest.raises(ValueError, match="source health"):
        build_certified_supplemental_coordinate(unhealthy, target=_target())

    wrong_semantics = _package(
        two=_source(
            "two",
            projected_events=2.8,
            exact_semantics=False,
            hash_char="b",
        )
    )
    with pytest.raises(ValueError, match="exact lost-fumble"):
        build_certified_supplemental_coordinate(wrong_semantics, target=_target())


def test_stale_source_remaining_game_state_is_rejected_not_heuristically_adjusted() -> None:
    with pytest.raises(ValueError, match="does not match canonical schedule"):
        _source(
            "stale",
            projected_events=1.4,
            source_games=15,
            canonical_games=14,
        )


def test_17_game_current_pace_normalization_uses_canonical_remaining_games() -> None:
    ensemble = build_certified_supplemental_coordinate(
        _package(),
        target=_target(),
    )

    by_source = {item.source_id: item for item in ensemble.normalized_source_values}
    one = by_source["one:ros:2026-09-26"]
    two = by_source["two:ros:2026-09-26"]
    assert one.source_projected_events == pytest.approx(1.4)
    assert one.source_games_represented == 14
    assert one.canonical_remaining_games_at_capture == 14
    assert one.source_rate_per_game == pytest.approx(0.1)
    assert one.target_games == 17
    assert one.normalized_events == pytest.approx(1.7)
    assert two.normalized_events == pytest.approx(3.4)

    observation = ensemble.observations[0]
    assert observation.distribution.mean == pytest.approx(2.55)
    assert observation.horizon == ForecastHorizon.SEASON
    assert ensemble.evidence_horizon == ForecastHorizon.REST_OF_SEASON.value
    assert ensemble.target_horizon == ForecastHorizon.SEASON.value
    assert ensemble.target_quantity_kind == "season_equivalent_current_pace"
    assert ensemble.authority_valid_from == CAPTURED
    assert ensemble.preseason_eligible is False
    assert ensemble.annual_preseason_snapshot_eligible is False
    assert ensemble.historical_pit_before_authority_valid_from is False
    assert ensemble.backfill_allowed is False


def test_uncertainty_uses_empirical_floor_and_provider_disagreement_without_zero_collapse() -> None:
    equal = _package(
        one=_source("one", projected_events=1.4, hash_char="a"),
        two=_source("two", projected_events=1.4, hash_char="b"),
    )
    equal_ensemble = build_certified_supplemental_coordinate(equal, target=_target())
    assert equal_ensemble.observations[0].distribution.stddev == pytest.approx(
        FUMBLES_LOST_EMPIRICAL_STDDEV_FLOOR
    )

    wide = _package(
        one=_source("one", projected_events=0.0, hash_char="a"),
        two=_source("two", projected_events=4.0, hash_char="b"),
    )
    wide_ensemble = build_certified_supplemental_coordinate(wide, target=_target())
    x_a = 0.0
    x_b = 4.0 / 14.0 * 17.0
    assert wide_ensemble.observations[0].distribution.stddev == pytest.approx(
        abs(x_a - x_b) / 2.0
    )
    assert wide_ensemble.observations[0].distribution.stddev > (
        FUMBLES_LOST_EMPIRICAL_STDDEV_FLOOR
    )


def test_full_required_player_coverage_is_mandatory_per_source() -> None:
    with pytest.raises(ValueError, match="lacks required player coverage"):
        build_certified_supplemental_coordinate(
            _package(),
            target=_target(required=("p1", "p2")),
        )


def test_supplement_is_invisible_before_authority_valid_from() -> None:
    ensemble = build_certified_supplemental_coordinate(_package(), target=_target())
    with pytest.raises(ValueError, match="before authority_valid_from"):
        apply_certified_supplemental_coordinate(
            (_base_observation(),),
            supplement=ensemble,
            rules=_rules(ScoringRule(stat="fum_lost", points=-2.0)),
            evaluation_as_of=CAPTURED - timedelta(seconds=1),
        )


def test_overlay_keeps_ordinary_raw_forecast_immutable_and_scores_mixed_vintage_separately() -> None:
    base = (_base_observation(),)
    rules = _rules(
        ScoringRule(stat="rush_yd", points=0.1),
        ScoringRule(stat="fum_lost", points=-2.0),
    )
    before = derive_league_scoring_result(base, rules=rules)
    assert before.authoritative_forecasts == ()
    assert before.partial_forecasts[0].omitted_rule_stats == ("fum_lost",)

    ensemble = build_certified_supplemental_coordinate(_package(), target=_target())
    applied = apply_certified_supplemental_coordinate(
        base,
        supplement=ensemble,
        rules=rules,
        evaluation_as_of=CAPTURED,
    )

    assert applied.base_observations == base
    assert base[0].source == "fsffl:immutable-ordinary-offense"
    assert base[0].model_version == "immutable-ordinary-offense-v1"
    assert base[0].as_of == PRESEASON_AS_OF
    assert len(applied.supplemental_observations) == 1
    supplemental = applied.supplemental_observations[0]
    assert supplemental.source == SUPPLEMENTAL_COORDINATE_SOURCE
    assert supplemental.as_of == CAPTURED
    assert supplemental.provenance.source == SUPPLEMENTAL_COORDINATE_SOURCE

    after = derive_league_scoring_result(
        applied.base_observations,
        supplemental_observations=applied.supplemental_observations,
        rules=rules,
    )
    assert after.partial_forecasts == ()
    scored = after.authoritative_forecasts[0]
    assert scored.distribution.mean == pytest.approx(94.9)
    assert scored.as_of == CAPTURED
    assert "supplemental_mixed_vintage_current" in scored.model_version
    assert SUPPLEMENTAL_COORDINATE_SOURCE in scored.provenance.source


def test_league_without_fumbles_lost_rule_is_semantically_unchanged() -> None:
    base = (_base_observation(),)
    rules = _rules(ScoringRule(stat="rush_yd", points=0.1))
    ensemble = build_certified_supplemental_coordinate(_package(), target=_target())

    applied = apply_certified_supplemental_coordinate(
        base,
        supplement=ensemble,
        rules=rules,
        evaluation_as_of=CAPTURED,
    )
    assert applied.base_observations == base
    assert applied.supplemental_observations == ()
    assert applied.lineage.consumed is False

    before = derive_league_scoring_result(base, rules=rules)
    after = derive_league_scoring_result(
        applied.base_observations,
        supplemental_observations=applied.supplemental_observations,
        rules=rules,
    )
    assert after == before


def test_scorer_refuses_supplement_if_ordinary_raw_forecast_already_has_fumbles_lost() -> None:
    base_fumble = _base_observation(
        metric=ForecastMetric.FUMBLES_LOST,
        mean=1.0,
        stddev=0.5,
    )
    ensemble = build_certified_supplemental_coordinate(_package(), target=_target())
    with pytest.raises(ValueError, match="cannot replace ordinary raw Forecast"):
        derive_league_scoring_result(
            (_base_observation(), base_fumble),
            supplemental_observations=ensemble.observations,
            rules=_rules(
                ScoringRule(stat="rush_yd", points=0.1),
                ScoringRule(stat="fum_lost", points=-2.0),
            ),
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


def test_invalidation_hook_only_calls_store_for_affected_current_artifacts() -> None:
    calls = []

    class Store:
        def invalidate_scope(self, **kwargs):
            calls.append(kwargs)

    plan = plan_fumbles_lost_supplement_invalidation(
        _rules(ScoringRule(stat="fum_lost", points=-2.0)),
        previous_authority_fingerprint=None,
        new_authority_fingerprint="certified-v2",
    )
    apply_fumbles_lost_supplement_invalidation(
        Store(),  # type: ignore[arg-type]
        league_state_id="state-1",
        plan=plan,
        observed_at=CAPTURED,
    )
    assert len(calls) == 1
    assert calls[0]["scope_id"] == "state-1"
    assert calls[0]["artifact_kinds"] == (
        FORECAST_ARTIFACT_KIND,
        SIMULATION_ARTIFACT_KIND,
    )
    assert calls[0]["cause_ref"] == "certified-v2"


def test_certified_artifact_is_current_supplement_not_forecast_or_preseason() -> None:
    ensemble = build_certified_supplemental_coordinate(_package(), target=_target())
    record = supplemental_coordinate_ensemble_artifact(ensemble)

    assert (
        record.key.artifact_kind
        == "current_supplemental_forecast_coordinate"
        == SUPPLEMENTAL_COORDINATE_ENSEMBLE_ARTIFACT_KIND
    )
    assert record.computed_at == ensemble.authority_valid_from
    assert record.key.artifact_kind != FORECAST_ARTIFACT_KIND
    assert record.key.artifact_kind != PRESEASON_FORECAST_BASELINE_ARTIFACT_KIND
    assert record.key.artifact_kind != ANNUAL_PRESEASON_PROJECTION_SNAPSHOT_ARTIFACT_KIND

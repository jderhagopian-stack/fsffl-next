from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

from pydantic import Field

from fsffl.providers.cbs_live import CBSLiveProjectionSource
from fsffl.providers.current_projection_rows import CurrentProjectionSnapshot
from fsffl.providers.fftoday_live import FFTodayLiveProjectionSource
from fsffl.providers.nfl_fantasy_live import NFLFantasyLiveProjectionSource
from fsffl.providers.razzball_season_live import RazzballSeasonProjectionSource
from fsffl.state.models import FrozenModel, LeagueState, RosterSlot

from .current_normalization import current_snapshot_from_razzball, normalize_current_projection_snapshot
from .fumbles_lost_first_party import (
    FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION,
    FirstPartyFumblesLostSupplement,
    build_first_party_fumbles_lost_supplement,
)
from .league_scoring import (
    ForecastRuleFamilyCoverage,
    PartialFantasyPointForecast,
    ScoringCoverage,
    derive_league_scoring_result,
)
from .live_ensemble import LiveEnsembleCoverage, LiveForecastSourceBatch, build_authoritative_live_ensemble
from .models import ForecastObservation
from .regular_season import derive_fantasy_regular_season_forecasts
from .season_uncertainty import apply_empirical_season_fantasy_point_uncertainty
from .supplemental_coordinate import league_consumes_fumbles_lost
from .source_health import (
    CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
    RevisionAgnosticScaleHealth,
    build_source_health_fantasy_point_forecasts,
    current_projection_payload_sha256,
    evaluate_revision_agnostic_scale_health,
    validate_current_projection_snapshot_health,
)


CurrentSnapshotFetcher = Callable[[int], CurrentProjectionSnapshot]
Clock = Callable[[], datetime]
FumblesLostSupplementBuilder = Callable[
    [LeagueState, tuple[ForecastObservation, ...]],
    FirstPartyFumblesLostSupplement,
]


@dataclass(frozen=True)
class NamedCurrentProjectionFetcher:
    source_id: str
    fetch: CurrentSnapshotFetcher


class LiveForecastSourceProvenance(FrozenModel):
    provider: str
    source_version: str
    captured_at: datetime
    effective_at: datetime
    usage_class: str
    provider_payload_sha256: str
    health_contract_version: str
    health_disposition: str = "accepted"


class LiveForecastSourceHealthEvent(FrozenModel):
    provider: str
    disposition: str
    check: str
    reason: str
    health_contract_version: str
    provider_payload_sha256: str
    reference_id: str | None = None
    comparable_player_count: int = 0
    ratio_threshold: float | None = None
    overall_median_ratio: float | None = None
    position_median_ratios: tuple[tuple[str, float], ...] = ()


class LiveForecastSourceHealthFailure(ValueError):
    def __init__(
        self,
        message: str,
        *,
        health_events: tuple[LiveForecastSourceHealthEvent, ...],
    ) -> None:
        super().__init__(message)
        self.health_events = health_events


class LiveForecastRuntimeResult(FrozenModel):
    raw_ensemble: tuple[ForecastObservation, ...]
    fantasy_point_forecasts: tuple[ForecastObservation, ...]
    partial_fantasy_point_forecasts: tuple[PartialFantasyPointForecast, ...] = ()
    league_scoring_coverage: ScoringCoverage | None = None
    family_coverage: tuple[ForecastRuleFamilyCoverage, ...] = ()
    simulation_authority_blockers: tuple[str, ...] = ()
    coverage: LiveEnsembleCoverage
    successful_source_ids: tuple[str, ...]
    failed_sources: tuple[str, ...]
    evaluation_as_of: datetime
    fantasy_regular_season_forecasts: tuple[ForecastObservation, ...] = ()
    source_provenance: tuple[LiveForecastSourceProvenance, ...] = ()
    source_health_events: tuple[LiveForecastSourceHealthEvent, ...] = ()
    fumbles_lost_supplement_authority_fingerprint: str | None = None
    fumbles_lost_supplement_player_count: int = 0
    fumbles_lost_supplement_failure: str | None = None
    fumbles_lost_supplement_model_version: str | None = None
    simulation_material_partial_player_ids: tuple[str, ...] = ()
    first_party_fumbles_lost_supplement: FirstPartyFumblesLostSupplement | None = Field(
        default=None,
        exclude=True,
    )
    model_version: str = "next2-current-runtime-v9:first-party-fumbles-lost"


def default_current_projection_fetchers() -> tuple[NamedCurrentProjectionFetcher, ...]:
    razzball = RazzballSeasonProjectionSource()
    fftoday = FFTodayLiveProjectionSource()
    cbs = CBSLiveProjectionSource()
    nfl_fantasy = NFLFantasyLiveProjectionSource()
    return (
        NamedCurrentProjectionFetcher(
            source_id="razzball",
            fetch=lambda season: current_snapshot_from_razzball(
                razzball.fetch_latest(season=season)
            ),
        ),
        NamedCurrentProjectionFetcher(
            source_id="fftoday",
            fetch=lambda season: fftoday.fetch_latest(season=season),
        ),
        NamedCurrentProjectionFetcher(
            source_id="cbs",
            fetch=lambda season: cbs.fetch_latest(season=season),
        ),
        NamedCurrentProjectionFetcher(
            source_id="nfl_fantasy",
            fetch=lambda season: nfl_fantasy.fetch_latest(season=season),
        ),
    )


def _fetch_current_snapshots(
    fetchers: tuple[NamedCurrentProjectionFetcher, ...],
    *,
    season: int,
) -> tuple[list[tuple[str, CurrentProjectionSnapshot]], list[str]]:
    """Acquire independent provider snapshots concurrently.

    Numerical-integrity authority is applied only after all available snapshots are
    normalized so the revision-agnostic contract can reason over a provider/dataset
    cohort before exact incident fingerprints are consulted as defense-in-depth.
    """

    if not fetchers:
        return [], []
    snapshots: list[tuple[str, CurrentProjectionSnapshot]] = []
    failed: list[str] = []
    with ThreadPoolExecutor(
        max_workers=len(fetchers),
        thread_name_prefix="fsffl-forecast-provider",
    ) as executor:
        future_by_source = {
            executor.submit(fetcher.fetch, season): fetcher.source_id
            for fetcher in fetchers
        }
        for future in as_completed(future_by_source):
            source_id = future_by_source[future]
            try:
                snapshot = future.result()
                if snapshot.provider != source_id:
                    raise ValueError("current projection fetcher returned wrong provider id")
                snapshots.append((source_id, snapshot))
            except Exception as exc:
                failed.append(f"{source_id}: {type(exc).__name__}: {exc}")

    snapshots.sort(key=lambda item: item[0])
    failed.sort()
    return snapshots, failed


def _scale_health_event(
    *,
    source_id: str,
    snapshot: CurrentProjectionSnapshot,
    result: RevisionAgnosticScaleHealth,
    check: str,
    disposition: str | None = None,
    reason: str | None = None,
) -> LiveForecastSourceHealthEvent:
    return LiveForecastSourceHealthEvent(
        provider=source_id,
        disposition=disposition or result.disposition,
        check=check,
        reason=reason or result.reason,
        health_contract_version=CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
        provider_payload_sha256=current_projection_payload_sha256(snapshot),
        reference_id=result.reference_id,
        comparable_player_count=result.comparable_player_count,
        ratio_threshold=result.ratio_threshold,
        overall_median_ratio=result.overall_median_ratio,
        position_median_ratios=result.position_median_ratios,
    )


def _health_failure_detail(
    event: LiveForecastSourceHealthEvent,
) -> str:
    ratio = (
        "unavailable"
        if event.overall_median_ratio is None
        else f"{event.overall_median_ratio:.6f}"
    )
    threshold = (
        "unavailable"
        if event.ratio_threshold is None
        else f"{event.ratio_threshold:.6f}"
    )
    positions = ",".join(
        f"{position}={value:.6f}"
        for position, value in event.position_median_ratios
    ) or "none"
    return (
        f"{event.check}: {event.reason}; reference={event.reference_id or 'none'}; "
        f"comparable_players={event.comparable_player_count}; "
        f"median_ratio={ratio}; threshold={threshold}; "
        f"position_medians={positions}"
    )


def build_current_live_forecasts(
    league_state: LeagueState,
    *,
    fetchers: tuple[NamedCurrentProjectionFetcher, ...] | None = None,
    clock: Clock | None = None,
    minimum_independent_sources: int = 2,
    reference_raw_forecasts: tuple[ForecastObservation, ...] | None = None,
    reference_id: str = "preserved_preseason_multi_source_raw_ensemble",
    fumbles_lost_supplement_builder: FumblesLostSupplementBuilder | None = None,
) -> LiveForecastRuntimeResult:
    """Build current authoritative FSFFL forecasts from independent live evidence.

    Independent network acquisitions run concurrently. A revision-agnostic,
    provider-neutral scale-integrity gate runs over normalized provider datasets
    before exact known-incident fingerprints are consulted. When a governed
    preseason reference exists, each source is tested against that independent
    multi-source coordinate. Without a reference, material broad scale disagreement
    between the only two sources fails closed rather than guessing which source wins.
    """

    active_fetchers = fetchers or default_current_projection_fetchers()
    if len({item.source_id for item in active_fetchers}) != len(active_fetchers):
        raise ValueError("current projection fetcher ids must be unique")

    snapshots, failed = _fetch_current_snapshots(
        active_fetchers,
        season=league_state.league.season,
    )

    cutoff = (clock or (lambda: datetime.now(UTC)))()
    if cutoff.tzinfo is None:
        raise ValueError("current forecast runtime clock must be timezone-aware")
    # State-first authority: the canonical LeagueState is the evaluation cutoff.
    # Providers may be retrieved after that State was synced, but only evidence whose
    # own effective_at is at-or-before the State cutoff can normalize. Acquisition
    # timestamps remain truthful in provenance and are never backdated.
    evaluation_as_of = league_state.as_of.astimezone(UTC)
    if cutoff.astimezone(UTC) < evaluation_as_of:
        raise ValueError("current forecast runtime clock cannot predate canonical State")

    snapshot_by_source = dict(snapshots)
    normalized_by_source: dict[str, tuple[ForecastObservation, ...]] = {}
    scored_by_source: dict[str, tuple[ForecastObservation, ...]] = {}
    payload_hash_by_source = {
        source_id: current_projection_payload_sha256(snapshot)
        for source_id, snapshot in snapshots
    }
    health_events: list[LiveForecastSourceHealthEvent] = []

    for source_id, snapshot in snapshots:
        try:
            observations = normalize_current_projection_snapshot(
                snapshot,
                league_state=league_state,
                season=league_state.league.season,
                evaluation_as_of=evaluation_as_of,
            )
            if not observations:
                raise ValueError("provider produced no canonical player observations")
            scored = build_source_health_fantasy_point_forecasts(
                observations,
                source=f"fsffl:source-health:{source_id}",
            )
            if not scored:
                raise ValueError(
                    "provider produced no complete season fantasy-point observations "
                    "for source-health evaluation"
                )
        except Exception as exc:
            failed.append(f"{source_id}: {type(exc).__name__}: {exc}")
            continue
        normalized_by_source[source_id] = observations
        scored_by_source[source_id] = scored

    generalized_quarantined: set[str] = set()
    scale_result_by_source: dict[str, RevisionAgnosticScaleHealth] = {}

    if reference_raw_forecasts:
        reference_scored = build_source_health_fantasy_point_forecasts(
            reference_raw_forecasts,
            source="fsffl:source-health:governed-reference",
        )
        for source_id in sorted(scored_by_source):
            result = evaluate_revision_agnostic_scale_health(
                scored_by_source[source_id],
                reference_scored,
                reference_id=reference_id,
            )
            scale_result_by_source[source_id] = result
            if result.disposition == "quarantined":
                generalized_quarantined.add(source_id)
                event = _scale_health_event(
                    source_id=source_id,
                    snapshot=snapshot_by_source[source_id],
                    result=result,
                    check="revision_agnostic_governed_reference_scale",
                )
                health_events.append(event)
                failed.append(
                    f"{source_id}: ValueError: current projection source quarantined "
                    f"by revision-agnostic numerical-integrity gate: "
                    f"{_health_failure_detail(event)}"
                )
    elif len(scored_by_source) >= 2:
        source_ids = sorted(scored_by_source)
        pair_results: dict[tuple[str, str], RevisionAgnosticScaleHealth] = {}
        for source_id in source_ids:
            for peer_id in source_ids:
                if source_id == peer_id:
                    continue
                pair_results[(source_id, peer_id)] = evaluate_revision_agnostic_scale_health(
                    scored_by_source[source_id],
                    scored_by_source[peer_id],
                    reference_id=f"peer_provider:{peer_id}",
                )

        if len(source_ids) == 2:
            first, second = source_ids
            first_result = pair_results[(first, second)]
            second_result = pair_results[(second, first)]
            if (
                first_result.disposition == "quarantined"
                or second_result.disposition == "quarantined"
            ):
                # With exactly two disagreeing providers and no governed reference,
                # choosing a winner would fabricate authority. Fail both closed.
                for source_id, result in (
                    (first, first_result),
                    (second, second_result),
                ):
                    generalized_quarantined.add(source_id)
                    event = _scale_health_event(
                        source_id=source_id,
                        snapshot=snapshot_by_source[source_id],
                        result=result,
                        check="revision_agnostic_two_source_scale_disagreement",
                        disposition="quarantined",
                        reason=(
                            "material broad scale disagreement exists between the "
                            "only two available independent sources and no governed "
                            "reference exists to identify the healthy source"
                        ),
                    )
                    health_events.append(event)
                    failed.append(
                        f"{source_id}: ValueError: current projection source quarantined "
                        f"by revision-agnostic numerical-integrity gate: "
                        f"{_health_failure_detail(event)}"
                    )
        else:
            for source_id in source_ids:
                inflated_vs = [
                    result
                    for (candidate_id, _peer_id), result in pair_results.items()
                    if candidate_id == source_id
                    and result.disposition == "quarantined"
                ]
                if len(inflated_vs) < 2:
                    continue
                worst = max(
                    inflated_vs,
                    key=lambda item: item.overall_median_ratio or 0.0,
                )
                generalized_quarantined.add(source_id)
                event = _scale_health_event(
                    source_id=source_id,
                    snapshot=snapshot_by_source[source_id],
                    result=worst,
                    check="revision_agnostic_multi_peer_scale_outlier",
                    disposition="quarantined",
                    reason=(
                        "provider is broadly inflated against at least two "
                        "independent peer-source datasets"
                    ),
                )
                health_events.append(event)
                failed.append(
                    f"{source_id}: ValueError: current projection source quarantined "
                    f"by revision-agnostic numerical-integrity gate: "
                    f"{_health_failure_detail(event)}"
                )

    batches: list[LiveForecastSourceBatch] = []
    successful: list[str] = []
    provenance_by_source: dict[str, LiveForecastSourceProvenance] = {}
    for source_id in sorted(normalized_by_source):
        if source_id in generalized_quarantined:
            continue
        snapshot = snapshot_by_source[source_id]

        # Exact incident matching is intentionally secondary forensic defense.
        try:
            validate_current_projection_snapshot_health(snapshot)
        except Exception as exc:
            event = LiveForecastSourceHealthEvent(
                provider=source_id,
                disposition="quarantined",
                check="known_incident_witness_secondary",
                reason=str(exc),
                health_contract_version=CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
                provider_payload_sha256=payload_hash_by_source[source_id],
            )
            health_events.append(event)
            failed.append(f"{source_id}: {type(exc).__name__}: {exc}")
            continue

        scale_result = scale_result_by_source.get(source_id)
        if scale_result is not None:
            health_events.append(
                _scale_health_event(
                    source_id=source_id,
                    snapshot=snapshot,
                    result=scale_result,
                    check="revision_agnostic_governed_reference_scale",
                    disposition="accepted",
                )
            )
        elif len(scored_by_source) >= 2:
            health_events.append(
                LiveForecastSourceHealthEvent(
                    provider=source_id,
                    disposition="accepted",
                    check="revision_agnostic_peer_scale_cohort",
                    reason=(
                        "no broad multi-position scale inflation was established "
                        "against the available peer-source cohort"
                    ),
                    health_contract_version=CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
                    provider_payload_sha256=payload_hash_by_source[source_id],
                )
            )
        else:
            health_events.append(
                LiveForecastSourceHealthEvent(
                    provider=source_id,
                    disposition="accepted",
                    check="revision_agnostic_scale_not_evaluable",
                    reason=(
                        "only one normalized source was available and no governed "
                        "reference was supplied; exact incident defense passed"
                    ),
                    health_contract_version=CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
                    provider_payload_sha256=payload_hash_by_source[source_id],
                )
            )

        observations = normalized_by_source[source_id]
        batches.append(LiveForecastSourceBatch(source_id=source_id, observations=observations))
        successful.append(source_id)
        provenance_by_source[source_id] = LiveForecastSourceProvenance(
            provider=snapshot.provider,
            source_version=snapshot.source_version,
            captured_at=snapshot.captured_at.astimezone(UTC),
            effective_at=snapshot.effective_at.astimezone(UTC),
            usage_class=snapshot.usage_class,
            provider_payload_sha256=payload_hash_by_source[source_id],
            health_contract_version=CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
            health_disposition="accepted",
        )

    if len(batches) < minimum_independent_sources:
        detail = "; ".join(sorted(failed)) if failed else "no provider-specific failure details"
        raise LiveForecastSourceHealthFailure(
            "authoritative live ensemble requires at least "
            f"{minimum_independent_sources} independent sources; found {len(batches)}; "
            f"successful={sorted(successful)}; failures={detail}",
            health_events=tuple(health_events),
        )

    raw_ensemble, coverage = build_authoritative_live_ensemble(
        tuple(batches),
        minimum_independent_sources=minimum_independent_sources,
    )

    fumbles_lost_supplement: FirstPartyFumblesLostSupplement | None = None
    fumbles_lost_failure: str | None = None
    supplemental_observations: tuple[ForecastObservation, ...] = ()
    if league_consumes_fumbles_lost(league_state.league.rules):
        builder = fumbles_lost_supplement_builder
        if builder is None:
            builder = lambda state, observations: build_first_party_fumbles_lost_supplement(
                state,
                base_observations=observations,
            )
        try:
            fumbles_lost_supplement = builder(league_state, raw_ensemble)
            if fumbles_lost_supplement.league_state_id != league_state.state_id:
                raise ValueError(
                    "first-party FUMBLES_LOST supplement does not match canonical State"
                )
            supplemental_observations = fumbles_lost_supplement.observations
        except Exception as exc:
            # Fail the material coordinate closed, not the unrelated raw Forecast.
            # The ordinary scorer will emit explicit partial outputs for fum_lost.
            fumbles_lost_failure = f"{type(exc).__name__}: {exc}"

    scoring = derive_league_scoring_result(
        raw_ensemble,
        rules=league_state.league.rules,
        supplemental_observations=supplemental_observations,
        source="fsffl:live_league_scored",
        model_version="next2-current-runtime-v9:first-party-fumbles-lost",
    )
    fantasy_points = (
        apply_empirical_season_fantasy_point_uncertainty(
            scoring.authoritative_forecasts
        )
        if scoring.authoritative_forecasts
        else ()
    )
    fantasy_regular_season = (
        derive_fantasy_regular_season_forecasts(league_state, fantasy_points)
        if league_state.matchups and fantasy_points
        else ()
    )
    active_simulation_player_ids = {
        entry.player_id
        for team_state in league_state.team_states
        for entry in team_state.roster
        if entry.slot not in {RosterSlot.TAXI, RosterSlot.IR}
    }
    simulation_material_partial_player_ids = tuple(
        sorted(
            {
                item.player_id
                for item in scoring.partial_forecasts
                if item.player_id in active_simulation_player_ids
            }
        )
    )
    simulation_blockers = tuple(
        sorted(
            {
                reason
                for family in scoring.family_coverage
                if family.blocks_full_downstream_authority
                for reason in family.reason_codes
            }
            | (
                {"partial_player_scoring_coordinates_present"}
                if simulation_material_partial_player_ids
                else set()
            )
        )
    )
    return LiveForecastRuntimeResult(
        raw_ensemble=raw_ensemble,
        fantasy_point_forecasts=fantasy_points,
        partial_fantasy_point_forecasts=scoring.partial_forecasts,
        league_scoring_coverage=scoring.coverage,
        family_coverage=scoring.family_coverage,
        simulation_authority_blockers=simulation_blockers,
        fantasy_regular_season_forecasts=fantasy_regular_season,
        coverage=coverage,
        successful_source_ids=tuple(sorted(successful)),
        failed_sources=tuple(sorted(failed)),
        evaluation_as_of=evaluation_as_of,
        source_provenance=tuple(
            provenance_by_source[source_id]
            for source_id in sorted(successful)
        ),
        source_health_events=tuple(health_events),
        fumbles_lost_supplement_authority_fingerprint=(
            fumbles_lost_supplement.authority_fingerprint
            if fumbles_lost_supplement is not None
            else None
        ),
        fumbles_lost_supplement_player_count=(
            len(fumbles_lost_supplement.observations)
            if fumbles_lost_supplement is not None
            else 0
        ),
        fumbles_lost_supplement_failure=fumbles_lost_failure,
        fumbles_lost_supplement_model_version=(
            FIRST_PARTY_FUMBLES_LOST_SUPPLEMENT_VERSION
            if fumbles_lost_supplement is not None
            else None
        ),
        simulation_material_partial_player_ids=simulation_material_partial_player_ids,
        first_party_fumbles_lost_supplement=fumbles_lost_supplement,
    )

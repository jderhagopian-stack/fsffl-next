from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from contextlib import nullcontext
from threading import RLock, Timer
from typing import Callable, Mapping
from weakref import ref

from fsffl.persistence.contracts import (
    ArtifactKey,
    canonical_fingerprint,
    PersistenceStore,
    ReusableArtifactRecord,
    utc_now,
)
from fsffl.value.career_forward_intrinsic import (
    CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION,
    CAREER_FORWARD_INTRINSIC_MODEL_VERSION,
    CareerForwardIntrinsicShadowContract,
    append_dynamic_career_estimates,
    build_career_forward_intrinsic_shadow,
)
from fsffl.value.career_tail import (
    CAREER_TAIL_MODEL_VERSION,
    build_career_tail_authority,
)
from fsffl.value.long_term_intrinsic import (
    LONG_TERM_INTRINSIC_MODEL_VERSION,
    LongTermIntrinsicShadowContract,
    build_long_term_intrinsic_shadow,
    long_term_intrinsic_input_fingerprint,
)
from fsffl.value.shapley_intrinsic_contract import (
    ShapleyIntrinsicAvailability,
    ShapleyIntrinsicContract,
)

from .foundation4_shadow_inputs import (
    FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256,
    FOUNDATION4_LONG_TERM_IGNORED_RESIDUAL_RULE_STATS,
    FOUNDATION4_TERMINAL_FEATURES_SEMANTIC_SHA256,
    provide_foundation4_long_horizon_forecast_contract_for_rules,
    provide_foundation4_terminal_features,
)
from .runtime import UserRuntimeContext
from .resource_coordinator import HeavyWorkCoordinator, reclaim_before_heavy_allocation
from fsffl.value.shapley_intrinsic import clear_shapley_execution_caches
from fsffl.memory_attribution import sample_rss_phase
from .foundation4_cohort import align_foundation4_cohort


FOUNDATION4_Y4_Y7_ARTIFACT_KIND = "foundation4_long_horizon_y4_y7_shadow"
CAREER_INTRINSIC_ARTIFACT_KIND = "career_intrinsic_v1"
CAREER_REFERENCE_CHECKPOINT_ARTIFACT_KIND = "career_intrinsic_reference_checkpoint_v1"
_UNREAD_CAREER_RECORD = object()
CAREER_INTRINSIC_SCOPE_KIND = "league_intrinsic"
# Read-only migration aliases for the accepted Foundation 4 persisted authority.
LEGACY_FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND = "foundation4_career_forward_intrinsic_shadow"
LEGACY_FOUNDATION4_SCOPE_KIND = "league_intrinsic_shadow"
FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND = CAREER_INTRINSIC_ARTIFACT_KIND
FOUNDATION4_SCOPE_KIND = CAREER_INTRINSIC_SCOPE_KIND
FOUNDATION4_RUNTIME_VERSION = (
    "foundation4-career-forward-runtime-v7:complete-exact-state-artifact:"
    "dynamic-rostered-y1-y3-shapley-bridge:"
    "fsffl-material-scoring-with-rare-residual-omission"
)


CurrentIntrinsicLoader = Callable[[UserRuntimeContext], ShapleyIntrinsicContract]
CurrentIntrinsicFingerprintResolver = Callable[[UserRuntimeContext], str]
@dataclass(frozen=True)
class ExpandedCareerContractResult:
    """Per-State append result with explicit failures for unsupported subjects.

    The callback composes valid candidates together in the full accepted cohort,
    while recording invalid/missing candidate evidence independently. No metric is
    supplied for a failed player.
    """

    contract: CareerForwardIntrinsicShadowContract | None
    failures: Mapping[str, str] = field(default_factory=dict)
    source_manifest: Mapping[str, object] = field(default_factory=dict)
    retryable_batch_incomplete: bool = False


class RetryableCareerExpansionIncomplete(RuntimeError):
    """Career expansion was saved as a checkpoint and should be retried explicitly."""


ExpandedCareerContractLoader = Callable[
    [UserRuntimeContext, CareerForwardIntrinsicShadowContract],
    ExpandedCareerContractResult | CareerForwardIntrinsicShadowContract | None,
]
ExpandedCareerContractFingerprintResolver = Callable[[UserRuntimeContext], str]
CareerArtifactKeyFingerprintResolver = Callable[[UserRuntimeContext], str]


def validate_foundation4_expanded_acceptance_cohort(
    *,
    frozen_reference_ids,
    current_intrinsic_ids,
    career_estimate_ids,
    expected_frozen_count: int,
) -> frozenset[str]:
    """Validate frozen reference identity and any fully composed dynamic rows."""
    frozen_rows = tuple(str(value) for value in frozen_reference_ids)
    current_rows = tuple(str(value) for value in current_intrinsic_ids)
    career_rows = tuple(str(value) for value in career_estimate_ids)
    frozen = frozenset(frozen_rows)
    current = frozenset(current_rows)
    career = frozenset(career_rows)
    if len(frozen_rows) != len(frozen):
        raise ValueError("Foundation 4 frozen reference contains duplicate players")
    if len(frozen) != expected_frozen_count:
        raise ValueError("Foundation 4 frozen reference cohort is not the governed size")
    if len(career_rows) != len(career):
        raise ValueError("Foundation 4 Career cohort contains duplicate players")
    if not frozen.issubset(career):
        raise ValueError("Foundation 4 Career cohort is missing frozen reference players")
    dynamic = career - frozen
    if not dynamic.issubset(current):
        raise ValueError("Foundation 4 dynamic Career players are outside expanded Current")
    return dynamic




def _rules_payload(context: UserRuntimeContext) -> dict[str, object]:
    if context.league_state is None:
        raise ValueError("Foundation 4 requires canonical league State")
    rules = context.league_state.league.rules
    return {
        "team_count": rules.team_count,
        "lineup": [
            {"slot": item.slot.value, "count": item.count}
            for item in rules.lineup
        ],
        "scoring": [
            {"stat": item.stat, "points": item.points}
            for item in rules.scoring
        ],
    }


class CareerIntrinsicLoader:
    """Build, restore, and persist canonical production Career Intrinsic authority."""

    forecast_model_version = "foundation4:fsffl-scored-y4-y7-plus-y8-terminal-v2"

    def __init__(
        self,
        *,
        current_intrinsic_loader: CurrentIntrinsicLoader,
        heavy_work_coordinator: HeavyWorkCoordinator | None = None,
        current_intrinsic_fingerprint_resolver: CurrentIntrinsicFingerprintResolver,
        persistence_store: PersistenceStore | None = None,
        expanded_career_contract_loader: ExpandedCareerContractLoader | None = None,
        expanded_career_contract_fingerprint_resolver: (
            ExpandedCareerContractFingerprintResolver | None
        ) = None,
        career_artifact_key_fingerprint_resolver: (
            CareerArtifactKeyFingerprintResolver | None
        ) = None,
    ) -> None:
        if (expanded_career_contract_loader is None) != (
            expanded_career_contract_fingerprint_resolver is None
        ):
            raise ValueError(
                "expanded Career contract loader and semantic fingerprint resolver "
                "must be configured together"
            )
        self._heavy_work_coordinator = heavy_work_coordinator
        self._expanded_career_contract_loader = expanded_career_contract_loader
        self._expanded_career_contract_fingerprint_resolver = (
            expanded_career_contract_fingerprint_resolver
        )
        self._career_artifact_key_fingerprint_resolver = (
            career_artifact_key_fingerprint_resolver
        )
        self._current_intrinsic_loader = current_intrinsic_loader
        self._current_intrinsic_fingerprint_resolver = (
            current_intrinsic_fingerprint_resolver
        )
        self._persistence_store = persistence_store
        self._lock = RLock()
        self._cached_user_id: str | None = None
        self._cached_fingerprint: str | None = None
        self._cached_contract: CareerForwardIntrinsicShadowContract | None = None
        self._cached_component: LongTermIntrinsicShadowContract | None = None
        self._component_timer: Timer | None = None

    def pin_build_context(self, context: UserRuntimeContext) -> UserRuntimeContext:
        """Use the published State/Forecast cutoff, never the reader's clock.

        A newer source capture requires a new governed evidence publication.
        Visiting a page must not advance its source window or force acquisition.
        """
        if context.career_fingerprint_evaluation_as_of is not None:
            return context
        cutoff = context.league_state.as_of if context.league_state is not None else utc_now()
        # The roster State and its governed Forecast publication have distinct
        # capture times. Preserve a later, already published Forecast cutoff;
        # using the roster timestamp alone could discard its admitted ROS rows.
        published_as_of = getattr(
            getattr(context.forecast_evidence, "runtime_result", None), "evaluation_as_of", None
        )
        if published_as_of is not None:
            if published_as_of.tzinfo is None:
                raise ValueError("published Career evidence cutoff must be timezone-aware")
            cutoff = max(cutoff, published_as_of)
        return replace(context, career_fingerprint_evaluation_as_of=cutoff)

    def intrinsic_input_fingerprint(self, context: UserRuntimeContext) -> str:
        return self._input_fingerprint(
            context, self._expanded_career_contract_fingerprint_resolver
        )

    def intrinsic_artifact_key_fingerprint(
        self, context: UserRuntimeContext
    ) -> str:
        """Stable durable key; freshness remains verified in the payload."""
        resolver = (
            self._career_artifact_key_fingerprint_resolver
            or self._expanded_career_contract_fingerprint_resolver
        )
        return self._input_fingerprint(context, resolver)

    def _input_fingerprint(
        self,
        context: UserRuntimeContext,
        expanded_fingerprint_resolver: Callable[[UserRuntimeContext], str] | None,
    ) -> str:
        context = self.pin_build_context(context)
        if context.league_state is None:
            raise ValueError("Foundation 4 requires canonical league State")
        payload = {
            "league_state_id": context.league_state.state_id,
            "evaluation_season": context.league_state.league.season,
            "league_id": context.league_state.league.league_id,
            "league_rules": _rules_payload(context),
            "current_intrinsic_input_fingerprint": (
                self._current_intrinsic_fingerprint_resolver(context)
            ),
            "long_horizon_board_semantic_sha256": (
                FOUNDATION4_LONG_HORIZON_BOARD_SEMANTIC_SHA256
            ),
            "terminal_features_semantic_sha256": (
                FOUNDATION4_TERMINAL_FEATURES_SEMANTIC_SHA256
            ),
            "career_forward_contract_version": (
                CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION
            ),
            "career_forward_model_version": CAREER_FORWARD_INTRINSIC_MODEL_VERSION,
            "long_horizon_value_model_version": LONG_TERM_INTRINSIC_MODEL_VERSION,
            "career_tail_model_version": CAREER_TAIL_MODEL_VERSION,
            "runtime_version": FOUNDATION4_RUNTIME_VERSION,
            "expanded_career_contract_input_fingerprint": (
                expanded_fingerprint_resolver(context)
                if expanded_fingerprint_resolver is not None
                else None
            ),
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    def _career_key(
        self,
        context: UserRuntimeContext,
        fingerprint: str,
    ) -> ArtifactKey:
        assert context.league_state is not None
        # Reuse one durable slot for the same non-time-varying source identity.
        # The payload still carries and validates the exact freshness fingerprint,
        # so a new epoch rebuilds and upserts this row instead of accumulating one.
        artifact_fingerprint = self.intrinsic_artifact_key_fingerprint(context)
        return ArtifactKey(
            artifact_kind=CAREER_INTRINSIC_ARTIFACT_KIND,
            scope_kind=CAREER_INTRINSIC_SCOPE_KIND,
            scope_id=context.league_state.league.league_id,
            input_fingerprint=artifact_fingerprint,
            model_version=(
                f"{CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION}"
                f"|{CAREER_FORWARD_INTRINSIC_MODEL_VERSION}"
            ),
        )

    def _component_key(
        self,
        context: UserRuntimeContext,
        component: LongTermIntrinsicShadowContract,
    ) -> ArtifactKey:
        assert context.league_state is not None
        return ArtifactKey(
            artifact_kind=FOUNDATION4_Y4_Y7_ARTIFACT_KIND,
            scope_kind=FOUNDATION4_SCOPE_KIND,
            scope_id=context.league_state.league.league_id,
            input_fingerprint=component.input_fingerprint,
            model_version=component.value_model_version,
        )

    def restore_compatible(
        self,
        context: UserRuntimeContext,
    ) -> CareerForwardIntrinsicShadowContract | None:
        context = self.pin_build_context(context)
        fingerprint = self.intrinsic_input_fingerprint(context)
        with self._lock:
            if (self._cached_user_id == context.user_id
                    and self._cached_fingerprint == fingerprint
                    and self._cached_contract is not None):
                return self._cached_contract
        return self._restore_frozen_compatible(context, require_complete=True)

    def _restore_frozen_compatible(
        self,
        context: UserRuntimeContext,
        *,
        require_complete: bool = False,
        canonical_record: ReusableArtifactRecord | None | object = _UNREAD_CAREER_RECORD,
    ) -> CareerForwardIntrinsicShadowContract | None:
        if self._persistence_store is None or context.league_state is None:
            return None
        fingerprint = self.intrinsic_input_fingerprint(context)
        prefetched = canonical_record is not _UNREAD_CAREER_RECORD
        record = canonical_record if prefetched else None
        if not require_complete and record is None:
            # Only the owned build may read an incomplete reference. A refresh
            # can share the stable durable key with last-good completed output;
            # checkpoints must never replace that output or restore as ready.
            record = self._persistence_store.get_reusable_artifact(
                self._reference_checkpoint_key(context, fingerprint)
            )
            if (record is not None
                    and record.payload.get("_foundation4_dependency_fingerprint") != fingerprint):
                record = None
        if record is None and not prefetched:
            record = self._persistence_store.get_reusable_artifact(
                self._career_key(context, fingerprint)
            )
        migrated_legacy = False
        if record is None:
            # Foundation 4 was accepted with a shadow-named persistence key. Reuse
            # that exact governed artifact once, then migrate it to the canonical
            # production Career Intrinsic key without recomputation.
            assert context.league_state is not None
            legacy_key = ArtifactKey(
                artifact_kind=LEGACY_FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND,
                scope_kind=LEGACY_FOUNDATION4_SCOPE_KIND,
                scope_id=context.league_state.league.league_id,
                input_fingerprint=fingerprint,
                model_version=(
                    f"{CAREER_FORWARD_INTRINSIC_CONTRACT_VERSION}"
                    f"|{CAREER_FORWARD_INTRINSIC_MODEL_VERSION}"
                ),
            )
            record = self._persistence_store.get_reusable_artifact(legacy_key)
            migrated_legacy = record is not None
        if record is None:
            return None
        payload = dict(record.payload)
        dependency = payload.pop("_foundation4_dependency_fingerprint", None)
        expansion_complete = payload.pop("_career_expansion_complete", False) is True
        retryable_batch_incomplete = payload.pop("_career_retryable_batch_incomplete", False) is True
        source_manifest = payload.pop("_career_source_manifest", {})
        complete_fingerprint = payload.pop("_career_complete_input_fingerprint", None)
        expansion_complete = expansion_complete and not retryable_batch_incomplete
        if self._expanded_career_contract_loader is not None:
            from .p0_live_candidate_runtime import valid_live_source_manifest
            expansion_complete = (
                expansion_complete and valid_live_source_manifest(source_manifest)
                and complete_fingerprint == canonical_fingerprint(
                    "career-complete-live-inputs-v1", fingerprint, source_manifest["digest"],
                )
            )
        if require_complete and self._expanded_career_contract_loader is not None and not expansion_complete:
            # Legacy base-only artifacts are inputs for an explicitly scheduled
            # build, not completed expanded products. Restore never calls providers.
            return None
        if dependency != fingerprint:
            return None
        try:
            contract = CareerForwardIntrinsicShadowContract.model_validate(payload)
        except (TypeError, ValueError):
            return None
        if retryable_batch_incomplete or self.retryable_incomplete_contract(contract):
            # A bound input manifest does not supersede a retryable batch gap.
            # Keep this frozen base reusable by an explicit retry, not ready.
            expansion_complete = False
            if require_complete:
                return None
        # Older hosted releases persisted the expanded Career contract. Treat
        # only its accepted Foundation 4 reference cohort as the frozen base;
        # dynamic roster rows must be rebuilt against current live evidence.
        reference_ids = set(
            provide_foundation4_long_horizon_forecast_contract_for_rules(
                context.league_state.league.rules
            ).player_ids
        )
        base_estimates = tuple(
            row for row in contract.estimates if row.player_id in reference_ids
        )
        if not expansion_complete:
            contract = contract.model_copy(update={
                "estimates": base_estimates,
                "player_count": len(base_estimates),
                "player_coverage_failures": {
                    player_id: reason
                    for player_id, reason in contract.player_coverage_failures.items()
                    if player_id in reference_ids
                },
            })
        if migrated_legacy:
            migrated_payload = contract.model_dump(mode="json")
            migrated_payload["_foundation4_dependency_fingerprint"] = fingerprint
            migrated_payload["_career_expansion_complete"] = expansion_complete
            migrated_payload["_career_retryable_batch_incomplete"] = retryable_batch_incomplete
            if expansion_complete and source_manifest:
                migrated_payload["_career_source_manifest"] = source_manifest
                migrated_payload["_career_complete_input_fingerprint"] = complete_fingerprint
            self._persistence_store.put_artifact(
                ReusableArtifactRecord(
                    key=self._career_key(context, fingerprint),
                    payload=migrated_payload,
                    computed_at=utc_now(),
                )
            )
        with self._lock:
            self._cached_user_id = context.user_id
            self._cached_fingerprint = fingerprint
            self._cached_contract = contract if (expansion_complete or self._expanded_career_contract_loader is None) else None
            self._cached_component = None
        return contract

    def restore_component(
        self,
        context: UserRuntimeContext,
    ) -> LongTermIntrinsicShadowContract | None:
        context = self.pin_build_context(context)
        fingerprint = self.intrinsic_input_fingerprint(context)
        with self._lock:
            if (self._cached_user_id == context.user_id
                    and self._cached_fingerprint == fingerprint
                    and self._cached_component is not None):
                return self._cached_component
        guard = (self._heavy_work_coordinator.claim(
            kind="career_component_restore", key=f"{context.user_id}:component"
        ) if self._heavy_work_coordinator is not None else nullcontext())
        with guard, self._lock:
            # Recheck under the lock: concurrent readers must deserialize once.
            return self._restore_component(context)

    def _restore_component(self, context: UserRuntimeContext) -> LongTermIntrinsicShadowContract | None:
        fingerprint = self.intrinsic_input_fingerprint(context)
        if (self._cached_user_id == context.user_id
                and self._cached_fingerprint == fingerprint
                and self._cached_component is not None):
            return self._cached_component
        if self._persistence_store is None or context.league_state is None:
            return None
        forecast = provide_foundation4_long_horizon_forecast_contract_for_rules(
            context.league_state.league.rules
        )
        # restore_compatible already retained the exact Career subject contract;
        # use its reference IDs to locate the corresponding scoped component.
        # This does not rebuild Current or reread the full Career payload.
        with self._lock:
            restored = self._cached_contract if self._cached_user_id == context.user_id else None
        if restored is not None:
            reference_ids = {row.player_id for row in forecast.forecasts}
            active_ids = {row.player_id for row in restored.estimates} & reference_ids
            forecast, _ = align_foundation4_cohort(player_ids=active_ids,
                long_forecast=forecast, terminal_features=provide_foundation4_terminal_features())
        expected_input = long_term_intrinsic_input_fingerprint(
            forecast,
            rules=context.league_state.league.rules,
        )
        canonical_key = ArtifactKey(
            artifact_kind=FOUNDATION4_Y4_Y7_ARTIFACT_KIND,
            scope_kind=CAREER_INTRINSIC_SCOPE_KIND,
            scope_id=context.league_state.league.league_id,
            input_fingerprint=expected_input,
            model_version=LONG_TERM_INTRINSIC_MODEL_VERSION,
        )
        record = self._persistence_store.get_reusable_artifact(canonical_key)
        migrated_legacy = False
        if record is None:
            legacy_key = ArtifactKey(
                artifact_kind=FOUNDATION4_Y4_Y7_ARTIFACT_KIND,
                scope_kind=LEGACY_FOUNDATION4_SCOPE_KIND,
                scope_id=context.league_state.league.league_id,
                input_fingerprint=expected_input,
                model_version=LONG_TERM_INTRINSIC_MODEL_VERSION,
            )
            record = self._persistence_store.get_reusable_artifact(legacy_key)
            migrated_legacy = record is not None
        if record is None:
            return None
        try:
            contract = LongTermIntrinsicShadowContract.model_validate(
                dict(record.payload)
            )
        except (TypeError, ValueError):
            return None
        if migrated_legacy:
            self._persistence_store.put_artifact(
                ReusableArtifactRecord(
                    key=canonical_key,
                    payload=contract.model_dump(mode="json"),
                    computed_at=utc_now(),
                )
            )
        with self._lock:
            # One component, exact semantic identity, short idle lifetime. Explicit
            # Y4-Y7 consumers reuse it without repeatedly reading a large JSONB row.
            if self._cached_user_id == context.user_id and self._cached_fingerprint == fingerprint:
                self._cached_component = contract
                if self._component_timer is not None:
                    self._component_timer.cancel()
                # A Timer retains its callback after firing. Capture only a
                # weak reference; otherwise the supposedly evicted full matrix
                # stays resident through self -> timer -> callback -> contract.
                component_ref = ref(contract)
                def evict():
                    with self._lock:
                        if self._component_timer is timer:
                            if self._cached_component is component_ref():
                                self._cached_component = None
                            self._component_timer = None
                timer = Timer(30.0, evict)
                self._component_timer = timer
                self._component_timer.daemon = True
                self._component_timer.start()
        return contract

    def _reference_checkpoint_key(
        self, context: UserRuntimeContext, fingerprint: str
    ) -> ArtifactKey:
        key = self._career_key(context, fingerprint)
        return ArtifactKey(
            artifact_kind=CAREER_REFERENCE_CHECKPOINT_ARTIFACT_KIND,
            scope_kind=key.scope_kind,
            scope_id=key.scope_id,
            input_fingerprint=key.input_fingerprint,
            model_version=key.model_version,
        )

    def _persist(
        self,
        context: UserRuntimeContext,
        *,
        dependency_fingerprint: str,
        component: LongTermIntrinsicShadowContract | None,
        contract: CareerForwardIntrinsicShadowContract,
        source_manifest: Mapping[str, object] | None = None,
        retryable_batch_incomplete: bool = False,
    ) -> None:
        if self._persistence_store is None:
            return
        if component is not None:
            clear_shapley_execution_caches()
            reclaim_before_heavy_allocation(label="career-before-component-serialization")
            self._persistence_store.put_artifact(
                ReusableArtifactRecord(
                    key=self._component_key(context, component),
                    payload=component.model_dump(mode="json"),
                    computed_at=utc_now(),
                )
            )
        clear_shapley_execution_caches()
        reclaim_before_heavy_allocation(label="career-before-contract-serialization")
        payload = contract.model_dump(mode="json")
        payload["_foundation4_dependency_fingerprint"] = dependency_fingerprint
        from .p0_live_candidate_runtime import valid_live_source_manifest
        source_complete = valid_live_source_manifest(source_manifest)
        retryable_batch_incomplete = (
            retryable_batch_incomplete or self.retryable_incomplete_contract(contract)
        )
        complete = (self._expanded_career_contract_loader is None
                    or (source_complete and not retryable_batch_incomplete))
        payload["_career_expansion_complete"] = complete
        payload["_career_retryable_batch_incomplete"] = retryable_batch_incomplete
        if source_complete:
            payload["_career_source_manifest"] = dict(source_manifest)
            payload["_career_complete_input_fingerprint"] = canonical_fingerprint(
                "career-complete-live-inputs-v1", dependency_fingerprint, source_manifest["digest"],
            )
        self._persistence_store.put_artifact(
            ReusableArtifactRecord(
                key=(self._career_key(context, dependency_fingerprint) if complete
                     else self._reference_checkpoint_key(context, dependency_fingerprint)),
                payload=payload,
                computed_at=utc_now(),
            )
        )

    def retryable_incomplete_contract(self, contract) -> bool:
        """Retry producer-owned batch failures, never infer failure from coverage.

        A completed expansion may legitimately have only explicit exceptions.
        These prefixes are emitted by this bridge's batch error boundaries;
        player-specific evidence/scoring/identity failures remain completed.
        """
        if self._expanded_career_contract_loader is None or contract is None:
            return False
        batch_failures = (
            "dynamic P0 acquisition failed:",
            "accepted Foundation 4 dynamic materializer failed:",
            "accepted Foundation 4 dynamic materializer input bundle is not configured",
        )
        return any(str(reason).startswith(batch_failures)
                   for reason in contract.player_coverage_failures.values())

    def clear_user_cache(self, user_id: str) -> int:
        with self._lock:
            if self._cached_user_id != user_id:
                return 0
            if self._component_timer is not None:
                self._component_timer.cancel()
                self._component_timer = None
            self._cached_user_id = None
            self._cached_fingerprint = None
            self._cached_contract = None
            self._cached_component = None
            return 1

    def _append_expanded_rostered_contract(
        self,
        context: UserRuntimeContext,
        frozen_reference: CareerForwardIntrinsicShadowContract,
    ) -> tuple[CareerForwardIntrinsicShadowContract, Mapping[str, object], bool]:
        loader = self._expanded_career_contract_loader
        if loader is None:
            return frozen_reference, {}, False
        if context.league_state is None:
            raise ValueError("dynamic Career append requires canonical league State")
        loaded = loader(context, frozen_reference)
        source_manifest = dict(loaded.source_manifest) if isinstance(loaded, ExpandedCareerContractResult) else {}
        retryable_batch_incomplete = bool(
            isinstance(loaded, ExpandedCareerContractResult)
            and loaded.retryable_batch_incomplete
        )
        if isinstance(loaded, ExpandedCareerContractResult):
            expanded = loaded.contract
            failures = dict(loaded.failures)
        else:
            expanded = loaded
            failures = {}
        state_players = {row.player_id: row for row in context.league_state.players}
        roster_ids = {
            entry.player_id
            for team_state in context.league_state.team_states
            for entry in team_state.roster
        }
        if failures:
            invalid_failure_ids = set(failures) - roster_ids
            if invalid_failure_ids:
                raise ValueError(
                    "expanded Career failures include players outside exact-State roster: "
                    + ", ".join(sorted(invalid_failure_ids))
                )
            for player_id, reason in failures.items():
                player = state_players.get(player_id)
                position = str(player.position.value) if player is not None else ""
                if position not in {"QB", "RB", "WR", "TE"}:
                    raise ValueError(
                        f"expanded Career failure has unsupported exact-State roster identity {player_id}"
                    )
                if not str(reason).strip():
                    raise ValueError(
                        f"expanded Career failure reason is empty for {player_id}"
                    )
            frozen_ids = {row.player_id for row in frozen_reference.estimates}
            if set(failures) & frozen_ids:
                raise ValueError("expanded Career failure overlaps frozen reference")
        if expanded is None:
            if failures:
                frozen_reference = frozen_reference.model_copy(update={
                    "player_coverage_failures": {**frozen_reference.player_coverage_failures, **failures},
                })
            return frozen_reference, source_manifest, retryable_batch_incomplete
        frozen_ids = {row.player_id for row in frozen_reference.estimates}
        expanded_ids = {row.player_id for row in expanded.estimates}
        candidate_ids = expanded_ids - frozen_ids
        if not candidate_ids:
            return frozen_reference, source_manifest, retryable_batch_incomplete

        expanded_by_id = {row.player_id: row for row in expanded.estimates}
        if set(failures) & candidate_ids:
            raise ValueError("expanded Career player cannot have both value and failure")
        outside_roster = candidate_ids - roster_ids
        if outside_roster:
            raise ValueError(
                "expanded Career contract includes players outside exact-State roster: "
                + ", ".join(sorted(outside_roster))
            )
        for player_id in candidate_ids:
            player = state_players.get(player_id)
            position = str(player.position.value) if player is not None else ""
            if position not in {"QB", "RB", "WR", "TE"}:
                raise ValueError(
                    f"expanded Career contract has unsupported exact-State roster identity {player_id}"
                )
            if expanded_by_id[player_id].position.value != position:
                raise ValueError(
                    f"expanded Career position differs from exact-State roster for {player_id}"
                )
        appended = append_dynamic_career_estimates(
            frozen_reference,
            expanded,
            candidate_player_ids=candidate_ids,
        )
        contract = appended.model_copy(
            update={
                "player_coverage_failures": {
                    **frozen_reference.player_coverage_failures,
                    **failures,
                }
            }
        )
        return contract, source_manifest, retryable_batch_incomplete

    def __call__(
        self,
        context: UserRuntimeContext,
    ) -> CareerForwardIntrinsicShadowContract:
        context = self.pin_build_context(context)
        if context.league_state is None:
            raise ValueError("Foundation 4 requires canonical league State")
        if context.league_state.league.season != 2026:
            raise ValueError("Foundation 4 frozen current-cohort shadow is 2026-only")

        dependency_fingerprint = self.intrinsic_input_fingerprint(context)
        with self._lock:
            if (
                self._cached_user_id == context.user_id
                and self._cached_fingerprint == dependency_fingerprint
                and self._cached_contract is not None
            ):
                return self._cached_contract

        canonical_record = (self._persistence_store.get_reusable_artifact(
            self._career_key(context, dependency_fingerprint)
        ) if self._persistence_store is not None else None)
        completed = self._restore_frozen_compatible(
            context, require_complete=True, canonical_record=canonical_record,
        )
        if completed is not None:
            return completed
        if (canonical_record is not None
                and canonical_record.payload.get("_foundation4_dependency_fingerprint") != dependency_fingerprint):
            canonical_record = None  # Release rejected transport before checkpoint read.
        restored = self._restore_frozen_compatible(context, canonical_record=canonical_record)
        canonical_record = None  # Typed frozen contract owns the resumed inputs now.
        if restored is not None:
            (
                expanded_restored,
                source_manifest,
                retryable_batch_incomplete,
            ) = self._append_expanded_rostered_contract(context, restored)
            # Also persist a completed expansion with explicit failures or no
            # new candidates. Otherwise a restart repeats that acquisition too.
            self._persist(
                context,
                dependency_fingerprint=dependency_fingerprint,
                component=None,
                contract=expanded_restored,
                source_manifest=source_manifest,
                retryable_batch_incomplete=retryable_batch_incomplete,
            )
            if retryable_batch_incomplete:
                self.clear_user_cache(context.user_id)
                raise RetryableCareerExpansionIncomplete(
                    "Career ROS source coverage remains under the independent-source minimum; "
                    "the incomplete expansion was checkpointed for an explicit retry"
                )
            with self._lock:
                self._cached_user_id = context.user_id
                self._cached_fingerprint = dependency_fingerprint
                self._cached_contract = expanded_restored
            return expanded_restored

        # Scoring-coordinate compatibility is an authority precondition for the
        # holistic sum.  Validate it before loading Current Intrinsic so an
        # incompatible league cannot spend work or appear partially materialized.
        long_forecast = provide_foundation4_long_horizon_forecast_contract_for_rules(
            context.league_state.league.rules
        )

        current = self._current_intrinsic_loader(context)
        if current.status != ShapleyIntrinsicAvailability.READY:
            raise ValueError(
                "Foundation 4 requires ready governed Current Intrinsic Y1-Y3"
            )

        player_ids = {item.player_id for item in current.estimates}
        long_forecast, terminal_features = align_foundation4_cohort(
            player_ids=player_ids, long_forecast=long_forecast,
            terminal_features=provide_foundation4_terminal_features(),
        )
        component = build_long_term_intrinsic_shadow(
            long_forecast,
            rules=context.league_state.league.rules,
        )
        component_player_ids = {item.player_id for item in component.estimates}
        if component_player_ids != player_ids or set(terminal_features) != player_ids:
            raise ValueError(
                "Foundation 4 requires Current, Y4-Y7 and terminal coverage for the identical full cohort"
            )
        tails = {
            player_id: build_career_tail_authority(
                terminal_features[player_id],
                rules=context.league_state.league.rules,
            )
            for player_id in sorted(player_ids)
        }
        contract = build_career_forward_intrinsic_shadow(
            current,
            component,
            tails,
        ).model_copy(
            update={
                "ignored_long_term_residual_rule_stats": (
                    FOUNDATION4_LONG_TERM_IGNORED_RESIDUAL_RULE_STATS
                ),
                "scoring_coordinate_limitation": (
                    "Foundation 4 Y4+ omits fum_rec, fum_rec_td, st_ff, "
                    "st_fum_rec and st_td as immaterial/unpredictable residual "
                    "bonuses. Standalone Current Intrinsic remains unchanged; its "
                    "Y1-Y3 contributions may retain the bounded current scorer's "
                    "residual estimate. No historical residual reconstruction, "
                    "retraining, or heuristic multiplier is applied."
                ),
            }
        )
        # The Career contract now owns the completed Y1–Y3 and Y4+ results.
        # Keeping the full Current Shapley contract alive through dynamic
        # roster expansion needlessly overlaps two large player matrices.
        del current
        # Reference aggregation is complete. The expanded phase reuses the
        # typed contract/component, not these transient forecast/tail inputs.
        del long_forecast, terminal_features, tails
        frozen_contract = contract
        if (self._expanded_career_contract_loader is not None
                and self._persistence_store is not None):
            # Save the already accepted reference before allocating the live
            # expansion. An interrupted expansion can resume this exact base;
            # without a bound live manifest it is never a completed Career.
            with sample_rss_phase("career.reference_checkpoint"):
                self._persist(
                    context,
                    dependency_fingerprint=dependency_fingerprint,
                    component=component,
                    contract=frozen_contract,
                )
            # Explicit Y4-Y7 readers restore the persisted component on demand.
            # Do not hold its full matrix during candidate acquisition/fitting.
            component = None
        (
            contract,
            source_manifest,
            retryable_batch_incomplete,
        ) = self._append_expanded_rostered_contract(context, frozen_contract)
        # Expansion returns a new Career contract (or the same base when there
        # are no candidates); the pre-expansion alias is no longer required for
        # validation or persistence.
        del frozen_contract
        self._persist(
            context,
            dependency_fingerprint=dependency_fingerprint,
            component=component,
            contract=contract,
            source_manifest=source_manifest,
            retryable_batch_incomplete=retryable_batch_incomplete,
        )
        if retryable_batch_incomplete:
            self.clear_user_cache(context.user_id)
            raise RetryableCareerExpansionIncomplete(
                "Career ROS source coverage remains under the independent-source minimum; "
                "the incomplete expansion was checkpointed for an explicit retry"
            )
        with self._lock:
            self._cached_user_id = context.user_id
            self._cached_fingerprint = dependency_fingerprint
            self._cached_contract = contract
            # The exact component is persisted above and can be restored on
            # demand by explicit Y4–Y7 consumers. Do not keep this second large
            # matrix resident alongside the Career contract after materializing
            # a league; the hosted worker runs below a 512 MiB hard limit.
            self._cached_component = component if self._persistence_store is None else None
        return contract

    def current_component(
        self,
        context: UserRuntimeContext,
    ) -> LongTermIntrinsicShadowContract | None:
        return self.restore_component(context)


# Compatibility import for bounded migration; new production composition uses
# CareerIntrinsicLoader directly.
Foundation4CareerForwardShadowLoader = CareerIntrinsicLoader

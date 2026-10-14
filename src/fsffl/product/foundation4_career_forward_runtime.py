from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable, Mapping

from fsffl.persistence.contracts import (
    ArtifactKey,
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
from .foundation4_cohort import align_foundation4_cohort


FOUNDATION4_Y4_Y7_ARTIFACT_KIND = "foundation4_long_horizon_y4_y7_shadow"
CAREER_INTRINSIC_ARTIFACT_KIND = "career_intrinsic_v1"
CAREER_INTRINSIC_SCOPE_KIND = "league_intrinsic"
# Read-only migration aliases for the accepted Foundation 4 persisted authority.
LEGACY_FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND = "foundation4_career_forward_intrinsic_shadow"
LEGACY_FOUNDATION4_SCOPE_KIND = "league_intrinsic_shadow"
FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND = CAREER_INTRINSIC_ARTIFACT_KIND
FOUNDATION4_SCOPE_KIND = CAREER_INTRINSIC_SCOPE_KIND
FOUNDATION4_RUNTIME_VERSION = (
    "foundation4-career-forward-runtime-v5:active-cohort:"
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


ExpandedCareerContractLoader = Callable[
    [UserRuntimeContext, CareerForwardIntrinsicShadowContract],
    ExpandedCareerContractResult | CareerForwardIntrinsicShadowContract | None,
]
ExpandedCareerContractFingerprintResolver = Callable[[UserRuntimeContext], str]


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
        current_intrinsic_fingerprint_resolver: CurrentIntrinsicFingerprintResolver,
        persistence_store: PersistenceStore | None = None,
        expanded_career_contract_loader: ExpandedCareerContractLoader | None = None,
        expanded_career_contract_fingerprint_resolver: (
            ExpandedCareerContractFingerprintResolver | None
        ) = None,
    ) -> None:
        if (expanded_career_contract_loader is None) != (
            expanded_career_contract_fingerprint_resolver is None
        ):
            raise ValueError(
                "expanded Career contract loader and semantic fingerprint resolver "
                "must be configured together"
            )
        self._expanded_career_contract_loader = expanded_career_contract_loader
        self._expanded_career_contract_fingerprint_resolver = (
            expanded_career_contract_fingerprint_resolver
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

    def intrinsic_input_fingerprint(self, context: UserRuntimeContext) -> str:
        if context.league_state is None:
            raise ValueError("Foundation 4 requires canonical league State")
        payload = {
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
                self._expanded_career_contract_fingerprint_resolver(context)
                if self._expanded_career_contract_fingerprint_resolver is not None
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
        return ArtifactKey(
            artifact_kind=CAREER_INTRINSIC_ARTIFACT_KIND,
            scope_kind=CAREER_INTRINSIC_SCOPE_KIND,
            scope_id=context.league_state.league.league_id,
            input_fingerprint=fingerprint,
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
        if self._persistence_store is None or context.league_state is None:
            return None
        fingerprint = self.intrinsic_input_fingerprint(context)
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
        if dependency != fingerprint:
            return None
        try:
            contract = CareerForwardIntrinsicShadowContract.model_validate(payload)
        except (TypeError, ValueError):
            return None
        if migrated_legacy:
            migrated_payload = contract.model_dump(mode="json")
            migrated_payload["_foundation4_dependency_fingerprint"] = fingerprint
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
            self._cached_contract = contract
            self._cached_component = None
        return contract

    def restore_component(
        self,
        context: UserRuntimeContext,
    ) -> LongTermIntrinsicShadowContract | None:
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
        return contract

    def _persist(
        self,
        context: UserRuntimeContext,
        *,
        dependency_fingerprint: str,
        component: LongTermIntrinsicShadowContract,
        contract: CareerForwardIntrinsicShadowContract,
    ) -> None:
        if self._persistence_store is None:
            return
        self._persistence_store.put_artifact(
            ReusableArtifactRecord(
                key=self._component_key(context, component),
                payload=component.model_dump(mode="json"),
                computed_at=utc_now(),
            )
        )
        payload = contract.model_dump(mode="json")
        payload["_foundation4_dependency_fingerprint"] = dependency_fingerprint
        self._persistence_store.put_artifact(
            ReusableArtifactRecord(
                key=self._career_key(context, dependency_fingerprint),
                payload=payload,
                computed_at=utc_now(),
            )
        )

    def clear_user_cache(self, user_id: str) -> int:
        with self._lock:
            if self._cached_user_id != user_id:
                return 0
            self._cached_user_id = None
            self._cached_fingerprint = None
            self._cached_contract = None
            self._cached_component = None
            return 1

    def _append_expanded_rostered_contract(
        self,
        context: UserRuntimeContext,
        frozen_reference: CareerForwardIntrinsicShadowContract,
    ) -> CareerForwardIntrinsicShadowContract:
        loader = self._expanded_career_contract_loader
        if loader is None:
            return frozen_reference
        if context.league_state is None:
            raise ValueError("dynamic Career append requires canonical league State")
        loaded = loader(context, frozen_reference)
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
            if not failures:
                return frozen_reference
            return frozen_reference.model_copy(
                update={
                    "player_coverage_failures": {
                        **frozen_reference.player_coverage_failures,
                        **failures,
                    }
                }
            )
        frozen_ids = {row.player_id for row in frozen_reference.estimates}
        expanded_ids = {row.player_id for row in expanded.estimates}
        candidate_ids = expanded_ids - frozen_ids
        if not candidate_ids:
            return frozen_reference

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
        return appended.model_copy(
            update={
                "player_coverage_failures": {
                    **frozen_reference.player_coverage_failures,
                    **failures,
                }
            }
        )

    def __call__(
        self,
        context: UserRuntimeContext,
    ) -> CareerForwardIntrinsicShadowContract:
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

        restored = self.restore_compatible(context)
        if restored is not None:
            expanded_restored = self._append_expanded_rostered_contract(
                context, restored
            )
            if expanded_restored != restored:
                component = self.restore_component(context)
                if component is not None:
                    self._persist(
                        context,
                        dependency_fingerprint=dependency_fingerprint,
                        component=component,
                        contract=expanded_restored,
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
        # Reference aggregation is complete. The expanded phase reuses the
        # typed contract/component, not these transient forecast/tail inputs.
        del long_forecast, terminal_features, tails
        contract = self._append_expanded_rostered_contract(context, contract)
        self._persist(
            context,
            dependency_fingerprint=dependency_fingerprint,
            component=component,
            contract=contract,
        )
        with self._lock:
            self._cached_user_id = context.user_id
            self._cached_fingerprint = dependency_fingerprint
            self._cached_contract = contract
            self._cached_component = component
        return contract

    def current_component(
        self,
        context: UserRuntimeContext,
    ) -> LongTermIntrinsicShadowContract | None:
        with self._lock:
            if self._cached_user_id == context.user_id and self._cached_component is not None:
                return self._cached_component
        return self.restore_component(context)


# Compatibility import for bounded migration; new production composition uses
# CareerIntrinsicLoader directly.
Foundation4CareerForwardShadowLoader = CareerIntrinsicLoader

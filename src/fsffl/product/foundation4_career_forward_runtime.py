from __future__ import annotations

import hashlib
import json
from threading import RLock
from typing import Callable

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
    FOUNDATION4_TERMINAL_FEATURES_SEMANTIC_SHA256,
    provide_foundation4_long_horizon_forecast_contract_for_rules,
    provide_foundation4_terminal_features,
)
from .runtime import UserRuntimeContext


FOUNDATION4_Y4_Y7_ARTIFACT_KIND = "foundation4_long_horizon_y4_y7_shadow"
FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND = "foundation4_career_forward_intrinsic_shadow"
FOUNDATION4_SCOPE_KIND = "league_intrinsic_shadow"
FOUNDATION4_RUNTIME_VERSION = "foundation4-career-forward-runtime-v2:fsffl-scored-freeze"


CurrentIntrinsicLoader = Callable[[UserRuntimeContext], ShapleyIntrinsicContract]
CurrentIntrinsicFingerprintResolver = Callable[[UserRuntimeContext], str]


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


class Foundation4CareerForwardShadowLoader:
    """Build/persist the holistic shadow without mutating Current Intrinsic."""

    forecast_model_version = "foundation4:fsffl-scored-y4-y7-plus-y8-terminal-v2"

    def __init__(
        self,
        *,
        current_intrinsic_loader: CurrentIntrinsicLoader,
        current_intrinsic_fingerprint_resolver: CurrentIntrinsicFingerprintResolver,
        persistence_store: PersistenceStore | None = None,
    ) -> None:
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
            artifact_kind=FOUNDATION4_CAREER_FORWARD_ARTIFACT_KIND,
            scope_kind=FOUNDATION4_SCOPE_KIND,
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
        expected_input = long_term_intrinsic_input_fingerprint(
            forecast,
            rules=context.league_state.league.rules,
        )
        record = self._persistence_store.get_reusable_artifact(
            ArtifactKey(
                artifact_kind=FOUNDATION4_Y4_Y7_ARTIFACT_KIND,
                scope_kind=FOUNDATION4_SCOPE_KIND,
                scope_id=context.league_state.league.league_id,
                input_fingerprint=expected_input,
                model_version=LONG_TERM_INTRINSIC_MODEL_VERSION,
            )
        )
        if record is None:
            return None
        try:
            contract = LongTermIntrinsicShadowContract.model_validate(
                dict(record.payload)
            )
        except (TypeError, ValueError):
            return None
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
            return restored

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

        component = build_long_term_intrinsic_shadow(
            long_forecast,
            rules=context.league_state.league.rules,
        )
        terminal_features = provide_foundation4_terminal_features()
        player_ids = {item.player_id for item in current.estimates}
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
        )
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

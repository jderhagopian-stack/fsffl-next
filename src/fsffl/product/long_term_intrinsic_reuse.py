"""Reuse a pure Value component after its upstream Forecast inputs are prepared.

No State/source acquisition or final Career readiness is owned here. There is no
process cache: the existing persistence transport holds one latest numerical
result per rules/cohort coordinate, shared only for identical semantic inputs.
"""
from __future__ import annotations

import logging

from fsffl.forecast.long_horizon_contract import LongHorizonForecastAuthorityContract
from fsffl.state.models import LeagueRules
from fsffl.persistence.contracts import ArtifactKey, PersistenceStore, ReusableArtifactRecord, canonical_fingerprint, utc_now
from fsffl.value.long_term_intrinsic import (
    LONG_TERM_INTRINSIC_MODEL_VERSION,
    LongTermIntrinsicShadowContract,
    build_long_term_intrinsic_shadow,
    long_term_intrinsic_input_fingerprint,
)
from fsffl.value.shapley_intrinsic import FROZEN_SHAPLEY_SEED, clear_shapley_execution_caches
from .resource_coordinator import reclaim_before_heavy_allocation

_logger = logging.getLogger("uvicorn.error")


class LongTermIntrinsicReuse:
    """An optional numerical execution shortcut, never an analytical authority."""

    def __init__(self, persistence_store: PersistenceStore):
        self.store = persistence_store

    def __call__(
        self, forecast: LongHorizonForecastAuthorityContract, *, rules: LeagueRules,
    ) -> LongTermIntrinsicShadowContract:
        expected = long_term_intrinsic_input_fingerprint(forecast, rules=rules)
        # The Value function consumes these public football Forecast rows and
        # rules, not league/user/State identity. Never key by a capture timestamp.
        # A stable slot avoids retaining a large JSON row per new projection.
        scope = canonical_fingerprint(
            "expanded-y4-y7-latest-v1", forecast.evaluation_season,
            rules.model_dump(mode="json"), sorted(forecast.player_ids),
        )
        key = ArtifactKey(
            artifact_kind="expanded_long_term_intrinsic_component",
            scope_kind="forecast_rules_cohort", scope_id=scope,
            input_fingerprint=scope, model_version=LONG_TERM_INTRINSIC_MODEL_VERSION,
        )
        record = cached = None
        try:
            record = self.store.get_reusable_artifact(key)
            if (record is not None and record.reusable and record.key == key
                    and record.payload.get("input_fingerprint") == expected):
                cached = LongTermIntrinsicShadowContract.model_validate(record.payload)
                positions = {row.player_id: row.position for row in forecast.forecasts}
                if (
                    cached.input_fingerprint == expected
                    and cached.base_seed == FROZEN_SHAPLEY_SEED
                    and cached.horizon_seeds == tuple(FROZEN_SHAPLEY_SEED + y for y in (4, 5, 6, 7))
                    and cached.evaluation_season == forecast.evaluation_season
                    and cached.forecast_contract_version == forecast.contract_version
                    and cached.forecast_model_version == forecast.forecast_model_version
                    and len(cached.estimates) == len(positions)
                    and {row.player_id: row.position for row in cached.estimates} == positions
                ):
                    _logger.info("FSFFL expanded long-term component reuse=hit")
                    return cached
        except Exception as exc:
            # Optimization failure must not turn a valid owned calculation into
            # missing Career coverage. Log no private payload/provider details.
            _logger.warning("FSFFL expanded long-term component read failed type=%s", type(exc).__name__)
        record = cached = None  # Release rejected JSON before allocating Shapley work.
        _logger.info("FSFFL expanded long-term component reuse=miss")
        contract = build_long_term_intrinsic_shadow(forecast, rules=rules)
        try:
            clear_shapley_execution_caches()
            reclaim_before_heavy_allocation(label="career-before-expanded-component-serialization")
            self.store.put_artifact(ReusableArtifactRecord(
                key=key, payload=contract.model_dump(mode="json"), computed_at=utc_now(),
            ))
        except Exception as exc:
            _logger.warning("FSFFL expanded long-term component write failed type=%s", type(exc).__name__)
        return contract

from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException

from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicContract

from .intrinsic_background import (
    IntrinsicBuildStatus,
    ShapleyIntrinsicBackgroundCoordinator,
    intrinsic_failure_payload,
    intrinsic_loading_payload,
)
from .league_value_lenses import (
    BROAD_MARKET_SCALE_ID,
    INTRINSIC_PRESENTATION_COORDINATE,
    LEAGUE_VALUE_LENS_CONTRACT_VERSION,
    build_league_value_lenses,
)
from .runtime import PrivateBetaRuntimeStore, UserRuntimeContext


IntrinsicContractLoader = Callable[[UserRuntimeContext], ShapleyIntrinsicContract]
PresentationPayloadLoader = Callable[[str, UserRuntimeContext, str], dict[str, object] | None]
_logger = logging.getLogger("uvicorn.error")


def install_league_value_lens_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    contract_loader: IntrinsicContractLoader,
    require_user,
    background_coordinator: ShapleyIntrinsicBackgroundCoordinator | None = None,
    presentation_payload_loader: PresentationPayloadLoader | None = None,
) -> None:
    """Expose Atlas-ready player lenses without creating team value authority."""

    @app.get("/api/league/value-lenses")
    def league_value_lenses(
        universe: str = "rostered",
        user_id: str = Depends(require_user),
    ) -> dict[str, object]:
        runtime = runtime_store.get(user_id)
        if universe not in {"rostered", "all"}:
            raise HTTPException(
                status_code=422,
                detail="universe must be rostered or all",
            )
        if runtime.league_state is None:
            raise HTTPException(
                status_code=409,
                detail="Connect a league before requesting League value lenses",
            )
        if presentation_payload_loader is not None:
            surface = (
                "market_value_lenses_all"
                if universe == "all"
                else "market_value_lenses_rostered"
            )
            stale = presentation_payload_loader(user_id, runtime, surface)
            if stale is not None:
                return stale

        intrinsic = None
        intrinsic_error = None
        intrinsic_record = None
        if background_coordinator is not None:
            record = background_coordinator.current(runtime)
            first_load_staging = bool(
                record is None
                and runtime.publication_generation_id is None
                and (
                    runtime.selected_team_id is None
                    or runtime_store.working_generation_active(user_id)
                    or runtime.forecast_evidence is None
                )
            )
            if first_load_staging:
                state = runtime.league_state
                player_universe = "all_players" if universe == "all" else "rostered_players"
                payload = {
                    "status": "building",
                    "contract_version": LEAGUE_VALUE_LENS_CONTRACT_VERSION,
                    "league_state_id": state.state_id,
                    "broad_market": {
                        "status": "building",
                        "scale_id": BROAD_MARKET_SCALE_ID,
                        "player_count": 0,
                        "universe": player_universe,
                        "team_total_authority": False,
                        "reason": (
                            "First-load value-lens materialization is staged until "
                            "the current core intelligence generation publishes."
                        ),
                    },
                    "fsffl_intrinsic": {
                        "authority_family": "canonical_shapley_intrinsic",
                        "status": "building",
                        "contract_version": None,
                        "quantity_semantics": None,
                        "display_coordinate": INTRINSIC_PRESENTATION_COORDINATE,
                        "player_count": 0,
                        "team_total_authority": False,
                        "reason": (
                            "Governed FSFFL Intrinsic is staged behind current core "
                            "intelligence enrichment."
                        ),
                        "retry_after_ms": 1500,
                        "build_status": "staged",
                    },
                    "value_presentation": {
                        "status": "building",
                        "reason": "Value presentation is staged behind current core enrichment.",
                        "presentation_only": True,
                    },
                    "players": [],
                    "all_player_forecast": {
                        "status": "building",
                        "horizon": "season",
                        "metric": "fantasy_points",
                        "covered_players": 0,
                        "requested_players": 0,
                        "evidence_basis": None,
                        "reason": "Current governed Forecast enrichment is still running.",
                    },
                    "player_universe": player_universe,
                    "teams": [
                        {
                            "team_id": team.team_id,
                            "team_name": team.display_name,
                            "rostered_player_count": 0,
                            "broad_market_covered_players": 0,
                            "intrinsic_covered_players": 0,
                            "comparable_players": 0,
                            "player_ids": [],
                        }
                        for team in sorted(state.teams, key=lambda item: item.team_id)
                    ],
                    "authority": {
                        "canonical_fsffl_intrinsic_authority": "shapley_intrinsic",
                        "broad_market_and_intrinsic_are_distinct_lenses": True,
                        "comparison_coordinate": INTRINSIC_PRESENTATION_COORDINATE,
                        "shared_value_index_presentation_only": False,
                        "raw_value_subtraction_used": False,
                        "display_value_index_subtraction_allowed": False,
                        "team_value_total_created": False,
                        "team_value_rank_created": False,
                        "league_market_value_available": False,
                        "team_utility_included": False,
                        "fsffl_cardinal_value_included": False,
                        "recommendation_authority": False,
                        "acceptance_probability": None,
                    },
                    "surface_readiness": {
                        "surface": "player_board",
                        "status": "building_optional",
                        "required_dependencies": ["canonical_state", "broad_market_value"],
                        "optional_dependencies": [
                            "fsffl_intrinsic_all_player",
                            "all_player_season_forecast",
                        ],
                        "blockers": [],
                        "missing_optional": [
                            "fsffl_intrinsic_all_player",
                            "all_player_season_forecast_partial",
                        ],
                        "league_state_id": state.state_id,
                        "retry_after_ms": 1500,
                    },
                    "intrinsic_execution": {
                        "status": "staged",
                        "league_state_id": state.state_id,
                        "forecast_coordinate": None,
                        "response_budget_exceeded": False,
                        "started_at": None,
                        "updated_at": None,
                        "error": None,
                    },
                }
                _logger.info(
                    "FSFFL Market value lenses staged first-load materialization universe=%s state=%s",
                    universe,
                    state.state_id,
                )
                return payload
            if record is None:
                record = background_coordinator.request(runtime)
            intrinsic_record = record
            if record.status in {
                IntrinsicBuildStatus.QUEUED,
                IntrinsicBuildStatus.RUNNING,
            }:
                loading = intrinsic_loading_payload(record)
                payload = build_league_value_lenses(
                    runtime,
                    None,
                    intrinsic_error=(
                        "Governed FSFFL Intrinsic is preparing server-side. "
                        "Broad Market remains independently usable."
                    ),
                    include_unrostered=universe == "all",
                )
                payload["status"] = (
                    "degraded"
                    if payload.get("broad_market", {}).get("status") == "ready"
                    else "building"
                )
                payload["fsffl_intrinsic"] = {
                    **dict(payload.get("fsffl_intrinsic") or {}),
                    "status": "building",
                    "reason": loading["message"],
                    "retry_after_ms": loading.get("retry_after_ms"),
                    "build_status": loading.get("build_status"),
                }
                forecast_status = str(
                    (payload.get("all_player_forecast") or {}).get("status")
                    or "unavailable"
                )
                payload["surface_readiness"] = {
                    "surface": "player_board",
                    "status": "building_optional",
                    "required_dependencies": ["canonical_state", "broad_market_value"],
                    "optional_dependencies": [
                        "fsffl_intrinsic_all_player",
                        "all_player_season_forecast",
                    ],
                    "blockers": [],
                    "missing_optional": [
                        "fsffl_intrinsic_all_player",
                        *(
                            []
                            if forecast_status == "ready"
                            else ["all_player_season_forecast_partial"]
                        ),
                    ],
                    "league_state_id": runtime.league_state.state_id,
                    "retry_after_ms": loading.get("retry_after_ms"),
                }
                payload["intrinsic_execution"] = {
                    "status": record.status.value,
                    "league_state_id": record.league_state_id,
                    "forecast_coordinate": record.forecast_coordinate,
                    "response_budget_exceeded": record.response_budget_exceeded,
                    "started_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat(),
                    "error": record.error,
                }
                _logger.info(
                    "FSFFL Market value lenses universe=%s state=%s forecast_status=%s "
                    "forecast_covered=%s/%s intrinsic_status=%s intrinsic_build=%s coordinate=%s",
                    universe,
                    runtime.league_state.state_id,
                    forecast_status,
                    (payload.get("all_player_forecast") or {}).get("covered_players"),
                    (payload.get("all_player_forecast") or {}).get("requested_players"),
                    (payload.get("fsffl_intrinsic") or {}).get("status"),
                    record.status.value,
                    record.forecast_coordinate,
                )
                return payload
            if record.status == IntrinsicBuildStatus.FAILED:
                intrinsic_error = str(intrinsic_failure_payload(record)["message"])
            else:
                intrinsic = record.contract
        else:
            try:
                intrinsic = contract_loader(runtime)
            except Exception as exc:
                # Broad Market remains independently usable. A failure in the Intrinsic
                # coordinate must not silently replace it or suppress the Market lens.
                intrinsic_error = (
                    "Governed FSFFL Intrinsic unavailable: "
                    f"{type(exc).__name__}: {exc}"
                )

        payload = build_league_value_lenses(
            runtime,
            intrinsic,
            intrinsic_error=intrinsic_error,
            include_unrostered=universe == "all",
        )
        broad_ready = payload.get("broad_market", {}).get("status") == "ready"
        intrinsic_ready = (
            payload.get("fsffl_intrinsic", {}).get("status") != "unavailable"
        )
        forecast_status = str(
            (payload.get("all_player_forecast") or {}).get("status")
            or "unavailable"
        )
        payload["surface_readiness"] = {
            "surface": "player_board",
            "status": (
                "ready"
                if broad_ready and intrinsic_ready and forecast_status == "ready"
                else ("degraded" if broad_ready else "blocked")
            ),
            "required_dependencies": ["canonical_state", "broad_market_value"],
            "optional_dependencies": [
                "fsffl_intrinsic_all_player",
                "all_player_season_forecast",
            ],
            "blockers": [] if broad_ready else ["broad_market_value"],
            "missing_optional": [
                *([] if intrinsic_ready else ["fsffl_intrinsic_all_player"]),
                *(
                    []
                    if forecast_status == "ready"
                    else ["all_player_season_forecast_partial"]
                ),
            ],
            "league_state_id": runtime.league_state.state_id,
            "retry_after_ms": None,
        }
        payload["intrinsic_execution"] = (
            {
                "status": intrinsic_record.status.value,
                "league_state_id": intrinsic_record.league_state_id,
                "forecast_coordinate": intrinsic_record.forecast_coordinate,
                "response_budget_exceeded": intrinsic_record.response_budget_exceeded,
                "started_at": intrinsic_record.created_at.isoformat(),
                "updated_at": intrinsic_record.updated_at.isoformat(),
                "error": intrinsic_record.error,
            }
            if intrinsic_record is not None
            else {
                "status": "synchronous",
                "league_state_id": runtime.league_state.state_id,
                "forecast_coordinate": getattr(intrinsic, "forecast_model_version", None),
                "response_budget_exceeded": False,
                "started_at": None,
                "updated_at": None,
                "error": intrinsic_error,
            }
        )
        _logger.info(
            "FSFFL Market value lenses universe=%s state=%s forecast_status=%s "
            "forecast_covered=%s/%s intrinsic_status=%s intrinsic_build=%s coordinate=%s reason=%s",
            universe,
            runtime.league_state.state_id,
            forecast_status,
            (payload.get("all_player_forecast") or {}).get("covered_players"),
            (payload.get("all_player_forecast") or {}).get("requested_players"),
            (payload.get("fsffl_intrinsic") or {}).get("status"),
            (payload.get("intrinsic_execution") or {}).get("status"),
            (payload.get("intrinsic_execution") or {}).get("forecast_coordinate"),
            (payload.get("fsffl_intrinsic") or {}).get("reason"),
        )
        return payload

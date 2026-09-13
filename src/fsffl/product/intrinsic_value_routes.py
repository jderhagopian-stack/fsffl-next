from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from fsffl.forecast.non_qb_career_state import build_non_qb_bounded_paths
from fsffl.forecast.qb_career_state_runtime import build_qb_career_state_forecasts
from fsffl.state.models import Position
from fsffl.value.intrinsic_runtime import build_current_intrinsic_values_v1
from fsffl.value.intrinsic_v2 import IntrinsicV2EvidenceState
from fsffl.value.intrinsic_v2_runtime import build_current_intrinsic_values_v2

from .runtime import PrivateBetaRuntimeStore
from .webapp import require_beta_user


def _percentiles(estimates) -> dict[str, float]:
    rows = sorted(estimates, key=lambda estimate: (estimate.fundamental_value, estimate.player_id))
    if not rows:
        return {}
    output: dict[str, float] = {}
    index = 0
    total = len(rows)
    while index < total:
        end = index + 1
        while end < total and rows[end].fundamental_value == rows[index].fundamental_value:
            end += 1
        midpoint_rank = (index + end - 1) / 2.0
        percentile = (midpoint_rank + 0.5) / total
        for tied in rows[index:end]:
            output[tied.player_id] = percentile
        index = end
    return output


def _key_driver(estimate) -> str:
    terminal = estimate.terminal
    if terminal.pedigree_score is not None:
        direction = "adds" if terminal.pedigree_residual_value >= 0 else "reduces"
        return (
            f"Governed Years 1-3 Forecast plus post-Year-3 continuation; residual draft pedigree "
            f"{direction} {abs(terminal.pedigree_residual_value):.1f} fundamental-value units after "
            "removing the portion explained by Forecast."
        )
    return (
        "Governed Years 1-3 Forecast plus post-Year-3 continuation; exact draft-pick pedigree is "
        "unavailable, so no residual pedigree adjustment is fabricated."
    )


def install_intrinsic_value_v1_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
) -> None:
    """Expose legacy v1 plus the independent Fundamental Intrinsic successor."""

    def _context_and_paths(user_id: str):
        context = runtime_store.get(user_id)
        if context.league_state is None:
            raise HTTPException(status_code=409, detail="Connect a league before requesting Intrinsic Value")
        if context.forecast_evidence is None or not context.forecast_evidence.league_scored_forecasts:
            raise HTTPException(status_code=409, detail="Refresh authoritative Forecast before requesting Intrinsic Value")
        season_forecasts = context.forecast_evidence.league_scored_forecasts
        qb_career_states = build_qb_career_state_forecasts(
            context.league_state,
            season_forecasts=season_forecasts,
        )
        bounded_paths = build_non_qb_bounded_paths(
            context.league_state,
            season_forecasts=season_forecasts,
        )
        return context, season_forecasts, bounded_paths, qb_career_states

    @app.get("/api/value/intrinsic-v1")
    def intrinsic_value_v1(user_id: str = Depends(require_beta_user)):
        try:
            context, season_forecasts, bounded_paths, qb_career_states = _context_and_paths(user_id)
            result = build_current_intrinsic_values_v1(
                context.league_state,
                season_forecasts=season_forecasts,
                base_forecast_model_version=context.forecast_evidence.runtime_result.model_version,
                bounded_paths=bounded_paths,
                qb_career_states=qb_career_states,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Governed Intrinsic Value v1 unavailable: {type(exc).__name__}: {exc}",
            ) from exc
        return {
            "model_version": result.model_version,
            "forecast_policy_version": result.forecast_policy_version,
            "base_forecast_model_version": result.base_forecast_model_version,
            "coverage": result.coverage,
            "roster_player_count": result.roster_player_count,
            "valued_roster_player_count": result.valued_roster_player_count,
            "estimates": [estimate.model_dump(mode="json") for estimate in result.estimates],
        }

    @app.get("/api/value/intrinsic-v2")
    def intrinsic_value_v2(user_id: str = Depends(require_beta_user)):
        try:
            context, season_forecasts, bounded_paths, qb_career_states = _context_and_paths(user_id)
            result = build_current_intrinsic_values_v2(
                context.league_state,
                season_forecasts=season_forecasts,
                base_forecast_model_version=context.forecast_evidence.runtime_result.model_version,
                bounded_paths=bounded_paths,
                qb_career_states=qb_career_states,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Fundamental Intrinsic Value unavailable: {type(exc).__name__}: {exc}",
            ) from exc

        by_id = {estimate.player_id: estimate for estimate in result.estimates}
        percentile_by_id = _percentiles(result.estimates)
        player_by_id = {player.player_id: player for player in context.league_state.players}
        roster_ids = sorted(
            {
                entry.player_id
                for team_state in context.league_state.team_states
                for entry in team_state.roster
                if entry.player_id in player_by_id
                and player_by_id[entry.player_id].position in {Position.QB, Position.RB, Position.WR, Position.TE}
            }
        )
        players = []
        for player_id in roster_ids:
            estimate = by_id.get(player_id)
            if estimate is None:
                players.append(
                    {
                        "player_id": player_id,
                        "availability": "UNAVAILABLE",
                        "evidence_state": "unavailable",
                        "reason": "Governed current Forecast evidence is unavailable for this player; no Intrinsic zero or percentile is fabricated.",
                        "confidence": None,
                        "raw_fundamental_intrinsic": None,
                        "intrinsic_value": None,
                        "percentile": None,
                        "uncertainty": None,
                        "key_driver": None,
                        "model_version": result.model_version,
                    }
                )
                continue
            players.append(
                {
                    "player_id": player_id,
                    "availability": "AVAILABLE" if estimate.evidence_state == IntrinsicV2EvidenceState.COMPLETE else "PARTIAL",
                    "evidence_state": estimate.evidence_state.value,
                    "reason": estimate.evidence_note,
                    "confidence": estimate.confidence.value,
                    "raw_fundamental_intrinsic": estimate.fundamental_value,
                    "intrinsic_value": estimate.display_value,
                    "percentile": percentile_by_id.get(player_id),
                    "uncertainty": estimate.fundamental_stddev,
                    "key_driver": _key_driver(estimate),
                    "model_version": estimate.model_version,
                    "calibration_version": estimate.calibration_version,
                    "display_scale_version": estimate.display_scale_version,
                    "forecast_policy_version": estimate.forecast_policy_version,
                    "base_forecast_model_version": estimate.base_forecast_model_version,
                }
            )

        return {
            "coordinate": "FSFFL Intrinsic Value",
            "definition": "team-independent fundamental long-term dynasty asset worth from football fundamentals",
            "model_version": result.model_version,
            "forecast_policy_version": result.forecast_policy_version,
            "base_forecast_model_version": result.base_forecast_model_version,
            "coverage": result.coverage,
            "roster_player_count": result.roster_player_count,
            "valued_roster_player_count": result.valued_roster_player_count,
            "players": players,
            "estimates": [estimate.model_dump(mode="json") for estimate in result.estimates],
        }

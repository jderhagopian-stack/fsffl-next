"""Select existing Forecast authority; never acquire or invent participation."""
from __future__ import annotations


def simulation_forecasts(evidence):
    forward = getattr(evidence, "simulation_forward_forecasts", None)
    return forward if forward is not None else evidence.league_scored_forecasts


def require_forward_simulation_evidence(state, evidence, baseline=None, *, changed_state=False):
    if getattr(evidence, "simulation_missing_player_ids", ()):
        raise ValueError("Current ROS coverage is incomplete; no confirmed competitive outcomes are available")
    if getattr(evidence, "simulation_forward_forecasts", None) is not None and (
        getattr(evidence, "simulation_evaluation_as_of", None) is None
        or not getattr(evidence, "simulation_source_state_id", None)
        or not getattr(evidence, "simulation_basis", None)
    ):
        raise ValueError("Simulation forward evidence lacks exact source coordinates")
    if (state.completed_through_week or 0) > 0 and getattr(evidence, "simulation_forward_forecasts", None) is None:
        raise ValueError(
            "Current-season Simulation requires participation-adjusted rest-of-season "
            "evidence. Refresh Intelligence; preseason projections cannot confirm remaining outcomes."
        )
    if (state.completed_through_week or 0) > 0:
        if getattr(evidence, "simulation_basis", None) == "preseason_remaining_prior":
            raise ValueError("Current ROS sources are unavailable; a preseason prior cannot confirm remaining outcomes")
        if not changed_state and getattr(evidence, "simulation_source_state_id", None) != state.state_id:
            raise ValueError("Simulation ROS evidence does not match the baseline State; Refresh Intelligence")
        if baseline is not None:
            from .simulation_runtime import simulation_forecast_dependency_fingerprint
            preparation = baseline.scenario_preparation
            fingerprint = simulation_forecast_dependency_fingerprint(
                simulation_forecasts(evidence), forecast_model_version=evidence.model_version)
            if preparation is None or preparation.forecast_fingerprint != fingerprint:
                raise ValueError("Baseline Simulation does not use the same ROS evidence; Refresh Intelligence")


def current_forecast_coordinates(state, evidence):
    """Shared current roster context; preserved full-season evidence stays separate."""
    from fsffl.forecast.models import ForecastHorizon
    if getattr(evidence, "simulation_missing_player_ids", ()):
        raise ValueError("Current ROS coverage is incomplete; current roster consequences are unavailable")
    forward = getattr(evidence, "simulation_forward_forecasts", None)
    if forward is not None:
        return forward, ForecastHorizon.REST_OF_SEASON, evidence.simulation_evaluation_as_of
    return (evidence.raw_forecasts + evidence.league_scored_forecasts,
            ForecastHorizon.SEASON, state.as_of)


def current_forecast_identity(state, evidence):
    from fsffl.forecast.models import ForecastHorizon
    horizon = (ForecastHorizon.REST_OF_SEASON if getattr(evidence, "simulation_forward_forecasts", None) is not None else ForecastHorizon.SEASON)
    cutoff = getattr(evidence, "simulation_evaluation_as_of", None) or state.as_of
    return {'missing_player_ids': list(getattr(evidence, 'simulation_missing_player_ids', ())),'basis': getattr(evidence, 'simulation_basis', None) or evidence.evidence_basis,
            'horizon': horizon.value, 'evaluation_as_of': cutoff.isoformat(),
            'source_state_id': getattr(evidence, 'simulation_source_state_id', None)}

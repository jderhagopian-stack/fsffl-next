from __future__ import annotations

from fsffl.forecast.k_dst_provisional import (
    ProvisionalKDstConsumer,
    ProvisionalKDstForecast,
    assess_provisional_k_dst_consumer,
    provisional_k_dst_readiness,
)


def build_provisional_k_dst_presentation(
    forecast: ProvisionalKDstForecast,
) -> dict[str, object]:
    """Presentation-only view that keeps degraded Forecast authority visible."""

    decision = assess_provisional_k_dst_consumer(
        forecast,
        ProvisionalKDstConsumer.PRESENTATION,
    )
    readiness = provisional_k_dst_readiness(forecast)
    return {
        "status": "ready" if decision.allowed else "unavailable",
        "label": "Provisional 2026 ROS K/DST",
        "authority_tier": forecast.authority_tier,
        "league_id": forecast.league_id,
        "league_state_id": forecast.league_state_id,
        "subject_key": forecast.subject_key,
        "subject_family": forecast.subject_family.value,
        "horizon": forecast.horizon,
        "as_of": forecast.as_of.isoformat(),
        "period_start": forecast.period_start.isoformat(),
        "period_end": forecast.period_end.isoformat(),
        "fantasy_points": forecast.fantasy_points_mean,
        "full_forecast_authority": False,
        "simulation_grade": False,
        "preseason_comparison": {
            "available": False,
            "status": forecast.preseason_comparison_status,
        },
        "coverage": {
            "supported_rule_stats": list(forecast.supported_rule_stats),
            "omitted_rule_stats": list(forecast.omitted_rule_stats),
            "partially_supported_rule_stats": list(
                forecast.partially_supported_rule_stats
            ),
            "included_coordinates": [
                item.model_dump(mode="json")
                for item in forecast.included_coordinates
            ],
            "omitted_coordinates": [
                item.model_dump(mode="json")
                for item in forecast.omitted_coordinates
            ],
        },
        "uncertainty": forecast.uncertainty.model_dump(mode="json"),
        "provenance": {
            "source_ids": list(forecast.source_ids),
            "independence_groups": list(forecast.independence_groups),
            "content_refs": list(forecast.provenance_refs),
        },
        "readiness": readiness.model_dump(mode="json"),
        "consumer_guard": {
            "allowed": decision.allowed,
            "requires_provisional_metadata": decision.requires_provisional_metadata,
            "reason": decision.reason,
        },
        "full_authority_blockers": list(forecast.full_authority_blockers),
    }

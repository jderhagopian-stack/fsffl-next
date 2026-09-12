from __future__ import annotations

from typing import Any


def _side_for_team(container: Any, team_id: str):
    if container is None:
        return None
    for name in ("side_a", "side_b"):
        side = getattr(container, name, None)
        if side is not None and getattr(side, "team_id", None) == team_id:
            return side
    return None


def _material_direction(material_assessment: Any, team_id: str, metric: str) -> str | None:
    side = _side_for_team(material_assessment, team_id)
    if side is None:
        return None
    value = getattr(side, metric, None)
    return getattr(value, "value", value)


def _economic_dimension(net: Any, *, materiality: str | None) -> dict[str, object]:
    if net is None:
        return {
            "available": False,
            "status": "unavailable",
            "net_delta": None,
            "sent_value": None,
            "received_value": None,
            "scale": None,
            "materiality": materiality,
        }
    status = getattr(getattr(net, "status", None), "value", getattr(net, "status", None))
    scale = getattr(getattr(net, "scale", None), "value", getattr(net, "scale", None))
    return {
        "available": status == "complete",
        "status": status or "unavailable",
        "net_delta": getattr(net, "mean_delta", None),
        "sent_value": getattr(net, "sent_mean", None),
        "received_value": getattr(net, "received_mean", None),
        "scale": scale,
        "materiality": materiality,
    }


def build_trade_decision_dimensions(
    *,
    focal_team_id: str,
    scenario_delta: Any = None,
    economic_net: Any = None,
    roster_adjusted_market_net: Any = None,
    material_assessment: Any = None,
    position_strength: Any = None,
    simulation_backed: bool,
) -> dict[str, object]:
    """Expose distinct Decision evidence channels without collapsing them into a score.

    This is an API/presentation evidence contract only. It copies already-authoritative
    Simulation, Team Utility, Value and Trade Decision outputs; it does not recalculate,
    weight or blend them. Near-term competition and long-term franchise value are
    intentionally allowed to disagree.
    """

    focal_economic = _side_for_team(economic_net, focal_team_id)
    intrinsic = getattr(focal_economic, "intrinsic", None) if focal_economic is not None else None
    raw_market = getattr(focal_economic, "market", None) if focal_economic is not None else None
    adjusted_market = _side_for_team(roster_adjusted_market_net, focal_team_id)

    competitive = getattr(scenario_delta, "competitive", None)
    resilience = getattr(scenario_delta, "resilience", None)
    competitive_available = bool(simulation_backed and competitive is not None)
    roster_available = resilience is not None or position_strength is not None

    market_status = getattr(getattr(adjusted_market, "status", None), "value", getattr(adjusted_market, "status", None))
    if adjusted_market is not None:
        market_dimension = {
            "available": market_status == "complete",
            "status": market_status or "unavailable",
            "net_delta": getattr(adjusted_market, "roster_adjusted_market_delta", None),
            "raw_trade_delta": getattr(adjusted_market, "raw_trade_market_delta", None),
            "mandatory_cut_cost": getattr(adjusted_market, "mandatory_cut_market_cost", None),
            "required_cut_count": getattr(adjusted_market, "required_cut_count", 0),
            "scale": getattr(getattr(raw_market, "scale", None), "value", getattr(raw_market, "scale", None)),
            "materiality": _material_direction(material_assessment, focal_team_id, "market_value"),
        }
    else:
        market_dimension = _economic_dimension(
            raw_market,
            materiality=_material_direction(material_assessment, focal_team_id, "market_value"),
        )

    intrinsic_dimension = _economic_dimension(
        intrinsic,
        materiality=_material_direction(material_assessment, focal_team_id, "intrinsic_value"),
    )

    near_term = {
        "available": competitive_available,
        "authority": "NEXT-4 Simulation",
        "simulation_backed": simulation_backed,
        "expected_wins_delta": getattr(competitive, "expected_wins", None) if competitive_available else None,
        "playoff_probability_delta": getattr(competitive, "playoff_probability", None) if competitive_available else None,
        "first_place_probability_delta": getattr(competitive, "first_place_probability", None) if competitive_available else None,
        "championship_probability_delta": getattr(competitive, "championship_probability", None) if competitive_available else None,
        "materiality": {
            "expected_wins": _material_direction(material_assessment, focal_team_id, "expected_wins"),
            "playoff_probability": _material_direction(material_assessment, focal_team_id, "playoff_probability"),
            "championship_probability": _material_direction(material_assessment, focal_team_id, "championship_probability"),
        },
    }

    long_term = {
        **intrinsic_dimension,
        "authority": "NEXT-3 Value",
        "concept": "intrinsic_franchise_value",
    }
    market = {
        **market_dimension,
        "authority": "NEXT-3 Value plus NEXT-5 mandatory-cut accounting",
        "concept": "current_market_economics",
    }
    roster = {
        "available": roster_available,
        "authority": "NEXT-4 Team Utility / NEXT-5 roster consequences",
        "resilience": resilience.model_dump(mode="json") if resilience is not None and hasattr(resilience, "model_dump") else None,
        "position_strength": position_strength.model_dump(mode="json") if position_strength is not None and hasattr(position_strength, "model_dump") else None,
        "largest_single_player_lineup_drop_materiality": _material_direction(
            material_assessment,
            focal_team_id,
            "largest_single_player_lineup_drop",
        ),
    }

    missing = tuple(
        name
        for name, available in (
            ("near_term_competitive", competitive_available),
            ("long_term_franchise_value", bool(intrinsic_dimension["available"])),
            ("roster_impact", roster_available),
            ("market_economics", bool(market_dimension["available"])),
        )
        if not available
    )
    return {
        "near_term_competitive": near_term,
        "long_term_franchise_value": long_term,
        "roster_impact": roster,
        "market_economics": market,
        "confidence": {
            "calibrated_confidence_available": False,
            "evidence_completeness": "complete" if not missing else "partial",
            "missing_dimensions": missing,
            "note": "No synthetic confidence score is created; each dimension preserves its source authority and availability.",
        },
        "combined_master_score": None,
    }

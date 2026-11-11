"""Bind published facts and request-scoped goals to Decision's directional view."""
from dataclasses import replace

from fsffl.state.models import FrozenModel, PlayerAsset
from fsffl.team_utility.utility import OwnerStrategicPosture
from fsffl.trade_decision.objectives import (
    ObjectiveMetric, OwnerObjectiveContext, TradeObjective, assess_owner_objectives,
)

from .opportunity_posture import calculated_competitive_state, default_posture_for_state


class TradeSearchInstructions(FrozenModel):
    objectives: tuple[TradeObjective, ...]
    protected_player_ids: tuple[str, ...] = ()


def objective_context(runtime, team_id, instructions=None):
    if instructions is not None:
        return OwnerObjectiveContext(
            team_id=team_id, objectives=instructions.objectives,
            protected_player_ids=instructions.protected_player_ids,
            source="explicit_request_instruction", explicitly_directed=True,
        )
    calculated = calculated_competitive_state(replace(runtime, selected_team_id=team_id))
    posture = default_posture_for_state(calculated)
    objectives = {
        OwnerStrategicPosture.WIN_NOW: (TradeObjective.CURRENT,),
        OwnerStrategicPosture.REBUILD: (TradeObjective.CAREER,),
        OwnerStrategicPosture.RETOOL: (TradeObjective.THREE_YEAR,),
    }.get(posture, (TradeObjective.CURRENT, TradeObjective.THREE_YEAR, TradeObjective.CAREER))
    return OwnerObjectiveContext(team_id=team_id, objectives=objectives,
        calculated_competitive_state=calculated.value, inferred_posture=posture.value,
        source="calculated_state_posture_hypothesis_v1")


def validate_search_instructions(runtime, proposal, instructions):
    if instructions is None:
        return
    context = objective_context(runtime, runtime.selected_team_id, instructions)
    owned = {entry.player_id for team in runtime.league_state.team_states
             if team.team_id == context.team_id for entry in team.roster}
    if not set(context.protected_player_ids) <= owned:
        raise ValueError("Protected players must belong to the managed team")
    sent = {asset.player_id for leg in (proposal.side_a, proposal.side_b)
            if leg.team_id == context.team_id for asset in leg.sends if isinstance(asset, PlayerAsset)}
    if sent.intersection(context.protected_player_ids):
        raise ValueError("The proposal sends a protected player")


def build_trade_objective_assessment(runtime, proposal, result, instructions=None):
    """Never recalculate models or alter their cache keys or final dispositions."""
    horizons = result.get("horizon_asset_economics") or {}
    by_team = {row["team_id"]: row for row in result.get("team_deltas", ())}
    cuts = {row["team_id"]: tuple(c["player_id"] for c in row["cuts"])
            for row in result.get("roster_legality", ())}
    authoritative = (result.get("scenario_computation") or {}).get("authoritative") is True
    source = f"{runtime.league_state.state_id}:{result.get('state_id_after', 'unavailable')}"
    sides = {}
    for label, leg in (("side_a", proposal.side_a), ("side_b", proposal.side_b)):
        context = objective_context(runtime, leg.team_id,
            instructions if leg.team_id == runtime.selected_team_id else None)
        metrics = []
        for horizon, goal in (("three_year", TradeObjective.THREE_YEAR), ("career", TradeObjective.CAREER)):
            row = ((horizons.get(horizon) or {}).get("roster_adjusted") or {}).get(label) or {}
            scale = row.get("scale") or {}
            metrics.append(ObjectiveMetric(objective=goal, metric="cut_adjusted_asset_contribution",
                unit=scale.get("unit_label", f"{horizon} raw Shapley contribution"),
                source_identity=scale.get("scale_id", "unavailable"),
                delta=row.get("roster_adjusted_intrinsic_delta"), authoritative=row.get("status") == "complete"))
        competitive = (by_team.get(leg.team_id) or {}).get("competitive") or {}
        for name, unit in (("expected_wins", "wins"), ("playoff_probability", "probability"),
                           ("first_place_probability", "regular_season_first_place_probability")):
            metrics.append(ObjectiveMetric(objective=TradeObjective.CURRENT, metric=name, unit=unit,
                source_identity=source, delta=competitive.get(name), authoritative=authoritative))
        resilience = (by_team.get(leg.team_id) or {}).get("resilience") or {}
        metrics.append(ObjectiveMetric(objective=TradeObjective.RESILIENCE,
            metric="largest_single_player_lineup_drop", unit="lineup_fantasy_points", source_identity=source,
            delta=resilience.get("largest_single_player_lineup_drop"), higher_is_better=False,
            authoritative=authoritative))
        market = ((result.get("roster_adjusted_market_net") or {}).get(label)) or {}
        economic_side = (result.get("economic_net") or {}).get(label) or {}
        market_scale = (economic_side.get("market") or {}).get("scale") or {}
        metrics.append(ObjectiveMetric(objective=TradeObjective.MARKET, metric="cut_adjusted_market_delta",
            unit=market_scale.get("unit_label", "upstream_market_value"),
            source_identity=f"{source}:{market_scale.get('scale_id', 'unavailable')}",
            delta=market.get("roster_adjusted_market_delta"), authoritative=market.get("status") == "complete"))
        sent = tuple(a.player_id for a in leg.sends if isinstance(a, PlayerAsset))
        assessment = assess_owner_objectives(context, tuple(metrics), sent_player_ids=sent,
            cut_player_ids=cuts.get(leg.team_id, ()))
        sides[label] = {**assessment.model_dump(mode="json"),
            "metrics": [m.model_dump(mode="json") for m in metrics]}
    return {**sides, "decision_effect": "no_disposition_change",
        "owner_behavior_used_for_priority_inference": False,
        "durable_owner_preference_claimed": False,
        "interpretation": "Directional alignment only; inferred motives, statistical significance and owner willingness are unconfirmed",
        "semantics": "asset_contribution_is_not_franchise_utility; overlapping_horizons_are_not_additive",
        "model_version": "trade-objective-assessment-v1"}

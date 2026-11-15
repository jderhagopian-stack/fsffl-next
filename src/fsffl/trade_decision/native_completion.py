"""Complete Decision with distinct native horizons, without invented materiality."""
from math import isfinite
from fsffl.state.models import FrozenModel
from fsffl.value.models import ValueScale
from .disposition import TradeDisposition as Action, _apply_package_guard
from .materiality import MaterialityDirection as M


class NativeHorizonChange(FrozenModel):
    horizon: str
    scale: ValueScale
    delta: float


def complete_native_trade_decision(base, *, material_side, native_changes, objectives,
                                  strategy, package_economics=None):
    """A completed strategic review does not require a fake native noise floor.

    Native-only gains and unresolved conflicts lead to REVIEW. They cannot become
    material gains merely because they are positive. Existing material Current
    benefits may support a clean, non-deteriorating complete package.
    """
    if material_side.team_id != base.evidence.focal_team_id:
        raise ValueError('Native completion must use the focal material assessment')
    if len(native_changes) != 2 or {n.horizon for n in native_changes} != {'three_year','career'}:
        raise ValueError('Both independent native horizons are required')
    if native_changes[0].scale == native_changes[1].scale:
        raise ValueError('Native horizons must retain distinct scales')
    if any(not isfinite(n.delta) for n in native_changes):
        raise ValueError('Native changes must be finite')
    metrics=('expected_wins','playoff_probability','championship_probability',
             'largest_single_player_lineup_drop','market_value')
    gains=tuple(k for k in metrics if getattr(material_side,k)==M.MATERIAL_GAIN)
    losses=tuple(k for k in metrics if getattr(material_side,k)==M.MATERIAL_LOSS)
    missing=tuple(k for k in metrics if getattr(material_side,k)==M.UNAVAILABLE)
    # Exact native direction is not an economic significance threshold.
    native_gains=tuple(n.horizon for n in native_changes if n.delta>0)
    native_losses=tuple(n.horizon for n in native_changes if n.delta<0)
    goal_set=set(objectives)
    future_goals={'three_year':'three_year_contribution','career':'career_contribution'}
    future_priority_gain=any(future_goals[h] in goal_set for h in native_gains)
    current_goal_gain='current_competitiveness' in goal_set and any(k in gains for k in metrics[:3])
    other_goal_gain=('market_capital' in goal_set and 'market_value' in gains) or ('resilience' in goal_set and 'largest_single_player_lineup_drop' in gains)
    reasons=[]
    constraints=strategy.get('status')=='constraints_violated'
    if missing:
        action=Action.INSUFFICIENT_EVIDENCE
    elif constraints:
        action=Action.DECLINE;reasons.append('protected_asset_constraint')
    elif losses and not gains and not native_gains:
        action=Action.DECLINE
    elif strategy.get('status')=='priority_tradeoff':
        action=Action.REVIEW;reasons.append('timeline_or_economic_tradeoff')
    elif (gains or native_gains) and (losses or native_losses):
        action=Action.REVIEW;reasons.append('timeline_or_economic_tradeoff')
    elif native_losses:
        action=Action.REVIEW;reasons.append('expected_native_contribution_loss')
    elif losses:
        action=Action.DECLINE
    elif current_goal_gain or other_goal_gain:
        if not strategy.get('position_evidence_available'):
            action=Action.REVIEW;reasons.append('positional_evidence_unavailable')
        elif strategy.get('positions_with_less_forecasted_depth') or strategy.get('positional_coverage_worsens'):
            action=Action.REVIEW;reasons.append('positional_depth_cost')
        else:
            action=Action.SUPPORT
    elif future_priority_gain or (native_gains and strategy.get('opportunistic_future_case')):
        action=Action.REVIEW;reasons.append('future_priority_benefit')
    elif native_gains or gains:
        action=Action.REVIEW;reasons.append('benefit_outside_selected_priorities')
    else:
        action=Action.NO_CLEAR_ADVANTAGE
    if strategy.get('resilience_worsens') and 'positional_depth_cost' not in reasons:
        reasons.append('lineup_resilience_cost')
    if strategy.get('depth_conversion_candidate'):
        reasons.append('potential_depth_to_future_conversion')
    action=_apply_package_guard(action,package_economics,focal_team_id=base.evidence.focal_team_id)
    if package_economics is not None and package_economics.status.value=='incomplete':
        missing=(*missing,'package_structure_economics')
    evidence=base.evidence.model_copy(update={
        'material_gains':gains,'material_losses':losses,'unavailable_metrics':missing,
        'native_horizons':tuple(n.model_dump(mode='json') for n in native_changes),
        'native_gains':native_gains,'native_losses':native_losses,
        'review_reasons':tuple(reasons),'priority_objectives':tuple(objectives),
        'native_materiality_status':'directional_only_not_calibrated',
        'strategic_resolution_applied':False})
    return base.model_copy(update={'disposition':action,'evidence':evidence,
        'model_version':'next5-trade-disposition-v6:separate-native-horizon-review'})

"""Transaction-specific motives beside materiality and final action authority."""
from .objectives import ObjectiveDirection as D, TradeObjective as G


def assess_transaction_strategy(assessment, metrics, position_context=None, *, preliminary_lineup_delta=None):
    """Recognize any priority horizon; preserve positional and timeline costs.

    This consumes existing evidence. Directional motives are not materiality,
    future optimized franchise utility, or an owner acceptance prediction.
    """
    goals = set(assessment.context.objectives)
    current = tuple(m for m in metrics if m.objective == G.CURRENT)
    current_known = bool(current) and all(m.direction() != D.UNKNOWN for m in current)
    current_losses = tuple(m.metric for m in current if m.direction() == D.LOSS)
    current_preserved = current_known and not current_losses
    future = (G.THREE_YEAR, G.CAREER)
    future_gains = tuple(g.value for g in future if any(m.objective == g and m.direction() == D.GAIN for m in metrics))
    future_losses = tuple(g.value for g in future if any(m.objective == g and m.direction() == D.LOSS for m in metrics))
    requested_gain = any(m.objective in goals for m in assessment.gains)
    opportunistic_future = bool(future_gains and current_preserved and not assessment.context.explicitly_directed)
    context = position_context or {}
    positions = context.get('positions', ())
    bench_sent = tuple(sorted({pid for row in positions for pid in row.get('outgoing_bench_ids', ())}))
    starters_sent = tuple(sorted({pid for row in positions for pid in row.get('outgoing_starter_ids', ())}))
    depth_costs = tuple(row['position'] for row in positions
        if len(row.get('after_forecasted_bench_ids', ())) < len(row.get('before_forecasted_bench_ids', ())))
    resilience = tuple(m for m in metrics if m.objective == G.RESILIENCE)
    resilience_known = bool(resilience) and all(m.direction() != D.UNKNOWN for m in resilience)
    resilience_loss = any(m.objective == G.RESILIENCE and m.direction() == D.LOSS for m in metrics)
    role_known = context.get('status') == 'complete'
    coverage_worse = role_known and context.get('after_unfilled_slots', 0) > context.get('before_unfilled_slots', 0)
    if assessment.protected_players_lost:
        status = 'constraints_violated'
    elif assessment.unresolved:
        status = 'incomplete'
    elif assessment.status in ('mixed', 'conflicts_with_priorities'):
        status = 'priority_tradeoff'
    elif requested_gain:
        status = 'priority_gain'
    elif opportunistic_future:
        status = 'future_gain_current_preserved'
    else:
        status = 'no_priority_gain'
    # A player can be on the bench and still be vital injury/bye coverage.
    depth_conversion = bool(status in ('priority_gain', 'future_gain_current_preserved') and future_gains
        and current_preserved and bench_sent and not starters_sent and role_known
        and resilience_known and not resilience_loss and not coverage_worse)
    # Admission is deliberately weaker than promotion: existing optimized roles
    # and the weekly screen can justify checking a hypothesis, never certify
    # resilience or competitive preservation before Simulation.
    from math import isfinite
    lineup_preserved = (isinstance(preliminary_lineup_delta,(int,float))
        and isfinite(preliminary_lineup_delta) and preliminary_lineup_delta >= -1e-9)
    native_known = all(any(m.objective == g and m.direction() != D.UNKNOWN for m in metrics) for g in future)
    investigation = bool(goals == {G.CURRENT} and not assessment.context.explicitly_directed
        and assessment.context.source == 'calculated_state_posture_hypothesis_v1'
        and not assessment.protected_players_lost and lineup_preserved and native_known
        and future_gains and not future_losses and bench_sent and not starters_sent
        and role_known and not coverage_worse and not resilience_loss)
    return {'depth_conversion_investigation_eligible':investigation,
        'depth_conversion_pending_checks':('competitive_effects','resilience') if investigation else (),
        'status':status, 'priority_horizons':tuple(g.value for g in assessment.context.objectives),
        'current_effects_known':current_known,'current_direction_preserved':current_preserved,
        'current_losses':current_losses,'future_gains':future_gains,'future_losses':future_losses,
        'position_evidence_available':role_known,'outgoing_projected_starter_ids':starters_sent,
        'outgoing_projected_bench_ids':bench_sent,'positions_with_less_forecasted_depth':depth_costs,
        'resilience_effect_known':resilience_known,'resilience_worsens':resilience_loss,'positional_coverage_worsens':coverage_worse,
        'received_pick_ids':tuple(context.get('received_pick_ids', ())),
        'depth_conversion_candidate':depth_conversion,'surplus_confirmed':False,
        'opportunistic_future_case':opportunistic_future and not requested_gain,
        'action_authority':'directional_review_only','materiality_assessed':False,
        'model_version':'next5-transaction-strategy-v1'}

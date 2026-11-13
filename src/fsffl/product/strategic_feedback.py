"""Bounded NEXT6 repair hypotheses; upstream Decision still evaluates each point."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from fsffl.opportunity.frontier import expand_adjacent_packages, make_frontier_point
from fsffl.opportunity.trade_universe import (
    TradePackageSeed, TradeSearchBounds, build_team_trade_inventory, canonical_package_id,
)
from fsffl.state.models import PlayerAsset
from .simulation_forecasts import require_forward_simulation_evidence


@dataclass
class FeedbackVisits:
    limit: int
    used: int = 0
    exhausted: bool = False
    skipped: Counter = field(default_factory=Counter)

    def visit(self):
        if self.used >= self.limit:
            self.exhausted = True
            return False
        self.used += 1
        return True


def _package(team, assets):
    return TradePackageSeed(team_id=team, assets=tuple(assets),
                            canonical_id=canonical_package_id(team, assets))


def repair_path(runtime, root, read, *, protected_player_ids, visits):
    """At most one remove/add path, with <=6 ingredients and <=2 assets per side.

    The root's weekly evidence must show a managed current loss and known native
    future alignment for the other side. Published starter/bench roles only order
    hypotheses; they do not establish expendability, utility or acceptance.
    Every yielded proposal requires the caller's same counted Decision screen.
    """
    def skip(reason):
        visits.skipped[reason] += 1
    state, evidence, baseline = runtime.league_state, runtime.forecast_evidence, runtime.simulation_analytics
    screen = root.get('preliminary_decision_screen') or {}
    assessment = root.get('objective_assessment') or {}
    if (read is None or evidence is None or baseline is None
            or screen.get('current_points_basis') != 'remaining_regular_season_weekly_mean'):
        skip('forward_source_unavailable'); return
    focal = assessment.get('side_a') or {}
    other = assessment.get('side_b') or {}
    if 'current_competitiveness' not in (focal.get('context') or {}).get('objectives', ()):
        skip('current_not_requested'); return
    if any((assessment.get(side) or {}).get('protected_players_lost') for side in ('side_a', 'side_b')):
        skip('protected_cut'); return
    loss = (screen.get('focal') or {}).get('starter_points_delta')
    goals = (other.get('context') or {}).get('objectives', ())
    horizons = {'three_year_contribution': 'three_year', 'career_contribution': 'career'}
    if (loss is None or loss >= -1e-9 or other.get('status') != 'aligns_with_priorities'
            or not goals or any(g not in horizons for g in goals)):
        skip('no_known_current_future_repair'); return
    if getattr(baseline, 'scenario_preparation', None) is None:
        skip('baseline_state_mismatch'); return
    try:
        require_forward_simulation_evidence(state, evidence, baseline)
    except ValueError:
        skip('baseline_source_mismatch'); return
    if baseline.scenario_preparation is None or baseline.scenario_preparation.source_state_id != state.state_id:
        skip('baseline_state_mismatch'); return
    if any(not x['asset_ref'].startswith('player:') for x in root['send'] + root['receive']):
        skip('nonplayer_repair_not_supported'); return
    sent = tuple(PlayerAsset(player_id=x['asset_ref'].removeprefix('player:')) for x in root['send'])
    received = tuple(PlayerAsset(player_id=x['asset_ref'].removeprefix('player:')) for x in root['receive'])
    if len(sent) != 2 or len(received) > 2:
        skip('no_bounded_replacement'); return
    bounds = TradeSearchBounds(max_assets_per_side=2, include_faab=False)
    try:
        inventory = build_team_trade_inventory(state, team_id=runtime.selected_team_id, bounds=bounds)
        counter_inventory = build_team_trade_inventory(state, team_id=root['counterparty_team_id'], bounds=bounds)
    except ValueError:
        skip('unknown_team'); return
    if (not set(sent) <= set(inventory.assets) or not set(received) <= set(counter_inventory.assets)
            or any(a.player_id in protected_player_ids for a in sent)):
        skip('ownership_or_protected_send'); return
    lineup = next((v.optimized_lineup for v in baseline.team_views
                   if v.team_id == runtime.selected_team_id), None)
    if lineup is None:
        skip('published_roles_unavailable'); return
    assigned = {a.player_id: a for a in lineup.assignments}
    players = {p.player_id: p for p in state.players}
    protected = frozenset(protected_player_ids)
    sent_ids = {a.player_id for a in sent}
    bench = {r.player_id for t in state.team_states if t.team_id == runtime.selected_team_id
             for r in t.roster if r.slot.value not in ('IR', 'TAXI')
             and r.player_id not in assigned and r.player_id not in protected and r.player_id not in sent_ids}
    starters = sorted((a for a in sent if a.player_id in assigned and a.player_id not in protected),
                      key=lambda a: (-assigned[a.player_id].expected_points, a.player_id))
    chosen = None
    for removed in starters:
        alternatives = [PlayerAsset(player_id=pid) for pid in bench
            if pid in players and players[pid].position == players[removed.player_id].position
            and all(pid in read.values[horizons[g]] for g in goals)]
        alternatives.sort(key=lambda a: tuple(-read.values[horizons[g]][a.player_id] for g in goals) + (a.player_id,))
        if alternatives:
            chosen = removed, alternatives[:4]; break
    if chosen is None:
        skip('no_same_position_bench'); return
    removed, alternatives = chosen
    # Both sides remain canonical owned packages. Cap ingredients before NEXT6.
    inventory = inventory.model_copy(update={'assets': tuple(dict.fromkeys((*sent, *alternatives)))})
    origin = _package(runtime.selected_team_id, sent)
    counter = _package(root['counterparty_team_id'], received)
    removals = sorted(expand_adjacent_packages(origin, inventory=inventory, bounds=bounds),
                      key=lambda n: (removed in n.package.assets, n.package.canonical_id))
    drop = None
    for neighbor in removals:
        if not visits.visit(): return
        if neighbor.move_kind == 'remove' and removed not in neighbor.package.assets:
            drop = neighbor; break
    if drop is None: return
    point = make_frontier_point(drop.package, counter)
    yield point, {'root_point_id': root['point_id'], 'parent_point_id': root['point_id'],
                  'move': 'remove', 'depth': 1, 'hypothesis_only': True}
    order = {asset: i for i, asset in enumerate(alternatives)}
    additions = sorted(expand_adjacent_packages(drop.package, inventory=inventory, bounds=bounds),
                       key=lambda n: (min((order[a] for a in n.package.assets if a in order), default=99),
                                      n.package.canonical_id))
    for neighbor in additions:
        if not visits.visit(): return
        if neighbor.move_kind != 'add' or not any(a in order for a in neighbor.package.assets):
            continue
        yield make_frontier_point(neighbor.package, counter), {
            'root_point_id': root['point_id'], 'parent_point_id': point.point_id,
            'move': 'add_same_position_bench', 'depth': 2, 'hypothesis_only': True}
        return


def needs_second_step(row):
    """Keep missing/violated evidence out; an adequate one-step repair can stop."""
    if row.get('evidence_status') != 'pre_simulation_screened':
        return False
    assessment = row.get('objective_assessment') or {}
    if any((assessment.get(s) or {}).get('protected_players_lost') for s in ('side_a', 'side_b')):
        return False
    value = ((row.get('preliminary_decision_screen') or {}).get('focal') or {}).get('starter_points_delta')
    return not (value is not None and value > 1e-9
                and (assessment.get('side_b') or {}).get('status') == 'aligns_with_priorities')

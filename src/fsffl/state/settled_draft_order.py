"""Resolve observed draft slots for the active league and draft-year policy."""
from dataclasses import dataclass
from fractions import Fraction
from itertools import groupby
from math import isfinite

from .postseason import verified_championship_tree
from .draft_order_policy import (
    STANDARD_DRAFT_ORDER_MECHANISM_V1, STANDARD_PLAYOFF_ORDER,
    STANDARD_REGULAR_SEASON_TIEBREAK, resolve_draft_order_policy,
)


@dataclass(frozen=True)
class OriginOrder:
    slot: int | None
    reason: str

    provisional: bool = False
    model: str = "settled_non_playoff_max_pf_v1"

    def conflicts(self, official):
        return self.slot is not None and official is not None and self.slot != official


def confirm_regular_totals(current, previous):
    """Confirm only on a distinct scored publication with matching official totals."""
    from .account_rules import provider_rule_state
    if previous is None or not current.regular_totals_observed_leg or current.regular_totals_confirmed:
        return current
    old = provider_rule_state(previous)
    new = provider_rule_state(current)
    if (old.league != new.league or not old.regular_totals_observed_leg
            or old.final_regular_totals_week != new.final_regular_totals_week
            or old.as_of > new.as_of or old.regular_totals_observed_leg > new.regular_totals_observed_leg):
        return current
    def totals(state):
        return {r.team_id: (r.max_points_for, r.final_regular_record) for r in state.team_states}
    later_report = old.regular_totals_observed_leg < new.regular_totals_observed_leg and old.as_of < new.as_of
    if (later_report or old.regular_totals_confirmed) and totals(old) == totals(new):
        return current.model_copy(update={"regular_totals_confirmed": True})
    return current


def _playoff_field(state, cutoff, count):
    # Read only entrants to the official championship tree. Later round scores
    # are unnecessary, and a team advancing from a feeder is not a new entrant.
    games = state.winners_bracket
    if not count or len(games) != count - 1 or not games:
        return None
    known = {team.team_id for team in state.teams}
    weeks = {}
    parents = set()
    entrants = set()
    for game in sorted(games, key=lambda g: g.week):
        if game.game in weeks or game.week <= cutoff:
            return None
        for team, parent in ((game.left, game.left_from), (game.right, game.right_from)):
            if parent is None:
                if team not in known or team in entrants or game.week > cutoff + 2:
                    return None
                entrants.add(team)
            elif parent in parents or weeks.get(parent) != game.week - 1:
                return None
            else:
                parents.add(parent)
        weeks[game.game] = game.week
    if min(weeks.values()) != cutoff + 1 or len(weeks.keys() - parents) != 1 or len(entrants) != count:
        return None
    return entrants


def playoff_finish_order(state, field, cutoff, terms):
    def pending(reason):
        return dict.fromkeys(field, OriginOrder(None, reason))

    if terms.get("playoff_order") != "elimination":
        return pending("The saved playoff order needs separate placement evidence or rules.")
    games = state.winners_bracket
    weeks = tuple(range(cutoff + 1, max(g.week for g in games) + 1))
    field_size = len(field)
    expected_rounds = (field_size - 1).bit_length()
    if len(weeks) != expected_rounds:
        return pending("The playoff format needs verification.")
    path = verified_championship_tree(state, weeks, field_size, 2**expected_rounds - field_size)
    if not path or not path[-1].winner:
        return pending("Waiting for a completed championship bracket and matching scores.")
    model = "settled_playoff_elimination_v1"
    def settled(slot, reason):
        return OriginOrder(slot, reason, model=model)
    result = {}
    first = state.league.rules.team_count - field_size + 1
    records = {r.team_id: r.final_regular_record for r in state.team_states}
    for week, group in groupby(path[:-1], key=lambda g: g.week):
        teams = [g.loser for g in group]
        if len(teams) == 1:
            result[teams[0]] = settled(first, f"Eliminated in Week {week}.")
        elif (state.regular_totals_confirmed and state.overall_record_standings
              and all(records[t] and sum(records[t]) for t in teams)):
            def record(team):
                w, l, ties = records[team]
                return Fraction(2*w + ties, 2*(w+l+ties))
            rank = first
            for _, equal in groupby(sorted(teams, key=record), key=record):
                tied = list(equal)
                placement = (settled(rank, f"Eliminated in Week {week} · lower regular-season finish picks earlier.")
                             if len(tied) == 1 else OriginOrder(None, "Same-round finish tied; official regular-season order needed."))
                result.update(dict.fromkeys(tied, placement))
                rank += len(tied)
        else:
            result.update(dict.fromkeys(teams, OriginOrder(None, "Confirmed regular-season finish needed for same-round teams.")))
        first += len(teams)
    result[path[-1].loser] = settled(first, "Championship runner-up.")
    result[path[-1].winner] = settled(first+1, "League champion.")
    return result


def settled_origin_order(state, draft_year):
    """An empty mapping delegates to the existing policy path."""
    policy = resolve_draft_order_policy(state.draft_order_policies, league_id=state.league.league_id,
                                        draft_season=draft_year, as_of=state.as_of)
    if not policy:
        return {}
    teams = {team.team_id for team in state.teams}

    def unresolved(reason):
        return dict.fromkeys(teams, OriginOrder(None, reason))

    if policy.mechanism == STANDARD_DRAFT_ORDER_MECHANISM_V1:
        # Preserve the standard simulation path while the season is in progress.
        rules = state.league.rules
        cutoff = rules.fantasy_regular_season_end_week
        if not cutoff or draft_year != state.league.season + 1 or (state.completed_through_week or 0) <= cutoff:
            return {}
        field = _playoff_field(state, cutoff, rules.playoff_team_count)
        terms = {p.name: p.value for p in policy.parameters}
        if terms.get("placement_games_affect_order"):
            return {}  # The existing placement-game policy owns these picks.
        elimination_terms = {
            "non_playoff_tiebreak_policy": STANDARD_REGULAR_SEASON_TIEBREAK,
            "playoff_order_policy": STANDARD_PLAYOFF_ORDER,
            "origin_slot_carries_across_rounds": True,
        }
        if {k: v for k, v in terms.items() if k != "placement_games_affect_order"} != elimination_terms:
            return unresolved("The saved draft-order terms are unsupported.")
        if not field:
            return unresolved("Waiting for a confirmed playoff field.")
        return playoff_finish_order(state, field, cutoff, {"playoff_order": "elimination"})
    if policy.mechanism != "account_custom_draft_order_v1":
        return unresolved("The saved draft-order rule is unsupported.")
    terms = {p.name: p.value for p in policy.parameters}
    tiebreak = terms.get("tiebreak")
    if terms.get("non_playoff_order") != "max_pf" or tiebreak not in ("record", "unresolved"):
        return unresolved("The saved ordering rule or tiebreak is unsupported.")
    rules = state.league.rules
    cutoff = rules.fantasy_regular_season_end_week
    if draft_year != state.league.season + 1 or not cutoff or (state.completed_through_week or 0) < cutoff:
        return unresolved("Waiting for final regular-season results.")
    if state.final_regular_totals_week != cutoff:
        return unresolved("Waiting for final regular-season roster totals.")
    if state.rule_configuration:
        provider = state.rule_configuration.provider_rules
        if provider.fantasy_regular_season_end_week != cutoff:
            return unresolved("Provider season totals do not verify the configured cutoff.")
        if provider.scoring != rules.scoring or provider.lineup != rules.lineup:
            return unresolved("Final Max PF under the selected lineup and scoring rules is unavailable.")
    field = _playoff_field(state, cutoff, rules.playoff_team_count)
    if field is None or len(teams) != rules.team_count or not teams - field:
        return unresolved("Waiting for a confirmed playoff field.")
    result = playoff_finish_order(state, field, cutoff, terms)
    rows = [row for row in state.team_states if row.team_id not in field]
    if any(row.max_points_for is None or not isfinite(row.max_points_for) for row in rows):
        result.update(dict.fromkeys(teams-field, OriginOrder(None, "Final Max PF is missing for a non-playoff team.")))
        return result
    first = 1
    for _, group in groupby(sorted(rows, key=lambda r: r.max_points_for), key=lambda r: r.max_points_for):
        tied = list(group)
        if len(tied) == 1:
            result[tied[0].team_id] = OriginOrder(first, "League rule · final Max PF")
        elif tiebreak == "record" and all(r.final_regular_record and sum(r.final_regular_record) for r in tied):
            def percentage(row):
                w, l, t = row.final_regular_record
                return Fraction(2*w+t, 2*(w+l+t))
            start = first
            for _, subgroup in groupby(sorted(tied, key=percentage), key=percentage):
                same = list(subgroup)
                order = (OriginOrder(start, "League rule · final Max PF, then record") if len(same) == 1
                         else OriginOrder(None, "Tied on final Max PF and regular-season record."))
                result.update(dict.fromkeys((r.team_id for r in same), order))
                start += len(same)
        else:
            reason = "Tied on final Max PF." if tiebreak == "unresolved" else "Final regular-season record is missing."
            result.update(dict.fromkeys((r.team_id for r in tied), OriginOrder(None, reason)))
        first += len(tied)
    if not state.regular_totals_confirmed:
        for team in teams - field:
            if result[team].slot is not None:
                result[team] = OriginOrder(result[team].slot, "Provisional Max PF slot · awaiting a confirming scoring report.", True)
    return result

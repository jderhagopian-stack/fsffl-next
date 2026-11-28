"""League trade annual. All marks are retrospective editorial opinions."""
from collections import Counter, defaultdict
from math import isfinite

from .owner_current_season import asset_labels


def collect_trades(state, record):
    """Admit one complete, balanced ledger from a single league and receipt cutoff."""
    ids = [r.external_id for r in state.league.provider_refs if r.provider == "sleeper"]
    if len(ids) != 1 or not record.result or record.sleeper_league_external_id != ids[0]:
        raise ValueError("Saved trade history is unavailable for this league.")
    result = record.result
    owners = dict(result.current_owner_by_roster)
    profiles = {p.owner_id: p for p in result.profiles if p.league_family_id == result.league_family_id}
    names = {int(r.external_id): t.display_name for t in state.teams for r in t.provider_refs
             if r.provider == "sleeper" and r.external_id.isdecimal()}
    trades = defaultdict(list)
    cutoffs = set()
    if not names or len(names) != len(state.teams):
        raise ValueError("Some franchises are missing from the archive.")
    for roster in names:
        p = profiles.get(owners.get(roster))
        activity = p.current_season_activity if p else None
        if (not activity or activity.league_external_id != ids[0] or activity.season != state.league.season
                or activity.cutoff > state.as_of or p.as_of > state.as_of or activity.missing_completion_count
                or activity.trade_count != len(activity.trade_examples)):
            raise ValueError("The saved trade receipts are incomplete for this league.")
        cutoffs.add(activity.cutoff)
        for move in activity.trade_examples:
            event = move.event
            if (event.owner_id != p.owner_id or event.roster_id != roster or event.kind != "trade"
                    or event.league_family_id != result.league_family_id):
                raise ValueError("A trade receipt has conflicting franchise information.")
            trades[move.source_sha256].append(move)
    if len(cutoffs) != 1:
        raise ValueError("The franchises have different trade-history cutoffs.")
    for moves in trades.values():
        acquired = Counter((a.asset_ref, a.faab_amount) for m in moves for a in m.event.acquired)
        sent = Counter((a.asset_ref, a.faab_amount) for m in moves for a in m.event.disposed)
        participants = {m.event.roster_id for m in moves}
        if (len(participants) < 2 or len(participants) != len(moves) or acquired != sent
                or not acquired or len({m.completed_at for m in moves}) != 1
                or any(set(m.event.counterparty_owner_ids) != {x.event.owner_id for x in moves if x is not m}
                       for m in moves)):
            raise ValueError("The two sides of a saved trade do not agree.")
    return ids[0], names, cutoffs.pop(), sorted(trades.values(), key=lambda ms: (ms[0].completed_at, ms[0].source_sha256))


def verdict(edge, thresholds):
    for threshold, better, worse in zip(thresholds, ("NUCLEAR", "ON FIRE", "NICE"),
                                      ("DISASTER", "DUMPSTER", "OOF")):
        if abs(edge) >= threshold:
            return better if edge > 0 else worse
    return "FAIR"


def season_take(event, moves, weeks, later, season, completed, label):
    if not weeks:
        return "UNAVAILABLE", "The finished weekly lineups are unavailable."
    outgoing = {a.asset_ref for a in event.disposed}
    received = {a.asset_ref for a in event.acquired}
    relevant = (*event.acquired, *event.disposed)
    def untraced(assets):
        return any(a.kind == "faab" or (a.kind == "pick" and a.pick_season <= season) for a in assets)

    unresolved = untraced(relevant)
    tally = [0., 0.]
    starts = [0, 0]
    performances = [Counter(), Counter()]
    count = 0
    for first, last, lineups in weeks:
        if first <= completed.date():
            continue
        count += 1
        for move in moves:
            team = move.event.roster_id
            for a in move.event.acquired:
                if a.kind != "player" or a.asset_ref not in received | outgoing:
                    continue
                exit_at = later.get((team, a.asset_ref))
                if exit_at and exit_at.date() <= last:
                    continue
                pts = lineups[team].get(a.asset_ref)
                if pts is not None:
                    side = int(a.asset_ref in outgoing)
                    tally[side] += pts
                    starts[side] += 1
                    performances[side][label(a)] += pts
    if unresolved and not any(a.kind == "player" for a in event.acquired):
        return "TOO SOON", "Their season return depends on what the pick or waiver money bought."
    if not count or not sum(starts):
        return "TOO SOON", "Neither side has a scored start in the full weeks checked after this trade."
    diff = tally[0] - tally[1]
    stars = performances[0] if diff >= 0 else performances[1]
    leader = max(stars, key=stars.get) if stars else None
    detail = f" {leader} accounted for {stars[leader]:g} of those points." if leader else ""
    mark = verdict(diff, (90, 45, 12))
    if unresolved:
        if not any(a.kind == "player" for a in event.disposed):
            if not starts[0]:
                return "TOO SOON", "The incoming player has yet to post a start in the weeks checked."
            return ("NICE" if tally[0] >= 12 else "FAIR"), (
                f"The player return delivered {tally[0]:g} points in {starts[0]} starts. "
                "What the pick or cash bought is still open.")
        detail += " This grade covers the players. The pick or waiver-money return is still open."
    return mark, (
        f"The return put up {tally[0]:g} points in {starts[0]} starts. The players sent away put up "
        f"{tally[1]:g} in {starts[1]} starts for their new teams." + detail)


def dynasty_take(event, prices, label, season):
    assets = (*event.acquired, *event.disposed)
    missing = [a for a in assets if a.asset_ref not in prices]
    cash_only_gap = (missing and all(a.kind == "faab" for a in missing)
                     and all(any(a.asset_ref in prices for a in side) for side in (event.acquired, event.disposed)))
    if not assets or (missing and not cash_only_gap):
        picks = [a for a in event.acquired if a.kind == "pick"]
        if picks:
            return "TOO SOON", f"They took back {len(picks)} draft pick(s). The full package still lacks a comparable price."
        return "UNAVAILABLE", "A price is missing for part of this deal."
    got = sum(prices[a.asset_ref] for a in event.acquired if a.asset_ref in prices)
    paid = sum(prices[a.asset_ref] for a in event.disposed if a.asset_ref in prices)
    if not max(got, paid):
        return "TOO SOON", "Neither package has a positive market price."
    edge = (got-paid)/max(got, paid)
    mark = verdict(edge, (.65, .35, .12))
    future = [a for a in assets if a.kind == "pick" and a.pick_season > season]
    if future:
        # An open pick can buy leverage today. Its player's career is still unwritten.
        mark = {"NUCLEAR": "ON FIRE", "DISASTER": "OOF", "DUMPSTER": "OOF"}.get(mark, mark)
    if abs(edge) < .12:
        reason = "You can argue the players. The market sees little daylight between the packages."
    elif future:
        owner_took_picks = any(a in future for a in event.acquired)
        reason = ("They bought draft capital whose eventual slots will decide the return." if owner_took_picks else
                  "They paid for a known return with picks whose slots can still change.")
    else:
        lead = max((a for a in assets if a.asset_ref in prices), key=lambda a: prices[a.asset_ref])
        reason = f"{label(lead)} carries the biggest price tag in this deal."
    if cash_only_gap:
        reason += " The grade covers players and picks. Waiver cash is priced separately by each owner."
    return mark, f"{reason} The return prices at {got:,.0f} against {paid:,.0f} sent."



def build_edition(runtime, names, cutoff, trades, weeks):
    state = runtime.league_state
    labels = asset_labels(state)
    values = runtime.value_evidence
    canonical = {r.asset_id: r.score for r in values.fsffl_cardinal_values
                 if isfinite(r.score)} if values and values.league_state_id == state.state_id else {}
    prices = dict(canonical)
    for pick in state.draft_picks:
        origin = next((r.external_id for t in state.teams if t.team_id == pick.original_team_id
                       for r in t.provider_refs if r.provider == "sleeper"), None)
        ref = f"sleeper:pick:{pick.season}:{pick.round}:{origin}"
        if pick.pick_id in canonical:
            prices[ref] = canonical[pick.pick_id]

    def label(a):
        if a.kind == "pick":
            origin = a.asset_ref.rsplit(":", 1)[-1]
            return f"{a.pick_season} round {a.pick_round} ({names.get(int(origin), origin) if origin.isdecimal() else origin})"
        if a.kind == "faab":
            return f"${a.faab_amount} FAAB"
        return labels.get(a.asset_ref, f"Player {a.asset_ref.rsplit(':', 1)[-1]}")

    ledger = []
    counts = Counter()
    activity = Counter()
    cash = 0
    next_exit = {}
    for moves in reversed(trades):
        completed = moves[0].completed_at
        sides = []
        for m in sorted(moves, key=lambda m: m.event.roster_id):
            e = m.event
            counts.update(a.kind.value for a in e.acquired)
            activity[e.roster_id] += 1
            cash += sum(a.faab_amount for a in e.acquired if a.kind == "faab")
            onward = [f"{label(a)} changed hands again on {next_exit[e.roster_id, a.asset_ref].date()}."
                      for a in e.acquired if (e.roster_id, a.asset_ref) in next_exit]
            sides.append(dict(onward=onward, team=names[e.roster_id], received=list(map(label, e.acquired)),
                              sent=list(map(label, e.disposed)), season=season_take(
                                  e, moves, weeks, next_exit, state.league.season, completed, label),
                              dynasty=dynasty_take(e, prices, label, state.league.season)))
        ledger.append(dict(date=completed.date().isoformat(), sides=sides))
        for m in moves:
            for a in m.event.disposed:
                next_exit[m.event.roster_id, a.asset_ref] = completed
    busiest = max(ledger, key=lambda deal: sum(len(s["received"]) for s in deal["sides"]), default=None)
    leaders = [names[r] for r in sorted(activity) if activity[r] == max(activity.values())]
    return dict(league=state.league.name, season=state.league.season, cutoff=cutoff.isoformat(),
                as_of=state.as_of.isoformat(), faab_dollars=cash, counts=counts, ledger=ledger,
                participating=len(activity), leaders=leaders, leader_count=max(activity.values(), default=0),
                biggest=busiest, scored_weeks=len(weeks))

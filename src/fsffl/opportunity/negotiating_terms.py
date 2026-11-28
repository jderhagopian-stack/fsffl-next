"""Opening and fallback terms among evaluated offers for the same assets."""
from math import isfinite


def negotiating_terms(points, *, focal_team, other_team, buying=False):
    metric_keys = {"current_competitiveness": "current", "three_year_contribution": "three_year",
                   "career_contribution": "career", "market_capital": "market"}
    eligible = []
    probes = []
    costly_returns = []
    for point in points:
        check = point.get("price_check") or {}
        if not check:
            continue
        if any(goal not in metric_keys for side in ("side_a", "side_b")
               for goal in point["objective_assessment"][side]["context"]["objectives"]):
            # The preliminary comparison has no confirmed resilience measurement.
            continue
        markets = check["market"]
        effects = point["counter_review"]["effects"]["teams"]
        if not all(isinstance(x, (int, float)) and isfinite(x)
                   for team in (focal_team, other_team)
                   for x in (*effects[team].values(), markets[team])):
            continue
        if check["group"] in {"preliminary_fit", "priority_tradeoff"}:
            eligible.append(point)
        elif not buying and check["band"] == "focal_economic_strain":
            costly_returns.append(point)
        elif (buying and check["band"] == "counterparty_economic_strain" and check["needs_filled"]
              and len(point["focal_assets"]) == 1 and len(point["counterparty_assets"]) == 1
              and not any(check["cuts"].values())
              and not any(point["objective_assessment"][s]["protected_players_lost"] for s in ("side_a", "side_b"))
              and all(v >= 0 for v in effects[focal_team].values()) and any(v > 0 for v in effects[focal_team].values())):
            # Optional inquiry paired with a supported fallback; never a new Decision disposition.
            probes.append(point)

    def price(point, team):
        return point["price_check"]["market"][team]

    def goals(point, side, team):
        context = point["objective_assessment"][side]["context"]
        effects = point["counter_review"]["effects"]["teams"][team]
        coordinates = {**effects, "market": price(point, team)}
        return tuple(coordinates[metric_keys[goal]]
                     for goal in context["objectives"])

    def dominates(left, right):
        # A worse-priced package buys nothing extra on either owner's objectives.
        lhs, rhs = [], []
        for side, team in (("side_a", focal_team), ("side_b", other_team)):
            lhs.extend((*goals(left, side, team), price(left, team)))
            rhs.extend((*goals(right, side, team), price(right, team)))
        return all(a >= b for a, b in zip(lhs, rhs)) and any(a > b for a, b in zip(lhs, rhs))

    choices = [p for p in eligible if not any(dominates(q, p) for q in eligible)]
    choices.sort(key=lambda p: (-price(p, focal_team), not p["is_seed"], p["point_id"]))
    if not choices:
        return {"opening": None, "fallback": None, "eligible_count": 0}
    opening = choices[0]
    seed = next((p for p in eligible if p["is_seed"]), None)
    if seed:
        def better_for_seeker(point):
            return (price(point, focal_team) > price(seed, focal_team)
                    and all(a >= b for a, b in zip(goals(point, "side_a", focal_team),
                                                    goals(seed, "side_a", focal_team))))

        # Start with the smallest favorable price improvement that preserves
        # the seeker's priorities and still gives the partner a reason to talk.
        improvements = [p for p in choices if better_for_seeker(p)
                        and any(v > 0 for v in goals(p, "side_b", other_team))]
        opening = min(improvements, key=lambda p: price(p, focal_team),
                      default=seed if seed in choices else choices[0])
        # Keep the incoming player and the position the seller would acquire.
        supported_rooms = set(seed["price_check"]["needs_filled"])
        plausible = [p for p in probes if supported_rooms.intersection(p["price_check"]["needs_filled"])
                     and better_for_seeker(p)
                     and all(a >= b for a, b in zip(goals(seed, "side_b", other_team), goals(p, "side_b", other_team)))]
        if plausible and opening is seed:
            probe = min(plausible, key=lambda p: price(p, focal_team))
            return {"opening": probe["point_id"], "fallback": seed["point_id"],
                    "conditional_opening": True, "eligible_count": len(choices)}
    before = goals(opening, "side_b", other_team)
    # Only quote a concession when the other owner receives better terms.
    fallback = next((p for p in sorted(choices, key=lambda p: p is not seed)
                     if price(p, focal_team) < price(opening, focal_team)
                     and price(p, other_team) > price(opening, other_team)
                     and any(a > b for a, b in zip(goals(p, "side_b", other_team), before))), None)
    def assets(point):
        return {a["asset"].get("pick_id") or a["asset"].get("player_id") for a in point["counterparty_assets"]}

    simpler = [p for p in costly_returns if assets(p) < assets(opening)
               and price(p, focal_team) < price(fallback or opening, focal_team)]
    stop = max(simpler, key=lambda p: price(p, focal_team), default=None)
    return {"opening": opening["point_id"], "fallback": fallback["point_id"] if fallback else None,
            "outside": stop["point_id"] if stop else None,
            "eligible_count": len(choices)}

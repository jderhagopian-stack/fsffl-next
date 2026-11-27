import pytest

from fsffl.opportunity.negotiating_terms import negotiating_terms


def offer(name, market, future, *, seed=False, band="robust_or_ordinary", need=False):
    group = "priority_tradeoff" if band == "robust_or_ordinary" else "priority_concern"
    return {"point_id": name, "is_seed": seed, "focal_assets": [{"asset": {"player_id": name}}],
            "counterparty_assets": [{"asset": {"player_id": "target"}}],
            "price_check": {"group": group, "band": band, "market": {"a": market, "b": -market},
                            "needs_filled": ["WR"] if need else [], "cuts": {"a": 0, "b": 0}},
            "objective_assessment": {s: {"context": {"objectives": ["career_contribution"]},
                                         "protected_players_lost": []} for s in ("side_a", "side_b")},
            "counter_review": {"effects": {"teams": {
                "a": {"current": 1, "three_year": 1, "career": future},
                "b": {"current": -1, "three_year": -1, "career": -future}}}}}


def plan(points, buying=True):
    return negotiating_terms(points, focal_team="a", other_team="b", buying=buying)


def test_conditional_opening_needs_a_supported_fallback_and_an_actual_roster_need():
    seed = offer("starter", 0, -2, seed=True, need=True)
    probe = offer("cheaper", 12, 3, band="counterparty_economic_strain", need=True)
    assert plan([probe])["opening"] is None
    assert plan([seed, probe])["conditional_opening"]
    assert plan([seed, probe])["fallback"] == "starter"
    probe["price_check"]["cuts"]["b"] = 1
    assert plan([seed, probe])["opening"] == "starter"
    probe["price_check"]["cuts"]["b"] = 0
    probe["price_check"]["needs_filled"] = []
    assert plan([seed, probe])["fallback"] is None


def test_both_directions_start_at_best_price_and_require_a_reason_to_concede():
    opening = offer("ask", 30, 40)
    fallback = offer("concede", 10, 20)
    for buying in (False, True):
        result = plan([fallback, opening], buying)
        assert (result["opening"], result["fallback"]) == ("ask", "concede")
    fallback["counter_review"]["effects"]["teams"]["b"]["career"] = -45
    assert plan([opening, fallback])["fallback"] is None
    opening["counter_review"]["effects"]["teams"]["a"]["career"] = None
    assert plan([opening])["opening"] is None


def test_smaller_return_outside_the_economic_gate_is_a_stop_only():
    opening = offer("both", 0, 4, seed=True)
    opening["counterparty_assets"].append({"asset": {"pick_id": "second"}})
    low = offer("one", -500, 2, band="focal_economic_strain")
    result = plan([low, opening], buying=False)
    assert result["outside"] == "one" and result["fallback"] is None


@pytest.mark.parametrize("buying", [True, False], ids=["buy", "sell"])
@pytest.mark.parametrize("goals", [
    ["market_capital"], ["current_competitiveness", "market_capital"],
])
def test_market_capital_counts_as_a_concession_for_both_comparisons(buying, goals):
    opening = offer("opening", 30, 20)
    alternative = offer("alternative", 10, 20)
    for point in (opening, alternative):
        for side in ("side_a", "side_b"):
            point["objective_assessment"][side]["context"]["objectives"] = goals
    # Lineup and both future horizons are identical. Only post-cut market value improves.
    result = plan([opening, alternative], buying)
    assert (result["opening"], result["fallback"]) == ("opening", "alternative")

    # A required cut can erase the partner's improvement even at a lower asking price.
    alternative["price_check"]["market"]["b"] = opening["price_check"]["market"]["b"]
    assert plan([opening, alternative], buying)["fallback"] is None


def test_market_with_an_unmeasured_goal_does_not_quote_a_price():
    point = offer("candidate", 12, 10)
    point["objective_assessment"]["side_a"]["context"]["objectives"] = ["market_capital", "resilience"]
    assert plan([point])["opening"] is None

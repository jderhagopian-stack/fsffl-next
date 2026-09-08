from fsffl.product.opportunity_spotlights import build_trade_spotlights


def _row(
    name: str,
    *,
    feasibility: str,
    focal: str,
    counterparty: str,
    evaluated: bool = True,
) -> dict[str, object]:
    return {
        "counterparty_team_id": name,
        "counterparty_name": name,
        "send": [{"asset_ref": f"player:send-{name}"}],
        "receive": [{"asset_ref": f"player:receive-{name}"}],
        "package_shape": "one_for_one",
        "market_gap_ratio": 0.01,
        "search_distance": 10.0,
        "bilateral_decision_evaluated": evaluated,
        "negotiation_feasibility_shape": feasibility,
        "focal_decision_shape": focal,
        "counterparty_decision_shape": counterparty,
        "decision_shape": "mixed_or_incomplete",
    }


def test_closest_market_match_and_promising_decision_lead_can_differ() -> None:
    rows = [
        _row(
            "closest",
            feasibility="counterparty_dominated",
            focal="uniform_gain",
            counterparty="uniform_loss",
        ),
        _row(
            "better-bilateral",
            feasibility="mutual_gain_candidate",
            focal="uniform_gain",
            counterparty="uniform_gain",
        ),
    ]

    result = build_trade_spotlights(rows)

    assert result["closest_market_match"]["counterparty_team_id"] == "closest"
    assert result["most_promising_evaluated"]["counterparty_team_id"] == "better-bilateral"
    assert result["same_candidate"] is False
    assert result["recommendation_authority"] is False
    assert result["acceptance_probability"] is None


def test_spotlight_selection_is_categorical_not_market_distance_rescoring() -> None:
    rows = [
        _row(
            "market-first",
            feasibility="mixed",
            focal="uniform_gain",
            counterparty="mixed",
        ),
        _row(
            "mutual",
            feasibility="mutual_gain_candidate",
            focal="uniform_gain",
            counterparty="uniform_gain",
        ),
    ]
    rows[0]["market_gap_ratio"] = 0.001
    rows[1]["market_gap_ratio"] = 0.20

    result = build_trade_spotlights(rows)

    assert result["closest_market_match"]["counterparty_team_id"] == "market-first"
    assert result["most_promising_evaluated"]["counterparty_team_id"] == "mutual"
    assert "No composite opportunity score" in result["selection_basis"]


def test_unevaluated_rows_cannot_become_promising_decision_lead() -> None:
    rows = [
        _row(
            "closest",
            feasibility="mutual_gain_candidate",
            focal="uniform_gain",
            counterparty="uniform_gain",
            evaluated=False,
        ),
        _row(
            "evaluated",
            feasibility="mixed",
            focal="mixed",
            counterparty="mixed",
        ),
    ]

    result = build_trade_spotlights(rows)

    assert result["closest_market_match"]["counterparty_team_id"] == "closest"
    assert result["most_promising_evaluated"]["counterparty_team_id"] == "evaluated"


def test_empty_candidate_set_publishes_no_spotlight() -> None:
    result = build_trade_spotlights([])

    assert result["closest_market_match"] is None
    assert result["most_promising_evaluated"] is None
    assert result["same_candidate"] is False

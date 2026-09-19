from fsffl.product.opportunity_workspace import _select_bilateral_evaluation_indices


def test_decision_budget_guarantees_a_premium_target_lane_when_available() -> None:
    rows = [
        {
            "counterparty_team_id": "market-team",
            "receive": [{"asset_ref": "player:market"}],
            "package_shape": "one_for_one",
            "target_fsffl_value": 40.0,
            "focal_position_strength_index": 95.0,
            "counterparty_receive_position_strength_index": 95.0,
        },
        {
            "counterparty_team_id": "premium-team",
            "receive": [{"asset_ref": "player:premium"}],
            "package_shape": "three_for_one",
            "target_fsffl_value": 99.0,
            "focal_position_strength_index": 80.0,
            "counterparty_receive_position_strength_index": 80.0,
        },
        {
            "counterparty_team_id": "need-team",
            "receive": [{"asset_ref": "player:need"}],
            "package_shape": "two_for_one",
            "target_fsffl_value": 60.0,
            "focal_position_strength_index": 40.0,
            "counterparty_receive_position_strength_index": 45.0,
        },
    ]

    selected = _select_bilateral_evaluation_indices(rows, limit=2)

    assert selected == (0, 1)

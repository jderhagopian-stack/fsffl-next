from pathlib import Path
from types import SimpleNamespace

import pytest

from fsffl.value.intrinsic_display import (
    INTRINSIC_DYNASTY_DISPLAY_SCALE,
    intrinsic_dynasty_display_value,
    intrinsic_population_percentiles,
)


ROOT = Path(__file__).resolve().parents[1]


def test_display_scale_is_versioned_bounded_and_market_independent():
    assert INTRINSIC_DYNASTY_DISPLAY_SCALE.scale_id == "fsffl-intrinsic-dynasty-value"
    assert INTRINSIC_DYNASTY_DISPLAY_SCALE.version == "1"
    source = (ROOT / "src" / "fsffl" / "value" / "intrinsic_display.py").read_text(encoding="utf-8")
    assert "from .market" not in source
    assert "MarketPriceEstimate" not in source
    assert "market_price" not in source


def test_display_transform_is_deterministic_strictly_monotone_and_bounded():
    raw_values = [0, 1, 10, 45, 80, 110, 145, 180, 223.43, 291.98, 311.21, 448.61, 1000]
    displayed = [intrinsic_dynasty_display_value(value) for value in raw_values]
    assert displayed == [intrinsic_dynasty_display_value(value) for value in raw_values]
    assert all(0 <= value < 10000 for value in displayed)
    assert all(left < right for left, right in zip(displayed, displayed[1:], strict=True))


def test_display_transform_has_useful_dynasty_tier_spacing():
    assert intrinsic_dynasty_display_value(0) == 0
    assert intrinsic_dynasty_display_value(45) == pytest.approx(3000)
    assert intrinsic_dynasty_display_value(110) == pytest.approx(6000)
    assert intrinsic_dynasty_display_value(180) == pytest.approx(8500)
    assert intrinsic_dynasty_display_value(300) == pytest.approx(9700)
    assert intrinsic_dynasty_display_value(448.61) > 9900
    assert intrinsic_dynasty_display_value(291.98) < intrinsic_dynasty_display_value(311.21)


def test_invalid_raw_intrinsic_cannot_be_silently_displayed():
    with pytest.raises(ValueError):
        intrinsic_dynasty_display_value(-1)
    with pytest.raises(ValueError):
        intrinsic_dynasty_display_value(float("nan"))


def test_valid_zero_surplus_gets_zero_percentile_not_midpoint_of_tied_zeros():
    estimates = [
        SimpleNamespace(player_id="zero-a", value=0.0),
        SimpleNamespace(player_id="zero-b", value=0.0),
        SimpleNamespace(player_id="depth", value=20.0),
        SimpleNamespace(player_id="starter", value=80.0),
        SimpleNamespace(player_id="elite", value=240.0),
    ]
    percentiles = intrinsic_population_percentiles(estimates)
    assert percentiles["zero-a"] == 0
    assert percentiles["zero-b"] == 0
    assert 0 < percentiles["depth"] < percentiles["starter"] < percentiles["elite"] <= 1


def test_api_contract_separates_raw_display_and_unavailable_values():
    source = (ROOT / "src" / "fsffl" / "product" / "intrinsic_value_routes.py").read_text(encoding="utf-8")
    for key in (
        '"raw_scale"',
        '"display_scale"',
        '"players"',
        '"availability"',
        '"evidence_state"',
        '"reason"',
        '"raw_intrinsic_value"',
        '"intrinsic_dynasty_value"',
        '"percentile"',
        '"confidence"',
    ):
        assert key in source
    assert '"availability": "unavailable"' in source
    assert '"raw_intrinsic_value": None' in source
    assert '"intrinsic_dynasty_value": None' in source
    assert '"percentile": None' in source
    assert "Valid zero surplus" in source


def test_display_transform_matches_named_live_reference_shape_without_named_player_rules():
    # These raw values come from frozen/current Intrinsic-v1 safety evidence and the
    # live Value Lens range. They are validation examples only; the transform takes
    # only the raw numeric coordinate and contains no player identity branches.
    examples = {
        "zero_surplus": 0.0,
        "fringe_qb": 45.10,
        "meaningful_asset": 109.7,
        "premium_wr_shape": 183.5,
        "live_elite_shape": 240.2,
        "elite_qb": 291.98,
        "apex_qb": 448.61,
    }
    displayed = {name: intrinsic_dynasty_display_value(raw) for name, raw in examples.items()}
    assert displayed["zero_surplus"] == 0
    assert displayed["fringe_qb"] < displayed["meaningful_asset"] < displayed["premium_wr_shape"]
    assert displayed["premium_wr_shape"] < displayed["live_elite_shape"] < displayed["elite_qb"] < displayed["apex_qb"]
    assert displayed["premium_wr_shape"] > 8500
    assert displayed["live_elite_shape"] > 9000

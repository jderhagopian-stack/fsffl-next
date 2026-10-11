from __future__ import annotations

import csv
import os
import runpy
from pathlib import Path

from fsffl.value.career_forward_intrinsic import build_career_forward_intrinsic_shadow


ROOT = Path(__file__).parents[1]
SEMANTIC = Path(os.environ["CAREER_PR1_SEMANTIC_DIR"])
FOUNDATION4 = Path(os.environ["CAREER_FOUNDATION4_DIR"])


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_frozen_335_shapley_and_career_numeric_parity() -> None:
    """Recompose all accepted reference rows and compare each numeric component."""
    helpers = runpy.run_path(str(ROOT / "scripts/verify_career_coverage_pr1_semantic.py"))
    source_rows = _rows(
        ROOT
        / "artifacts/implementation/corrected_p0_preseason_credibility_gate_20260919/"
        / "RECONCILED_PRESEASON_SOURCE_335.csv"
    )
    crosswalk = {row["current_player_id"]: row["player_id"] for row in source_rows}
    assert len(crosswalk) == 335

    frozen_shapley_rows = [
        {**row, "player_id": crosswalk[row["player_id"]]}
        for row in _rows(SEMANTIC / "unchanged_current/SHAPLEY_CURRENT_BOARD_335.csv")
    ]
    current = helpers["current_intrinsic"](frozen_shapley_rows)
    assert current.coverage.player_count == len(current.estimates) == 335

    long_term = helpers["build_long_term_intrinsic_shadow"](
        helpers["forecast_contract"](
            FOUNDATION4 / "f4/FOUNDATION4_CURRENT_LONG_HORIZON_BOARD_335.csv"
        ),
        rules=helpers["rules"](),
    )
    tails = helpers["tails"](
        FOUNDATION4 / "f4/FOUNDATION4_CURRENT_TERMINAL_FEATURES_335.csv",
        helpers["rules"](),
    )
    composed = build_career_forward_intrinsic_shadow(current, long_term, tails)
    actual = {row.player_id: row for row in composed.estimates}
    expected = {
        row["player_id"]: row
        for row in _rows(SEMANTIC / "career_335_player_differences.csv")
    }
    assert len(actual) == len(expected) == 335
    assert actual.keys() == expected.keys()

    comparisons = (
        ("current_intrinsic_raw_y1_y3", "current_y1_y3_ref"),
        ("long_horizon_raw_y4_y7_reference", "long_y4_y7_ref"),
        ("terminal_raw_y8_plus_reference", "terminal_y8plus_ref"),
        ("raw_career_forward_reference", "career_raw_ref"),
        ("career_authority_low", "career_authority_low_ref"),
        ("career_authority_high", "career_authority_high_ref"),
    )
    max_delta = 0.0
    for player_id, estimate in actual.items():
        reference = expected[player_id]
        current_sum = sum(
            component.raw_shapley_contribution
            for component in estimate.uncertainty.current_y1_y3
        )
        assert abs(current_sum - estimate.current_intrinsic_raw_y1_y3) <= 1e-12
        for actual_field, expected_field in comparisons:
            value = getattr(
                estimate.model_authority,
                actual_field.removeprefix("career_authority_"),
            ) if actual_field.startswith("career_authority_") else getattr(estimate, actual_field)
            delta = abs(value - float(reference[expected_field]))
            max_delta = max(max_delta, delta)
            assert delta <= 1e-9, (
                player_id, actual_field, value, reference[expected_field], delta
            )
    print(f"frozen_335_shapley_career_numeric_max_abs_delta={max_delta:.3g}")

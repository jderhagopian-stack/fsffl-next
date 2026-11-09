from datetime import date
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from fsffl.forecast.feature_origin import (
    AGE_YEAR_DAYS, FORECAST_ORIGIN_AGE_VERSION, age_at_forecast_origin, age_date,
)


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "origin_materializer_test", ROOT / "scripts/materialize_foundation4_forecast_origin.py"
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def source_board():
    return pd.read_csv(ROOT / "artifacts/implementation/final_forecast_route_implementation_20260920/FINAL_CONNECTED_LEAGUE_BOARD_335.csv")


def empty_identities():
    return pd.DataFrame(columns=["gsis_id", "birth_date"])


def test_real_reference_cohort_keeps_all_subjects_and_source_facts():
    source = source_board()
    original = source.copy(deep=True)
    result = MOD.align_board_ages(source, empty_identities(), evaluation_season=2026)
    assert len(result) == 335
    assert result.player_id.tolist() == source.player_id.tolist()
    pd.testing.assert_frame_equal(source, original)
    pd.testing.assert_frame_equal(result[source.columns.drop("age")], source.drop(columns="age"))
    assert result.source_age_years.tolist() == source.age.tolist()
    assert set(result.age_as_of) == {"2026-09-01"}
    assert set(result.age_feature_version) == {FORECAST_ORIGIN_AGE_VERSION}
    # Independent original provenance identifies only the new identity branch
    # as already dated in 2026. Shared completed-source rows are dated in 2025.
    provenance = json.loads((ROOT / "artifacts/implementation/corrected_p0_preseason_credibility_gate_20260919/PROVENANCE_MANIFEST.json").read_text())
    new_id = provenance["population_reconciliation"]["preseason_only"]["current_player_id"]
    for before, after in zip(source.itertuples(), result.itertuples(), strict=True):
        expected_delta = 0 if before.current_player_id == new_id else 365 / AGE_YEAR_DAYS
        assert after.age == pytest.approx(before.age + expected_delta, abs=1e-12)


def test_DOB_and_dated_age_agree_and_rollover_is_idempotent():
    source = pd.DataFrame([{
        "player_id": "new", "historical_gsis_id": "g1", "position": "QB",
        "age": (date(2025, 9, 1) - date(2003, 1, 20)).days / AGE_YEAR_DAYS,
        "age_as_of": "2025-09-01", "experience": 2,
    }])
    players = pd.DataFrame([{"gsis_id": "g1", "birth_date": "2003-01-20"}])
    by_dob = MOD.align_board_ages(source, players, evaluation_season=2026)
    by_age = MOD.align_board_ages(source, empty_identities(), evaluation_season=2026)
    assert by_dob.age.iloc[0] == pytest.approx(by_age.age.iloc[0], abs=1e-12)
    pd.testing.assert_frame_equal(by_dob, MOD.align_board_ages(by_dob, players, evaluation_season=2026))
    next_year = MOD.align_board_ages(by_age, empty_identities(), evaluation_season=2027)
    assert next_year.age.iloc[0] == pytest.approx((date(2027, 9, 1) - date(2003, 1, 20)).days / AGE_YEAR_DAYS)
    assert next_year.source_age_years.iloc[0] == source.age.iloc[0]
    assert next_year.experience.iloc[0] == 2  # Never invent an experience correction.


@pytest.mark.parametrize("position", ["QB", "RB", "WR", "TE"])
def test_new_subjects_use_the_same_origin_rule_in_every_position(position):
    frame = pd.DataFrame([{"player_id": "new", "position": position,
                           "age": 24., "state_as_of": "2026-11-09T02:00:00Z"}])
    result = MOD.align_board_ages(frame, empty_identities(), evaluation_season=2026)
    assert result.age.iloc[0] == pytest.approx(24 - 69 / AGE_YEAR_DAYS)
    assert result.source_age_as_of.iloc[0] == "2026-11-09"


def test_unknown_reference_origin_is_not_guessed():
    frame = source_board()
    frame.loc[0, "age"] += 1
    with pytest.raises(ValueError, match="does not match"):
        MOD.align_board_ages(frame, empty_identities(), evaluation_season=2026)
    with pytest.raises(ValueError, match="explicit age-as-of"):
        age_at_forecast_origin(evaluation_season=2026, source_age_years=24, source_age_as_of=None)


def test_conflicting_birth_dates_and_duplicate_subjects_fail_closed():
    frame = source_board()
    with pytest.raises(ValueError, match="unique"):
        MOD.align_board_ages(pd.concat([frame, frame.iloc[:1]]), empty_identities(), evaluation_season=2026)
    metadata = pd.DataFrame([{"gsis_id": "g", "birth_date": "2000-01-01"},
                             {"gsis_id": "g", "birth_date": "2001-01-01"}])
    with pytest.raises(ValueError, match="conflicting"):
        MOD.align_board_ages(frame, metadata, evaluation_season=2026)


@pytest.mark.parametrize("age", [float("nan"), float("inf"), -1.])
def test_invalid_age_is_not_zero_filled(age):
    with pytest.raises(ValueError, match="finite and nonnegative"):
        age_at_forecast_origin(evaluation_season=2026, source_age_years=age, source_age_as_of=date(2025, 9, 1))


def test_date_parser_has_no_clock_fallback():
    assert age_date("2026-09-01T00:00:00Z") == date(2026, 9, 1)
    assert age_date(None) is None
    assert age_date(pd.NaT) is None
    assert age_date(pd.NA) is None
    with pytest.raises(ValueError, match="invalid age evidence"):
        age_date("not-a-date")


def test_preparation_preserves_original_files_and_refuses_output_overwrite(tmp_path):
    source = tmp_path / "source.csv"
    source_board().to_csv(source, index=False)
    players = tmp_path / "players.csv"
    empty_identities().to_csv(players, index=False)
    before = source.read_bytes()
    output = tmp_path / "new-version"
    args = ["--prepare-only", "--board", str(source), "--players", str(players), "--out-dir", str(output)]
    MOD.main(args)
    assert source.read_bytes() == before
    receipt = json.loads((output / "FEATURE_ORIGIN_MANIFEST.json").read_text())
    assert receipt["players"] == 335
    assert receipt["materialization_complete"] is False
    assert receipt["feature_origin_version"] == FORECAST_ORIGIN_AGE_VERSION
    with pytest.raises(FileExistsError):
        MOD.main(args)


def test_corrected_input_reaches_accepted_materializer_with_new_identity(monkeypatch, tmp_path):
    seen = {}
    def execute(module):
        module.MODEL_VERSION = "accepted-model-v1"
        def main():
            import sys
            seen["argv"] = list(sys.argv)
            seen["version"] = module.MODEL_VERSION
        module.main = main
    monkeypatch.setattr(MOD.importlib.util, "spec_from_file_location", lambda *args: SimpleNamespace(loader=SimpleNamespace(exec_module=execute)))
    monkeypatch.setattr(MOD.importlib.util, "module_from_spec", lambda spec: SimpleNamespace())
    import sys
    original = sys.argv
    MOD.run_materializer(["--development-module", "unchanged.py"], corrected_board=tmp_path / "corrected.csv", players=tmp_path / "players.csv", output=tmp_path / "new-output")
    assert sys.argv is original
    assert seen["version"] == "accepted-model-v1:forecast-origin-age-v1"
    assert seen["argv"][seen["argv"].index("--board") + 1] == str(tmp_path / "corrected.csv")
    assert seen["argv"][1:3] == ["--development-module", "unchanged.py"]

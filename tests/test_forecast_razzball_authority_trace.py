from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_live_forecast_uses_one_horizon_isolated_razzball_source_id() -> None:
    runtime = (ROOT / "src" / "fsffl" / "forecast" / "current_runtime.py").read_text(
        encoding="utf-8"
    )
    razzball = (
        ROOT / "src" / "fsffl" / "providers" / "razzball_season_live.py"
    ).read_text(encoding="utf-8")

    assert "RazzballSeasonProjectionSource" in runtime
    assert "RazzballLiveProjectionSource" not in runtime
    assert 'source_id="razzball"' in runtime
    assert "Full-season Razzball source that never reads rest-of-season pages." in razzball
    assert "Never read the ROS pages" in razzball


def test_live_ensemble_rejects_duplicate_provider_ids_and_equal_weights_sources() -> None:
    source = (ROOT / "src" / "fsffl" / "forecast" / "live_ensemble.py").read_text(
        encoding="utf-8"
    )
    assert "live ensemble source ids must be unique" in source
    assert "equal_weight_ensemble" in source
    assert "minimum_independent_sources" in source
    assert "aggregate" in source.lower()


def test_frozen_preseason_lineage_contains_razzball_once_alongside_fftoday() -> None:
    provenance = json.loads(
        (
            ROOT
            / "artifacts"
            / "implementation"
            / "final_forecast_route_implementation_20260920"
            / "FROZEN_SOURCE_PACKAGE_PROVENANCE.json"
        ).read_text(encoding="utf-8")
    )
    assert provenance["frozen_preseason_sources"] == ["fftoday", "razzball"]
    assert provenance["frozen_preseason_sources"].count("razzball") == 1
    assert provenance["future_scoring_translation"].endswith("applied exactly once")


def test_product_projection_display_selects_season_forecast_not_provider_specific_value() -> None:
    shell = (
        ROOT / "src" / "fsffl" / "product" / "static" / "product_shell.js"
    ).read_text(encoding="utf-8")
    assert "fsfflDisplayedProjectionObservation" in shell
    assert "item.metric==='fantasy_points'&&item.horizon==='season'" in shell
    assert "razzball" not in shell.lower()

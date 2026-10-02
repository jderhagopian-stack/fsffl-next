from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDY_PATH = ROOT / "scripts/run_simulation_convergence_pit_study.py"
WORKFLOW_PATH = ROOT / ".github/workflows/simulation-convergence-pit-study.yml"
INVENTORY_PATH = (
    ROOT / "docs/operations/evidence/simulation_item8_pit_inventory_20261002.json"
)


def _study_module():
    spec = importlib.util.spec_from_file_location("simulation_item8_study", STUDY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        sys.modules.pop(spec.name, None)


def test_item8_count_authority_remains_50k_with_100k_research_reference() -> None:
    study = _study_module()

    assert study.PRODUCTION_COUNT == 50_000
    assert study.REFERENCE_COUNT == 100_000
    assert study.SCREENING_CONTEXT_COUNT == 1_000
    assert study.SCREENING_CONTEXT_COUNT not in study.CONVERGENCE_COUNTS
    assert study.CONVERGENCE_COUNTS == (
        5_000,
        10_000,
        25_000,
        35_000,
        50_000,
        75_000,
        100_000,
    )
    assert study.COUNTS == (1_000, *study.CONVERGENCE_COUNTS)
    assert len(study.ROOT_SEEDS) == 8


def test_item8_workflow_runs_all_eight_roots_in_bounded_parallel_slices() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "cancel-in-progress: true" in workflow
    assert "seed_start: 0" in workflow and "seed_count: 3" in workflow
    assert "seed_start: 3" in workflow and workflow.count("seed_count: 3") == 2
    assert "seed_start: 6" in workflow and "seed_count: 2" in workflow
    assert "aggregate_simulation_convergence_pit_study.py" in workflow


def test_item8_pit_inventory_distinguishes_authentic_inputs_from_realized_targets() -> None:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    evidence = inventory["authentic_evidence"]
    eligibility = inventory["calibration_eligibility"]

    assert evidence["canonical_state_snapshots"]["total"] == 364
    assert evidence["provider_projection_snapshots"]["total"] == 12
    assert evidence["provider_projection_snapshots"]["normalized_observations"] == 22_050
    assert evidence["prospective_football_state_captures"]["total"] == 6

    pre = evidence["pre_opener_forecast_only_evidence"]
    assert pre["forecast_artifact_id"] == 63
    assert pre["before_official_opener"] is True
    assert pre["matching_retained_canonical_state_payload"] is False
    assert pre["eligible_full_state_forecast_checkpoint"] is False

    matched = evidence["earliest_matched_state_forecast_checkpoint"]
    assert matched["forecast_artifact_id"] == 87
    assert matched["after_official_opener"] is True
    assert matched["authentic_input_checkpoint"] is True

    frozen = evidence["post_opener_frozen_baseline"]
    assert frozen["artifact_id"] == 145
    assert "not_preseason" in frozen["classification"]

    assert eligibility["fully_realized_final_season_cases"] == 0
    assert eligibility["scored_probability_observations"] == 0
    assert eligibility["scored_continuous_observations"] == 0
    assert eligibility["prospective_input_checkpoints_exist"] is True
    assert eligibility["broad_multi_year_forecast_coverage"] is False

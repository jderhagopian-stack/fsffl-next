from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from fsffl.team_utility.simulation import NUMPY_PCG64_BATCHED_GAUSS_V1, simulate_regular_season


ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "scripts/run_simulation_35k_stress_test.py"
AGGREGATE = ROOT / "scripts/aggregate_simulation_35k_stress_test.py"
WORKFLOW = ROOT / ".github/workflows/simulation-35k-stress-test.yml"
DIRECTIVE = ROOT / "docs/operations/directives/20261002_SIMULATION_35K_STRESS_TEST.md"


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        sys.modules.pop(name, None)


def test_stress_contract_keeps_50k_authority_and_100k_reference_only() -> None:
    study = _module(STUDY, "simulation_35k_stress")

    assert study.CANDIDATE_COUNT == 35_000
    assert study.PRODUCTION_COUNT == 50_000
    assert study.REFERENCE_COUNT == 100_000
    assert study.COUNTS == (35_000, 50_000, 100_000)
    assert len(study.ROOT_SEEDS) == 12
    assert study.RNG_BATCH_SIZE == 500
    assert study.NUMPY_PCG64_BATCHED_GAUSS_V1 == NUMPY_PCG64_BATCHED_GAUSS_V1


def test_stress_fixtures_cover_every_management_category_with_supported_rules() -> None:
    study = _module(STUDY, "simulation_35k_stress_fixtures")
    rows = study.fixtures()
    tags = {tag for row in rows for tag in row.tags}

    assert len(rows) == 4
    assert {
        "razor_thin_playoff_bubble",
        "high_parity_league",
        "tail_championship_case",
        "future_pick_boundary_case",
        "near_zero_scenario_delta",
        "material_scenario_delta",
        "postseason_no_bye",
        "postseason_with_byes",
    } <= tags
    assert {row.playoff_teams for row in rows} == {4, 6}
    assert len({row.fixture_hash for row in rows}) == len(rows)


def test_stress_request_uses_production_rng_and_governed_pick_fallback() -> None:
    study = _module(STUDY, "simulation_35k_stress_request")
    pick_fixture = next(row for row in study.fixtures() if row.future_pick)
    request = study._request(pick_fixture, count=250, seed=123)

    assert request.rng_protocol == NUMPY_PCG64_BATCHED_GAUSS_V1
    assert request.rng_batch_size == 500
    assert request.future_pick_draft_season == 2027
    assert request.future_pick_draft_order_policy is None

    result = simulate_regular_season(request)
    assert len(result.future_pick_distributions) == 12
    assert {
        row.draft_order_policy_authority for row in result.future_pick_distributions
    } == {"derived_standard_fallback"}


def test_stress_product_checks_use_existing_rounding_classification_and_materiality() -> None:
    study = _module(STUDY, "simulation_35k_stress_product")
    scenario = next(
        row for row in study.fixtures() if row.scenario_near_shift is not None
    )
    baseline = simulate_regular_season(
        study._request(scenario, count=500, seed=456)
    )
    changed = simulate_regular_season(
        study._request(
            scenario,
            count=500,
            seed=456,
            focal_shift=scenario.scenario_near_shift,
            other_shift=-scenario.scenario_near_shift,
        )
    )

    assert study._js_round_percent(0.9149) == 91
    assert study._js_round_percent(0.9150) == 92
    assert len(study._competitive_state_signature(baseline)) == 12
    materiality = study._materiality_signature(baseline, changed)
    assert materiality["policy"]["expected_wins_abs"] == 0.20
    assert materiality["policy"]["playoff_probability_abs"] == 0.02
    assert materiality["policy"]["championship_probability_abs"] == 0.01
    assert (
        materiality["disposition_check"]
        == "not_applicable_simulation_only_fixture_no_fabricated_economics_or_negotiation"
    )


def test_stress_aggregation_surfaces_candidate_only_boundary_failure() -> None:
    aggregate = _module(AGGREGATE, "simulation_35k_stress_aggregate")
    rows = {}
    for seed in aggregate.EXPECTED_SEEDS:
        for count in (35_000, 50_000, 100_000):
            rows[(seed, "fixture", count)] = {
                "comparison": {
                    "product_check_results": {
                        "ranking_matches_100k": not (
                            seed == aggregate.EXPECTED_SEEDS[0] and count == 35_000
                        )
                    }
                }
            }

    result = aggregate._product_divergences(rows)

    assert result["candidate_only_count"] == 1
    assert result["production_only_count"] == 0
    assert result["both_count"] == 0


def test_stress_workflow_is_bounded_parallel_and_not_a_deployment_path() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "seed_start: 0" in workflow
    assert "seed_start: 3" in workflow
    assert "seed_start: 6" in workflow
    assert "seed_start: 9" in workflow
    assert workflow.count("seed_count: 3") == 4
    assert "simulation-35k-stress-final" in workflow
    assert "render" not in workflow.lower()


def test_management_directive_remains_explicitly_research_only() -> None:
    directive = DIRECTIVE.read_text(encoding="utf-8")

    assert "50,000 canonical runs" in directive
    assert "100,000 runs for same-root comparison only" in directive
    assert "Do not change production count" in directive
    assert "Temporarily hold the next origin-aware draft-pick Value implementation" in directive

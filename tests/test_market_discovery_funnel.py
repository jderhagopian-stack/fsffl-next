from pathlib import Path
from types import SimpleNamespace

from fsffl.opportunity import (
    BilateralPlausibility,
    PreliminaryEconomicBand,
)
from fsffl.product.market_discovery_runtime import (
    _build_path_seeds,
    _path_can_support_attention,
    _prune_package_neighborhood,
    _row_dominates,
    select_preliminary_screen_indices,
)


ROOT = Path(__file__).resolve().parents[1]


def _gibbs_row(shape: str, send_count: int, variant: int, gap: float) -> dict[str, object]:
    return {
        "kind": "trade",
        "discovery_status": "structurally_valid",
        "counterparty_team_id": "team-gibbs",
        "counterparty_name": "Gibbs Owner",
        "target_position": "RB",
        "market_gap_ratio": gap,
        "search_distance": gap * 100,
        "package_shape": shape,
        "package_variant_rank": variant,
        "send": [
            {
                "asset_ref": f"player:send-{shape}-{variant}-{index}",
                "label": f"Send {index}",
                "asset_kind": "player",
            }
            for index in range(send_count)
        ],
        "receive": [
            {
                "asset_ref": "player:gibbs",
                "label": "Jahmyr Gibbs",
                "asset_kind": "player",
            }
        ],
    }


def test_repeated_gibbs_neighborhood_collapses_to_one_candidate_path_family() -> None:
    runtime = SimpleNamespace(
        selected_team_id="team-me",
        league_state=SimpleNamespace(state_id="state-1"),
    )
    rows = []
    for shape, count in (
        ("one_for_one", 1),
        ("two_for_one", 2),
        ("three_for_one", 3),
    ):
        for variant in range(1, 4):
            rows.append(_gibbs_row(shape, count, variant, 0.01 * variant))

    seeds, collapsed = _build_path_seeds(
        runtime,
        rows,
        source="automatic_for_you",
        exact_target_constraint=None,
    )

    assert len(seeds) == 1
    assert collapsed == 6
    seed = seeds[0]
    assert seed["receive_asset_refs"] == ("player:gibbs",)
    assert len(seed["alternates"]) == 2
    assert {
        seed["representative"]["package_shape"],
        *(row["package_shape"] for row in seed["alternates"]),
    } == {"one_for_one", "two_for_one", "three_for_one"}


def test_preliminary_decision_budget_is_family_first_before_second_paths() -> None:
    seeds = [
        {"opportunity_id": "rb", "counterparty_team_id": "a"},
        {"opportunity_id": "rb", "counterparty_team_id": "b"},
        {"opportunity_id": "wr", "counterparty_team_id": "c"},
        {"opportunity_id": "wr", "counterparty_team_id": "d"},
        {"opportunity_id": "te", "counterparty_team_id": "e"},
    ]
    selected = select_preliminary_screen_indices(seeds, limit=3)
    assert selected == (0, 2, 4)


def test_extreme_focal_economic_strain_cannot_earn_attention_without_uniform_gain() -> None:
    row = {
        "focal_decision_shape": "mixed",
        "counterparty_decision_shape": "mixed",
        "negotiation_feasibility_shape": "mixed",
    }
    assert not _path_can_support_attention(
        row,
        PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN,
        BilateralPlausibility.BILATERAL_FRICTION,
    )
    row["focal_decision_shape"] = "uniform_gain"
    assert _path_can_support_attention(
        row,
        PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN,
        BilateralPlausibility.BILATERAL_FRICTION,
    )


def test_counterparty_dominated_path_never_supports_for_you_attention() -> None:
    assert not _path_can_support_attention(
        {"focal_decision_shape": "uniform_gain"},
        PreliminaryEconomicBand.ROBUST_OR_ORDINARY,
        BilateralPlausibility.COUNTERPARTY_DOMINATED,
    )


def test_within_provisional_package_band_is_uncertainty_not_rejection() -> None:
    assert _path_can_support_attention(
        {"focal_decision_shape": "mixed"},
        PreliminaryEconomicBand.BOUNDED_UNCERTAINTY,
        BilateralPlausibility.BILATERAL_SUPPORTED,
    )


def test_broad_market_discovery_never_imports_or_runs_changed_state_simulation() -> None:
    source = (ROOT / "src/fsffl/product/market_discovery_runtime.py").read_text()
    assert "build_post_trade_simulation_comparison" not in source
    assert "run_live_simulation_analytics" not in source
    assert "50_000" not in source
    assert '"changed_state_simulation_calls_during_discovery": 0' in source
    assert '"acceptance_probability": None' in source


def test_package_pruning_preserves_distinct_shapes_and_economic_categories() -> None:
    robust = _gibbs_row("one_for_one", 1, 1, 0.04)
    robust["preliminary_economic_band"] = PreliminaryEconomicBand.ROBUST_OR_ORDINARY.value
    strained = _gibbs_row("one_for_one", 1, 2, 0.01)
    strained["preliminary_economic_band"] = PreliminaryEconomicBand.FOCAL_ECONOMIC_STRAIN.value
    consolidation = _gibbs_row("two_for_one", 2, 1, 0.02)
    consolidation["preliminary_economic_band"] = PreliminaryEconomicBand.BOUNDED_UNCERTAINTY.value

    assert not _row_dominates(strained, robust)
    assert not _row_dominates(robust, strained)
    representative, alternates, pruned = _prune_package_neighborhood(
        [strained, robust, consolidation]
    )
    assert representative["preliminary_economic_band"] == PreliminaryEconomicBand.ROBUST_OR_ORDINARY.value
    assert {representative["package_shape"], *(row["package_shape"] for row in alternates)} == {
        "one_for_one",
        "two_for_one",
    }
    assert pruned == 0


def test_cheap_decision_economics_precedes_family_pruning_and_excludes_heavy_analysis() -> None:
    source = (ROOT / "src/fsffl/product/market_discovery_runtime.py").read_text()
    build = source.split("def build_market_discovery(", 1)[1]
    assert build.index("evaluate_candidate_economics(") < build.index("_build_path_seeds(")
    cheap = source.split("def evaluate_candidate_economics(", 1)[1].split(
        "def evaluate_candidate_path(", 1
    )[0]
    assert "summarize_bilateral_trade_economics" in cheap
    assert "calculate_bilateral_economic_net" in cheap
    assert "summarize_package_concentration" in cheap
    assert "assess_package_economics" in cheap
    assert "build_private_beta_trade_analysis" not in cheap
    assert "cached_behavior_profile_for_team" not in cheap
    assert "run_live_simulation_analytics" not in cheap

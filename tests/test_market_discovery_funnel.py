from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from fsffl.opportunity import (
    BilateralPlausibility,
    OpportunitySource,
    PreliminaryEconomicBand,
)
from fsffl.state.models import PlayerAsset

from fsffl.product.market_discovery_runtime import (
    DEFAULT_PRELIMINARY_DECISION_BUDGET,
    _proposal_from_row,
    _build_path_seeds,
    _candidate_path_order,
    _opportunity_identity,
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


def test_explicit_trade_finder_intents_group_at_the_approved_opportunity_level() -> None:
    runtime = SimpleNamespace(
        selected_team_id="team-me",
        league_state=SimpleNamespace(state_id="state-1"),
    )
    gibbs = _gibbs_row("one_for_one", 1, 1, 0.02)
    bijan = {
        **_gibbs_row("one_for_one", 1, 1, 0.03),
        "counterparty_team_id": "team-bijan",
        "receive": [
            {
                "asset_ref": "player:bijan",
                "label": "Bijan Robinson",
                "asset_kind": "player",
            }
        ],
    }

    target_gibbs = _opportunity_identity(
        runtime,
        gibbs,
        source=OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT,
        exact_target_constraint="player:gibbs",
        intent="target",
        intent_value="player:gibbs",
    )
    target_bijan = _opportunity_identity(
        runtime,
        bijan,
        source=OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT,
        exact_target_constraint="player:bijan",
        intent="target",
        intent_value="player:bijan",
    )
    assert target_gibbs[0] != target_bijan[0]

    position_gibbs = _opportunity_identity(
        runtime,
        gibbs,
        source=OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT,
        exact_target_constraint=None,
        intent="position",
        intent_value="RB",
    )
    position_bijan = _opportunity_identity(
        runtime,
        bijan,
        source=OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT,
        exact_target_constraint=None,
        intent="position",
        intent_value="RB",
    )
    assert position_gibbs[0] == position_bijan[0]
    assert position_gibbs[2:] == ("target_position", "RB", "RB:starter_upgrade")

    owner_gibbs = _opportunity_identity(
        runtime,
        gibbs,
        source=OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT,
        exact_target_constraint=None,
        intent="owner",
        intent_value="team-gibbs",
    )
    owner_other_target = _opportunity_identity(
        runtime,
        {
            **gibbs,
            "receive": [
                {
                    "asset_ref": "player:other",
                    "label": "Other Player",
                    "asset_kind": "player",
                }
            ],
        },
        source=OpportunitySource.EXPLICIT_TRADE_FINDER_INTENT,
        exact_target_constraint=None,
        intent="owner",
        intent_value="team-gibbs",
    )
    assert owner_gibbs[0] == owner_other_target[0]
    assert owner_gibbs[2:] == ("explore_owner", "OWNER", "owner:team-gibbs")


def test_market_discovery_observability_exposes_required_counts_and_reason_codes() -> None:
    runtime_source = (ROOT / "src/fsffl/product/market_discovery_runtime.py").read_text()
    contract_source = (ROOT / "src/fsffl/opportunity/market_discovery.py").read_text()
    search_source = (ROOT / "src/fsffl/product/opportunity_search.py").read_text()

    for token in (
        '"hypotheses_generated"',
        '"targets_considered"',
        '"raw_packages_generated_pre_dedup"',
        '"packages_removed_exact_duplicate"',
        '"packages_screened_economic"',
        '"packages_economic_incomplete"',
        '"path_families_created"',
        '"preliminary_decision_budget"',
        '"preliminary_decision_runs"',
        '"counterparty_dominated_count"',
        '"focal_dominated_count"',
        '"opportunities_created"',
        '"opportunities_suppressed"',
        '"opportunities_attention_ready"',
        '"for_you_selected"',
        '"diversity_relaxations"',
        '"changed_state_simulation_calls_during_discovery"',
    ):
        assert token in runtime_source
    assert "reason_codes: tuple[str, ...]" in contract_source
    assert '"attention_eligible_path_present"' in runtime_source
    assert '"package_variants_clustered"' in runtime_source
    assert "class SearchCandidateCollection" in search_source
    assert '"packages_removed_exact_duplicate": exact_duplicates_removed' in search_source


def test_representative_path_order_prefers_governed_categories_before_market_distance() -> None:
    supported = SimpleNamespace(
        bilateral_plausibility=BilateralPlausibility.BILATERAL_SUPPORTED,
        economic_screen=PreliminaryEconomicBand.ROBUST_OR_ORDINARY,
        evidence_completeness="complete",
        representative_package={"market_gap_ratio": 0.15, "search_distance": 150.0},
        path_id="supported",
    )
    closer_but_friction = SimpleNamespace(
        bilateral_plausibility=BilateralPlausibility.BILATERAL_FRICTION,
        economic_screen=PreliminaryEconomicBand.ROBUST_OR_ORDINARY,
        evidence_completeness="complete",
        representative_package={"market_gap_ratio": 0.01, "search_distance": 10.0},
        path_id="friction",
    )
    assert _candidate_path_order(supported) < _candidate_path_order(closer_but_friction)


def test_market_preliminary_screen_is_lightweight_decision_not_full_trade_analysis() -> None:
    source = (ROOT / "src/fsffl/product/market_discovery_runtime.py").read_text()
    evaluator = source.split("def evaluate_candidate_path(", 1)[1].split("def _side(", 1)[0]

    assert "assess_preliminary_bilateral_screen" in evaluator
    assert "resolve_mandatory_roster_cuts" in evaluator
    assert "compare_position_strengths" in evaluator
    assert "optimize_team_lineup" in evaluator
    assert "build_private_beta_trade_analysis" not in evaluator
    assert "build_post_trade_simulation_comparison" not in evaluator
    assert "run_live_simulation_analytics" not in evaluator
    assert '"post_trade_simulation_attached": False' in evaluator


def test_market_funnel_exposes_early_admission_rejections_timings_and_zero_simulation() -> None:
    source = (ROOT / "src/fsffl/product/market_discovery_runtime.py").read_text()
    search = (ROOT / "src/fsffl/product/opportunity_search.py").read_text()

    for token in (
        '"counterparties_considered"',
        '"counterparties_admitted_pre_package"',
        '"targets_admitted_pre_package"',
        '"send_assets_admitted_for_counterparty_need"',
        '"admission_rejection_reasons"',
        '"search_cache_hit"',
        '"timing_ms"',
        '"cheap_economic_screen"',
        '"preliminary_decision_screen"',
        '"changed_state_simulation_calls_during_discovery": 0',
    ):
        assert token in source
    assert "actionable_need_positions" in search
    assert "supply_positions" in search
    assert "build_scoped_trade_candidates" in search
    assert "Cardinal Value only bounded package cost" in search
    assert "FSFFL Market discovery funnel" in source


def test_pr232_discovery_budget_and_simulation_boundary_remain_invariant() -> None:
    assert DEFAULT_PRELIMINARY_DECISION_BUDGET == 8
    source = (ROOT / "src/fsffl/product/market_discovery_runtime.py").read_text()
    assert '"changed_state_simulation_calls_during_discovery": 0' in source
    assert '"acceptance_probability": None' in source
    assert "select_preliminary_screen_indices(seeds, limit=evaluation_limit)" in source


def test_request_local_asset_index_does_not_change_trade_proposal_semantics() -> None:
    runtime = SimpleNamespace(
        selected_team_id="team-me",
        league_state=SimpleNamespace(
            state_id="state-1",
            as_of=datetime(2026, 9, 25, 12, 0, tzinfo=UTC),
        ),
    )
    row = {
        "counterparty_team_id": "team-them",
        "send": [{"asset_ref": "player:mine"}],
        "receive": [{"asset_ref": "player:theirs"}],
    }
    asset_index = {
        ("team-me", "player:mine"): PlayerAsset(player_id="mine"),
        ("team-them", "player:theirs"): PlayerAsset(player_id="theirs"),
    }

    proposal = _proposal_from_row(
        runtime,
        row,
        prefix="market-economic",
        asset_index=asset_index,
    )

    assert proposal.side_a.team_id == "team-me"
    assert proposal.side_b.team_id == "team-them"
    assert proposal.side_a.sends == (PlayerAsset(player_id="mine"),)
    assert proposal.side_b.sends == (PlayerAsset(player_id="theirs"),)

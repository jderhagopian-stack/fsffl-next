from pathlib import Path


ATLAS = Path("src/fsffl/product/static/league_atlas_v1.js")


def _source() -> str:
    return ATLAS.read_text(encoding="utf-8")


def test_atlas_consumes_governed_team_and_value_lens_contracts() -> None:
    source = _source()

    assert "api('/api/league/team-views')" in source
    assert "api('/api/league/value-lenses')" in source
    assert "api('/api/values')" not in source
    assert "team_cardinal_portfolios" not in source
    assert "total_value" not in source


def test_atlas_preserves_parallel_player_value_lenses_without_team_totals() -> None:
    source = _source()

    for token in (
        "Broad Market",
        "FSFFL Intrinsic",
        "Difference",
        "broad_market_percentile",
        "intrinsic_percentile",
        "percentile_gap",
        "Player-level percentiles only",
        "no team value total",
    ):
        assert token in source

    assert "League Market Value" in source
    assert "team Intrinsic totals" in source
    assert "acceptance probability" in source
    assert "team_cardinal_portfolios" not in source
    assert "raw_intrinsic_value" not in source


def test_atlas_is_scan_first_across_governed_structural_lanes() -> None:
    source = _source()

    for token in (
        "Positional control",
        "calculated_competitive_state",
        "position_strengths",
        "league_rank",
        "strength_index",
        "Age profile",
        "roster_average_age",
        "starter_average_age",
        "Future flexibility",
        "draft_picks",
        "Depth & fragility",
        "roster_resilience",
    ):
        assert token in source


def test_atlas_trade_context_is_descriptive_not_recommendation_authority() -> None:
    source = _source()

    assert "not trade recommendations or partner-fit scores" in source
    assert "Partner fit stays unavailable" in source
    assert "Investigate in Market" in source
    assert "setRoute('opportunities')" in source


def test_atlas_surfaces_unavailable_value_state_without_blocking_structure() -> None:
    source = _source()

    assert "League structure remains independently usable" in source
    assert "valueLensResult.status==='fulfilled'?valueLensResult.value:null" in source
    assert "if(teamResult.status!=='fulfilled')throw teamResult.reason" in source


def test_atlas_has_mobile_compression_and_latency_measurement() -> None:
    source = _source()

    assert "@media(max-width:900px)" in source
    assert "@media(max-width:560px)" in source
    assert "performance.now" in source
    assert "Atlas load:" in source


def test_atlas_uses_governed_server_gap_instead_of_raw_value_subtraction() -> None:
    source = _source()

    assert "return row?.percentile_gap" in source
    assert "intrinsic_percentile-row.broad_market_percentile" not in source
    assert "raw values are never subtracted" in source


def test_pick_wealth_remains_state_inventory_not_value_score() -> None:
    source = _source()

    assert "view.draft_picks?.length||0" in source
    assert "Canonical owned-pick count only" in source
    assert "FSFFL Cardinal pick value" not in source

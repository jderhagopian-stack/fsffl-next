from pathlib import Path


def test_league_comparison_consumes_authoritative_atlas_analytics_and_value_contracts() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    for evidence in (
        "calculated_competitive_state",
        "expected_wins",
        "position_strengths",
        "strength_index",
        "league_rank",
        "playoff_probability",
        "preseason_expectation",
        "pick_map",
    ):
        assert evidence in source
    assert "api('/api/league/atlas')" in source
    assert "api('/api/league/team-views')" in source
    assert "api('/api/league/value-lenses')" in source
    assert "api('/api/values')" not in source
    assert "team_cardinal_portfolios" not in source
    assert "No team Market total, team Intrinsic total" in source


def test_value_api_exposes_server_owned_team_value_portfolios_without_atlas_consuming_them() -> None:
    source = Path("src/fsffl/product/webapp.py").read_text(encoding="utf-8")
    atlas = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert '"team_market_value_portfolios"' in source
    assert '"team_cardinal_portfolios"' in source
    assert "team_cardinal_portfolios" not in atlas


def test_league_comparison_is_wired_as_a_real_product_surface() -> None:
    shell = Path("src/fsffl/product/static/product_shell.js").read_text(encoding="utf-8")
    assert "league_comparison.js" in shell
    assert "renderFsfflLeagueComparison" in shell
    assert "route==='league_comparison'" in shell


def test_league_comparison_has_mobile_first_hierarchy() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    css = Path("src/fsffl/product/static/league_atlas.css").read_text(encoding="utf-8")
    assert ".league-edge-row" in source
    assert "@media(max-width:720px)" in css
    assert ".league-atlas-tabs" in css
    assert ".atlas-race-list{overflow-x:auto}" in css
    assert ".atlas-pick-table{overflow-x:auto}" in css
    assert ".atlas-outlook-list{overflow-x:auto}" in css



def test_league_atlas_explicitly_labels_stale_last_good_during_target_rebuild() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "intelligence_freshness||{}" in source
    assert "State current · last-good intelligence" in source
    assert "league-last-good-status" in source
    assert "Derived fields as of " in source
    assert "Replacement league intelligence is rebuilding." not in source


def test_league_atlas_rollout_surfaces_simulation_futures_and_origin_aware_pick_intelligence() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    assert "Season scenarios" in source
    assert "sim?.multiverse?.worlds" in source
    assert "row.projected_slot" in source
    assert "row.fsffl_intrinsic_pick_value" in source
    assert "Team-of-origin value" in source
    assert "Generic class fallback" in source
    assert "league-wide situation used to select each example" in source
    assert "not a team-specific upside/downside or a separate probability" in source
    assert "world?.team_outcomes||[]" in source
    assert "outcome?.team_id===managed" in source
    assert "outcome.regular_season_rank" in source
    assert "outcome.champion" in source
    assert "estimate?.distribution?.mean" in source
    assert "estimate.distribution.mean" in source
    assert "estimate.expected_value" not in source
    assert "world?.rarity?.label" in source
    assert "world.label" not in source
    assert "world.summary" not in source
    assert "world.description" not in source


def test_league_atlas_pick_drawer_groups_owned_assets_before_traded_history() -> None:
    source = Path("src/fsffl/product/static/league_comparison.js").read_text(encoding="utf-8")
    drawer = source[source.index("function laPickDrawer()") : source.index("function laActiveTab()")]
    assert 'class="atlas-pick-group"><h4>Currently owned</h4>' in drawer
    assert 'class="atlas-pick-group atlas-traded-picks"><h4>Traded away</h4>' in drawer
    assert drawer.index('class="atlas-pick-group"><h4>Currently owned</h4>') < drawer.index(
        'class="atlas-pick-group atlas-traded-picks"><h4>Traded away</h4>'
    )
    assert "row.pick_id" not in drawer
    assert "row.projected_slot" in drawer
    assert "row.fsffl_intrinsic_pick_value" in drawer
    assert "row.owner_team_name" in drawer
    assert "row.original_team_name" in drawer
    assert "20261003-scenarios-pick-order1" in Path(
        "src/fsffl/product/static/product_shell.js"
    ).read_text(encoding="utf-8")
    assert "20261003-scenarios-pick-order1" in source

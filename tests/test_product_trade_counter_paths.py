from pathlib import Path


STATIC = Path("src/fsffl/product/static")


def test_trade_counter_paths_load_after_primary_narrative():
    html = (STATIC / "index.html").read_text()
    assert html.index('/static/trade_counter_paths.js?v=20260909-beta-feedback1') > html.index('/static/trade_primary_narrative.js?v=20260909-beta-feedback1')


def test_counter_paths_only_surface_governed_mutual_gain_frontier_points():
    source = (STATIC / "trade_counter_paths.js").read_text()
    assert "point.feasibility_shape==='mutual_gain_candidate'" in source
    assert ".slice(0,3)" in source
    assert "first mutual-gain packages in the governed NEXT-6 frontier order" in source
    assert ".sort(" not in source
    assert "acceptance predictions" in source


def test_counter_paths_reconstruct_current_canonical_asset_refs_and_fail_closed():
    source = (STATIC / "trade_counter_paths.js").read_text()
    assert "`player:${asset.player_id}`" in source
    assert "`pick:${asset.pick_id}`" in source
    assert "currentOwnershipAllows(point,result)" in source
    assert "focalRefs.every(ref=>focal.has(ref))" in source
    assert "otherRefs.every(ref=>other.has(ref))" in source
    assert "Ownership changed — refresh frontier" in source


def test_counter_paths_reuse_existing_trade_builder_without_new_model_authority():
    source = (STATIC / "trade_counter_paths.js").read_text()
    assert "tradeUiState.focalSelected=new Set" in source
    assert "tradeUiState.counterpartySelected=new Set" in source
    assert "Analyze Trade to run this exact package" in source
    assert "api('/api/" not in source
    assert "fetch(" not in source
    assert "score=" not in source.lower()

from pathlib import Path


def test_product_surfaces_present_separate_three_year_index_and_raw_career_value():
    source = (
        Path(__file__).parents[1]
        / "src/fsffl/product/static/my_team_dashboard.js"
    ).read_text(encoding="utf-8")

    assert "3-Year Intrinsic Index (0–10,000)" in source
    assert "Career Intrinsic (raw)" in source
    assert "3-Year Intrinsic · 0–10,000 index" in source
    assert "Career Intrinsic · raw value" in source
    assert "raw_career_forward_reference.toFixed(1)" in source
    assert "intrinsic_value_index" in source
    assert "api('/api/value/career-intrinsic-v1')" in source
    assert "payload?.league_state_id&&payload.league_state_id!==expectedStateId" in source
    assert "payload?.status==='ready'&&payload.league_state_id===expectedStateId" in source

from pathlib import Path


def test_franchise_presents_separate_indexes_and_retains_raw_career():
    source = (
        Path(__file__).parents[1]
        / "src/fsffl/product/static/my_team_dashboard.js"
    ).read_text(encoding="utf-8")

    assert "3-Year Intrinsic Index (0–10,000)" in source
    assert "Career Intrinsic Index (0–10,000)" in source
    assert "3-Year Intrinsic · 0–10,000 index" in source
    assert "Career Intrinsic · 0–10,000 index" in source
    assert "career_intrinsic_index" in source
    assert "intrinsic_value_index" in source
    assert "api('/api/value/career-intrinsic-v1?'+query)" in source
    assert "payload?.league_state_id&&payload.league_state_id!==expectedStateId" in source
    assert "if(!myTeamCareerMatchesView(payload))" in source

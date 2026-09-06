from pathlib import Path


def test_shared_asset_browser_exposes_age_from_state_only() -> None:
    source = Path("src/fsffl/product/trade_center_view.py").read_text(encoding="utf-8")
    assert "age_years: float | None = None" in source
    assert "player_states_by_id" in source
    assert "age_years=player_state.age_years" in source
    assert "canonical point-in-time" in source
    assert "forecast" not in source.lower().split("def _team_browser", 1)[1].split("def build_trade_center_browser_view", 1)[0]


def test_players_assets_renders_and_sorts_canonical_age_without_derivation() -> None:
    source = Path("src/fsffl/product/static/explorer.js").read_text(encoding="utf-8")
    assert "age:asset.age_years??null" in source
    assert "explorerSortButton('Age','age'" in source
    assert "explorerAge(row.age)" in source
    assert "Age / ownership / roster slot:</strong> canonical point-in-time State" in source
    assert "Date.now" not in source
    assert "getFullYear" not in source

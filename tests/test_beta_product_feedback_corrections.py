from pathlib import Path


STATIC = Path(__file__).resolve().parents[1] / "src" / "fsffl" / "product" / "static"


def test_beta_product_correction_layer_is_loaded_last_with_fresh_cache_key() -> None:
    html = (STATIC / "index.html").read_text()
    assert "/static/beta_product_corrections.js?v=" in html
    assert html.rfind("beta_product_corrections.js") > html.rfind("product_shell.js")
    versions = {
        token.split("?v=")[1].split('"')[0]
        for token in html.split()
        if "?v=" in token
    }
    assert len(versions) == 1


def test_dead_additive_market_total_is_not_offered_on_primary_home_chart() -> None:
    html = (STATIC / "index.html").read_text()
    assert 'value="total_market_value"' not in html
    assert 'value="total_cardinal_value">Franchise value' in html


def test_trade_simulation_updates_competitive_summary_and_keeps_methods_secondary() -> None:
    script = (STATIC / "beta_product_corrections.js").read_text()
    assert "Simulation complete" in script
    assert "competitiveSummary(result)" in script
    assert "Methods & evidence" in script
    assert "Decision summary" in script


def test_position_strength_is_explicitly_current_season_and_long_term_is_roadmap_only() -> None:
    script = (STATIC / "beta_product_corrections.js").read_text()
    assert "current-season lineup strength" in script
    assert "2026 lineup strength by franchise" in script
    assert "Longer-term dynasty position outlook is a separate roadmap item" in script


def test_behavioral_correction_hides_raw_counterparty_identifiers_when_name_is_unknown() -> None:
    script = (STATIC / "beta_product_corrections.js").read_text()
    assert "League owner" in script
    assert "[data-behavior-owner]" in script
    assert "behavior-counterparty-row" in script

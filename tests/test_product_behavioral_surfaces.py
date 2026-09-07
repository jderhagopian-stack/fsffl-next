from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_analytics_terminal_exposes_behavior_without_revaluing_assets() -> None:
    source = (ROOT / "src/fsffl/product/static/analytics_terminal.js").read_text()
    assert "/api/behavioral/profiles" in source
    assert 'data-at-tab="behavior"' in source
    assert "Observed owner behavior" in source
    assert "does not change general FSFFL market Value" in source
    assert "acceptance percentage" in source
    assert "consolidation_trade_count" in source
    assert "diversification_trade_count" in source


def test_trade_center_consumes_descriptive_counterparty_behavior() -> None:
    source = (ROOT / "src/fsffl/product/static/product_polish.js").read_text()
    assert "/api/behavioral/profiles" in source
    assert "tradeBehaviorNarrative" in source
    assert "Observed history informs negotiation context" in source
    assert "does not change market Value" in source
    assert "not an acceptance percentage" in source
    assert "MutationObserver" not in source
    assert "setInterval(presentRuntimeCapabilities" not in source


def test_opportunity_discovery_shows_behavior_as_context_not_search_authority() -> None:
    source = (ROOT / "src/fsffl/product/static/opportunities.js").read_text()
    assert "/api/behavioral/profiles" in source
    assert "Observed owner behavior" in source
    assert "context only" in source
    assert "does not rewrite market Value" in source
    assert "Decision materiality pending" in source

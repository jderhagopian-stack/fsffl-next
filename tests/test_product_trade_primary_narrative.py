from pathlib import Path


STATIC = Path("src/fsffl/product/static")


def test_trade_primary_narrative_loads_after_existing_trade_explainer():
    html = (STATIC / "index.html").read_text()
    explainer = html.index('/static/trade_explainer.js?v=20260909-beta-feedback1')
    narrative = html.index('/static/trade_primary_narrative.js?v=20260909-beta-feedback1')
    assert narrative > explainer


def test_trade_primary_narrative_separates_decision_jobs_in_plain_language():
    source = (STATIC / "trade_primary_narrative.js").read_text()
    assert "Decision brief" in source
    assert "What this deal actually does" in source
    assert "Your case" in source
    assert "Their case" in source
    assert "Main tradeoff" in source
    assert "What to do next" in source
    assert "Run Simulate Impact next" in source
    assert "This is bilateral evidence, not an acceptance prediction." in source


def test_trade_primary_narrative_only_presents_existing_authoritative_evidence():
    source = (STATIC / "trade_primary_narrative.js").read_text()
    assert "roster_adjusted_market_net" in source
    assert "position_strength" in source
    assert "team_deltas" in source
    assert "result?.disposition" in source
    assert "api('/api/" not in source
    assert "fetch(" not in source
    assert "acceptance probability" not in source.lower()
    assert "opportunity score" not in source.lower()


def test_trade_primary_narrative_updates_after_changed_roster_simulation():
    source = (STATIC / "trade_primary_narrative.js").read_text()
    assert "lastSimulation=result" in source
    assert "window.renderTradeSimulationResult=function(result)" in source
    assert "renderBrief()" in source
    assert "document.querySelector('#simulate-trade')?.click()" in source

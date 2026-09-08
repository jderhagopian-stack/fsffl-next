from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_trade_finder_presents_published_asset_context_without_browser_model_logic() -> None:
    script = (ROOT / "src/fsffl/product/static/trade_finder_feasibility.js").read_text(encoding="utf-8")

    assert "item?.detail" in script
    assert "item?.age_years" in script
    assert "item?.roster_slot" in script
    assert "FSFFL Value ${oppValue(item.fsffl_value)}" in script
    assert "authoritative Cardinal Value to find economically plausible structures" in script
    assert "Roster need and counterparty fit then help prioritize" in script
    assert "authoritative Cardinal Value first to locate market-plausible structures" in script
    assert "acceptance probability" in script


def test_trade_finder_presentation_does_not_recompute_value_or_decision_truth() -> None:
    script = (ROOT / "src/fsffl/product/static/trade_finder_feasibility.js").read_text(encoding="utf-8")

    forbidden = (
        "market_gap_ratio=",
        "decision_quality_score=",
        "acceptance_probability=",
        "fsffl_value+",
        "fsffl_value-",
        "fsffl_value*",
        "fsffl_value/",
    )
    for token in forbidden:
        assert token not in script

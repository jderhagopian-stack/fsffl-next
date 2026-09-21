from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "src" / "fsffl" / "product"
STATIC = PRODUCT / "static"


def test_franchise_and_market_share_one_server_value_lens_evidence_contract() -> None:
    league = (PRODUCT / "league_value_lenses.py").read_text(encoding="utf-8")
    discovery = (PRODUCT / "intrinsic_market_discovery.py").read_text(encoding="utf-8")
    shared = (PRODUCT / "value_lens_evidence.py").read_text(encoding="utf-8")

    assert "build_governed_value_lens_evidence(runtime, intrinsic)" in league
    assert "build_governed_value_lens_evidence(runtime, intrinsic)" in discovery
    assert "def build_governed_value_lens_evidence" in shared
    assert "build_value_presentation_coordinate" in shared


def test_market_unavailable_result_is_not_terminally_cached_for_same_state() -> None:
    source = (STATIC / "intrinsic_market_discovery.js").read_text(encoding="utf-8")
    assert "cached&&cached.status==='ready'" in source
    assert "if(cacheMatches()){render();return cached}" in source
    assert "fsffl:product-context-updated" in source


def test_both_value_surfaces_keep_true_unavailability_fail_closed() -> None:
    franchise = (STATIC / "intrinsic_value_experience.js").read_text(encoding="utf-8")
    market = (STATIC / "intrinsic_market_discovery.js").read_text(encoding="utf-8")
    assert "No substitute number is shown" in franchise
    assert "No substitute value or recommendation is fabricated" in market
    assert "League Market Value remains unavailable" in market

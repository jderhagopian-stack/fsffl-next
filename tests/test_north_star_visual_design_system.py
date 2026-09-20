from pathlib import Path

STATIC = Path("src/fsffl/product/static")
DESIGN = STATIC / "north_star_design_system.css"
TRADE = STATIC / "north_star_trade_center.js"
INDEX = STATIC / "index.html"
DOC = Path("docs/NORTH_STAR_VISUAL_DESIGN_SYSTEM.md")
RELEASE = "20260913-phase3-latency1"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_design_system_is_loaded_without_changing_model_authority() -> None:
    index = _read(INDEX)
    design = _read(DESIGN)
    assert f"north_star_design_system.css?v={RELEASE}" in index
    assert "approved hybrid North Star visual design system" in design
    assert "premium dark, mobile-first consumer fantasy product" in design
    assert "Presentation only" in design
    assert "no model scores" in design
    assert "recommendations" in design
    assert "thresholds" in design


def test_canonical_system_prefers_open_stage_over_card_wall() -> None:
    design = _read(DESIGN)
    doc = _read(DOC)
    assert ".nx-stage{" in design
    assert "linear-gradient(180deg,#0d1a2b" in design
    assert ".nx-reference-tabs{" in design
    assert ".nx-story-rail{" in design
    assert "Open composition rule" in doc
    assert "A section does **not** become a card merely because it needs grouping" in doc


def test_reference_trade_uses_identity_exchange_visual_shift_and_story() -> None:
    source = _read(TRADE)
    for token in (
        "nx-reference-tabs",
        "nx-team-mark",
        "nx-identity-line",
        "nx-stage__title",
        "nx-exchange",
        "nx-impact",
        "nx-story-rail",
        "nx-action-button",
    ):
        assert token in source
    assert "scrollIntoView" in source
    assert "prefers-reduced-motion" in source


def test_reference_trade_keeps_simulation_and_decision_authority_upstream() -> None:
    source = _read(TRADE)
    assert "team_deltas" in source
    assert "disposition" in source
    assert "scenario_simulation_count" in source
    assert "fetch(" not in source
    assert "/api/" not in source
    assert "acceptance_probability" not in source
    assert "composite_score" not in source
    assert "master_score" not in source


def test_mobile_reference_is_recomposed_not_desktop_shrunk() -> None:
    design = _read(DESIGN)
    assert "@media(max-width:640px)" in design
    assert ".nx-exchange{" in design
    assert "grid-template-columns:1fr;" in design
    assert ".nx-impact__teams{display:none}" in design
    assert ".nx-story-rail{grid-template-columns:1fr" in design
    assert ".nx-reference-tabs{display:grid" in design
    assert ".nx-action-button{min-height:46px}" in design


def test_design_spec_preserves_visual_grammar_and_progressive_disclosure() -> None:
    doc = _read(DOC)
    for phrase in (
        "SEE -> UNDERSTAND -> INTERACT -> DRILL DEEPER",
        "Rank Band",
        "Delta Band",
        "Probability Shift",
        "Risk Band",
        "Trajectory Strip",
        "Distribution",
        "Atlas / Heat Map",
        "Package Comparison",
        "Progressive disclosure",
        "Mobile composition",
        "Approved product-family benchmark",
        "premium dark, mobile-first",
        "visual/product benchmark, not a model specification",
    ):
        assert phrase in doc

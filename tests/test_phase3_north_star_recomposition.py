from pathlib import Path


RECOMPOSITION = Path("src/fsffl/product/static/north_star_recomposition.css")
INDEX = Path("src/fsffl/product/static/index.html")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_recomposition_is_loaded_after_shared_north_star_styles() -> None:
    source = _source(INDEX)
    shared = source.index("/static/north_star.css?v=20260910-phase3-visual2")
    recomposed = source.index("/static/north_star_recomposition.css?v=20260910-phase3-visual2")
    assert shared < recomposed


def test_home_recomposition_uses_editorial_composition_not_card_wall() -> None:
    source = _source(RECOMPOSITION)
    assert ".home-priority{" in source
    assert "min-height:340px!important" in source
    assert "font-size:clamp(2.7rem,6vw,5.6rem)!important" in source
    assert ".home-pulse-list{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))" in source
    assert ".home-current{margin-top:34px!important;border:0!important" in source
    assert ".home-workflow,.home-workflow:first-child" in source
    assert "border-radius:0!important" in source


def test_franchise_recomposition_reads_as_diagnosis_spread() -> None:
    source = _source(RECOMPOSITION)
    assert ".franchise-hero{min-height:410px!important" in source
    assert "font-size:clamp(2.8rem,6vw,5.2rem)!important" in source
    assert ".franchise-outlook{margin:0!important" in source
    assert "border-left:1px solid rgba(255,255,255,.12)!important" in source
    assert ".franchise-section{margin-top:34px!important;padding:0!important;border:0!important" in source
    assert ".franchise-focus,.franchise-focus:first-child" in source
    assert "background:transparent!important" in source


def test_recomposition_has_deliberate_mobile_layouts() -> None:
    source = _source(RECOMPOSITION)
    assert "@media(max-width:900px)" in source
    assert ".home-pulse-list{grid-template-columns:1fr!important}" in source
    assert ".franchise-hero{grid-template-columns:1fr!important" in source
    assert "@media(max-width:680px)" in source
    assert ".franchise-position-row{grid-template-columns:56px minmax(0,1fr) 78px!important" in source


def test_recomposition_stays_presentation_only() -> None:
    source = _source(RECOMPOSITION)
    assert "Presentation only" in source
    assert "creates no State, Forecast, Value, Decision, Search, Simulation or Behavioral truth" in source

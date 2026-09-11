from pathlib import Path


NORTH_STAR = Path("src/fsffl/product/static/north_star.css")
INDEX = Path("src/fsffl/product/static/index.html")
PRODUCT_SHELL = Path("src/fsffl/product/static/product_shell.js")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_north_star_keeps_visual_hierarchy_in_presentation_lane() -> None:
    source = _source(NORTH_STAR)

    assert "Presentation expresses hierarchy only" in source
    assert "State/Forecast/Value/Decision/Analytics" in source
    assert "avoids a wall" in source


def test_home_has_one_dominant_command_surface_and_asymmetric_workflows() -> None:
    source = _source(NORTH_STAR)

    assert ".home-priority{" in source
    assert "min-height:220px" in source
    assert ".home-priority h3{" in source
    assert "font-size:clamp(1.8rem,4.2vw,3.1rem)" in source
    assert ".home-workflows{grid-template-columns:1.25fr .9fr .9fr" in source
    assert ".home-workflow:first-child{" in source
    assert ".home-attention,.franchise-shell,.league-structure-panel{max-width:1180px!important;margin-inline:auto!important}" in source


def test_franchise_uses_unequal_visual_weight_for_diagnosis() -> None:
    source = _source(NORTH_STAR)

    assert ".franchise-hero{" in source
    assert "grid-template-columns:minmax(0,1.45fr) minmax(260px,.55fr)" in source
    assert ".franchise-diagnosis-grid{" in source
    assert "grid-template-columns:1.35fr .825fr .825fr" in source
    assert ".franchise-focus:first-child{" in source


def test_mobile_rules_are_intentional_not_desktop_compression() -> None:
    source = _source(NORTH_STAR)

    assert "@media(max-width:680px)" in source
    assert ".home-priority{min-height:0" in source
    assert ".home-workflows{grid-template-columns:1fr!important}" in source
    assert ".franchise-diagnosis-grid{grid-template-columns:1fr!important}" in source
    assert ".franchise-position-row{grid-template-columns:64px minmax(0,1fr) 68px" in source


def test_visual_system_respects_reduced_motion() -> None:
    source = _source(NORTH_STAR)

    assert "@media(prefers-reduced-motion:reduce)" in source
    assert "transition:none!important" in source


def test_north_star_release_cache_generation_is_coherent() -> None:
    source = _source(INDEX)

    assert "/static/north_star.css?v=" in source
    assert "/static/session_recovery.js?v=" in source
    assert "/static/mobile_safari_recovery.js?v=" in source
    versions = {
        token.split("?v=")[1].split('"')[0]
        for token in source.split()
        if "?v=" in token
    }
    assert len(versions) == 1


def test_lazy_product_modules_share_the_north_star_release_generation() -> None:
    source = _source(PRODUCT_SHELL)

    assert "const fsfflStaticVersion='" in source
    assert "'/static/my_team_dashboard.js'" in source
    assert "script.src=`${path}?v=${fsfflStaticVersion}`" in source

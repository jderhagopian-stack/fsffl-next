from pathlib import Path


INDEX = Path("src/fsffl/product/static/index.html")
SHELL = Path("src/fsffl/product/static/product_shell.js")
APP = Path("src/fsffl/product/static/north_star_app.js")
RELEASE = "20260911-northstar3"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_north_star_release_busts_eager_static_cache() -> None:
    source = _source(INDEX)
    assert "20260910-phase3-visual2" not in source
    assert source.count(f"?v={RELEASE}") >= 10
    assert f"north_star_app.js?v={RELEASE}" in source
    assert f"north_star_app.css?v={RELEASE}" in source


def test_lazy_product_assets_use_same_release_generation() -> None:
    source = _source(SHELL)
    assert f"const fsfflStaticVersion='{RELEASE}'" in source
    assert "20260910-phase3-visual2" not in source


def test_market_assets_use_same_release_generation() -> None:
    source = _source(APP)
    assert f"north_star_market.css?v={RELEASE}" in source
    assert f"north_star_market.js?v={RELEASE}" in source
    assert "20260910-phase3-visual2" not in source

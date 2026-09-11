from pathlib import Path


INDEX = Path("src/fsffl/product/static/index.html")
RELEASE = "20260911-northstar3"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_north_star_release_busts_eager_static_cache() -> None:
    source = _source(INDEX)
    assert "20260910-phase3-visual2" not in source
    assert source.count(f"?v={RELEASE}") >= 10
    assert f"north_star_app.js?v={RELEASE}" in source
    assert f"north_star_app.css?v={RELEASE}" in source
    assert f"product_shell.js?v={RELEASE}" in source

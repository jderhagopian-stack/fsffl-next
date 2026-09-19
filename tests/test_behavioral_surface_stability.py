from pathlib import Path


def _source(name: str) -> str:
    return Path(f"src/fsffl/product/static/{name}").read_text(encoding="utf-8")


def test_behavioral_surface_restores_shared_generic_scaffold_before_navigation() -> None:
    source = _source("behavioral_intelligence.js")
    assert "function fsfflBehaviorRestoreGenericScaffold" in source
    assert "if(route!=='behavioral_intelligence')fsfflBehaviorRestoreGenericScaffold()" in source
    assert 'id="generic-eyebrow"' in source
    assert 'id="generic-title"' in source
    assert 'id="generic-copy"' in source


def test_behavioral_surface_uses_existing_product_components() -> None:
    source = _source("behavioral_intelligence.js")
    assert 'class="panel' in source
    assert 'class="metric-grid behavior-metrics"' in source
    assert 'class="dashboard-grid behavior-grid"' in source
    assert "behavior-maturity-panel" not in source
    assert "linear-gradient" not in _source("behavioral_intelligence.css")


def test_behavioral_surface_does_not_present_unavailable_inference_as_scores() -> None:
    source = _source("behavioral_intelligence.js")
    assert "Context-controlled position preference" in source
    assert "acceptance probability" in source.lower()
    assert "not shown as blank scores" in source
    assert "Completed actions only" in source

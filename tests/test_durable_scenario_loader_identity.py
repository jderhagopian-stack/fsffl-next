from pathlib import Path

from fsffl.product.scenario_cache import _durable_loader_identity


SCENARIO_CACHE = Path("src/fsffl/product/scenario_cache.py")


def _loader_a(state, evidence):
    return state, evidence


def _loader_b(state, evidence):
    return evidence, state


def test_durable_loader_identity_changes_with_implementation() -> None:
    assert _durable_loader_identity(_loader_a) != _durable_loader_identity(_loader_b)
    assert _durable_loader_identity(_loader_a) == _durable_loader_identity(_loader_a)


def test_explicit_loader_configuration_identity_is_supported() -> None:
    def configured_loader(state, evidence):
        return state, evidence

    configured_loader.__fsffl_cache_identity__ = "simulation-config:v2"
    first = _durable_loader_identity(configured_loader)
    configured_loader.__fsffl_cache_identity__ = "simulation-config:v3"
    second = _durable_loader_identity(configured_loader)
    assert first != second


def test_durable_read_and_write_share_loader_aware_fingerprint() -> None:
    source = SCENARIO_CACHE.read_text(encoding="utf-8")
    assert "_durable_key(league_state, evidence, simulation_loader)" in source
    assert "_durable_forecast_fingerprint(" in source
    assert "evidence, simulation_loader" in source
    assert "_persist_durable(league_state, evidence, simulation_loader, result)" in source

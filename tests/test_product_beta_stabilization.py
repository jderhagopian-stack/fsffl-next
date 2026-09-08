from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_simulator_public_renderer_does_not_recurse_through_global_binding() -> None:
    ui = (ROOT / "src/fsffl/product/static/simulator.js").read_text(encoding="utf-8")
    assert "function renderFsfflSimulatorView()" in ui
    assert "window.renderFsfflSimulator=function(){renderFsfflSimulatorView();" in ui
    assert "function renderFsfflSimulator(){" not in ui


def test_trade_discovery_suppresses_generic_pick_for_pick_mirrors() -> None:
    source = (ROOT / "src/fsffl/product/opportunity_workspace.py").read_text(encoding="utf-8")
    assert 'focal_asset.asset_kind == "pick" and target_asset.asset_kind == "pick"' in source
    assert "seen_structures" in source
    assert "_candidate_family_priority" in source
    assert "authoritative_cardinal_market_distance_with_player_target_priority" in source


def test_live_sleeper_snapshot_includes_unrostered_fantasy_player_universe() -> None:
    source = (ROOT / "src/fsffl/providers/sleeper_snapshot.py").read_text(encoding="utf-8")
    assert "include_unrostered_players: bool = True" in source
    assert "_attach_current_fantasy_player_universe" in source
    assert '"QB": Position.QB' in source
    assert '"RB": Position.RB' in source
    assert '"WR": Position.WR' in source
    assert '"TE": Position.TE' in source
    assert "Ownership remains entirely in TeamState.roster" in source
    assert "position is None or nfl_team is None" in source


def test_historical_callers_can_disable_live_player_universe_enrichment() -> None:
    source = (ROOT / "src/fsffl/providers/sleeper_snapshot.py").read_text(encoding="utf-8")
    assert "if self._include_unrostered_players:" in source
    assert "Historical callers can" in source
    assert "explicitly disable" in source

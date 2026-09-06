from datetime import UTC, datetime
from pathlib import Path
import re

import pytest

from fsffl.providers.sleeper_live import SleeperLiveSource


def test_runtime_polish_does_not_observe_its_own_character_mutations() -> None:
    source = Path("src/fsffl/product/static/product_polish.js").read_text(encoding="utf-8")
    assert "setTextIfChanged" in source
    assert "observer.observe(grid,{childList:true})" in source
    assert "characterData:true" not in source
    assert "subtree:true" not in source


def test_core_beta_assets_are_versioned_to_break_mobile_cache() -> None:
    html = Path("src/fsffl/product/static/index.html").read_text(encoding="utf-8")
    assets = (
        "app.css",
        "explorer.css",
        "app.js",
        "trade_center.js",
        "forecast_refresh.js",
        "product_polish.js",
        "explorer.js",
        "product_shell.js",
    )
    versions = []
    for asset in assets:
        match = re.search(rf"/static/{re.escape(asset)}\?v=([^\"']+)", html)
        assert match is not None, f"{asset} must carry an explicit cache-busting version"
        versions.append(match.group(1))
    assert len(set(versions)) == 1, "core beta assets must use one coherent deployment version"


def test_sleeper_live_retries_a_partial_roster_payload_once() -> None:
    roster_url = "https://api.sleeper.app/v1/league/league-1/rosters"
    roster_calls = 0

    def getter(url: str):
        nonlocal roster_calls
        if url.endswith("/league/league-1"):
            return {"league_id": "league-1", "settings": {"num_teams": 2}}
        if url == roster_url:
            roster_calls += 1
            if roster_calls == 1:
                return [{"roster_id": 1}]
            return [{"roster_id": 1}, {"roster_id": 2}]
        if url.endswith("/league/league-1/users"):
            return []
        if url.endswith("/players/nfl"):
            return {}
        if url.endswith("/league/league-1/traded_picks"):
            return []
        raise AssertionError(f"unexpected URL {url}")

    source = SleeperLiveSource(
        http_get_json=getter,
        clock=lambda: datetime(2026, 9, 6, tzinfo=UTC),
    )
    snapshot = source.fetch_latest(league_external_id="league-1")

    assert roster_calls == 2
    assert len(snapshot.payload["rosters"]) == 2


def test_sleeper_live_rejects_a_persistently_partial_roster_payload() -> None:
    def getter(url: str):
        if url.endswith("/league/league-1"):
            return {"league_id": "league-1", "settings": {"num_teams": 2}}
        if url.endswith("/league/league-1/rosters"):
            return [{"roster_id": 1}]
        raise AssertionError(f"unexpected URL {url}")

    source = SleeperLiveSource(
        http_get_json=getter,
        clock=lambda: datetime(2026, 9, 6, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="expected 2 teams, received 1"):
        source.fetch_latest(league_external_id="league-1")

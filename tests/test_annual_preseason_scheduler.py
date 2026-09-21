from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.forecast.annual_preseason_scheduler import (
    AnnualPreseasonSchedulerResult,
    run_annual_preseason_scheduler_tick,
)
from fsffl.forecast.current_runtime import NamedCurrentProjectionFetcher
from fsffl.product import annual_preseason_scheduler_routes
from fsffl.providers.current_projection_rows import (
    CurrentProjectionRow,
    CurrentProjectionSnapshot,
)
from fsffl.state.models import Position


CAPTURED_AT = datetime(2027, 8, 26, 15, 0, tzinfo=UTC)
BEFORE_WINDOW = datetime(2027, 8, 25, 15, 0, tzinfo=UTC)
SCHEDULE = (
    {"week": 1, "date": "2027-09-09", "home": "PHI", "away": "DAL"},
    {"week": 1, "date": "2027-09-12", "home": "BUF", "away": "NYJ"},
)
RAW_PLAYERS = {
    "josh": {
        "full_name": "Josh Allen",
        "position": "QB",
        "team": "BUF",
        "status": "Active",
    },
}


class _Store:
    def __init__(self, record=None):
        self.record = record
        self.puts = []

    def get_latest_reusable_artifact(self, **_kwargs):
        return self.record

    def put_artifact(self, record):
        self.record = record
        self.puts.append(record)


class _Sleeper:
    def __init__(self):
        self.player_fetches = 0
        self.schedule_fetches = 0

    def fetch_nfl_player_universe(self):
        self.player_fetches += 1
        return RAW_PLAYERS

    def fetch_nfl_regular_season_schedule(self, *, season: int):
        self.schedule_fetches += 1
        assert season == 2027
        return SCHEDULE


class _ExplodingSleeper:
    def fetch_nfl_player_universe(self):
        raise AssertionError("already-frozen scheduler run must not refetch Sleeper")

    def fetch_nfl_regular_season_schedule(self, *, season: int):
        raise AssertionError("already-frozen scheduler run must not refetch Sleeper")


def _snapshot(provider: str, *, pass_yd: float) -> CurrentProjectionSnapshot:
    return CurrentProjectionSnapshot(
        provider=provider,
        captured_at=CAPTURED_AT,
        effective_at=CAPTURED_AT,
        rows=(
            CurrentProjectionRow(
                provider=provider,
                external_id=f"{provider}:josh",
                player_name="Josh Allen",
                position=Position.QB,
                nfl_team="BUF",
                stats={
                    "pass_yd": pass_yd,
                    "pass_td": 30.0,
                    "pass_int": 10.0,
                    "rush_yd": 500.0,
                    "rush_td": 7.0,
                },
            ),
        ),
        source_version=f"{provider}-fixture-v1",
        usage_class="fixture",
    )


def _fetcher(provider: str, pass_yd: float) -> NamedCurrentProjectionFetcher:
    return NamedCurrentProjectionFetcher(
        source_id=provider,
        fetch=lambda _season: _snapshot(provider, pass_yd=pass_yd),
    )


def test_scheduler_tick_captures_through_governed_annual_service() -> None:
    store = _Store()
    sleeper = _Sleeper()

    result = run_annual_preseason_scheduler_tick(
        store,
        clock=lambda: CAPTURED_AT,
        sleeper_source=sleeper,
        fetchers=(_fetcher("alpha", 4000.0), _fetcher("beta", 4200.0)),
    )

    assert result.attempted is True
    assert result.outcome == "captured"
    assert len(store.puts) == 1
    assert sleeper.player_fetches == 1
    assert sleeper.schedule_fetches == 1


def test_scheduler_tick_before_window_is_harmless_and_writes_nothing() -> None:
    store = _Store()
    sleeper = _Sleeper()

    def should_not_fetch(_season: int):
        raise AssertionError("provider projections must not run before T-14")

    result = run_annual_preseason_scheduler_tick(
        store,
        clock=lambda: BEFORE_WINDOW,
        sleeper_source=sleeper,
        fetchers=(
            NamedCurrentProjectionFetcher(source_id="alpha", fetch=should_not_fetch),
            NamedCurrentProjectionFetcher(source_id="beta", fetch=should_not_fetch),
        ),
    )

    assert result.attempted is True
    assert result.outcome == "before-window"
    assert store.puts == []


def test_scheduler_tick_already_frozen_skips_all_provider_work() -> None:
    store = _Store(record=object())

    result = run_annual_preseason_scheduler_tick(
        store,
        clock=lambda: CAPTURED_AT,
        sleeper_source=_ExplodingSleeper(),
    )

    assert result.attempted is True
    assert result.outcome == "already-frozen"
    assert store.puts == []


def test_scheduler_route_is_token_protected_and_reports_outcome(monkeypatch) -> None:
    app = FastAPI()
    monkeypatch.setenv("FSFFL_SCHEDULER_TOKEN", "test-token")
    monkeypatch.setattr(
        annual_preseason_scheduler_routes,
        "run_annual_preseason_scheduler_tick",
        lambda _store: AnnualPreseasonSchedulerResult(
            season=2027,
            attempted=True,
            outcome="already-frozen",
            detail="fixture",
        ),
    )
    annual_preseason_scheduler_routes.install_annual_preseason_scheduler_route(
        app,
        persistence_store=_Store(),
    )
    client = TestClient(app)

    unauthorized = client.post("/internal/annual-preseason-snapshot/capture")
    assert unauthorized.status_code == 401

    authorized = client.post(
        "/internal/annual-preseason-snapshot/capture",
        headers={"X-FSFFL-Scheduler-Token": "test-token"},
    )
    assert authorized.status_code == 200
    assert authorized.json()["outcome"] == "already-frozen"


def test_render_config_preserves_web_endpoint_without_paid_cron() -> None:
    render_yaml = (Path(__file__).resolve().parents[1] / "render.yaml").read_text(
        encoding="utf-8"
    )

    assert "type: web" in render_yaml
    assert "FSFFL_SCHEDULER_TOKEN" in render_yaml
    assert "sync: false" in render_yaml
    assert "type: cron" not in render_yaml
    assert "fsffl-next-annual-preseason-snapshot" not in render_yaml
    assert "plan: starter" not in render_yaml


def test_github_actions_declares_free_daily_scheduler_contract() -> None:
    workflow = (
        Path(__file__).resolve().parents[1]
        / ".github"
        / "workflows"
        / "annual-preseason-snapshot-scheduler.yml"
    ).read_text(encoding="utf-8")

    assert 'cron: "17 8 * * *"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "python scripts/run_annual_preseason_scheduler_tick.py" in workflow
    assert "FSFFL_ANNUAL_SNAPSHOT_ENDPOINT" in workflow
    assert "secrets.FSFFL_SCHEDULER_TOKEN" in workflow
    assert "DORMANT - secure GitHub Actions secret" in workflow
    assert "type: cron" not in workflow
    assert "plan: starter" not in workflow

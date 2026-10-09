"""Focused provider acquisition telemetry contract tests: zero added HTTP or payload leakage."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from datetime import UTC, datetime
import json
from types import SimpleNamespace

import pytest

from fsffl.providers.acquisition_telemetry import (
    acquisition_cause,
    log_reuse,
    observe_acquisition,
    observed_getter,
    response_body_read,
)


def _events(caplog):
    prefix = "FSFFL_PROVIDER_ACQUISITION "
    return [
        json.loads(record.message[len(prefix):])
        for record in caplog.records
        if record.name == "fsffl.provider_acquisition"
        and record.message.startswith(prefix)
    ]


class _Body:
    status = 200

    def __init__(self, body):
        self.body = body
        self.calls = 0

    def read(self):
        self.calls += 1
        return self.body


def test_existing_http_getter_has_exact_attempt_and_raw_byte_parity(caplog, monkeypatch):
    monkeypatch.setenv("FSFFL_PROVIDER_ACQUISITION_TELEMETRY", "1")
    caplog.set_level("INFO", logger="fsffl.provider_acquisition")
    calls = []
    bodies = []

    def get(url):
        calls.append(url)
        response = _Body("été".encode("utf-8"))
        bodies.append(response)
        return response_body_read(response).decode("utf-8")

    class Source:
        def __init__(self):
            self._http_get_text = observed_getter(get, "cbs")

        @observe_acquisition("cbs", "rest_of_season")
        def fetch(self, *, season):
            for position in ("qb", "rb", "wr", "te"):
                self._http_get_text(
                    f"https://example.org/stats/{position}/{season}/restofseason/?secret=PRIVATE_TOKEN"
                )
            return SimpleNamespace(
                rows=("one", "two"), source_version="stable-v1",
                captured_at=datetime(2026, 10, 9, tzinfo=UTC),
                effective_at=datetime(2026, 10, 9, tzinfo=UTC),
            )

    with acquisition_cause("independent_current"):
        Source().fetch(season=2026)
    assert len(calls) == 4
    assert all(x.calls == 1 for x in bodies)
    event, = _events(caplog)
    assert event["requests"] == 4
    assert event["success"] == 4
    assert event["failures"] == 0
    assert event["retries"] == 0
    assert event["response_body_bytes"] == len("été".encode()) * 4
    assert event["unknown_body_count"] == 0
    assert event["status_classes"] == {"2xx": 4}
    assert event["families"] == {"projection_page": 4}
    assert event["season"] == 2026
    assert event["horizon"] == "rest_of_season"
    assert event["cause"] == "independent_current"
    assert event["normalized_rows"] == 2
    assert event["content_fingerprint"]
    assert "PRIVATE_TOKEN" not in caplog.text
    assert "example.org" not in caplog.text


def test_failure_and_repeated_exact_url_count_as_attempts_not_second_fetch(caplog, monkeypatch):
    monkeypatch.setenv("FSFFL_PROVIDER_ACQUISITION_TELEMETRY", "1")
    caplog.set_level("INFO", logger="fsffl.provider_acquisition")
    attempts = []

    def get(url):
        attempts.append(url)
        if len(attempts) == 1:
            raise TimeoutError("SECRET_PROJECTION_RESPONSE")
        return "ok"  # injected getter: original raw bytes are not observable

    @observe_acquisition("razzball", "rest_of_season")
    def acquire():
        getter = observed_getter(get, "razzball")
        try:
            getter("https://example.org/PRIVATE_ID")
        except TimeoutError:
            pass
        return getter("https://example.org/PRIVATE_ID")

    assert acquire() == "ok"
    assert len(attempts) == 2
    event, = _events(caplog)
    assert event["requests"] == 2
    assert event["failures"] == 1
    assert event["success"] == 1
    assert event["retries"] == 1
    assert event["unknown_body_count"] == 2
    assert event["response_body_bytes"] == 0
    assert "SECRET_PROJECTION_RESPONSE" not in caplog.text
    assert "PRIVATE_ID" not in caplog.text


def test_sleeper_parallel_worker_context_is_explicit_and_aggregate_is_safe(caplog, monkeypatch):
    monkeypatch.setenv("FSFFL_PROVIDER_ACQUISITION_TELEMETRY", "1")
    caplog.set_level("INFO", logger="fsffl.provider_acquisition")
    url = "https://api.sleeper.app/v1/league/private-league/rosters"
    hits = []

    def getter(value):
        hits.append(value)
        return response_body_read(_Body(b'{"rosters":[]}'))

    @observe_acquisition("sleeper", "probe", cause="unknown")
    def probe():
        observed = observed_getter(getter, "sleeper")
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(copy_context().run, observed, url) for _ in range(3)]
            assert all(future.result() for future in futures)
        return SimpleNamespace(fingerprint="a" * 64, week=5)

    with acquisition_cause("saved_session_probe"):
        result = probe()
    assert result.week == 5
    assert len(hits) == 3
    event, = _events(caplog)
    assert event["requests"] == 3
    assert event["response_body_bytes"] == len(b'{"rosters":[]}') * 3
    assert event["cause"] == "saved_session_probe"
    assert event["families"] == {"rosters": 3}
    assert event["retries"] == 2
    assert "private-league" not in caplog.text


def test_disabled_telemetry_does_not_modify_existing_acquisition(caplog, monkeypatch):
    monkeypatch.setenv("FSFFL_PROVIDER_ACQUISITION_TELEMETRY", "0")
    caplog.set_level("INFO", logger="fsffl.provider_acquisition")
    hit = []

    @observe_acquisition("nfl_fantasy", "season")
    def acquire():
        getter = observed_getter(lambda url: hit.append(url) or "original", "nfl_fantasy")
        return getter("https://example.org/x")

    assert acquire() == "original"
    assert hit == ["https://example.org/x"]
    assert _events(caplog) == []


def test_proven_zero_request_reuse_is_different_from_attempt(caplog, monkeypatch):
    monkeypatch.setenv("FSFFL_PROVIDER_ACQUISITION_TELEMETRY", "1")
    caplog.set_level("INFO", logger="fsffl.provider_acquisition")
    log_reuse(provider="sleeper", cause="connection", reuse="active_connection")
    event, = _events(caplog)
    assert event["requests"] == 0
    assert event["cache"] == "hit"
    assert event["response_body_bytes"] == 0
    assert "trace" not in event


def test_timestamp_only_change_does_not_change_normalized_content_digest(caplog, monkeypatch):
    monkeypatch.setenv("FSFFL_PROVIDER_ACQUISITION_TELEMETRY", "1")
    caplog.set_level("INFO", logger="fsffl.provider_acquisition")

    @observe_acquisition("fftoday", "season")
    def acquire(*, season, time):
        return SimpleNamespace(
            rows=({"position": "WR", "yards": 100.0},),
            source_version="test-v1", captured_at=time, effective_at=time,
        )

    acquire(season=2026, time=datetime(2026, 10, 8, tzinfo=UTC))
    acquire(season=2026, time=datetime(2026, 10, 9, tzinfo=UTC))
    first, second = _events(caplog)
    assert first["content_fingerprint"] == second["content_fingerprint"]
    assert first["captured_at"] != second["captured_at"]
    assert first["cohort"] == second["cohort"]

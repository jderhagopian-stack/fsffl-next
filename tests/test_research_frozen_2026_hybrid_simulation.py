"""Offline synthetic checks for frozen historical source IO.

No real user files, external provider requests or simulation runs in tests.
"""
from __future__ import annotations

from io import BytesIO

import pytest

from scripts import research_frozen_2026_hybrid_simulation as replay


def test_hash_pinned_inputs_are_downloaded_once_per_job(monkeypatch, tmp_path):
    raw=b'{"source":"synthetic"}'
    calls=[]
    monkeypatch.setattr(replay, "PINNED_BLOBS", {"synthetic.json": replay._git_blob_sha1(raw)})
    monkeypatch.setenv("FSFFL_HISTORICAL_SOURCE_CACHE_DIR", str(tmp_path))
    def fake_urlopen(req, timeout):
        calls.append((req.full_url,timeout))
        return BytesIO(raw)
    monkeypatch.setattr(replay,"urlopen",fake_urlopen)

    first=replay.load_pinned_sources()
    second=replay.load_pinned_sources()
    assert first==second=={"synthetic.json":{"source":"synthetic"}}
    assert len(calls)==1


def test_cached_data_is_still_hash_verified(monkeypatch,tmp_path):
    original=b'{"source":"synthetic"}'
    monkeypatch.setattr(replay, "PINNED_BLOBS", {"synthetic.json": replay._git_blob_sha1(original)})
    monkeypatch.setenv("FSFFL_HISTORICAL_SOURCE_CACHE_DIR",str(tmp_path))
    file=tmp_path/"synthetic.json"
    file.write_bytes(b'{"source":"untrusted replacement"}')
    monkeypatch.setattr(replay,"urlopen",lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError("cache must not fetch")))

    with pytest.raises(ValueError,match="content hash mismatch"):
        replay.load_pinned_sources()


def test_archived_commit_date_precedes_kickoff():
    assert replay.ARCHIVE_CAPTURE < replay.PREGAME_CUTOFF
    assert set(replay.PINNED_BLOBS) >= {
        "data/league.json", "data/rosters.json",
        "data/stats/fsffl/2026/league_matchups_raw.json",
    }


def test_pregame_correction_is_source_bounded():
    assert len(replay.PREKICKOFF_TEAM_CORRECTIONS)==1
    row=replay.PREKICKOFF_TEAM_CORRECTIONS[0]
    assert row["player_id"]=="sleeper:player:12504"
    assert row["expected_stale_team"]=="PIT" and row["verified_team"]=="GB"
    assert row["source_url"].startswith("https://www.packers.com/news/")


def test_travis_hunter_stays_on_bing_bong_at_sept9_cutoff():
    from scripts import research_2026_sept9_reconstruction as historical
    hunter = historical.ARCHIVE_ANALYTICS_COVERAGE_GAPS["12530"]
    assert hunter == {"name": "Travis Hunter", "roster_id": 11, "slot": "BENCH"}
    # The original September 9 Analytics export covers only 237 of 238
    # rostered assets. Missing from an analytics cohort != a Sleeper drop.
    assert "12530" not in historical.PREKICKOFF_SLOT_OVERRIDES
    assert historical.EXPECTED_MEMBERSHIP_SHA

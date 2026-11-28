"""Synthetic checks for direct archived preseason roster and Forecast evidence."""
from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from research_preseason_archive_bridge import ArchiveBridgeError, extract_preseason_archive_evidence

CUT="2026-09-10T00:20:00Z"
ASOF="2026-09-09T23:15:00Z"
LID="sleeper:fixture"


def sample():
    def team(n, slot):
        tid=f"{LID}:team:{n}"
        return {"team_id":tid, "context":{"as_of":ASOF},
            "players":[{"player_id":f"p{n}", "position":"TE", "full_name":f"Player {n}",
                "roster_slot":slot, "forecasts":[{"player_id":f"p{n}", "metric":"fantasy_points",
                "horizon":"season","as_of":ASOF,"period_start":"2026-09-01T00:00:00Z",
                "period_end":"2027-03-01T00:00:00Z",
                "provenance":{"effective_at":ASOF,"retrieved_at":ASOF}}]}],
            "draft_picks":[{"pick":{"pick_id":f"pick:{n}","round":1,"season":2027,
                "original_team_id":tid}}]}
    return {"id":65,"artifact_kind":"live_simulation_analytics",
        "computed_at":ASOF, "input_fingerprint":"f"*64,
        "payload":{"team_views":[team(1,"TE"),team(2,"BENCH")]}}


def extract(data=None):
    return extract_preseason_archive_evidence(sample() if data is None else data,
        cutoff=CUT,expected_league_id=LID)


def test_source_slot_is_authority_not_future_lineup():
    got=extract()
    assert [p["roster_slot"] for p in got["player_memberships"]]==["TE","BENCH"]
    assert got["counts"]=={"rostered_players":2,"picks":2,"historical_season_forecasts":2,"rostered_without_season_forecast":0}
    assert not got["publication_ready"]


def test_future_scored_or_later_state_not_included():
    got=extract()
    assert "historical_state" not in got
    assert "matchups" not in got
    assert "modern simulation kernel result" in got["not_yet_evidenced"]


def test_post_cutoff_artifact_blocked():
    a=sample()
    a["computed_at"]="2026-09-11T12:00:00Z"
    with pytest.raises(ArchiveBridgeError,match="before cutoff"):
        extract(a)


def test_forecast_source_retrieved_later_blocked():
    a=sample()
    a["payload"]["team_views"][0]["players"][0]["forecasts"][0]["provenance"]["retrieved_at"]="2026-09-10T01:00:00Z"
    with pytest.raises(ArchiveBridgeError,match="before cutoff"):
        extract(a)


def test_duplicate_player_across_teams_blocked():
    a=sample()
    a["payload"]["team_views"][1]["players"][0]["player_id"]="p1"
    with pytest.raises(ArchiveBridgeError,match="ownership/slot conflict"):
        extract(a)


def test_duplicate_future_pick_blocked():
    a=sample()
    a["payload"]["team_views"][1]["draft_picks"][0]["pick"]["pick_id"]="pick:1"
    with pytest.raises(ArchiveBridgeError,match="pick ownership conflict"):
        extract(a)


def test_unavailable_forecast_remains_unavailable():
    a=sample()
    a["payload"]["team_views"][0]["players"][0]["forecasts"]=[]
    got=extract(a)
    assert got["counts"]["rostered_without_season_forecast"]==1
    assert len(got["historical_forecasts"])==1


def test_out_of_league_identity_blocked():
    a=sample()
    a["payload"]["team_views"][0]["team_id"]="other-league:team:1"
    with pytest.raises(ArchiveBridgeError,match="cross-league"):
        extract(a)


def test_missing_historical_slot_blocked():
    a=sample()
    a["payload"]["team_views"][1]["players"][0]["roster_slot"]=None
    with pytest.raises(ArchiveBridgeError,match="slot conflict"):
        extract(a)


def test_duplicate_original_season_forecast_blocked():
    a=sample()
    f=deepcopy(a["payload"]["team_views"][0]["players"][0]["forecasts"][0])
    a["payload"]["team_views"][0]["players"][0]["forecasts"].append(f)
    with pytest.raises(ArchiveBridgeError,match="duplicate preseason"):
        extract(a)



def raw_sample():
    t = sample()
    raw = []
    for i in (1, 2):
        raw.append({
            "player_id": f"p{i}", "metric": "rush_yards", "horizon": "season",
            "as_of": ASOF,
            "provenance": {"effective_at": ASOF, "retrieved_at": ASOF},
        })
    return {"id": 63, "artifact_kind": "current_forecast_evidence",
        "computed_at": ASOF, "payload": {
            "runtime_result": {
                "raw_ensemble": raw, "model_version": "original-vintage",
                "successful_source_ids": ["provider-a", "provider-b"],
                "coverage": {"minimum_independent_sources": 2},
            },
        }}


def raw_extract(a=None):
    from research_preseason_archive_bridge import extract_preseason_raw_forecast_evidence
    return extract_preseason_raw_forecast_evidence(raw_sample() if a is None else a, cutoff=CUT)


def test_raw_forecast_vintage_is_not_modern_forecast():
    result=raw_extract()
    assert result["status"]=="raw_preseason_forecast_evidence_recovered_not_rescored"
    assert result["counts"]=={"raw_observations":2,"unique_subjects":2}
    assert not result["publication_ready"]


def test_raw_forecast_post_kickoff_provenance_blocks():
    a=raw_sample()
    a["payload"]["runtime_result"]["raw_ensemble"][0]["provenance"]["retrieved_at"]="2026-09-11T00:00:00Z"
    with pytest.raises(ArchiveBridgeError,match="before cutoff"):
        raw_extract(a)


def test_raw_forecast_duplicate_metric_blocks():
    a=raw_sample()
    a["payload"]["runtime_result"]["raw_ensemble"].append(deepcopy(a["payload"]["runtime_result"]["raw_ensemble"][0]))
    with pytest.raises(ArchiveBridgeError,match="duplicated"):
        raw_extract(a)


def test_raw_forecast_missing_independent_source_blocks():
    a=raw_sample()
    a["payload"]["runtime_result"]["successful_source_ids"]=["provider-a"]
    with pytest.raises(ArchiveBridgeError,match="independent"):
        raw_extract(a)


def test_raw_forecast_undercovered_source_blocks():
    a=raw_sample()
    a["payload"]["runtime_result"]["coverage"]["minimum_independent_sources"]=3
    with pytest.raises(ArchiveBridgeError,match="below accepted minimum"):
        raw_extract(a)

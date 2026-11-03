"""Real source longitudinal acceptance (source mounted ephemerally, no league data in git)."""
from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1
import json
import os
from pathlib import Path

import pytest
from fsffl.state.retrospective_season_audit import audit_retrospective_sleeper_season
from fsffl.state.historical_roster_context import reconstruct_sleeper_roster_context

PINNED_BLOB = "e18c01bf25f58c5dfe3d0802f53de484ea257ca1"


def test_yearwide_2023_catches_exact_single_waiver_evidence_gap():
    path = os.getenv("FSFFL_RESEARCH_HISTORICAL_ARCHIVE")
    if not path:
        pytest.skip("original archived source not mounted; no real-source claim")
    source = Path(path).read_bytes()
    assert sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest() == PINNED_BLOB
    seasons = [s for s in json.loads(source) if str(s["league"]["season"]) == "2023"]
    assert len(seasons) == 1
    out = audit_retrospective_sleeper_season(seasons[0], source_revision="git-blob:"+PINNED_BLOB)
    assert out.season == 2023
    assert out.team_count == 12
    assert out.completed_events_examined == 350
    assert out.completed_trades_examined == 48
    assert out.player_movements_examined == 588
    assert out.pick_movements_examined == 83
    assert out.faab_transfers_examined == 24
    assert out.waiver_bids_examined == 82
    assert out.completed_timestamp_tie_groups == 21
    assert out.status == "incomplete_source_history"
    assert len(out.issues) == 1, out.issues
    assert out.issues[0].code == "post_event_player_missing"
    assert out.issues[0].event_type == "waiver"
    assert out.issues[0].completed_at == datetime(2023, 7, 27, 7, 5, 25, 93000, tzinfo=UTC)
    assert out.source_provides_contemporaneous_state is False
    assert out.eligible_for_pit_decision_grade is False
    assert out.historically_validated_faab_balances is False


def test_all_retained_seasons_preserve_original_rules_and_expose_incomplete_years():
    """Source-wide research acceptance, not a claim of full historical coverage."""
    path = os.getenv("FSFFL_RESEARCH_HISTORICAL_ARCHIVE")
    if not path:
        pytest.skip("original historical source not mounted")
    raw = Path(path).read_bytes()
    assert sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == PINNED_BLOB
    years = sorted(json.loads(raw), key=lambda x: int(x["league"]["season"]))
    assert [int(y["league"]["season"]) for y in years] == [2022, 2023, 2024, 2025, 2026]
    summaries = []
    for idx, y in enumerate(years):
        if idx:
            assert str(y["league"]["previous_league_id"]) == str(years[idx-1]["league"]["league_id"])
        audit = audit_retrospective_sleeper_season(y, source_revision="git-blob:" + PINNED_BLOB)
        assert audit.team_count == len(y["rosters"])
        assert audit.completed_events_examined == len([t for t in y["transactions"] if t["status"] == "complete"])
        assert audit.source_provides_contemporaneous_state is False
        assert audit.eligible_for_pit_decision_grade is False
        summaries.append(audit)
    expected = [(2022, 246, 14), (2023, 350, 48), (2024, 358, 26), (2025, 339, 34), (2026, 107, 22)]
    assert [(x.season, x.completed_events_examined, x.completed_trades_examined) for x in summaries] == expected
    assert summaries[1].status == "incomplete_source_history"
    assert [issue.code for issue in summaries[1].issues] == ["post_event_player_missing"]
    assert all(not x.issues for idx, x in enumerate(summaries) if idx != 1)
    assert summaries[1].original_rules_sha256 != summaries[2].original_rules_sha256
    # Even a source-consistent 2022 or archived 2026 portion is not a valid PIT
    # decision State: startup/draft events and original availability still need proof.
    assert all(x.historically_validated_faab_balances is False for x in summaries)


def test_all_retained_seasons_produce_rule_scoped_roster_context_snapshots():
    """Exercise the reusable provider across the complete retained year cohort."""
    path = os.getenv("FSFFL_RESEARCH_HISTORICAL_ARCHIVE")
    if not path:
        pytest.skip("original historical source not mounted")
    raw = Path(path).read_bytes()
    assert sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == PINNED_BLOB
    years = sorted(json.loads(raw), key=lambda x: int(x["league"]["season"]))
    histories = [
        reconstruct_sleeper_roster_context(year, source_revision="git-blob:" + PINNED_BLOB)
        for year in years
    ]

    assert [row.season for row in histories] == [2022, 2023, 2024, 2025, 2026]
    assert [row.observed_team_count for row in histories] == [12, 12, 12, 12, 12]
    assert [row.completed_event_count for row in histories] == [246, 350, 358, 339, 107]
    assert all(row.provider_league_id == str(year["league"]["league_id"])
               for row, year in zip(histories, years))
    assert all(row.raw_roster_slots == tuple(year["league"]["roster_positions"])
               for row, year in zip(histories, years))
    assert all(row.league_rules_sha256 for row in histories)
    assert len({row.league_rules_sha256 for row in histories}) > 1
    assert all(row.eligible_for_pit_decision_grade is False for row in histories)
    assert all(snapshot.roster_slot_coverage == "unknown"
               for history in histories for snapshot in history.snapshots)
    assert histories[1].status == "incomplete_source_history"
    assert "post_event_player_ownership_mismatch" in histories[1].issues
    assert all(not history.issues for index, history in enumerate(histories) if index != 1)

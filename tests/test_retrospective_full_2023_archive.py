"""Real source longitudinal acceptance (source mounted ephemerally, no league data in git)."""
from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1
import json
import os
from pathlib import Path

import pytest
from fsffl.state.retrospective_season_audit import audit_retrospective_sleeper_season

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

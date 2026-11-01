"""Optional offline archived-source acceptance; never checked-in league source.

Sets FSFFL_RESEARCH_HISTORICAL_ARCHIVE to a secure local source path. Absent the
original pinned archive, this test cannot claim real-source acceptance.
"""
from __future__ import annotations

from hashlib import sha1
import json
import os
from pathlib import Path

import pytest

from fsffl.state.retrospective_sleeper_replay import replay_archived_sleeper_trade


PINNED_SOURCE_BLOB = "e18c01bf25f58c5dfe3d0802f53de484ea257ca1"
PINNED_TRADE = "1014282713371283456"


def test_pinned_original_archive_2023_factual_replay_private():
    source = os.environ.get("FSFFL_RESEARCH_HISTORICAL_ARCHIVE")
    if not source:
        pytest.skip("private original archived source not mounted; no real-source claim")
    bytes_ = Path(source).read_bytes()
    actual = sha1(b"blob " + str(len(bytes_)).encode() + b"\0" + bytes_).hexdigest()
    assert actual == PINNED_SOURCE_BLOB, "archived source changed; do not silently rebaseline"
    archive = json.loads(bytes_)
    seasons = [row for row in archive if row["league"]["season"] == "2023"]
    assert len(seasons) == 1
    s = seasons[0]
    replay = replay_archived_sleeper_trade(
        s, transaction_id=PINNED_TRADE, source_revision="git-blob:" + PINNED_SOURCE_BLOB)
    assert replay.status == "provisionally_consistent", replay.issues
    assert replay.future_completed_events_reversed == 191
    assert replay.observed_team_count == 12
    assert len([x for x in replay.transfers if x.asset_kind == "player"]) == 1
    assert len([x for x in replay.transfers if x.asset_kind == "pick"]) == 1
    assert len(replay.faab) == 2
    assert replay.eligible_for_pit_decision_grade is False
    assert replay.historical_anchor_independently_verified is False
    balances = {x.roster_id: x for x in replay.faab}
    assert balances["2"].used_before == 60 and balances["2"].used_after == 70
    assert balances["7"].used_before == 25 and balances["7"].used_after == 15

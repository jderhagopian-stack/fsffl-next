"""Pinned public research fixtures; not an original-availability certificate."""
import csv
from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

CALENDAR_SHA256='05dd485f7418350cd6fcbbc7790286b319276353c3261dcde592ff72dc5aeda8'
CALENDAR_COMMIT='b925cb83ec90782ae4bbfc06a4f8288fe7ac33c0'


def completion_bounds(path):
    raw=Path(path).read_bytes()
    assert sha256(raw).hexdigest()==CALENDAR_SHA256,'pinned NFL calendar changed'
    rows=list(csv.DictReader(raw.decode().splitlines()))
    out={}
    for year in range(2022,2026):
        selected=[r for r in rows if r['season']==str(year) and r['game_type']=='REG']
        assert len(selected)==(271 if year==2022 else 272)
        assert all(r['home_score']!='' and r['away_score']!=''for r in selected)
        for week in range(1,19):
            games=[r for r in selected if int(r['week'])==week]
            assert games
            # Conservative completion upper bound, not a game's exact end or
            # statistics-publication timestamp. Covers date/timezone ambiguity.
            end=date.fromisoformat(max(r['gameday'] for r in games))+timedelta(days=2)
            out[(year,week)]=datetime.combine(end,datetime.min.time(),tzinfo=UTC)
    return out


def accepted_2023_supplement(records):
    from fsffl.state.retrospective_season_audit import audit_retrospective_sleeper_season
    from fsffl.state.historical_supplemental_evidence import HistoricalSupplementalEvidenceReceipt,HistoricalSupplementalPlayerMovement
    identity=next(s for s in records if s.season==2023)
    audit=audit_retrospective_sleeper_season(records[identity],source_revision='pinned-fixture')
    assert len(audit.issues)==1 and audit.issues[0].code=='post_event_player_missing'
    issue=audit.issues[0]
    receipt=HistoricalSupplementalEvidenceReceipt(evidence_id='accepted-20261101-screenshot',
        source='user_supplied_screenshot',source_fingerprint_sha256='0613107bc386ccc01c877962a1d5be1232812a24f7db17ad7706ca0c2dc80c05',
        received_at=datetime(2026,11,1,tzinfo=UTC),source_reference='accepted-historical-supplement-20261101')
    movement=HistoricalSupplementalPlayerMovement(season=identity,provider='sleeper',source_player_id=issue.asset_id,
        player_id=issue.asset_id,provider_roster_id=issue.provider_roster_id,kind='dropped_to_waivers',
        effective_date=date(2023,8,23),date_precision='date_only',receipt=receipt)
    return {identity:(movement,)}

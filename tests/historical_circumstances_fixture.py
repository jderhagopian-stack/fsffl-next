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


def pinned_delivery_inputs(root):
    """One disposable fixture manifest for source, persistence and browser gates."""
    import json
    from hashlib import sha1
    from fsffl.state.historical_coverage import HistoricalEvidenceReceipt
    from fsffl.state.historical_roster_context import _digest
    from fsffl.providers.sleeper_historical_circumstances import normalize_legacy_historical_production,normalize_sleeper_historical_results
    from tests.historical_archive_context_fixture import declared_archive_context_inputs
    from tests.test_historical_circumstances_pinned import BLOBS
    root=Path(root);data={}
    for name,blob in BLOBS.items():
        raw=(root/name).read_bytes()
        assert sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,'pinned source changed'
        data[name]=json.loads(raw)
    bounds=completion_bounds(root/'nfl-games.csv')
    observed=datetime(2026,11,17,tzinfo=UTC)
    records,lineage,drafts=declared_archive_context_inputs(data['league_history.json'],observed=observed,source_revision='pinned-owner-delivery')
    sources={s.season:s for s in lineage.sources};identities={s.season:s for s in records}
    from fsffl.providers.sleeper_historical_circumstances import normalize_historical_season_window
    calendar=list(csv.DictReader((root/'nfl-games.csv').read_text().splitlines()))
    # Explicit FSFFL fixture admission: three one-week rounds, final in Week 17.
    windows=tuple(normalize_historical_season_window(calendar,season=year,regular_season_end_week=14,
        season_end_week=17,source_sha256=CALENDAR_SHA256)for year in range(2022,2027))
    production={};results=[];names={}
    for year in range(2022,2026):
        identity=identities[year]
        def receipt(kind,eid,at):return HistoricalEvidenceReceipt(season=identity,kind=kind,evidence_id=eid,effective_at=at,
            source='pinned-legacy-archive',source_version='calendar-completion-upper-bound:'+CALENDAR_SHA256)
        rows=data[f'actuals-{year}.json']
        names.update({str(p['player_id']):p['player_name']for p in rows if p.get('player_name')})
        production[year]=normalize_legacy_historical_production(rows,
            receipt=receipt('player_production',f'actuals-{year}',bounds[(year,18)]),
            scoring_rules_sha256=_digest(records[identity]['league']['scoring_settings']))
        end=int(records[identity]['league']['settings']['playoff_week_start'])-1
        for week in range(1,end+1):results.append(normalize_sleeper_historical_results(data[f'matchups-{year}.json'][str(week)],
            week=week,source=sources[identity],receipt=receipt('matchups',f'results-{year}-{week}',bounds[(year,week)])))
    for season in records.values():
        for draft in season.get('drafts',()):
            for pick in draft.get('picks',()):
                m=pick.get('metadata')or{};name=(str(m.get('first_name')or'')+' '+str(m.get('last_name')or'')).strip()
                if name:names[str(pick['player_id'])]=name
    return dict(season_windows=windows,seasons=records,lineage=lineage,rookie_drafts=drafts,source_revision='pinned-owner-delivery',source_observed_at=observed,
        production_by_previous_season=production,results=tuple(results),player_names=names,supplemental_movements=accepted_2023_supplement(records))

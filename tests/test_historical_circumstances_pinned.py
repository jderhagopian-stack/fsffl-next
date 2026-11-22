"""Disposable real-source joins; no raw rosters/stat lines in repository or logs."""
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha1
import json
import os
from pathlib import Path
import pytest
from fsffl.behavioral.historical_circumstances import build_historical_trade_circumstances
from fsffl.behavioral.context_inputs import context_feature_readiness
from fsffl.providers.sleeper_historical_context import build_sleeper_historical_context
from fsffl.providers.sleeper_historical_circumstances import normalize_legacy_historical_production,normalize_sleeper_historical_results
from fsffl.state.historical_coverage import HistoricalEvidenceReceipt
from fsffl.state.historical_roster_context import _digest
from tests.historical_archive_context_fixture import declared_archive_context_inputs
from tests.historical_circumstances_fixture import completion_bounds,accepted_2023_supplement,CALENDAR_SHA256

BLOBS={
 'actuals-2022.json':'c292e281970ac8ccc5b3ab27adb06854da0df24e',
 'actuals-2023.json':'f09a47ab988d9c8049de31aef946404875d9602f',
 'actuals-2024.json':'e40e17c4854ece71e2cd3b4edc07e0f8e2c53203',
 'actuals-2025.json':'4c834406768d2d959fcf82a4318d94986ef57980',
 'matchups-2022.json':'0fb025434cb4ef83c6fe228722c9900e25beb069',
 'matchups-2023.json':'1179da6dfb1d0da6bd86c5686227b566a1341377',
 'matchups-2024.json':'7102e132169f778db48bdfd6873c19dc59476dec',
 'matchups-2025.json':'604f2860e1d072427b03235b02b76591a00df50f',
 'league_history.json':'e18c01bf25f58c5dfe3d0802f53de484ea257ca1'}


def test_real_circumstances_join_prior_actuals_completed_results_and_partial_native_inputs():
    dirname=os.getenv('FSFFL_RESEARCH_CIRCUMSTANCE_SOURCE')
    if not dirname:pytest.skip('disposable pinned circumstance sources not mounted')
    root=Path(dirname);data={}
    for name,blob in BLOBS.items():
        raw=(root/name).read_bytes()
        assert sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob,'fixture source hash changed'
        data[name]=json.loads(raw)
    bounds=completion_bounds(root/'nfl-games.csv')
    records,lineage,drafts=declared_archive_context_inputs(data['league_history.json'],
        observed=datetime(2026,11,17,tzinfo=UTC),source_revision='pinned-circumstances')
    integration=build_sleeper_historical_context(seasons=records,lineage=lineage,rookie_drafts=drafts,
        source_revision='pinned-circumstances',source_observed_at=datetime(2026,11,17,tzinfo=UTC),
        supplemental_movements=accepted_2023_supplement(records))
    assert integration.trades.summary()['membership_context_rows']==127
    sources={s.season:s for s in lineage.sources};identities={s.season:s for s in records}
    histories={h.season:h for h in integration.roster_histories}
    production={};results=[]
    def receipt(identity,kind,eid,at):
        return HistoricalEvidenceReceipt(season=identity,kind=kind,evidence_id=eid,effective_at=at,
            source='pinned-legacy-archive',source_version='calendar-completion-upper-bound:'+CALENDAR_SHA256)
    for year in range(2022,2026):
        identity=identities[year]
        production[year]=normalize_legacy_historical_production(data[f'actuals-{year}.json'],
            receipt=receipt(identity,'player_production',f'actuals-{year}',bounds[(year,18)]),
            scoring_rules_sha256=_digest(records[identity]['league']['scoring_settings']))
        end=int(records[identity]['league']['settings']['playoff_week_start'])-1
        for week in range(1,end+1):
            results.append(normalize_sleeper_historical_results(data[f'matchups-{year}.json'][str(week)],
                week=week,source=sources[identity],receipt=receipt(identity,'matchups',f'results-{year}-{week}',bounds[(year,week)])))
    counts=Counter();by_year={};partial=Counter()
    for coverage in integration.trades.rows:
        year=coverage.request.season.season
        out=build_historical_trade_circumstances(coverage=coverage,history=histories[year],lineage=lineage,
            prior_production=production.get(year-1),results=tuple(results))
        counts['trade_dossiers']+=1;by_year.setdefault(year,Counter())['trades']+=1
        assert not out.source_availability_verified and not out.eligible_for_owner_model_training
        assert all(r.effective_at<out.completed_at for r in out.used_receipts)
        for team in out.teams:
            counts['participant_dossiers']+=1
            if team.roster_size is not None and team.prior_production_season is not None:
                counts['rostered_observations']+=team.roster_size
                counts['prior_production_observations']+=len(team.prior_production)
                counts['unknown_prior_production_observations']+=team.unknown_prior_production_count
            assert team.prior_production_season is None or team.prior_production_season.season<year
            readiness=context_feature_readiness(team.partial_model_inputs)
            assert not readiness.complete
            partial[len(readiness.values)-len(readiness.missing_features)]+=1
            if team.records:counts['participants_with_completed_results']+=1
    assert counts['trade_dossiers']==144
    assert counts['participant_dossiers']>=288  # Multi-party source events remain represented.
    assert counts['prior_production_observations']>2693  # Includes admitted2023supplement contexts.
    print(json.dumps({'historical_circumstance_join':dict(counts),'known_native_input_counts':dict(partial),
        'full_model_training_rows':0,'raw_ownership_or_production_printed':False},sort_keys=True))

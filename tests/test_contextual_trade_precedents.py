from datetime import date,datetime,UTC,timedelta
from dataclasses import replace
from types import SimpleNamespace
import pytest
from fsffl.behavioral.historical_trade_context import HistoricalSeasonWindow,HistoricalCaseRecord,HistoricalCaseAsset,historical_trade_phase,historical_record_text
from fsffl.behavioral.historical_cases import compile_historical_owner_case,attach_historical_owner_cases
from fsffl.behavioral.profiles import build_owner_behavior_profiles
from fsffl.trade_decision.owner_history import describe_owner_package_history
from fsffl.state.models import PlayerAsset
from fsffl.trade_decision.models import BilateralTradeProposal,TradeLeg
from tests.test_contextual_owner_delivery import inputs,OBS


def window(year):
    return HistoricalSeasonWindow(season=year,first_game_date=date(year,9,7),regular_season_end_date=date(year,12,12),
        season_end_date=date(year,12,31),source_sha256='a'*64)


def test_timing_uses_calendar_not_prior_season_results_or_container_year():
    windows=(window(2025),window(2026))
    phase=lambda at,season=2026:historical_trade_phase(datetime.fromisoformat(at).replace(tzinfo=UTC),season=season,windows=windows)
    assert phase('2026-08-01')=='offseason'
    assert phase('2026-01-04',2025)=='offseason'  # Same prior-year Sleeper container.
    assert phase('2025-12-20',2025)=='postseason'
    assert phase('2026-11-01')=='regular_season'
    assert phase('2026-09-07')=='unknown'  # Date alone cannot establish kickoff.
    assert historical_trade_phase(datetime(2026,8,1,tzinfo=UTC),season=2026,windows=())=='unknown'


def test_completed_prior_year_is_not_current_inseason_record():
    row=HistoricalCaseRecord(season=2025,wins=9,losses=5,ties=0,through_week=14,regular_season_complete=True)
    text,sentence=historical_record_text(row,trade_season=2026)
    assert text=='Finished the 2025 regular season 9–5'
    assert 'through Week' not in sentence and '2025' in sentence
    row=row.model_copy(update={'regular_season_complete':False})
    assert historical_record_text(row,trade_season=2026)[0]=='2025 record: 9–5 through Week 14'


def example(*,phase='regular_season',record_year=None):
    kwargs,events=inputs();base=compile_historical_owner_case(**kwargs).case
    record=HistoricalCaseRecord(season=(base.season-1 if record_year==-1 else record_year or base.season),wins=1,losses=0,ties=0,through_week=1)
    case=base.model_copy(update={'trade_phase':phase,'football_season':base.season,'calendar_source_sha256':('a'*64,), 'record_context':record,
        'acquired_assets':(HistoricalCaseAsset(kind='player',asset_ref='sleeper:player:player-b',position='RB'),),
        'disposed_assets':(HistoricalCaseAsset(kind='player',asset_ref='sleeper:player:player-a',position='WR'),)})
    profiles=attach_historical_owner_cases(build_owner_behavior_profiles(events,as_of=OBS),events=events,cases=(case,))
    profile=next(p for p in profiles if p.owner_id==case.owner_id)
    proposal=BilateralTradeProposal(proposal_id='now',as_of=OBS,side_a=TradeLeg(team_id='a',sends=(PlayerAsset(player_id='rb-now'),)),
        side_b=TradeLeg(team_id='b',sends=(PlayerAsset(player_id='wr-now'),)))
    current={'season':base.season,'wins':1,'losses':0,'ties':0,'through_week':1,'phase':'regular_season'}
    def describe(profile=profile,positions=None,current_record=current):
        return describe_owner_package_history(proposal,team_id='b',profile=profile,
            player_positions=positions or {'rb-now':'RB','wr-now':'WR'},source_state_id='state',current_record=current_record)
    return case,profile,proposal,current,describe


def test_shared_consumer_prefers_contextual_direction_without_predicting_willingness():
    case,profile,proposal,current,describe=example()
    row=describe()
    assert row['matching_features'][0]=='contextual_precedent'
    precedent=row['contextual_precedents'][0]
    assert precedent['case_id']==case.case_id and precedent['match_type']=='contextual'
    assert set(precedent['match_basis'])=={'position_direction','same_season_phase','same_completed_week','same_record_balance'}
    assert row['acceptance_probability'] is None and not row['willingness_inferred']
    assert row['decision_effect']=='no_disposition_change'
    assert describe(current_record={**current,'wins':0,'losses':1})['matching_features'][0]=='directional_precedent'
    assert describe(current_record={**current,'through_week':10})['matching_features'][0]=='directional_precedent'
    assert not describe(positions={'rb-now':'QB','wr-now':'WR'})['contextual_precedents']


def test_offseason_prior_record_never_matches_current_competitive_context():
    case,profile,proposal,current,describe=example(phase='offseason',record_year=-1)
    row=describe()
    assert row['matching_features'][0]=='directional_precedent'
    assert 'same_record_balance' not in row['contextual_precedents'][0]['match_basis']
    future=case.model_copy(update={'evidence_as_of':OBS+timedelta(days=1)})
    # Deliberately malformed in-memory profile cannot evade the consumer cutoff.
    profile=profile.model_copy(update={'historical_trade_cases':(future,)})
    assert not describe(profile=profile)['contextual_precedents']


def test_economic_selection_precedes_all_history_categories():
    from fsffl.product.strategic_discovery import _representative_indices
    def row(team,band,features):return {'counterparty_team_id':team,'preliminary_economic_band':band,
        'send':[{'asset_ref':'send'}],'receive':[{'asset_ref':'get'}],'hypotheses':[],
        'owner_history':{team:{'matching_features':features}}}
    weak=row('weak','strained',('contextual_precedent',));sound=row('sound','robust_or_ordinary',('package_shape',))
    assert _representative_indices((weak,sound),1)==[1]
    contextual=row('context','robust_or_ordinary',('contextual_precedent',))
    assert _representative_indices((sound,contextual),1)==[1]


def test_legacy_artifact_fingerprint_validates_stored_content_not_new_defaults():
    from fsffl.behavioral.dossier_publication import PreparedOwnerDossier,dossier_artifact,load_admitted_dossier
    from fsffl.state.historical_roster_context import _digest
    case,*_=example()
    prepared=PreparedOwnerDossier(league_family_id=case.league_family_id,current_provider_league_id=case.provider_league_id,cases=(case,))
    record=dossier_artifact(prepared,computed_at=OBS);payload=dict(record.payload)
    old=dict(payload['cases'][0])
    for key in ('football_season','trade_phase','calendar_source_sha256','record_context','acquired_assets','disposed_assets'):old.pop(key)
    payload['cases']=[old]
    record=replace(record,payload=payload,key=replace(record.key,input_fingerprint=_digest(payload)))
    class Store:
        def get_latest_reusable_artifact(self,**_):return record
    loaded=load_admitted_dossier(Store(),family_id=case.league_family_id,current_provider_league_id=case.provider_league_id)
    assert loaded.cases[0].trade_phase=='unknown' and not loaded.cases[0].acquired_assets



def test_refresh_keeps_structured_revision_with_original_source_clock(tmp_path):
    from fsffl.behavioral.store import BehavioralIntelligenceStore
    from fsffl.behavioral.historical_cases import preserve_historical_owner_cases
    case,profile,*_=example()
    kwargs,events=inputs()
    old=case.model_copy(update={'model_version':'owner-historical-trade-case-v1','acquired_assets':(),
        'disposed_assets':(),'trade_phase':'unknown','football_season':None,'calendar_source_sha256':(),'record_context':None})
    previous=profile.model_copy(update={'historical_trade_cases':(old,)})
    store=BehavioralIntelligenceStore(tmp_path/'upgrade.sqlite3');store.put_profiles((previous,))
    refreshed=store.put_refreshed_profiles((profile,),events=events)
    assert refreshed[0].historical_trade_cases[0].model_version=='owner-historical-trade-case-v2'
    assert refreshed[0].historical_trade_cases[0].evidence_as_of==old.evidence_as_of
    assert refreshed[0].historical_trade_cases[0].acquired_assets


def test_shared_consumer_story_explains_prior_campaign_without_relabeling_it_current():
    import subprocess,shutil,json
    node=shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    case,profile,proposal,current,describe=example(phase='offseason',record_year=-1)
    row=describe();p=row['contextual_precedents'][0]
    p['record_context']['regular_season_complete']=True
    script="""global.window={};const fs=require('fs');eval(fs.readFileSync(process.argv[1],'utf8'));
const row=JSON.parse(process.argv[2]);
const text=window.fsfflOwnerHistoryFacts({b:row},'b','state');
if(!text[0].includes('traded')||!text[0].includes('regular season'))throw Error(text[0]);
if(text[0].includes('record was'))throw Error('prior result mislabeled current');
console.log(JSON.stringify(text));"""
    result=subprocess.run([node,'-e',script,'src/fsffl/product/static/trade_football_story.js',json.dumps(row)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr



def test_generic_activity_does_not_replace_missing_contextual_precedents():
    case,profile,proposal,current,describe=example()
    profile=profile.model_copy(update={'balanced_trade_count':profile.trade_count,'consolidation_trade_count':0,'diversification_trade_count':0})
    row=describe(profile=profile,positions={'rb-now':'QB','wr-now':'WR'})
    assert row['facts']  # Descriptive legacy activity remains available.
    assert not row['contextual_precedents'] and row['matching_features']==[]

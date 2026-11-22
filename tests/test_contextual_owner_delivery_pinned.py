"""Integrated real-data gate; optional disposable public sources, no raw logs."""
import json,os
from pathlib import Path
import pytest
from fsffl.product.historical_owner_delivery import build_historical_owner_delivery
from fsffl.behavioral.store import BehavioralIntelligenceStore
from fsffl.behavioral.historical_cases import preserve_historical_owner_cases
from fsffl.behavioral.profiles import build_owner_behavior_profiles
from fsffl.state.historical_roster_context import _digest
from tests.historical_circumstances_fixture import pinned_delivery_inputs


def test_pinned_sources_to_grounded_cases_profiles_persistence_and_refresh(tmp_path):
    root=os.getenv('FSFFL_RESEARCH_CIRCUMSTANCE_SOURCE')
    if not root:pytest.skip('disposable owner-delivery source cohort not mounted')
    inputs=pinned_delivery_inputs(root)
    delivery=build_historical_owner_delivery(**inputs)
    assert delivery.coverage['compiled_initiator_cases']==144
    assert delivery.coverage['profiles_with_cases']==12
    assert delivery.coverage['case_blocker_counts']=={'initiating_account_not_witnessed':147}
    assert not delivery.model_policy_promoted
    assert delivery.coverage['owner_model_training_rows_admitted']==0
    assert all(c.created_at<=c.completed_at<=c.evidence_as_of for c in delivery.cases)
    assert all(not c.learned_preference for c in delivery.cases)
    store=BehavioralIntelligenceStore(tmp_path/'profile-review.sqlite3')
    store.put_events(delivery.events);store.put_profiles(delivery.profiles)
    family=delivery.profiles[0].league_family_id
    restored=BehavioralIntelligenceStore(tmp_path/'profile-review.sqlite3').load_profiles(family)
    assert sum(len(p.historical_trade_cases)for p in restored)==delivery.coverage['profile_cases']
    refreshed=preserve_historical_owner_cases(build_owner_behavior_profiles(delivery.events,as_of=inputs['source_observed_at']),
        previous_profiles=restored,events=delivery.events)
    assert _digest([p.model_dump(mode='json')for p in refreshed])==_digest([p.model_dump(mode='json')for p in restored])
    total_bytes=sum(len(p.model_dump_json().encode())for p in restored)
    assert total_bytes<250_000,'compact profile payload budget exceeded'
    print(json.dumps({'owner_delivery':delivery.coverage,'profile_json_bytes':total_bytes,
        'profiles_restored':len(restored),'raw_owner_or_trade_payload_printed':False},sort_keys=True))

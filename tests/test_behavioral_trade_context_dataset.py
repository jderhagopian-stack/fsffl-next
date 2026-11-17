from datetime import timedelta

import pytest

from fsffl.behavioral.models import BehavioralAsset,BehavioralEventKind
from fsffl.behavioral.trade_context_dataset import (build_trade_context_calibration_dataset,
    trade_context_integrity_issues)
from fsffl.behavioral.context_dataset import build_behavioral_context_calibration_dataset
from fsffl.state.history import InMemorySnapshotStore
from tests.test_behavioral_action_context import _event,_state,PRE_AT,EVENT_AT


def trade():
    return _event().model_copy(update={
        'acquired':(BehavioralAsset(kind='player',asset_ref='b-rb1',position='RB'),),
        'disposed':(BehavioralAsset(kind='player',asset_ref='a-wr1',position='WR'),)})


def build(events,states=None):
    events=tuple(events)
    return build_trade_context_calibration_dataset(events,
        snapshots=InMemorySnapshotStore(states if states is not None else (_state(PRE_AT),)),
        league_id_by_event={e.event_id:'league-1' for e in events},
        team_id_by_event={e.event_id:'a' for e in events})


def test_trade_only_dataset_reuses_native_context_and_does_not_train_on_waivers():
    event=trade()
    old_waiver=event.model_copy(update={'event_id':'waiver','kind':BehavioralEventKind.WAIVER,
        'occurred_at':PRE_AT-timedelta(seconds=1)})
    result=build((event,old_waiver))
    assert result.total_event_count==1 and result.usable_event_count==1
    original=build_behavioral_context_calibration_dataset((event,),snapshots=InMemorySnapshotStore((_state(PRE_AT),)),
        league_id_by_event={event.event_id:'league-1'},team_id_by_event={event.event_id:'a'})
    assert result.rows==original.rows
    assert result.rows[0].context.snapshot_state_id==_state(PRE_AT).state_id


def test_known_other_owner_activity_stales_league_context_without_becoming_negative_offer():
    event=trade()
    waiver=event.model_copy(update={'event_id':'waiver','owner_id':'other','roster_id':2,
        'kind':BehavioralEventKind.FREE_AGENT,'occurred_at':PRE_AT+timedelta(seconds=1)})
    result=build((event,waiver))
    assert result.total_event_count==1 and result.usable_event_count==0
    assert 'recorded league activity' in result.unavailable[0].reason
    # Historical comparison excludes contemporaneous, future and other-league actions.
    for change in ({'occurred_at':EVENT_AT},{'occurred_at':EVENT_AT+timedelta(seconds=1)},
                   {'league_external_id':'another-season'}):
        assert build((event,waiver.model_copy(update=change))).usable_event_count==1


def test_snapshot_that_cannot_account_for_the_traded_player_is_not_training_context():
    event=trade().model_copy(update={'disposed':(BehavioralAsset(kind='player',asset_ref='b-wr',position='WR'),)})
    result=build((event,))
    assert result.usable_event_count==0 and 'disposed player is absent' in result.unavailable[0].reason
    event=trade().model_copy(update={'acquired':(BehavioralAsset(kind='player',asset_ref='a-rb-0',position='RB'),)})
    assert 'already on' in build((event,)).unavailable[0].reason


def test_identity_and_historical_position_must_be_explicit_not_silently_assumed():
    event=trade().model_copy(update={'acquired':(BehavioralAsset(kind='player',asset_ref='provider-alias',position='RB'),)})
    assert 'identity is unavailable' in build((event,)).unavailable[0].reason
    assert trade_context_integrity_issues(event,state=_state(PRE_AT),team_id='a',
        known_intervening_activity=False,player_id_by_asset_ref={'provider-alias':'b-rb1'})==()
    wrong=event.model_copy(update={'acquired':(BehavioralAsset(kind='player',asset_ref='b-rb1',position='WR'),)})
    assert 'position differs' in build((wrong,)).unavailable[0].reason


def test_missing_or_post_action_snapshots_and_duplicate_history_remain_explicit():
    event=trade()
    assert build((event,),states=()).usable_event_count==0
    assert 'strictly pre-action' in build((event,),states=(_state(EVENT_AT),)).unavailable[0].reason
    with pytest.raises(ValueError,match='unique event ids'):
        build((event,event))


def test_guard_uses_only_one_external_snapshot_lookup_per_trade():
    class Store(InMemorySnapshotStore):
        calls=0
        def latest_at_or_before(self,*args,**kwargs):
            self.calls+=1;return super().latest_at_or_before(*args,**kwargs)
    store=Store((_state(PRE_AT),));event=trade()
    result=build_trade_context_calibration_dataset((event,),snapshots=store,
        league_id_by_event={event.event_id:'league-1'},team_id_by_event={event.event_id:'a'})
    assert result.usable_event_count==1 and store.calls==1


def test_unknown_acquisition_position_does_not_become_zero_in_a_partial_outcome():
    event=trade().model_copy(update={'acquired':(
        BehavioralAsset(kind='player',asset_ref='b-rb1',position='RB'),
        BehavioralAsset(kind='player',asset_ref='b-wr'))})
    result=build((event,))
    assert result.usable_event_count==0
    assert 'position is unavailable' in result.unavailable[0].reason

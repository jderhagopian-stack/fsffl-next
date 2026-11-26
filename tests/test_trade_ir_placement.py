from copy import deepcopy
from datetime import timedelta
import pytest
from fsffl.state.models import RosterEntry, RosterSlot, PlayerStatus
from fsffl.trade_decision.models import BilateralTradeProposal, TradeLeg
from fsffl.state.models import PlayerAsset
from fsffl.trade_decision import resolve_mandatory_roster_cuts
from tests.test_trade_decision_roster_legality import _state, AS_OF


def case(*, eligible=True, space=True, active_outgoing=False):
    s=_state()
    rules=s.league.rules.model_copy(update={'ir_size':1})
    teams=list(s.team_states)
    teams[0]=teams[0].model_copy(update={'roster':(
        RosterEntry(player_id='p1',slot=RosterSlot.BENCH),
        *((RosterEntry(player_id='p2',slot=RosterSlot.BENCH),) if not active_outgoing else ()),
        RosterEntry(player_id='p3',slot=RosterSlot.BENCH if active_outgoing else RosterSlot.IR),
    )})
    if not space:
        teams[0]=teams[0].model_copy(update={'roster':(*teams[0].roster,RosterEntry(player_id='p4',slot=RosterSlot.IR))})
    states=tuple(x.model_copy(update={'status':PlayerStatus.INJURED,'nfl_injured_reserve':eligible}) if x.player_id=='p5' else x for x in s.player_states)
    s=s.model_copy(update={'league':s.league.model_copy(update={'rules':rules}),'team_states':tuple(teams),'player_states':states})
    p=BilateralTradeProposal(proposal_id='ir-exchange',as_of=AS_OF,
        side_a=TradeLeg(team_id='A',sends=(PlayerAsset(player_id='p3'),)),
        side_b=TradeLeg(team_id='B',sends=(PlayerAsset(player_id='p5'),PlayerAsset(player_id='p6'))))
    return s,p


def test_vacated_ir_slot_is_used_before_cut_and_lineup_evaluation():
    from fsffl.trade_decision.scenario import apply_bilateral_trade_with_ir_placements
    s,p=case();before=deepcopy(s.model_dump())
    scenario=apply_bilateral_trade_with_ir_placements(s,p)
    result=resolve_mandatory_roster_cuts(scenario.after,before_state=s,market_values={'p1':1,'p2':2,'p5':50,'p6':60})
    a=next(r for r in result.resolutions if r.team_id=='A')
    assert a.required_cut_count==1 and a.ir_placements==('p5',)
    assert next(x for x in result.league_state.team_states[0].roster if x.player_id=='p5').slot==RosterSlot.IR
    assert s.model_dump()==before


@pytest.mark.parametrize('eligible,space,expected',[(False,True,2),(None,True,2)])
def test_unknown_or_ineligible_ir_and_full_ir_do_not_waive_cuts(eligible,space,expected):
    from fsffl.trade_decision.scenario import apply_bilateral_trade_with_ir_placements
    s,p=case(eligible=eligible,space=space)
    result=resolve_mandatory_roster_cuts(apply_bilateral_trade_with_ir_placements(s,p).after,before_state=s)
    assert result.resolutions[0].required_cut_count==expected
    assert not result.resolutions[0].ir_placements


def test_unrelated_team_facts_survive_transaction():
    from fsffl.trade_decision.scenario import apply_bilateral_trade
    from tests.test_trade_decision_roster_legality import PROVENANCE
    s,p=case();states=list(s.team_states);states[0]=states[0].model_copy(update={'max_points_for':123.,'max_points_for_provenance':PROVENANCE})
    s=s.model_copy(update={'team_states':tuple(states)})
    after=apply_bilateral_trade(s,p).after
    assert after.team_states[0].max_points_for==123.


def test_full_ir_and_active_outgoing_does_not_create_extra_ir_space():
    from fsffl.trade_decision.scenario import apply_bilateral_trade_with_ir_placements
    s,p=case(space=False,active_outgoing=True)
    a=resolve_mandatory_roster_cuts(apply_bilateral_trade_with_ir_placements(s,p).after,before_state=s).resolutions[0]
    assert a.required_cut_count==1 and not a.ir_placements


def test_future_ir_evidence_is_not_available_for_roster_planning():
    from fsffl.trade_decision.scenario import apply_bilateral_trade_with_ir_placements
    s,p=case();s=s.model_copy(update={'player_states':tuple(x.model_copy(update={'as_of':AS_OF+timedelta(days=1)}) if x.player_id=='p5' else x for x in s.player_states)})
    a=resolve_mandatory_roster_cuts(apply_bilateral_trade_with_ir_placements(s,p).after,before_state=s).resolutions[0]
    assert a.required_cut_count==2 and not a.ir_placements


def test_ir_plan_is_explained_by_the_explore_card():
    import subprocess
    script=r"""
const vm=require('vm'),fs=require('fs'),assert=require('assert');
const c={window:{addEventListener:()=>{}},console};vm.createContext(c);
vm.runInContext(fs.readFileSync('src/fsffl/product/static/strategic_explore.js','utf8').replace('{render,run,priorities,applyIntent}','{render,run,priorities,applyIntent,irPlacement}'),c);
const text=c.window.fsfflStrategicExplore.irPlacement({receive:[{asset_ref:'player:rb',label:'Incoming RB'}],roster_legality:[{team_id:'a',ir_placements:['rb']}]},'a');
assert(text.includes('Move Incoming RB to the available IR spot'));
"""
    subprocess.run(['node','-e',script],check=True,capture_output=True,text=True)

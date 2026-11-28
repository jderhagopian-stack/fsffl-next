from datetime import date
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

from fsffl.product.runtime import PrivateBetaRuntimeStore
from fsffl.product.trade_edition import build_edition, collect_trades
from fsffl.product.trade_edition_boxes import scored_weeks
from fsffl.product.webapp import create_app
from fsffl.state.models import ProviderRef
from tests.test_owner_current_season import NOW, history, profiles
from tests.test_state_foundation import make_state


def fixture():
    state = make_state(NOW)
    def refs(k):
        return (ProviderRef(provider="sleeper", external_id=str(k)),)
    teams = tuple(t.model_copy(update={"provider_refs": refs(i)}) for i,t in enumerate(state.teams,1))
    state = state.model_copy(update={"teams":teams,"league":state.league.model_copy(update={"provider_refs":refs("live")})})
    h = history()
    record = NS(sleeper_league_external_id="live", result=NS(profiles=profiles(h),
                league_family_id=h.league_family_id, current_owner_by_roster=h.current_owner_by_roster))
    return state, record


def test_authenticated_report_route_replays_both_legs_and_handles_missing_boxes(monkeypatch):
    state, record = fixture()
    monkeypatch.setenv("FSFFL_BETA_AUTH","0")
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user",state)
    monkeypatch.setattr("fsffl.product.trade_edition_boxes.report_boxes",lambda *args: ())
    client = TestClient(create_app(runtime_store=store, behavioral_coordinator=NS(current=lambda *a,**k:record)))
    result = client.post("/api/reports/trade-season")
    assert result.status_code == 200, result.text
    issue = result.json()
    assert issue["counts"] == {"player":1,"pick":1}
    assert len(issue["ledger"][0]["sides"]) == 2
    assert issue["ledger"][0]["sides"][0]["season"][0] == "UNAVAILABLE"
    record.sleeper_league_external_id = "other"
    assert client.post("/api/reports/trade-season").status_code == 409


def test_only_finished_weeks_after_deal_and_before_next_transfer_score():
    state, record = fixture()
    _, names, cutoff, trades = collect_trades(state, record)
    ref = "sleeper:player:p1"
    def week(day, pts):
        when=date(2026,11,day)
        return when,when,{1:{},2:{ref:pts}}
    weeks = (week(1,200),week(7,25),week(16,50))
    runtime = NS(league_state=state,value_evidence=None)
    issue=build_edition(runtime,names,cutoff,trades,weeks)
    assert [s["season"][0] for s in issue["ledger"][0]["sides"]] == ["DUMPSTER","ON FIRE"]
    move=trades[0][1]
    from fsffl.product.trade_edition import season_take
    mark,why=season_take(move.event,trades[0],weeks,{(2,ref):NOW.replace(day=12)},2026,move.completed_at,lambda a:a.asset_ref)
    assert mark=="NICE" and "25 points" in why


def test_partial_receipts_are_never_published_as_a_full_ledger():
    state, record = fixture()
    p=record.result.profiles[0]
    record.result.profiles=(p.model_copy(update={"current_season_activity":p.current_season_activity.model_copy(
        update={"trade_count":65})}),*record.result.profiles[1:])
    with pytest.raises(ValueError,match="incomplete"):
        collect_trades(state,record)


def test_open_pick_grade_reserves_final_verdict():
    from fsffl.product.trade_edition import dynasty_take
    _, record=fixture()
    event=record.result.profiles[0].current_season_activity.trade_examples[0].event
    prices={a.asset_ref: (1000 if a.kind=="pick" else 80) for a in (*event.acquired,*event.disposed)}
    assert dynasty_take(event,prices,lambda a:a.asset_ref,2026)[0]=="ON FIRE"
    prices.clear()
    assert dynasty_take(event,prices,lambda a:a.asset_ref,2026)[0]=="TOO SOON"


def test_box_scores_require_saved_totals_and_complete_starters():
    state, _ = fixture()
    state = state.model_copy(update={"completed_through_week":1,
        "league":state.league.model_copy(update={"rules":state.league.rules.model_copy(
            update={"fantasy_regular_season_end_week":14})}),
        "matchups":(NS(week=1,team_a_id=state.teams[0].team_id,team_b_id=state.teams[1].team_id,
                      team_a_points=10,team_b_points=20),)})
    rows=[dict(roster_id=i,points=i*10,starters=[str(i)],starters_points=[i*10]) for i in (1,2)]
    provider=NS(fetch_nfl_regular_season_schedule=lambda **k:[dict(week=1,date="2026-09-10")],
                fetch_league_matchup_week=lambda *a:rows)
    assert scored_weeks(state,"live",NOW,provider)[0][2][1]=={"sleeper:player:1":10}
    rows[0]["points"]+=1
    assert scored_weeks(state,"live",NOW,provider) == ()
    rows[0]["points"]-=1
    rows[0]["starters_points"]=[]
    assert scored_weeks(state,"live",NOW,provider) == ()


def test_cash_kicker_does_not_hide_observed_player_return_or_impute_cash_price():
    from fsffl.behavioral.models import BehavioralAsset
    from fsffl.product.trade_edition import dynasty_take, season_take
    _, record=fixture()
    event=record.result.profiles[0].current_season_activity.trade_examples[0].event
    incoming=BehavioralAsset(kind="player",asset_ref="sleeper:player:99")
    cash=BehavioralAsset(kind="faab",asset_ref="sleeper:faab:test:1:2",faab_amount=3)
    mixed=event.model_copy(update={"acquired":(incoming,),"disposed":(cash,*event.disposed)})
    prices={incoming.asset_ref:100,event.disposed[0].asset_ref:90}
    grade,why=dynasty_take(mixed,prices,lambda a:a.asset_ref,2026)
    assert grade=="FAIR" and "players and picks" in why
    buyer=mixed.model_copy(update={"disposed":(cash,)})
    coords=date(2026,11,8)
    week=(coords,coords,{buyer.roster_id:{incoming.asset_ref:24}})
    mark,why=season_take(buyer,[NS(event=buyer)],(week,),{},2026,event.occurred_at,lambda a:a.asset_ref)
    assert mark=="NICE" and "24 points" in why
    assert dynasty_take(buyer,prices,lambda a:a.asset_ref,2026)[0]=="UNAVAILABLE"


def test_dated_editorial_survives_lineup_outage_only_for_matching_receipts(tmp_path, monkeypatch):
    import json
    from fsffl.product.trade_annual_editorial import read_editorial, reviewed_trade
    state, record = fixture()
    _, names, cutoff, trades = collect_trades(state, record)
    digest = trades[0][0].source_sha256
    private = {"league":"123","season":2026,"published":"2026-11-17","teams":{"1":"Alpha"},
               "trades":{digest:{"grades":{"1":["NICE","FAIR"],"2":["OOF","ON FIRE"]},
                                 "argument":"Alpha got their receiver."}}}
    (tmp_path/"trade-annual-123-2026.json").write_text(json.dumps(private))
    monkeypatch.setenv("FSFFL_REPORT_EDITION_DIR",str(tmp_path))
    assert read_editorial("123",2026,NOW.replace(day=1)) == {}
    assert read_editorial("456",2026,NOW) == {}
    edition = read_editorial("123",2026,NOW)
    issue = build_edition(NS(league_state=state,value_evidence=None),names,cutoff,trades,(),edition)
    deal = issue["ledger"][0]
    assert deal["reviewed_on"]=="2026-11-17" and deal["sides"][0]["season"]==("NICE","")
    assert deal["argument"]=="Alpha got their receiver."
    assert reviewed_trade(edition,trades[0][:1]) is None
    assert reviewed_trade({**edition,"trades":{}},trades[0]) is None

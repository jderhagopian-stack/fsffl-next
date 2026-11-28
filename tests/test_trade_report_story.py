from datetime import date, datetime, UTC
from types import SimpleNamespace as N

from fsffl.product.trade_report_story import side_story
from fsffl.providers.trade_report_results import read_results


def test_public_results_drop_unfinished_games_and_ambiguous_ids():
    games=[dict(game_id="g",season="2027",game_type="REG",gameday="2027-09-10",home_score="7",away_score="0")]
    row=dict(player_display_name="Some Receiver",player_id="one",season="2027",season_type="REG",
             week="1",game_id="g",position="WR",rushing_yards="0",receiving_yards="61",rushing_tds="0",receiving_tds="1")
    assert list(read_results(2027,games,[row]).values())==[((date(2027,9,10),1,61,1),)]
    assert not read_results(2027,games,[row,dict(row,player_id="two")])
    assert not read_results(2027,[dict(games[0],home_score="")],[row])


def test_story_never_spends_future_results_or_recredits_a_transferred_player():
    dt=lambda day: datetime(2027,10,day,tzinfo=UTC)
    player=N(asset_ref="p",kind="player")
    m=N(event=N(roster_id=1,acquired=(player,),occurred_at=dt(2)),completed_at=dt(3))
    index={"p":("WR",[(dt(d).date(),w,yards,1) for d,w,yards in [(3,4,12),(6,5,71),(13,6,120),(20,7,95)]])}
    def render(cutoff,week,exit_day=None):
        exits={(1,"p"):dt(exit_day)} if exit_day else {}
        return side_story(m,{1:"North"},2027,dt(cutoff),week,index,exits,lambda a:"Receiver")
    early=render(14,5)
    assert "71 scrimmage yards" in early[0] and "1 NFL game " in early[0]
    assert "191 scrimmage yards" in render(18,6)[0]
    assert "71 scrimmage yards" in render(23,7,13)[0]
    assert "286 scrimmage yards" in render(23,7)[0]


def test_injury_context_needs_public_prognosis_before_offer():
    player=N(asset_ref="sleeper:player:9226",kind="player")
    def story(day):
        dt=datetime(2026,9,day,tzinfo=UTC)
        m=N(event=N(roster_id=1,acquired=(player,),occurred_at=dt),completed_at=dt)
        return side_story(m,{1:"North"},2026,datetime(2026,11,1,tzinfo=UTC),8,{}, {},lambda a:"Achane")
    assert "ACL" not in story(27)[0]
    assert "ACL" in story(29)[0] and story(29)[1][0]=="OOF"

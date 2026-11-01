"""Historical factual replay proof; no forecasts, market values or hidden hindsight grading."""
from datetime import UTC, datetime, timedelta

import pytest
from fsffl.state.historical_coverage import HistoricalEvidenceKind as Kind, HistoricalEvidenceReceipt as Receipt, HistoricalSeasonIdentity as Season
from fsffl.state.historical_trade import HistoricalTradeLeg, HistoricalTradeRecord
from fsffl.state.historical_trade_transition import TransitionStatus, verify_historical_trade_transition
from fsffl.state.models import (DraftPick, FaabAsset, League, LeagueRules, LeagueState,
    PickAsset, PickOwnership, Player, PlayerAsset, PlayerState, Position, Provenance, RosterEntry,
    RosterSlot, Team, TeamState)


T0=datetime(2023,9,10,11,tzinfo=UTC)
T1=T0+timedelta(hours=1)
T2=T1+timedelta(hours=1)
SEASON=Season(league_family_id="sample-family",league_id="provider:2023",season=2023)


def stamp(t):
    return Provenance(source="original-provider",retrieved_at=T2+timedelta(days=365),effective_at=t)


def roster_receipt(t,id):
    return Receipt(season=SEASON,kind=Kind.ROSTERS,evidence_id=id,
                   effective_at=t,available_at=t,availability_basis="provider_timestamp",source="original-provider")


def snapshot(*, count=8, after=False):
    teams=tuple(Team(team_id=f"team-{i}",league_id=SEASON.league_id,display_name=f"name-{i}") for i in range(count))
    pids=("p-1","p-2","p-extra")
    players=tuple(Player(player_id=p,full_name=p,position=Position.QB) for p in pids)
    ts=[]
    for i in range(count):
        owned=(["p-2"] if after else ["p-1"]) if i==0 else (["p-1"] if after else ["p-2"]) if i==1 else ["p-extra"] if i==2 else []
        ts.append(TeamState(team_id=f"team-{i}",roster=tuple(RosterEntry(player_id=p,slot=RosterSlot.BENCH) for p in owned),
                            faab_balance=99 if after and i==0 else 101 if after and i==1 else 100))
    return LeagueState(league=League(league_id=SEASON.league_id,name="Historic",season=2023,
                      rules=LeagueRules(team_count=count,roster_size=25,lineup=(),scoring=())),
        as_of=T2 if after else T0,teams=teams,team_states=tuple(ts),players=players,
        player_states=tuple(PlayerState(player_id=p.player_id,as_of=T0,provenance=stamp(T0)) for p in players),
        draft_picks=(DraftPick(pick_id="2024-pick-1",league_id=SEASON.league_id,season=2024,round=1,original_team_id="team-0"),),
        pick_ownership=(PickOwnership(pick_id="2024-pick-1",owner_team_id="team-1" if after else "team-0"),))


def states(count=8):
    return snapshot(count=count,after=False), snapshot(count=count,after=True)


def trade():
    return HistoricalTradeRecord(transaction_id="transaction-2023",league_id=SEASON.league_id,
        completed_at=T1,provenance=stamp(T1),legs=(
            HistoricalTradeLeg(team_id="team-0",sends=(PlayerAsset(player_id="p-1"),PickAsset(pick_id="2024-pick-1"),FaabAsset(amount=3))),
            HistoricalTradeLeg(team_id="team-1",sends=(PlayerAsset(player_id="p-2"),FaabAsset(amount=2))),
        ))


def inspect(before,after, transaction=None, r1=None,r2=None):
    return verify_historical_trade_transition(season=SEASON,trade=transaction or trade(),
          before=before,after=after,before_receipt=r1 or roster_receipt(before.as_of,"before"),
          after_receipt=r2 or roster_receipt(after.as_of,"after"))


@pytest.mark.parametrize("size",[8,12,16])
def test_verified_historical_trade_proves_players_picks_faab_for_any_team_count(size):
    a,b=states(size)
    result=inspect(a,b)
    assert result.status==TransitionStatus.VERIFIED and not result.differences
    assert result.before_state_id==a.state_id and result.after_state_id==b.state_id
    assert result.scope=="retrospective_facts_only"


def test_missing_post_trade_player_is_a_factual_mismatch():
    a,b=states()
    ts=list(b.team_states)
    ts[1]=ts[1].model_copy(update={"roster":()})
    b=LeagueState.model_validate(b.model_copy(update={"team_states":tuple(ts)}).model_dump())
    result=inspect(a,b)
    assert result.status==TransitionStatus.MISMATCH
    assert "wrong_posttrade_owner:player:p-1" in result.differences


def test_incorrect_pick_ownership_fails():
    a,b=states()
    b=LeagueState.model_validate(b.model_copy(update={"pick_ownership":a.pick_ownership}).model_dump())
    assert "wrong_posttrade_owner:pick:2024-pick-1" in inspect(a,b).differences


def test_unrelated_waiver_move_is_not_silently_attributed_to_trade():
    a,b=states()
    ts=list(b.team_states)
    ts[2]=ts[2].model_copy(update={"roster":()})
    b=LeagueState.model_validate(b.model_copy(update={"team_states":tuple(ts)}).model_dump())
    result=inspect(a,b)
    assert result.status==TransitionStatus.AMBIGUOUS
    assert "other_asset_change:player:p-extra" in result.differences


def test_fake_bilateral_three_team_trade_does_not_infer_receiver():
    a,b=states()
    t=trade()
    t=t.model_copy(update={"legs":t.legs+(HistoricalTradeLeg(team_id="team-2",sends=(PlayerAsset(player_id="p-extra"),)),)})
    result=inspect(a,b,transaction=t)
    assert result.status==TransitionStatus.UNSUPPORTED


def test_future_source_or_other_league_cannot_witness_trade():
    a,b=states()
    wrong=Season(league_family_id="another-family",league_id=SEASON.league_id,season=2023)
    r=roster_receipt(T0,"before").model_copy(update={"season":wrong})
    with pytest.raises(ValueError,match="exact historical season"):
        inspect(a,b,r1=r)
    unknown=Receipt(season=SEASON,kind=Kind.ROSTERS,evidence_id="unknown",effective_at=T0,source="source")
    with pytest.raises(ValueError,match="availability not verified"):
        inspect(a,b,r1=unknown)
    future=roster_receipt(T2+timedelta(hours=1),"future")
    with pytest.raises(ValueError,match="timestamp must match"):
        inspect(a,b,r1=future)


def test_rules_changes_between_snapshots_require_separate_event():
    a,b=states()
    updated_rules=LeagueRules(team_count=8,roster_size=26,lineup=(),scoring=())
    b=LeagueState.model_validate(b.model_copy(update={"league":b.league.model_copy(update={"rules":updated_rules})}).model_dump())
    with pytest.raises(ValueError,match="rules-change event"):
        inspect(a,b)


def test_historical_trade_not_before_snapshot_and_other_season_fails():
    a,b=states()
    x=trade().model_copy(update={"completed_at":T0-timedelta(hours=1)})
    with pytest.raises(ValueError,match="do not bracket"):
        inspect(a,b,transaction=x)
    x=trade().model_copy(update={"league_id":"other-league"})
    with pytest.raises(ValueError,match="another league"):
        inspect(a,b,transaction=x)

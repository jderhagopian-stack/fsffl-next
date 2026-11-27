from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from fsffl.providers.acquisition import ProviderSnapshot
from fsffl.providers.sleeper_snapshot import SleeperSnapshotNormalizer
from fsffl.providers.sleeper_rookie_window import acquire, fsffl_pick_years
from fsffl.product.trade_center_view import build_trade_center_browser_view
from fsffl.product.owner_current_season import current_owner_view
from fsffl.state.models import RookiePickWindow
from fsffl.state.serialization import load_state_json

NOW = datetime(2027, 2, 1, tzinfo=UTC)
PARENT = "1312071960615731200"


def packet(status="pre_draft", *, used=0, assigned=True, supplemental=False):
    league = dict(league_id="next", previous_league_id=PARENT, season="2027", draft_id="regular",
                  settings={"draft_rounds": 2}, roster_positions=["QB", "BN"])
    draft = dict(league_id="next", draft_id="regular", season="2027", type="linear", status=status,
                 settings={"rounds": 2, "teams": 4}, draft_order={f"u{i}": i for i in range(1, 5)} if assigned else {})
    picks = [dict(pick_no=i, draft_slot=(i-1)%4+1, round=(i-1)//4+1, draft_id="regular", player_id=str(i))
             for i in range(1, used+1)]
    rows = [draft]
    if supplemental:
        rows.extend([{**draft, "draft_id": "extra", "type": kind, "status": "complete", "metadata":{"name":"Supplemental"}} for kind in ("linear", "auction")])
    def get(path):
        return {"/league/next/drafts": rows, "/draft/regular/picks": picks, "/draft/regular/traded_picks": []}[path]
    return dict(league=league, rosters=[dict(roster_id=i, owner_id=f"u{i}", players=[], starters=[]) for i in range(1,5)],
                users=[], players={}, traded_picks=[dict(season=str(y), round=1, roster_id=2, owner_id=4)
                                                     for y in (2027, 2029)], **acquire(get, league))


def normalize(data, prior=None):
    return SleeperSnapshotNormalizer(prior_pick_window=prior).normalize_snapshot(
        ProviderSnapshot("sleeper", data["league"]["league_id"], NOW, data), as_of=NOW)


def surfaces(state, holder=4):
    team = f"{state.league.league_id}:team:{holder}"
    trade = build_trade_center_browser_view(state, focal_team_id=team)
    owner = current_owner_view(state, team, SimpleNamespace(current_season_activity=None, franchise_resume=None))
    assert trade.pick_window_notice == owner["pick_window_notice"]
    assets = {row.pick_id for row in trade.focal_team.assets if row.pick_id}
    assert assets == {row["pick_id"] for row in owner["picks"]}
    return {p.pick_id:p for p in state.draft_picks if p.pick_id in assets}


@pytest.mark.parametrize(("status","used","first","has_pick","slot"),
                         [("pre_draft",0,2027,True,None),("drafting",1,2027,True,2),
                          ("drafting",2,2027,False,None),("complete",8,2028,False,None)])
def test_linked_rollover_through_both_surfaces(status, used, first, has_pick, slot):
    state = normalize(packet(status, used=used, assigned=status!="pre_draft", supplemental=True))
    assert load_state_json(state.canonical_json()).state_id == state.state_id
    assert {p.season for p in state.draft_picks} == set(range(first, first+3))
    picks = surfaces(state)
    assert "sleeper:next:pick:2029:1:2" in picks
    pick = picks.get("sleeper:next:pick:2027:1:2")
    assert bool(pick) == has_pick
    if pick:
        assert pick.original_team_id.endswith(":2") and pick.verified_slot == slot


@pytest.mark.parametrize("problem", ["auction", "wrong_league", "wrong_year", "duplicate", "missing",
                                     "incomplete", "conflicting_scorecard"])
def test_missing_or_conflicting_never_rolls(problem):
    data = packet("complete", used=8)
    rows = data["rookie_drafts"]
    if problem == "auction": rows[0]["type"] = "auction"
    elif problem == "wrong_league": rows[0]["league_id"] = "elsewhere"
    elif problem == "wrong_year": rows[0]["season"] = "2028"
    elif problem == "duplicate": rows.append(dict(rows[0],status="pre_draft"))
    elif problem == "missing": rows.clear()
    elif problem == "incomplete": data["rookie_selections"].pop()
    else: data["rookie_selections"][0]["draft_slot"] = 2
    unresolved = normalize(data)
    assert unresolved.rookie_pick_window.status == "unresolved"
    assert not surfaces(unresolved)
    saved = normalize(data, lambda league, cutoff: RookiePickWindow(first_year=2027, status="verified", draft_season=2026) if league == f"sleeper:{PARENT}" else None)
    assert saved.rookie_pick_window.first_year == 2027
    assert saved.rookie_pick_window.status == "retained"
    assert "sleeper:next:pick:2029:1:2" in surfaces(saved)


def test_unrelated_league_and_future_renewal():
    data = packet()
    data["league"]["previous_league_id"] = "elsewhere"
    assert normalize(data).rookie_pick_window is None
    league = dict(league_id="future", season="2028", previous_league_id="next", settings={"draft_rounds":2})
    replies = {"/league/next": {"league_id":"next","previous_league_id":PARENT}, "/league/future/drafts":[]}
    assert acquire(replies.__getitem__, league)["rookie_ancestors"][0]["league_id"] == "next"
    assert fsffl_pick_years(2030, regular_draft_complete=True) == range(2031,2034)
    assert fsffl_pick_years(2030, regular_draft_complete=None) is None


def test_saved_partial_draft_cannot_rewind_or_offer_uncertain_current_picks():
    from fsffl.product.trade_center_view import owned_asset_index
    from fsffl.opportunity.trade_universe import build_team_trade_inventory, TradeSearchBounds
    saved = normalize(packet("drafting", used=2))
    restored = load_state_json(saved.canonical_json())
    def prior(league, cutoff):
        return restored.rookie_pick_window if league == restored.league.league_id else None
    for data in (packet("drafting", used=1), packet("pre_draft"), dict(packet(), rookie_drafts=[])):
        state = normalize(data, prior)
        assert state.rookie_pick_window.status == "retained"
        assert {p.season for p in state.draft_picks} == {2027,2028,2029}
        held = surfaces(state)
        assert "sleeper:next:pick:2027:1:2" not in held
        team = "sleeper:next:team:4"
        view = build_trade_center_browser_view(state, focal_team_id=team)
        offers = owned_asset_index(view)
        assert (team,"pick:sleeper:next:pick:2027:1:4") not in offers
        assert (team,"pick:sleeper:next:pick:2029:1:2") in offers
        inventory = build_team_trade_inventory(state, team_id=team, bounds=TradeSearchBounds())
        assert all(":pick:2027:" not in getattr(a,"pick_id","") for a in inventory.assets)


def test_supplemental_named_primary_and_conflicting_slot_evidence():
    data = packet("complete", used=8)
    data["rookie_drafts"][0]["metadata"] = {"name":"Supplemental draft"}
    assert normalize(data).rookie_pick_window.status == "unresolved"
    data = packet("drafting", used=1)
    data["rookie_drafts"][0]["slot_to_roster_id"] = {"1":2}
    assert normalize(data).rookie_pick_window.status == "unresolved"


def test_draft_transfer_can_identify_holder_before_slot_assignment():
    data = packet(assigned=False)
    transfer = data['traded_picks'].pop(0)
    data['rookie_transfers'] = [transfer]
    state = normalize(data)
    pick_id = "sleeper:next:pick:2027:1:2"
    assert surfaces(state)[pick_id].verified_slot is None
    data['traded_picks'].append(dict(transfer, owner_id=3))
    state = normalize(data)
    assert not any(own.pick_id == pick_id for own in state.pick_ownership)


def test_provider_probe_detects_consumed_selection_without_a_transfer():
    from fsffl.providers.sleeper_live import SleeperLiveSource

    data = packet("drafting", used=1)
    league = data["league"]
    calls = []
    def get(url):
        path = url.split("/v1")[-1]
        calls.append(path)
        endpoints = {
            "/league/next": league, "/league/next/rosters": data["rosters"],
            "/league/next/users": [], "/league/next/traded_picks": data["traded_picks"],
            "/league/next/drafts": data["rookie_drafts"], "/draft/regular/picks": data["rookie_selections"],
            "/draft/regular/traded_picks": [], "/state/nfl": {"season": "2027"},
            "/players/nfl": {},
        }
        return endpoints.get(path, [])
    source = SleeperLiveSource(http_get_json=get, clock=lambda: NOW)
    old = source.fetch_sync_probe(league_external_id="next")
    data["rookie_selections"] = packet("drafting", used=2)["rookie_selections"]
    assert source.fetch_sync_probe(league_external_id="next").fingerprint != old.fingerprint
    snapshot = source.fetch_latest(league_external_id="next")
    state = SleeperSnapshotNormalizer().normalize_snapshot(snapshot, as_of=NOW)
    assert "sleeper:next:pick:2027:1:2" not in surfaces(state)
    assert "/draft/regular/traded_picks" in calls

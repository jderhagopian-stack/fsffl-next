from dataclasses import replace

from fsffl.persistence.account_rules import AccountRuleSettingsStore
from fsffl.product.native_pick_prior_runtime import published_pick_values
from fsffl.product.trade_center_view import build_trade_center_browser_view
from fsffl.product.trade_intrinsic_evidence import bind_trade_intrinsic_values
from fsffl.state.account_rules import DraftOrderSettings, LeagueRuleChanges, apply_account_rules
from fsffl.state.models import DraftPick, PickOwnership, Provenance
from fsffl.state.serialization import load_state_json
from fsffl.state.settled_draft_order import settled_origin_order
from tests.test_account_league_rules import state as other_league
from tests.test_native_pick_prior_production import fixture, read
from tests.test_postseason_continuity import rounds, saved_state


def configured(state, metric="max_pf", tie="record"):
    repo = AccountRuleSettingsStore()
    key = state.league.league_id
    season = state.league.season
    settings = repo.prepare("owner", key, season, LeagueRuleChanges(),
        DraftOrderSettings(non_playoff_order=metric, playoff_order="elimination", tiebreak=tie),
        saved_at=state.as_of, provider_rules=state.league.rules)
    repo.save("owner", settings, expected_revision=None)
    return apply_account_rules(state, repo.get("owner", key, season))


def factual(state, totals):
    prov = Provenance(source="test-final-rosters", effective_at=state.as_of, retrieved_at=state.as_of)
    return state.model_copy(update={"final_regular_totals_week":state.league.rules.fantasy_regular_season_end_week,
        "team_states": tuple(row.model_copy(update={
        "max_points_for": value, "max_points_for_provenance": prov if value is not None else None,
        "final_regular_record": record}) for row, (value, record) in zip(state.team_states, totals, strict=True))})


def test_correction_tiebreaks_traded_pick_and_official_disagreement():
    base = saved_state(14, rounds())
    team = lambda i: next(t.team_id for t in base.teams if t.provider_refs[0].external_id == str(i))
    nonplayoff = [3, 4, 6, 7, 10, 11]
    totals = {team(i):(100+n//2, (4+n, 10-n, 0)) for n,i in enumerate(nonplayoff)}
    base = factual(base, [totals.get(r.team_id, (250, (10,4,0))) for r in base.team_states])
    pick = DraftPick(pick_id="moved", league_id=base.league.league_id, season=2026, round=2,
                     original_team_id=team(6), verified_slot=3)
    owner = PickOwnership(pick_id=pick.pick_id, owner_team_id=team(9))
    state = configured(base.model_copy(update={"draft_picks":(pick,), "pick_ownership":(owner,)}))
    def slots(s):
        return {k:r.slot for k,r in settled_origin_order(s,2026).items() if r.slot}
    assert slots(state) == {team(i):n for n,i in enumerate(nonplayoff,1)}
    assert slots(load_state_json(state.canonical_json())) == slots(state)
    def option(s):
        return build_trade_center_browser_view(s,focal_team_id=team(9)).focal_team.assets[-1]
    assert (option(state).rule_slot,option(state).official_slot,option(state).slot_disagreement)==(3,3,False)
    def corrected(**change):
        return state.model_copy(update={"team_states":tuple(r.model_copy(update=change)
            if r.team_id==team(6) else r for r in state.team_states)})
    revised=corrected(max_points_for=90)
    assert slots(revised)[team(6)]==1 and revised.state_id!=state.state_id
    assert option(revised).slot_disagreement and (option(revised).official_slot,option(revised).rule_slot)==(3,1)
    tied=corrected(final_regular_record=totals[team(7)][1])
    assert team(6) not in slots(tied) and team(7) not in slots(tied) and slots(tied)[team(10)]==5
    assert "Tied on final Max PF and regular-season record" in option(tied).detail
    assert "record is missing" in option(corrected(final_regular_record=None)).detail
    assert not slots(corrected(max_points_for=None,max_points_for_provenance=None))
    assert not slots(state.model_copy(update={"completed_through_week":13}))
    assert not slots(state.model_copy(update={"winners_bracket":()}))
    assert not slots(state.model_copy(update={"final_regular_totals_week":None}))
    assert settled_origin_order(state,2027)=={}


def test_other_league_policy_and_explicit_unsupported(other_league):
    other = other_league
    assert settled_origin_order(configured(other,"record","record_h2h_points_for"),2027)=={}
    unresolved=settled_origin_order(configured(other,"record","points_for"),2027)
    assert all(row.slot is None and "unsupported" in row.reason for row in unresolved.values())


def test_exact_curve_flows_to_trade_without_simulation_and_conflict_withholds():
    from fsffl.state.postseason import BracketGame
    from fsffl.value.native_pick_prior import lineup_capacity_signature
    from fsffl.state.models import Team, TeamState
    runtime, artifact, proposal, release=fixture()
    state=runtime.league_state
    # Four franchises, two playoff entrants, a two-round curve is unnecessary.
    key=state.league.league_id
    teams=state.teams + tuple(Team(team_id=t,league_id=key,display_name=t) for t in ("gamma","delta"))
    rows=state.team_states + tuple(TeamState(team_id=t,roster=()) for t in ("gamma","delta"))
    rules=state.league.rules.model_copy(update={"team_count":4,"playoff_team_count":2,
        "playoff_start_week":13,"fantasy_regular_season_end_week":12})
    bracket=(BracketGame(game=1,week=13,left="gamma",right="delta",left_from=None,right_from=None,
        winner=None,loser=None,left_points=None,right_points=None),)
    state=state.model_copy(update={"league":state.league.model_copy(update={"rules":rules}),"teams":teams,
        "team_states":rows,"winners_bracket":bracket,"completed_through_week":12})
    state=configured(factual(state,[(10+i,(5,7,0)) for i in range(4)]))
    release=release.model_copy(update={"team_count":4,"rules_signature":lineup_capacity_signature(rules),"slots":release.slots+tuple(
        s.model_copy(update={"rank":s.rank+2}) for s in release.slots)})
    runtime=replace(runtime,league_state=state,simulation_analytics=None)
    artifact.league_state_id=state.state_id
    projection=read(runtime,artifact,release,None)
    bound=bind_trade_intrinsic_values(runtime,proposal,projection)
    assert bound["three_year"]["side_a"]["sent_mean"]==release.slot_point(
        round_number=1,slot=1,draft_season=2027,horizon="three_year")
    assert bound["source"]["pick_sources"]["pick:alpha"]["rule_slot"]==1
    assert bound["career"]["side_a"]["sent_mean"]==240
    # Swap the holders. Both released references must still follow their origins.
    moved=state.model_copy(update={"pick_ownership":tuple(o.model_copy(update={
        "owner_team_id":"beta" if o.owner_team_id=="alpha" else "alpha"}) for o in state.pick_ownership)})
    moved_runtime=replace(runtime,league_state=moved)
    artifact.league_state_id=moved.state_id
    moved_read=read(moved_runtime,artifact,release,None)
    assert moved_read.pick_values==projection.pick_values
    assert moved_read.pick_sources["pick:alpha"]["owner_team_id"]=="beta"
    assert bind_trade_intrinsic_values(moved_runtime,proposal,moved_read)["status"]=="unavailable"
    conflict=state.model_copy(update={"draft_picks":tuple(p.model_copy(update={"verified_slot":2})
        if p.original_team_id=="alpha" else p for p in state.draft_picks)})
    for wrong_state,wrong_release in [(conflict,release),(state,release.model_copy(update={"scoring_signature":"other"}))]:
        values,_=published_pick_values(replace(runtime,league_state=wrong_state),wrong_release,None)
        assert "pick:alpha" not in values["career"]


def test_sleeper_keeps_only_settled_regular_record():
    from fsffl.providers.sleeper import SleeperNormalizer
    from tests.test_sleeper_normalizer import bundle, AS_OF
    base = bundle()
    rosters = tuple(dict(r, settings={**r.get("settings", {}), "wins": 3, "losses": 1, "ties": 0})
                    for r in base.rosters)
    def normalize(week, scored=4):
        league = dict(base.league, settings={**base.league["settings"], "playoff_week_start":5,"leg":week,"last_scored_leg":scored})
        return SleeperNormalizer().normalize(replace(base,league=league,rosters=rosters),as_of=AS_OF)
    assert all(r.final_regular_record is None for r in normalize(4).team_states)
    assert normalize(5,3).final_regular_totals_week is None
    assert all(r.final_regular_record == (3, 1, 0) for r in normalize(5).team_states)

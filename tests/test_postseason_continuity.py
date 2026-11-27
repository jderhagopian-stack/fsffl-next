"""Controlled Sleeper-shaped bracket. These are not archived official bracket rows."""
from types import SimpleNamespace

import pytest

from fsffl.providers.sleeper_live import SleeperLiveSource
from fsffl.providers.sleeper_snapshot import SleeperSnapshotNormalizer
from fsffl.state.serialization import load_state_json
from fsffl.team_utility.simulation import (
    WeeklyTeamScoringDistribution, build_regular_season_simulation_input, simulate_regular_season,
)
from fsffl.product.simulation_forecasts import require_forward_simulation_evidence


def rounds():
    return [
        dict(r=1, m=21, t1=5, t2=9, w=5, l=9),
        dict(r=1, m=32, t1=1, t2=2, w=1, l=2),
        dict(r=2, m=45, t1=8, t2=5, t2_from={"w":21}, w=8, l=5),
        dict(r=2, m=49, t1=12, t2=1, t2_from={"w":32}, w=12, l=1),
        dict(r=3, m=75, t1=8, t2=12, t1_from={"w":45}, t2_from={"w":49}, w=8, l=12, p=1),
        dict(r=3, m=70, p=3, t1_from={"l":45}, t2_from={"l":49}),
    ]


def saved_state(boundary, bracket, scores=None):
    from fsffl.forecast.in_season_orchestration import canonical_week_window
    now = canonical_week_window(2025, boundary + 1)[0]
    def fetch(url):
        suffix = url.split("/league/demo/")[-1]
        if url.endswith("/league/demo"):
            return dict(league_id="demo", name="Controlled replay", season="2025",
                        settings=dict(playoff_week_start=15, playoff_teams=6, leg=boundary+1),
                        roster_positions=["QB"],scoring_settings={"pass_yd":.04})
        if suffix == "winners_bracket":return bracket
        if suffix == "rosters":return [dict(roster_id=i,owner_id=str(i),players=[str(i)],starters=[str(i)]) for i in range(1,13)]
        if suffix == "users":return [dict(user_id=str(i),display_name=str(i)) for i in range(1,13)]
        if suffix == "traded_picks" or "/schedule/nfl/" in url:return []
        if url.endswith("/players/nfl"):return {str(i): dict(player_id=str(i), full_name=f"QB {i}", position="QB", team="KC", active=True) for i in range(1,13)}
        if url.endswith("/state/nfl"):return dict(season="2025",week=boundary+1)
        w=int(suffix.split("/")[-1])
        if scores is not None:return scores[str(w)]
        return [dict(roster_id=i,matchup_id=(i+1)//2 if w<15 else None,
                     points={15:{5:135,9:133,1:127,2:119,8:250,12:300},
                             16:{8:160,5:121,12:116,1:93},17:{8:154.75,12:104}}.get(w,{}).get(i,100+i))
                for i in range(1,13)]
    snap=SleeperLiveSource(http_get_json=fetch,clock=lambda:now).fetch_latest(league_external_id="demo")
    return SleeperSnapshotNormalizer().normalize_snapshot(snap,as_of=now)


def run(state,n=128):
    scoring=tuple(WeeklyTeamScoringDistribution(team_id=t.team_id,week=w,mean_points=100,
        stddev_points=12,model_version="fixture") for w in range(max(15,state.completed_through_week+1),18) for t in sorted(state.teams,key=lambda t:t.team_id))
    request=build_regular_season_simulation_input(state,playoff_weekly_scoring=scoring,simulation_count=n)
    return simulate_regular_season(request)


@pytest.mark.parametrize(("week","alive"),[(14,{1,2,5,8,9,12}),(15,{1,5,8,12}),(16,{8,12}),(17,{8})])
def test_first_refresh_and_restored_bracket(week,alive):
    state=saved_state(week,rounds())
    original=state.canonical_json()
    restored=load_state_json(original)
    assert restored.state_id==state.state_id
    fresh=run(state)
    assert fresh==run(restored)
    assert original==state.canonical_json()
    odds={int(t.team_id.split(":")[-1]):t for t in fresh.outcomes}
    assert {i for i,t in odds.items() if t.championship_probability>0}==alive
    assert {i for i,t in odds.items() if t.bye_probability==1}=={8,12}
    assert {i for i,t in odds.items() if t.playoff_probability==1}=={1,2,5,8,9,12}
    if week==17:
        assert odds[8].championship_probability==1
        assert (state.winners_bracket[-1].left_points,state.winners_bracket[-1].right_points)==(154.75,104.00)


@pytest.mark.parametrize("problem",["missing","wrong_winner","wrong_feeder","bye_substitution","missing_score"])
def test_inconsistent_bracket_never_authorizes_odds(problem):
    bracket=rounds()
    if problem=="missing":bracket=[]
    if problem=="wrong_winner":bracket[0].update(w=9,l=5)
    if problem=="wrong_feeder":bracket[2]["t2"]=9
    if problem=="bye_substitution":bracket[2]["t1"]=5
    state=saved_state(15,bracket)
    if problem=="missing_score":
        first,*rest=state.winners_bracket
        state=state.model_copy(update={"winners_bracket":(first.model_copy(update={"left_points":None}),*rest)})
    with pytest.raises(ValueError,match="factual completed-bracket"):
        require_forward_simulation_evidence(state,SimpleNamespace(simulation_basis="governed_ros"))
    with pytest.raises(ValueError,match="factual completed-bracket"):
        run(state)


@pytest.mark.parametrize("week", [15, 17])
def test_refresh_prepares_and_restores_exact_postseason_evidence(week):
    from fsffl.forecast.in_season_orchestration import canonical_week_window
    from fsffl.forecast.models import ForecastHorizon
    from fsffl.forecast.season_comparison import SEASON_COMPARISON_VERSION
    from fsffl.product.season_comparison_runtime import SeasonComparisonService
    from fsffl.product.webapp import _build_default_simulation
    from tests.test_bye_aware_weekly_simulation import _forecast, _state, PROV
    from tests.test_product_forecast_refresh import _evidence
    from tests.test_season_comparison import Store

    state = saved_state(week, rounds())
    start = canonical_week_window(2025, week + 1)[0]
    end = canonical_week_window(2025, 18)[1]
    provenance = PROV.model_copy(update={"retrieved_at": start, "effective_at": start})
    byes = tuple(b.model_copy(update={"season": 2025, "provenance": provenance}) for b in _state().nfl_team_byes)
    state = state.model_copy(update={"nfl_team_byes": byes})
    rows = [_forecast(p.player_id, 100, 12).model_copy(update={
        "provenance": PROV.model_copy(update={"retrieved_at": start, "effective_at": start}),
        "as_of": start, "period_start": start, "period_end": end,
        "horizon": ForecastHorizon.REST_OF_SEASON,
    }).model_dump(mode="json") for p in state.players]
    store = Store()
    service = SeasonComparisonService(persistence_store=store, builder=lambda s, **kwargs: {
        "version": SEASON_COMPARISON_VERSION, "league_state_id": s.state_id,
        "season": 2025, "as_of": start.isoformat(), "completed_through_week": week,
        "players": {}, "evidence_basis": "current_rest_of_season", "forward_forecasts": rows,
    })
    context = SimpleNamespace(user_id="u", league_state=state)
    service.prepare(context)
    fresh = service.simulation_evidence(context, _evidence())
    restored = load_state_json(state.canonical_json())
    service = SeasonComparisonService(persistence_store=store, builder=lambda *a, **kw: pytest.fail("reacquired"))
    evidence = service.simulation_evidence(SimpleNamespace(user_id="u", league_state=restored), _evidence())
    assert evidence == fresh
    result = _build_default_simulation(restored, evidence, simulation_count=128)
    assert set(result.scenario_preparation.scoring_panel_weeks) == set(range(week + 1, 18))
    alive = {int(t.team_id.split(":")[-1]) for t in result.simulation_result.outcomes if t.championship_probability}
    assert alive == ({1, 5, 8, 12} if week == 15 else {8})


def test_atlas_keeps_official_games_when_scores_conflict():
    from fsffl.product.league_atlas import build_league_atlas_payload
    from fsffl.product.runtime import UserRuntimeContext

    bracket = rounds()
    bracket[0].update(w=9, l=5)
    state = saved_state(15, bracket)
    payload = build_league_atlas_payload(UserRuntimeContext(user_id="fixture", league_state=state))
    assert len(payload["winners_bracket"]) == 5
    assert payload["winners_bracket"][0]["left_points"] == 135


def test_missing_feeder_keeps_visible_games_and_withholds_odds():
    state = saved_state(15, rounds()[1:])
    assert len(state.winners_bracket) == 4
    with pytest.raises(ValueError, match="factual completed-bracket"):
        run(state)

from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from fsffl.forecast.current_runtime import build_current_live_forecasts
from fsffl.forecast.non_qb_career_state import build_non_qb_bounded_paths
from fsffl.forecast.qb_career_state_runtime import build_qb_career_state_forecasts
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    PlayerStatus,
    Position,
    Provenance,
    ProviderRef,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)
from fsffl.value.intrinsic_v2_runtime import build_current_intrinsic_values_v2

APEX = 897.9723670871264
TARGETS = {
    "Josh Allen", "Drake Maye", "Lamar Jackson", "Sam Darnold", "Dak Prescott",
    "Bijan Robinson", "Quinshon Judkins", "Derrick Henry", "Rhamondre Stevenson", "Tyler Allgeier", "Jonathon Brooks",
    "CeeDee Lamb", "Jaxon Smith-Njigba", "Tee Higgins", "Zay Flowers", "DeVonta Smith", "KC Concepcion", "Troy Franklin",
    "Brock Bowers", "Trey McBride", "Kyle Pitts", "Dallas Goedert", "Ja'Tavion Sanders",
}


def display(raw: float) -> int:
    if raw <= 0:
        return 0
    if raw <= APEX:
        return min(9500, round(9500 * math.sqrt(raw / APEX)))
    return min(9999, round(9500 + 500 * (1 - math.exp(-(raw - APEX) / APEX))))


def integer(value, minimum=0):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    return v if v >= minimum else None


def floating(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v >= 0 else None


def build_state() -> LeagueState:
    now = datetime.now(UTC)
    with urlopen("https://api.sleeper.app/v1/players/nfl", timeout=30) as response:
        raw_players = json.load(response)
    provenance = Provenance(source="sleeper:players:nfl:current-sanity", retrieved_at=now, effective_at=now)
    positions = {"QB": Position.QB, "RB": Position.RB, "WR": Position.WR, "TE": Position.TE}
    players = []
    states = []
    for external_id, raw in raw_players.items():
        pos = positions.get(str(raw.get("position") or "").upper())
        team = str(raw.get("team") or "").upper().strip()
        if pos is None or not team:
            continue
        name = str(raw.get("full_name") or " ".join(filter(None, [raw.get("first_name"), raw.get("last_name")])) or external_id)
        pid = f"sleeper:player:{external_id}"
        players.append(Player(player_id=pid, full_name=name, position=pos, nfl_team=team, provider_refs=(ProviderRef(provider="sleeper", external_id=str(external_id)),)))
        states.append(PlayerState(
            player_id=pid,
            as_of=now,
            age_years=floating(raw.get("age")),
            experience_years=integer(raw.get("years_exp"), 0),
            draft_year=integer(raw.get("draft_year"), 1900),
            draft_round=integer(raw.get("draft_round"), 1),
            draft_number=integer(raw.get("draft_number"), 1),
            nfl_team=team,
            status=PlayerStatus.ACTIVE if str(raw.get("status") or "").lower() == "active" else PlayerStatus.UNKNOWN,
            provenance=provenance,
        ))

    teams = tuple(Team(team_id=f"t{i}", league_id="sanity", display_name=f"T{i}") for i in range(12))
    team_states = tuple(TeamState(team_id=team.team_id, roster=()) for team in teams)
    rules = LeagueRules(
        team_count=12,
        roster_size=18,
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.RB, count=2),
            LineupRequirement(slot=RosterSlot.WR, count=3),
            LineupRequirement(slot=RosterSlot.TE, count=1),
            LineupRequirement(slot=RosterSlot.FLEX, count=1),
            LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
        ),
        scoring=(
            ScoringRule(stat="pass_yd", points=0.04),
            ScoringRule(stat="pass_td", points=4.0),
            ScoringRule(stat="pass_int", points=-2.0),
            ScoringRule(stat="rush_yd", points=0.1),
            ScoringRule(stat="rush_td", points=6.0),
            ScoringRule(stat="rec", points=0.5),
            ScoringRule(stat="rec_yd", points=0.1),
            ScoringRule(stat="rec_td", points=6.0),
            ScoringRule(stat="fum_lost", points=-2.0),
        ),
    )
    league = League(league_id="sanity", name="Intrinsic sanity", season=2026, rules=rules)
    return LeagueState(
        league=league,
        as_of=now,
        teams=teams,
        team_states=team_states,
        players=tuple(players),
        player_states=tuple(states),
        provenance=(provenance,),
    )


def main():
    state = build_state()
    live = build_current_live_forecasts(state, minimum_independent_sources=2)
    state = state.model_copy(update={
        "as_of": live.evaluation_as_of,
        "player_states": tuple(ps.model_copy(update={"as_of": live.evaluation_as_of}) for ps in state.player_states),
    })
    bounded = build_non_qb_bounded_paths(state, season_forecasts=live.fantasy_point_forecasts)
    qb = build_qb_career_state_forecasts(state, season_forecasts=live.fantasy_point_forecasts)
    result = build_current_intrinsic_values_v2(
        state,
        season_forecasts=live.fantasy_point_forecasts,
        base_forecast_model_version=live.model_version,
        bounded_paths=bounded,
        qb_career_states=qb,
    )
    players = {p.player_id: p for p in state.players}
    states = {p.player_id: p for p in state.player_states}
    rows = []
    for estimate in result.estimates:
        player = players[estimate.player_id]
        if player.full_name not in TARGETS:
            continue
        path = [h.forecast_mean for h in estimate.horizons]
        sd = [h.forecast_stddev for h in estimate.horizons]
        growth_prob_note = "distribution retained; mean-only structural conversion"
        rows.append({
            "player": player.full_name,
            "position": player.position.value,
            "age": states[estimate.player_id].age_years,
            "experience": states[estimate.player_id].experience_years,
            "career_state": estimate.confidence.value,
            "y1": path[0], "y2": path[1], "y3": path[2],
            "trajectory": "growth" if path[1] > path[0] or path[2] > path[1] else "plateau" if abs(path[1]-path[0]) < 1e-6 else "decline",
            "forecast_sd": sd,
            "upside_summary": growth_prob_note,
            "continuation": estimate.raw_terminal_value,
            "pre_structural": estimate.pre_structural_fundamental_value,
            "structural_factor_realized": estimate.structural_factor,
            "structural_starter_demand": estimate.structural_starter_demand,
            "structural_effective_supply": estimate.structural_effective_supply,
            "raw_intrinsic": estimate.fundamental_value,
            "display_intrinsic": display(estimate.fundamental_value),
        })
    rows.sort(key=lambda r: (-r["raw_intrinsic"], r["player"]))
    payload = {
        "evaluation_as_of": live.evaluation_as_of.isoformat(),
        "successful_sources": list(live.successful_source_ids),
        "failed_sources": list(live.failed_sources),
        "player_count": len(result.estimates),
        "targets_found": len(rows),
        "rows": rows,
    }
    out = Path("artifacts/current-intrinsic-sanity")
    out.mkdir(parents=True, exist_ok=True)
    (out / "current_intrinsic_v6_nonlinear_sanity.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

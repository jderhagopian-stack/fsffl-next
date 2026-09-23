from __future__ import annotations

import json
from pathlib import Path

from fsffl.providers.sleeper_live import SleeperLiveSource
from fsffl.product.runtime import default_sleeper_state_loader
from fsffl.state.matchups import completed_matchups, completed_through_week

LEAGUE_ID = "1312071960615731200"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/diagnostics/league_atlas_final_acceptance_20260923"


def _number(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sleeper_split(settings, whole_key: str, decimal_key: str):
    whole = _number(settings.get(whole_key))
    decimal = _number(settings.get(decimal_key))
    if whole is None:
        return None
    return whole + ((decimal or 0.0) / 100.0)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    snapshot = SleeperLiveSource().fetch_latest(league_external_id=LEAGUE_ID)
    raw_rosters = snapshot.payload.get("rosters") or []
    state = default_sleeper_state_loader(LEAGUE_ID)

    completed = completed_matchups(state)
    pf = {team.team_id: 0.0 for team in state.teams}
    for matchup in completed:
        pf[matchup.team_a_id] += float(matchup.team_a_points or 0.0)
        pf[matchup.team_b_id] += float(matchup.team_b_points or 0.0)

    team_by_roster = {}
    for team in state.teams:
        sleeper_ref = next((ref for ref in team.provider_refs if ref.provider == "sleeper"), None)
        if sleeper_ref is not None:
            team_by_roster[int(sleeper_ref.external_id)] = team

    raw_nfl_state = snapshot.payload.get("nfl_state") or {}
    try:
        provider_completed_week = max(0, int(raw_nfl_state.get("week")) - 1)
    except (TypeError, ValueError):
        provider_completed_week = None
    raw_completed_pf_by_roster = {}
    if provider_completed_week is not None:
        for week in range(1, provider_completed_week + 1):
            for matchup in (snapshot.payload.get("matchups") or {}).get(str(week), []) or []:
                roster_id = matchup.get("roster_id")
                if roster_id is None:
                    continue
                raw_completed_pf_by_roster[int(roster_id)] = (
                    raw_completed_pf_by_roster.get(int(roster_id), 0.0)
                    + float(matchup.get("points") or 0.0)
                )

    rows = []
    for roster in sorted(raw_rosters, key=lambda item: int(item.get("roster_id") or 0)):
        roster_id = int(roster["roster_id"])
        settings = roster.get("settings") or {}
        team = team_by_roster.get(roster_id)
        ppts = _sleeper_split(settings, "ppts", "ppts_decimal")
        fpts = _sleeper_split(settings, "fpts", "fpts_decimal")
        rows.append({
            "roster_id": roster_id,
            "team_id": team.team_id if team is not None else None,
            "team_name": team.display_name if team is not None else None,
            "settings_has_ppts": "ppts" in settings,
            "settings_has_ppts_decimal": "ppts_decimal" in settings,
            "provider_ppts": ppts,
            "provider_fpts": fpts,
            "canonical_completed_pf": pf.get(team.team_id) if team is not None else None,
            "raw_provider_completed_pf": raw_completed_pf_by_roster.get(roster_id),
            "ppts_minus_fpts": (
                ppts - fpts if ppts is not None and fpts is not None else None
            ),
        })

    schedule = snapshot.payload.get("nfl_schedule") or []
    week1 = [row for row in schedule if isinstance(row, dict) and str(row.get("week")) == "1"]
    schedule_sample = []
    for row in week1[:2]:
        schedule_sample.append({key: row.get(key) for key in sorted(row) if key in {"week", "date", "time", "start_time", "kickoff", "timestamp", "season", "season_type", "home", "away", "home_team", "away_team"}})

    manifest = {
        "schema_version": "fsffl-league-atlas-final-acceptance-audit-v1",
        "captured_at": snapshot.captured_at.isoformat(),
        "league_id": state.league.league_id,
        "raw_league_leg": (snapshot.payload.get("league") or {}).get("settings", {}).get("leg"),
        "raw_nfl_state": raw_nfl_state,
        "provider_completed_week_candidate": provider_completed_week,
        "week1_schedule_sample": schedule_sample,
        "week1_earliest_date": min((str(row.get("date")) for row in week1 if row.get("date")), default=None),
        "week1_schedule_keys": sorted(week1[0].keys()) if week1 else [],
        "team_count": len(state.teams),
        "completed_through_week": completed_through_week(state),
        "completed_matchup_count": len(completed),
        "roster_count": len(rows),
        "all_rosters_have_ppts": all(row["settings_has_ppts"] for row in rows),
        "all_rosters_have_ppts_decimal": all(row["settings_has_ppts_decimal"] for row in rows),
        "all_ppts_at_least_fpts": all(
            row["provider_ppts"] is not None
            and row["provider_fpts"] is not None
            and row["provider_ppts"] + 1e-9 >= row["provider_fpts"]
            for row in rows
        ),
        "all_fpts_match_completed_pf": all(
            row["provider_fpts"] is not None
            and row["canonical_completed_pf"] is not None
            and abs(row["provider_fpts"] - row["canonical_completed_pf"]) <= 0.011
            for row in rows
        ),
        "all_fpts_match_raw_provider_completed_pf": all(
            row["provider_fpts"] is not None
            and row["raw_provider_completed_pf"] is not None
            and abs(row["provider_fpts"] - row["raw_provider_completed_pf"]) <= 0.011
            for row in rows
        ),
        "rows": rows,
        "authority_observation": (
            "Sleeper roster settings ppts/ppts_decimal are inspected as candidate "
            "provider potential-points evidence only; this audit does not promote them."
        ),
    }
    (OUT / "MAX_PF_PROVIDER_AUDIT.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

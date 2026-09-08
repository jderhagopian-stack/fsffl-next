from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from fsffl.team_utility.realized_metric import RealizedPlayerScore, WeeklyEligibleRosterScores


def normalize_sleeper_weekly_realized_scores(
    rows: Sequence[Mapping[str, Any]],
    *,
    league_id: str,
    week: int,
    as_of: datetime,
    roster_id_to_team_id: Mapping[int, str],
    eligible_player_ids_by_team: Mapping[str, tuple[str, ...]],
    model_version: str = "sleeper-weekly-realized-v1",
) -> tuple[WeeklyEligibleRosterScores, ...]:
    """Normalize Sleeper matchup player scores using upstream eligibility evidence.

    Sleeper's matchup payload can contain player-level scores, but this adapter does
    not decide whether reserve/taxi players count toward a league's Max-PF rule.
    Historical State must supply the eligible player ids for each team/week.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    output: list[WeeklyEligibleRosterScores] = []
    seen_teams: set[str] = set()

    for row in rows:
        try:
            roster_id = int(row["roster_id"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Sleeper matchup row requires roster_id") from None
        team_id = roster_id_to_team_id.get(roster_id)
        if team_id is None:
            raise ValueError("Sleeper matchup roster_id has no historical team mapping")
        if team_id in seen_teams:
            raise ValueError("Sleeper matchup payload contains duplicate team rows")
        seen_teams.add(team_id)

        eligible_external = eligible_player_ids_by_team.get(team_id)
        if eligible_external is None:
            raise ValueError("historical eligibility evidence is required for every team")
        raw_points = row.get("players_points")
        if not isinstance(raw_points, Mapping):
            raise ValueError("Sleeper matchup row requires players_points evidence")

        normalized_eligible = tuple(f"sleeper:player:{pid}" for pid in eligible_external)
        scores: list[RealizedPlayerScore] = []
        for external_id in eligible_external:
            if external_id not in raw_points:
                raise ValueError("Sleeper players_points is missing an eligible player")
            value = raw_points[external_id]
            if not isinstance(value, (int, float)):
                raise ValueError("Sleeper player score must be numeric")
            scores.append(
                RealizedPlayerScore(
                    player_id=f"sleeper:player:{external_id}",
                    points=float(value),
                )
            )

        output.append(
            WeeklyEligibleRosterScores(
                league_id=league_id,
                team_id=team_id,
                week=week,
                as_of=as_of,
                eligible_player_ids=normalized_eligible,
                scores=tuple(scores),
                model_version=model_version,
                provenance="Sleeper matchup players_points plus historical State eligibility",
            )
        )

    expected_teams = set(eligible_player_ids_by_team)
    if seen_teams != expected_teams:
        raise ValueError("Sleeper matchup payload must cover every team with eligibility evidence")
    return tuple(sorted(output, key=lambda item: item.team_id))

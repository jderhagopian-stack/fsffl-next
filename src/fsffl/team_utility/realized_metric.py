from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, LeagueRules, LineupRequirement, Player, Position, RosterSlot


_STARTER_ELIGIBILITY: dict[RosterSlot, frozenset[Position]] = {
    RosterSlot.QB: frozenset({Position.QB}),
    RosterSlot.RB: frozenset({Position.RB}),
    RosterSlot.WR: frozenset({Position.WR}),
    RosterSlot.TE: frozenset({Position.TE}),
    RosterSlot.FLEX: frozenset({Position.RB, Position.WR, Position.TE}),
    RosterSlot.SUPERFLEX: frozenset({Position.QB, Position.RB, Position.WR, Position.TE}),
    RosterSlot.K: frozenset({Position.K}),
    RosterSlot.DST: frozenset({Position.DST}),
}


class RealizedPlayerScore(FrozenModel):
    player_id: str
    points: float

    @field_validator("player_id")
    @classmethod
    def require_player_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("realized score player_id cannot be blank")
        return value


class WeeklyEligibleRosterScores(FrozenModel):
    """Provider/state-normalized realized weekly scoring evidence.

    ``eligible_player_ids`` must already reflect that league's historical roster
    eligibility (for example, taxi/IR treatment). This calculator does not infer
    eligibility from provider-specific roster fields.
    """

    league_id: str
    team_id: str
    week: Annotated[int, Field(ge=1)]
    as_of: datetime
    eligible_player_ids: tuple[str, ...]
    scores: tuple[RealizedPlayerScore, ...]
    model_version: str
    provenance: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("weekly realized metric as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_evidence(self) -> "WeeklyEligibleRosterScores":
        if any(not value.strip() for value in (self.league_id, self.team_id, self.model_version, self.provenance)):
            raise ValueError("weekly realized metric identifiers/provenance cannot be blank")
        if len(self.eligible_player_ids) != len(set(self.eligible_player_ids)):
            raise ValueError("eligible player ids must be unique")
        score_ids = [item.player_id for item in self.scores]
        if len(score_ids) != len(set(score_ids)):
            raise ValueError("realized player scores must be unique")
        if set(score_ids) != set(self.eligible_player_ids):
            raise ValueError("realized scores must cover every and only eligible player")
        return self


class WeeklyRealizedMaxPoints(FrozenModel):
    team_id: str
    week: int
    points: float
    chosen_player_ids: tuple[str, ...]


class SeasonRealizedDraftMetric(FrozenModel):
    league_id: str
    team_id: str
    metric_id: str
    total_value: float
    weeks: tuple[WeeklyRealizedMaxPoints, ...]
    as_of: datetime
    model_version: str
    provenance: str


def calculate_weekly_realized_max_points(
    evidence: WeeklyEligibleRosterScores,
    *,
    players: tuple[Player, ...],
    league_rules: LeagueRules,
) -> WeeklyRealizedMaxPoints:
    """Maximize realized points under the league's configured starting lineup."""

    players_by_id = {item.player_id: item for item in players}
    scores = {item.player_id: item.points for item in evidence.scores}
    missing_positions = [pid for pid in evidence.eligible_player_ids if pid not in players_by_id]
    if missing_positions:
        raise ValueError("player position evidence is required for every eligible player")

    slots: list[RosterSlot] = []
    for requirement in league_rules.lineup:
        if requirement.slot not in _STARTER_ELIGIBILITY:
            continue
        slots.extend([requirement.slot] * requirement.count)
    if not slots:
        raise ValueError("league has no supported starting lineup slots")

    states: dict[int, tuple[float, tuple[str, ...]]] = {0: (0.0, ())}
    for player_id in sorted(evidence.eligible_player_ids):
        position = players_by_id[player_id].position
        next_states = dict(states)
        for mask, (score, chosen) in states.items():
            for slot_index, slot in enumerate(slots):
                bit = 1 << slot_index
                if mask & bit or position not in _STARTER_ELIGIBILITY[slot]:
                    continue
                candidate = (score + scores[player_id], chosen + (player_id,))
                prior = next_states.get(mask | bit)
                if prior is None or candidate[0] > prior[0] + 1e-12 or (
                    abs(candidate[0] - prior[0]) <= 1e-12 and candidate[1] < prior[1]
                ):
                    next_states[mask | bit] = candidate
        states = next_states

    full_mask = (1 << len(slots)) - 1
    if full_mask not in states:
        raise ValueError("eligible roster cannot fill every required lineup slot")
    points, chosen = states[full_mask]
    return WeeklyRealizedMaxPoints(
        team_id=evidence.team_id,
        week=evidence.week,
        points=points,
        chosen_player_ids=chosen,
    )


def calculate_season_realized_max_points(
    weeks: tuple[WeeklyEligibleRosterScores, ...],
    *,
    players: tuple[Player, ...],
    league_rules: LeagueRules,
    metric_id: str = "max_pf",
    model_version: str = "realized-max-pf-v1",
) -> SeasonRealizedDraftMetric:
    if not weeks:
        raise ValueError("season realized metric requires weekly evidence")
    identities = {(item.league_id, item.team_id) for item in weeks}
    if len(identities) != 1:
        raise ValueError("weekly evidence must describe one league team")
    week_numbers = [item.week for item in weeks]
    if len(week_numbers) != len(set(week_numbers)):
        raise ValueError("weekly evidence must contain unique weeks")

    realized = tuple(
        calculate_weekly_realized_max_points(item, players=players, league_rules=league_rules)
        for item in sorted(weeks, key=lambda item: item.week)
    )
    league_id, team_id = next(iter(identities))
    return SeasonRealizedDraftMetric(
        league_id=league_id,
        team_id=team_id,
        metric_id=metric_id,
        total_value=sum(item.points for item in realized),
        weeks=realized,
        as_of=max(item.as_of for item in weeks),
        model_version=model_version,
        provenance="; ".join(sorted({item.provenance for item in weeks})),
    )

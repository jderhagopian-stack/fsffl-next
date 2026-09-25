from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position, Provenance, canonical_nfl_team


class ForecastHorizon(StrEnum):
    WEEK = "week"
    REST_OF_SEASON = "rest_of_season"
    FANTASY_REGULAR_SEASON = "fantasy_regular_season"
    SEASON = "season"
    MULTI_YEAR = "multi_year"


class ForecastMetric(StrEnum):
    FANTASY_POINTS = "fantasy_points"
    PASS_YARDS = "pass_yards"
    PASS_TD = "pass_td"
    INTERCEPTIONS = "interceptions"
    RUSH_YARDS = "rush_yards"
    RUSH_TD = "rush_td"
    RECEPTIONS = "receptions"
    REC_YARDS = "rec_yards"
    REC_TD = "rec_td"
    FUMBLES_LOST = "fumbles_lost"

    # Kicker raw-event authority. Provider-native fantasy points are never a
    # substitute for these scoring coordinates.
    FG_ATTEMPT = "fg_attempt"
    FG_MADE = "fg_made"
    FG_MISS = "fg_miss"
    FG_MADE_0_19 = "fg_made_0_19"
    FG_MADE_20_29 = "fg_made_20_29"
    FG_MADE_30_39 = "fg_made_30_39"
    FG_MADE_40_49 = "fg_made_40_49"
    FG_MADE_50_59 = "fg_made_50_59"
    FG_MADE_60_PLUS = "fg_made_60_plus"
    FG_MADE_50_PLUS = "fg_made_50_plus"
    FG_MISS_0_19 = "fg_miss_0_19"
    FG_MISS_20_29 = "fg_miss_20_29"
    FG_MISS_30_39 = "fg_miss_30_39"
    FG_MISS_40_49 = "fg_miss_40_49"
    FG_MISS_50_59 = "fg_miss_50_59"
    FG_MISS_60_PLUS = "fg_miss_60_plus"
    FG_MADE_YARDS = "fg_made_yards"
    FG_MADE_YARDS_OVER_30 = "fg_made_yards_over_30"
    XP_ATTEMPT = "xp_attempt"
    XP_MADE = "xp_made"
    XP_MISS = "xp_miss"

    # D/ST raw events are team-unit metrics. They are intentionally distinct
    # from similarly named player/offensive metrics.
    DST_SACK = "dst_sack"
    DST_INTERCEPTION = "dst_interception"
    DST_FUMBLE_RECOVERY = "dst_fumble_recovery"
    DST_FORCED_FUMBLE = "dst_forced_fumble"
    DST_SAFETY = "dst_safety"
    DST_BLOCKED_KICK = "dst_blocked_kick"
    DST_DEFENSIVE_TD = "dst_defensive_td"
    DST_DEFENSIVE_TWO_POINT_RETURN = "dst_defensive_two_point_return"
    DST_TEAM_ST_TD = "dst_team_st_td"
    DST_TEAM_ST_FORCED_FUMBLE = "dst_team_st_forced_fumble"
    DST_TEAM_ST_FUMBLE_RECOVERY = "dst_team_st_fumble_recovery"
    DST_INT_RETURN_YARDS = "dst_int_return_yards"
    DST_FUMBLE_RETURN_YARDS = "dst_fumble_return_yards"
    DST_BLOCKED_KICK_RETURN_YARDS = "dst_blocked_kick_return_yards"
    DST_SACK_YARDS = "dst_sack_yards"
    DST_TACKLE = "dst_tackle"
    DST_SOLO_TACKLE = "dst_solo_tackle"
    DST_ASSISTED_TACKLE = "dst_assisted_tackle"
    DST_TACKLE_FOR_LOSS = "dst_tackle_for_loss"
    DST_QB_HIT = "dst_qb_hit"
    DST_PASS_DEFENDED = "dst_pass_defended"
    DST_TEAM_ST_SOLO_TACKLE = "dst_team_st_solo_tackle"
    DST_PUNT_RETURN_YARDS = "dst_punt_return_yards"
    DST_KICK_RETURN_YARDS = "dst_kick_return_yards"
    DST_MISSED_FG_RETURN_YARDS = "dst_missed_fg_return_yards"
    DST_THREE_AND_OUT = "dst_three_and_out"
    DST_FOURTH_DOWN_STOP = "dst_fourth_down_stop"
    DST_FORCED_PUNT = "dst_forced_punt"


class PlayerForecastSubject(FrozenModel):
    """Canonical Forecast subject for an individual NFL player."""

    kind: Literal["player"] = "player"
    player_id: str
    position: Position

    @field_validator("player_id")
    @classmethod
    def require_player_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("player_id cannot be empty")
        return value

    @model_validator(mode="after")
    def reject_dst_player_subject(self) -> "PlayerForecastSubject":
        if self.position == Position.DST:
            raise ValueError("D/ST Forecast subjects must use NflTeamUnitForecastSubject")
        return self

    @property
    def roster_asset_key(self) -> str:
        return self.player_id


class NflTeamUnitForecastSubject(FrozenModel):
    """Canonical team-season Forecast subject for an NFL D/ST unit."""

    kind: Literal["nfl_team_unit"] = "nfl_team_unit"
    season: Annotated[int, Field(ge=2000)]
    nfl_team: str
    unit: Literal["DST"] = "DST"

    @field_validator("nfl_team")
    @classmethod
    def normalize_team(cls, value: str) -> str:
        return canonical_nfl_team(value)

    @property
    def position(self) -> Position:
        return Position.DST

    @property
    def roster_asset_key(self) -> str:
        return f"nfl-team-unit:{self.season}:{self.nfl_team}:{self.unit}"


ForecastSubject = Annotated[
    PlayerForecastSubject | NflTeamUnitForecastSubject,
    Field(discriminator="kind"),
]


def forecast_subject_for_roster_asset(
    *,
    player_id: str,
    position: Position,
    season: int,
    nfl_team: str | None = None,
) -> ForecastSubject:
    """Bridge current player-shaped roster state to the governed Forecast subject.

    Sleeper currently stores D/ST roster identifiers in its player namespace. This
    helper is the compatibility boundary: D/ST is converted to a canonical
    team-season unit before any Forecast observation is created.
    """

    if position == Position.DST:
        if nfl_team is None:
            raise ValueError("D/ST roster asset requires canonical nfl_team identity")
        return NflTeamUnitForecastSubject(season=season, nfl_team=nfl_team)
    return PlayerForecastSubject(player_id=player_id, position=position)


class ForecastDistribution(FrozenModel):
    mean: float
    stddev: Annotated[float, Field(ge=0)]
    p10: float | None = None
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None
    p90: float | None = None

    @model_validator(mode="after")
    def validate_quantiles(self) -> "ForecastDistribution":
        supplied = [
            self.p10,
            self.p25,
            self.p50,
            self.p75,
            self.p90,
        ]
        concrete = [value for value in supplied if value is not None]
        if concrete != sorted(concrete):
            raise ValueError(
                "forecast quantiles must be ordered p10 <= p25 <= p50 <= p75 <= p90"
            )
        return self


class ForecastObservation(FrozenModel):
    player_id: str
    position: Position
    horizon: ForecastHorizon
    metric: ForecastMetric
    period_start: datetime
    period_end: datetime
    distribution: ForecastDistribution
    source: str
    model_version: str
    as_of: datetime
    provenance: Provenance

    @field_validator("period_start", "period_end", "as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("forecast timestamps must be timezone-aware")
        return value

    @field_validator("player_id", "source", "model_version")
    @classmethod
    def require_nonempty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("forecast identifiers cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_point_in_time_semantics(self) -> "ForecastObservation":
        if self.position == Position.DST:
            raise ValueError("D/ST Forecast observations must use TeamUnitForecastObservation")
        if self.period_end <= self.period_start:
            raise ValueError("forecast period_end must be after period_start")
        if self.provenance.effective_at > self.as_of:
            raise ValueError("forecast evidence cannot postdate observation as_of")
        return self


class TeamUnitForecastObservation(FrozenModel):
    """Forecast observation for a canonical NFL team unit such as D/ST."""

    subject: NflTeamUnitForecastSubject
    horizon: ForecastHorizon
    metric: ForecastMetric
    period_start: datetime
    period_end: datetime
    distribution: ForecastDistribution
    source: str
    model_version: str
    as_of: datetime
    provenance: Provenance

    @field_validator("period_start", "period_end", "as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("forecast timestamps must be timezone-aware")
        return value

    @field_validator("source", "model_version")
    @classmethod
    def require_nonempty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("forecast identifiers cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_point_in_time_semantics(self) -> "TeamUnitForecastObservation":
        if self.period_end <= self.period_start:
            raise ValueError("forecast period_end must be after period_start")
        if self.provenance.effective_at > self.as_of:
            raise ValueError("forecast evidence cannot postdate observation as_of")
        if (
            self.metric != ForecastMetric.FANTASY_POINTS
            and not self.metric.value.startswith("dst_")
        ):
            raise ValueError("D/ST team-unit observations require D/ST raw metrics")
        return self

    @property
    def position(self) -> Position:
        return Position.DST

    @property
    def roster_asset_key(self) -> str:
        return self.subject.roster_asset_key


class ForecastBundle(FrozenModel):
    player_id: str
    as_of: datetime
    observations: tuple[ForecastObservation, ...]
    model_version: str

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_bundle_consistency(self) -> "ForecastBundle":
        for observation in self.observations:
            if observation.player_id != self.player_id:
                raise ValueError("bundle observations must match bundle player_id")
            if observation.as_of != self.as_of:
                raise ValueError("bundle observations must match bundle as_of")
        return self
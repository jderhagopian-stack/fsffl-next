from __future__ import annotations

from typing import Annotated, Mapping

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel, Position, Provenance


class CanonicalRoleEvidence(FrozenModel):
    """Provider-neutral role/opportunity facts available at the evaluation cutoff."""

    games: Annotated[float, Field(ge=0)] = 0.0
    opportunity_per_game: Annotated[float, Field(ge=0)] = 0.0
    role_band: str = "unknown"

    @field_validator("role_band")
    @classmethod
    def normalize_role_band(cls, value: str) -> str:
        normalized = value.strip().lower() or "unknown"
        return normalized


class CanonicalFootballStateEvidence(FrozenModel):
    """Source-agnostic current football facts consumed by I1.

    Raw provider status codes never enter the Forecast model. Adapters must map
    them into these factual coordinates first. Missing evidence is represented by
    explicit zero coverage / None rather than by inferred health, attachment,
    release, retirement or persistence.
    """

    player_id: str
    position: Position
    age_years: float | None = Field(default=None, ge=0)
    experience_years: int | None = Field(default=None, ge=0)

    current_fantasy_points: Annotated[float, Field(ge=0)]
    prior_fantasy_points: Annotated[float | None, Field(default=None, ge=0)] = None
    role: CanonicalRoleEvidence | None = None

    roster_weeks: Annotated[float, Field(ge=0)] = 0.0
    injury_report_weeks: Annotated[float, Field(ge=0)] = 0.0
    participation_weeks: Annotated[float, Field(ge=0)] = 0.0
    stats_weeks: Annotated[float, Field(ge=0)] = 0.0
    snap_play_weeks: Annotated[float, Field(ge=0)] = 0.0

    active_share: Annotated[float, Field(ge=0, le=1)] = 0.0
    released_share: Annotated[float, Field(ge=0, le=1)] = 0.0
    practice_share: Annotated[float, Field(ge=0, le=1)] = 0.0
    reserve_share: Annotated[float, Field(ge=0, le=1)] = 0.0

    last_status_active: bool = False
    last_status_attached: bool = False
    last_status_release: bool = False
    last_status_practice: bool = False
    last_status_reserve: bool = False

    status_change_count: Annotated[float, Field(ge=0)] = 0.0
    team_change_count: Annotated[float, Field(ge=0)] = 0.0
    active_return_count: Annotated[float, Field(ge=0)] = 0.0
    release_entry_count: Annotated[float, Field(ge=0)] = 0.0
    practice_entry_count: Annotated[float, Field(ge=0)] = 0.0
    reserve_entry_count: Annotated[float, Field(ge=0)] = 0.0

    injury_limited_weeks: Annotated[float, Field(ge=0)] = 0.0
    non_ir_injury_limited_weeks: Annotated[float, Field(ge=0)] = 0.0
    inactive_injury_limited_weeks: Annotated[float, Field(ge=0)] = 0.0
    reserve_injury_limited_weeks: Annotated[float, Field(ge=0)] = 0.0
    non_ir_injury_flag: bool = False
    inactive_injury_flag: bool = False

    roster_coverage: bool = False
    injury_coverage: bool = False
    participation_coverage: bool = False
    role_coverage: bool = False
    provenance: tuple[Provenance, ...] = ()

    @model_validator(mode="after")
    def validate_coverage(self) -> "CanonicalFootballStateEvidence":
        if self.roster_weeks > 0 and not self.roster_coverage:
            raise ValueError("positive roster_weeks requires roster_coverage")
        if self.injury_report_weeks > 0 and not self.injury_coverage:
            raise ValueError("positive injury_report_weeks requires injury_coverage")
        if self.participation_weeks > 0 and not self.participation_coverage:
            raise ValueError("positive participation_weeks requires participation_coverage")
        if self.role is not None and not self.role_coverage:
            raise ValueError("role evidence requires role_coverage")
        return self

    @property
    def rich_roster_evidence_available(self) -> bool:
        return self.roster_coverage and self.roster_weeks > 0


class ProviderStatusMapping(FrozenModel):
    """Adapter-owned mapping from provider status codes to canonical facts.

    The model sees only the canonical result. Mapping objects are explicit so a
    provider can be replaced without changing Forecast semantics.
    """

    active_codes: frozenset[str] = frozenset()
    attached_codes: frozenset[str] = frozenset()
    release_codes: frozenset[str] = frozenset()
    practice_codes: frozenset[str] = frozenset()
    reserve_codes: frozenset[str] = frozenset()

    @field_validator(
        "active_codes",
        "attached_codes",
        "release_codes",
        "practice_codes",
        "reserve_codes",
    )
    @classmethod
    def normalize_codes(cls, values: frozenset[str]) -> frozenset[str]:
        return frozenset(str(value).strip().upper() for value in values if str(value).strip())


def canonical_status_flags(
    raw_status: str | None,
    *,
    mapping: ProviderStatusMapping,
) -> Mapping[str, bool]:
    """Map one provider status into canonical facts without provider leakage."""

    if raw_status is None or not raw_status.strip():
        return {
            "active": False,
            "attached": False,
            "release": False,
            "practice": False,
            "reserve": False,
            "covered": False,
        }
    code = raw_status.strip().upper()
    return {
        "active": code in mapping.active_codes,
        "attached": code in mapping.attached_codes,
        "release": code in mapping.release_codes,
        "practice": code in mapping.practice_codes,
        "reserve": code in mapping.reserve_codes,
        "covered": code
        in (
            mapping.active_codes
            | mapping.attached_codes
            | mapping.release_codes
            | mapping.practice_codes
            | mapping.reserve_codes
        ),
    }


def coverage_summary(
    rows: tuple[CanonicalFootballStateEvidence, ...],
) -> dict[str, float | int]:
    n = len(rows)
    if n == 0:
        return {
            "players": 0,
            "rich_roster_share": 0.0,
            "role_share": 0.0,
            "injury_share": 0.0,
            "participation_share": 0.0,
            "prior_production_share": 0.0,
        }
    return {
        "players": n,
        "rich_roster_share": sum(row.rich_roster_evidence_available for row in rows) / n,
        "role_share": sum(row.role_coverage for row in rows) / n,
        "injury_share": sum(row.injury_coverage for row in rows) / n,
        "participation_share": sum(row.participation_coverage for row in rows) / n,
        "prior_production_share": sum(row.prior_fantasy_points is not None for row in rows) / n,
    }

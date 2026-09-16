from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class EvidenceProvenance:
    """Source metadata for one provider-neutral football-state observation."""

    source_family: str
    source_version: str
    effective_season: int
    observed_at: str | None = None


@dataclass(frozen=True)
class CanonicalFootballState:
    """Provider-neutral current football facts consumed by the frozen I1 candidate.

    None always means unknown/unavailable. It must never be interpreted as healthy,
    active, released, retained, or non-persistent. Raw provider status codes belong
    in provider adapters and are deliberately absent from this contract.
    """

    player_id: str
    position: str
    age_band: str
    current_state: str
    horizon: int
    current_fantasy_points: float
    experience_years: float
    prior_fantasy_points: float | None = None

    role_band: str | None = None
    opportunity_per_game: float | None = None
    games: float | None = None

    active_share: float | None = None
    released_share: float | None = None
    practice_share: float | None = None
    reserve_share: float | None = None
    last_status_active: float | None = None
    last_status_attached: float | None = None
    last_status_release: float | None = None
    last_status_practice: float | None = None
    last_status_reserve: float | None = None
    status_change_count: float | None = None
    team_change_count: float | None = None
    active_return_count: float | None = None
    release_entry_count: float | None = None
    practice_entry_count: float | None = None
    reserve_entry_count: float | None = None

    injury_report_weeks: float | None = None
    injury_limited_weeks: float | None = None
    non_ir_injury_limited_weeks: float | None = None
    non_ir_injury_flag: float | None = None
    inactive_injury_limited_weeks: float | None = None
    inactive_injury_flag: float | None = None
    reserve_injury_limited_weeks: float | None = None
    participation_weeks: float | None = None
    stats_weeks: float | None = None
    snap_play_weeks: float | None = None

    roster_evidence_coverage: bool = False
    availability_evidence_coverage: bool = False
    usage_evidence_coverage: bool = False
    participation_evidence_coverage: bool = False
    provenance: tuple[EvidenceProvenance, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.position not in {"QB", "RB", "WR", "TE"}:
            raise ValueError(f"unsupported position: {self.position}")
        if self.horizon not in {1, 2}:
            raise ValueError("frozen I1 horizon must be 1 or 2")
        if self.age_band not in {"young", "prime", "aging", "unknown"}:
            raise ValueError(f"unsupported age band: {self.age_band}")
        if self.current_state not in {"out", "depth", "usable", "starter", "premium", "elite"}:
            raise ValueError(f"unsupported career state: {self.current_state}")
        if self.current_fantasy_points < 0:
            raise ValueError("current_fantasy_points cannot be negative")
        if self.experience_years < 0:
            raise ValueError("experience_years cannot be negative")

    @property
    def has_full_i1_evidence(self) -> bool:
        # Frozen research routing used roster evidence coverage to select the rich
        # model. Availability/participation stay features within that route and
        # have their own explicit coverage indicators.
        return self.roster_evidence_coverage

    def coverage_flags(self) -> Mapping[str, bool]:
        return {
            "roster": self.roster_evidence_coverage,
            "availability": self.availability_evidence_coverage,
            "usage": self.usage_evidence_coverage,
            "participation": self.participation_evidence_coverage,
        }


def canonical_coverage_report(rows: tuple[CanonicalFootballState, ...]) -> dict[str, object]:
    n = len(rows)
    if not n:
        return {
            "players": 0,
            "full_i1_evidence": 0,
            "full_i1_evidence_share": 0.0,
            "coverage": {},
        }
    families = ("roster", "availability", "usage", "participation")
    counts = {name: sum(bool(row.coverage_flags()[name]) for row in rows) for name in families}
    full = sum(row.has_full_i1_evidence for row in rows)
    return {
        "players": n,
        "full_i1_evidence": full,
        "full_i1_evidence_share": full / n,
        "coverage": {
            name: {"count": counts[name], "share": counts[name] / n}
            for name in families
        },
    }

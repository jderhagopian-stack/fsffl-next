from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from fsffl.state.models import LeagueState, Position

from .football_state import CanonicalFootballStateEvidence, CanonicalRoleEvidence
from .integrated_i1 import I1ForecastInput, STATE_NAMES, age_band

I1_CURRENT_FACTS_SCHEMA_VERSION = "i1-current-source-facts-v1"


def _normalize_name(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", "", value.lower()).split())


@dataclass(frozen=True)
class CurrentI1SourceFact:
    source_player_id: str
    display_name: str
    position: Position
    source_season: int
    current_fantasy_points: float
    prior_fantasy_points: float | None
    age_years: float | None
    experience_years: int | None
    current_state: str
    games: float | None
    opportunity_per_game: float | None
    role_band: str | None
    source_version: str
    identity_provider: str | None = None
    identity_external_id: str | None = None

    def __post_init__(self) -> None:
        if self.source_season < 2000:
            raise ValueError("current I1 source season is invalid")
        if self.current_fantasy_points < 0:
            raise ValueError("current I1 fantasy production cannot be negative")
        if self.prior_fantasy_points is not None and self.prior_fantasy_points < 0:
            raise ValueError("prior I1 fantasy production cannot be negative")
        if self.current_state not in STATE_NAMES:
            raise ValueError("current I1 source fact has an unknown career state")
        if self.games is not None and self.games < 0:
            raise ValueError("games cannot be negative")
        if self.opportunity_per_game is not None and self.opportunity_per_game < 0:
            raise ValueError("opportunity_per_game cannot be negative")
        if self.role_band is not None and self.role_band not in {"weak", "established"}:
            raise ValueError("current I1 role band must be weak or established when covered")
        if not self.source_player_id.strip() or not self.display_name.strip() or not self.source_version.strip():
            raise ValueError("current I1 source fact identity/version cannot be blank")

    @property
    def has_role_evidence(self) -> bool:
        return (
            self.games is not None
            and self.opportunity_per_game is not None
            and self.role_band is not None
            and bool(self.role_band.strip())
        )


@dataclass(frozen=True)
class CurrentI1FactsArtifact:
    schema_version: str
    evaluation_season: int
    completed_source_season: int
    state_boundary_version: str
    source_version: str
    rows: tuple[CurrentI1SourceFact, ...]
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.schema_version != I1_CURRENT_FACTS_SCHEMA_VERSION:
            raise ValueError("unsupported current I1 facts schema")
        if self.evaluation_season != self.completed_source_season + 1:
            raise ValueError("current I1 facts must describe the immediately completed source season")
        if not self.state_boundary_version.strip() or not self.source_version.strip():
            raise ValueError("current I1 facts artifact versions cannot be blank")
        if any(row.source_season != self.completed_source_season for row in self.rows):
            raise ValueError("every current I1 source row must match the artifact completed source season")
        ids = [row.source_player_id for row in self.rows]
        if len(ids) != len(set(ids)):
            raise ValueError("current I1 source player ids must be unique")

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> "CurrentI1FactsArtifact":
        rows_raw = raw.get("rows")
        if not isinstance(rows_raw, list):
            raise ValueError("current I1 facts rows must be a list")
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("current I1 facts metadata must be a mapping")
        rows: list[CurrentI1SourceFact] = []
        for item in rows_raw:
            if not isinstance(item, Mapping):
                raise ValueError("current I1 source fact row must be a mapping")
            rows.append(
                CurrentI1SourceFact(
                    source_player_id=str(item["source_player_id"]),
                    display_name=str(item["display_name"]),
                    position=Position(str(item["position"])),
                    source_season=int(item["source_season"]),
                    current_fantasy_points=float(item["current_fantasy_points"]),
                    prior_fantasy_points=(
                        None if item.get("prior_fantasy_points") is None else float(item["prior_fantasy_points"])
                    ),
                    age_years=None if item.get("age_years") is None else float(item["age_years"]),
                    experience_years=(
                        None if item.get("experience_years") is None else int(item["experience_years"])
                    ),
                    current_state=str(item["current_state"]),
                    games=None if item.get("games") is None else float(item["games"]),
                    opportunity_per_game=(
                        None if item.get("opportunity_per_game") is None else float(item["opportunity_per_game"])
                    ),
                    role_band=None if item.get("role_band") is None else str(item["role_band"]),
                    source_version=str(item.get("source_version") or raw["source_version"]),
                    identity_provider=(
                        None if item.get("identity_provider") is None else str(item["identity_provider"])
                    ),
                    identity_external_id=(
                        None if item.get("identity_external_id") is None else str(item["identity_external_id"])
                    ),
                )
            )
        return cls(
            schema_version=str(raw["schema_version"]),
            evaluation_season=int(raw["evaluation_season"]),
            completed_source_season=int(raw["completed_source_season"]),
            state_boundary_version=str(raw["state_boundary_version"]),
            source_version=str(raw["source_version"]),
            rows=tuple(rows),
            metadata=metadata,
        )

    @classmethod
    def load(cls, path: Path) -> "CurrentI1FactsArtifact":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise ValueError("current I1 facts artifact must be a JSON object")
        return cls.from_dict(raw)


@dataclass(frozen=True)
class CurrentI1MappingResult:
    inputs: Mapping[str, tuple[I1ForecastInput, I1ForecastInput]]
    mapped_source_ids: Mapping[str, str]
    unmapped_player_ids: tuple[str, ...]
    ambiguous_player_ids: tuple[str, ...]
    source_rows_unmatched: tuple[str, ...]
    evaluation_season: int
    completed_source_season: int

    @property
    def mapped_count(self) -> int:
        return len(self.inputs)

    def target_season(self, horizon: int) -> int:
        """Return the calendar season predicted by an I1 horizon.

        I1 horizons are relative to the completed source season, not to the
        evaluation season. For an in-season evaluation, horizon 1 therefore
        targets the evaluation season itself. Callers must preserve this
        coordinate rather than relabeling horizon 1 as the following season.
        """

        if horizon not in (1, 2):
            raise ValueError("I1 current-facts horizon must be 1 or 2")
        return self.completed_source_season + horizon

    @property
    def target_seasons(self) -> tuple[int, int]:
        return (self.target_season(1), self.target_season(2))

    def target_is_after_evaluation(self, horizon: int) -> bool:
        return self.target_season(horizon) > self.evaluation_season


def map_current_i1_facts(
    league_state: LeagueState,
    artifact: CurrentI1FactsArtifact,
) -> CurrentI1MappingResult:
    """Map completed source-season facts to the live canonical player universe.

    Stable provider identity wins. Exact normalized-name + position is a fallback
    only when it resolves uniquely on both sides. Missing or ambiguous evidence is
    returned explicitly and never converted to zero production or non-persistence.

    The returned model inputs retain research-time horizon semantics: horizon h
    predicts completed_source_season + h. The mapper does not reinterpret those
    horizons relative to the live evaluation season.
    """

    if artifact.evaluation_season != league_state.league.season:
        raise ValueError("current I1 facts evaluation season does not match league season")

    by_provider: dict[tuple[str, str], list[CurrentI1SourceFact]] = {}
    by_name_position: dict[tuple[str, Position], list[CurrentI1SourceFact]] = {}
    for row in artifact.rows:
        if row.identity_provider and row.identity_external_id:
            by_provider.setdefault((row.identity_provider.lower(), row.identity_external_id), []).append(row)
        by_name_position.setdefault((_normalize_name(row.display_name), row.position), []).append(row)

    mapped: dict[str, tuple[I1ForecastInput, I1ForecastInput]] = {}
    mapped_source: dict[str, str] = {}
    ambiguous: list[str] = []
    unmapped: list[str] = []
    used_source: set[str] = set()

    for player in league_state.players:
        if player.position not in {Position.QB, Position.RB, Position.WR, Position.TE}:
            continue
        candidates: list[CurrentI1SourceFact] = []
        for ref in player.provider_refs:
            candidates.extend(
                item
                for item in by_provider.get((ref.provider.lower(), ref.external_id), [])
                if item.position == player.position
            )
        candidates = list({item.source_player_id: item for item in candidates}.values())
        if not candidates:
            candidates = by_name_position.get((_normalize_name(player.full_name), player.position), [])
        if len(candidates) != 1:
            (ambiguous if len(candidates) > 1 else unmapped).append(player.player_id)
            continue
        source = candidates[0]
        evidence = _canonical_evidence(player.player_id, source)
        band = age_band(player.position, source.age_years)
        mapped[player.player_id] = (
            I1ForecastInput(
                position=player.position,
                age_band=band,
                current_state=source.current_state,
                horizon=1,
                current_points=source.current_fantasy_points,
                prior_points=source.prior_fantasy_points,
                experience_years=source.experience_years,
                evidence=evidence,
            ),
            I1ForecastInput(
                position=player.position,
                age_band=band,
                current_state=source.current_state,
                horizon=2,
                current_points=source.current_fantasy_points,
                prior_points=source.prior_fantasy_points,
                experience_years=source.experience_years,
                evidence=evidence,
            ),
        )
        mapped_source[player.player_id] = source.source_player_id
        used_source.add(source.source_player_id)

    return CurrentI1MappingResult(
        inputs=mapped,
        mapped_source_ids=mapped_source,
        unmapped_player_ids=tuple(sorted(unmapped)),
        ambiguous_player_ids=tuple(sorted(ambiguous)),
        source_rows_unmatched=tuple(
            sorted(row.source_player_id for row in artifact.rows if row.source_player_id not in used_source)
        ),
        evaluation_season=artifact.evaluation_season,
        completed_source_season=artifact.completed_source_season,
    )


def _canonical_evidence(player_id: str, row: CurrentI1SourceFact) -> CanonicalFootballStateEvidence:
    role = None
    if row.has_role_evidence:
        role = CanonicalRoleEvidence(
            games=float(row.games),
            opportunity_per_game=float(row.opportunity_per_game),
            role_band=str(row.role_band),
        )
    return CanonicalFootballStateEvidence(
        player_id=player_id,
        position=row.position,
        age_years=row.age_years,
        experience_years=row.experience_years,
        current_fantasy_points=row.current_fantasy_points,
        prior_fantasy_points=row.prior_fantasy_points,
        role=role,
        role_coverage=role is not None,
        # Rich evidence is deliberately absent from the completed-source fact
        # artifact unless a separately governed canonical provider supplies it.
        roster_coverage=False,
        injury_coverage=False,
        participation_coverage=False,
    )

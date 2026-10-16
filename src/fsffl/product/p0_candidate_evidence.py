"""Point-in-time feature assembly for players outside the frozen P0 benchmark.

The fitted P0 package and its 335 reference rows are immutable.  This module
reuses those rows as the empirical percentile coordinate and assembles an
additional player's model row from already-governed Year-1 and history inputs.
It intentionally does not fetch, fit, impute, or replace source evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Mapping, Sequence

from fsffl.state.models import LeagueState

from .p0_forecast_runtime import P0SourceRow, frozen_p0_source_rows

P0_ACCEPTED_SOURCE_STATE_AUTHORITY_SHA256 = (
    "51a6a892e9a19e52b0ab8d2ac7f90b2850c199254f3021db0b5a989efdc107d5"
)


@dataclass(frozen=True)
class P0CandidateFacts:
    """Accepted upstream facts required by the unchanged P0 feature schema.

    Values must come from canonical identity, point-in-time age/experience, and
    the retained historical production panel.  Missing history is represented
    with the model's existing missingness flags; missing identity, age, or
    experience is an authority failure and must be reported by the caller.
    """

    player_id: str
    current_player_id: str
    player_name: str
    position: str
    age: float
    experience: int
    mapping_status: str
    historical_gsis_id: str | None
    history_status: str
    standard_y1_points: float
    connected_league_y1_points: float
    prior1_points: float | None
    prior1_coverage: int
    source_role_band: str
    games: float | None
    opportunity_per_game: float | None
    prior_age_state_resid_z: float | None
    prior2_coverage: int
    prior2_mean_age_state_z: float | None
    prior2_gap_age_state_z: float | None
    facts_as_of: datetime
    facts_source_version: str
    facts_digest: str


@dataclass(frozen=True)
class P0SourceStateAuthority:
    """Accepted point thresholds used by the source-generation workflow.

    ``artifact_sha256`` is the digest of the canonical threshold artifact bytes.
    The expected digest is held by the deployment/configuration layer so this
    adapter never makes up state boundaries.
    """

    thresholds_by_position: Mapping[str, tuple[float, ...]]
    artifact_sha256: str

    @classmethod
    def from_artifact_bytes(cls, artifact_bytes: bytes) -> "P0SourceStateAuthority":
        digest = hashlib.sha256(artifact_bytes).hexdigest()
        if digest != P0_ACCEPTED_SOURCE_STATE_AUTHORITY_SHA256:
            raise ValueError("P0 source-state threshold authority digest mismatch")
        try:
            artifact = json.loads(artifact_bytes)
            boundaries = artifact["boundaries"]
            thresholds = {
                str(position): tuple(float(value) for value in row["thresholds"])
                for position, row in boundaries.items()
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("P0 source-state threshold artifact schema is invalid") from exc
        if any(
            len(values) != 4
            or any(not math.isfinite(value) for value in values)
            or tuple(sorted(values)) != values
            for values in thresholds.values()
        ):
            raise ValueError("P0 source-state threshold artifact has invalid cutpoints")
        return cls(thresholds_by_position=thresholds, artifact_sha256=digest)


# Exact original research input, recovered from the September 19 artifact and
# verified against the accepted provenance SHA-256. Embedded so deployment does
# not depend on a local research checkout or a runtime filesystem path.
P0_ACCEPTED_SOURCE_STATE_BOUNDARIES_JSON = r'''{
  "schema_version": "fsffl-redevelopment-current-boundaries-v1",
  "basis": "completed historical fantasy points strictly before 2026",
  "boundaries": {
    "QB": {
      "centers": [
        1.2764534917314387,
        9.269988850762617,
        32.55087507864474,
        95.45507040029189,
        244.05177868114126
      ],
      "thresholds": [
        5.2732211712470285,
        20.910431964703676,
        64.0029727394683,
        169.75342454071657
      ]
    },
    "RB": {
      "centers": [
        1.6817447725918724,
        8.352437786972093,
        23.715673921179597,
        64.14175327237696,
        169.22006024104235
      ],
      "thresholds": [
        5.017091279781983,
        16.034055854075845,
        43.92871359677828,
        116.68090675670965
      ]
    },
    "WR": {
      "centers": [
        1.8918103288781487,
        8.855446670353974,
        25.656202859963766,
        61.26342926896892,
        136.17254284122106
      ],
      "thresholds": [
        5.3736284996160615,
        17.25582476515887,
        43.459816064466345,
        98.717986055095
      ]
    },
    "TE": {
      "centers": [
        1.4383214899573071,
        6.053636229700034,
        15.567346340958311,
        38.26483287198442,
        93.18343279094003
      ],
      "thresholds": [
        3.7459788598286705,
        10.810491285329173,
        26.916089606471363,
        65.72413283146223
      ]
    }
  }
}
'''


def accepted_p0_source_state_authority() -> P0SourceStateAuthority:
    """Load the original, digest-verified source-state cutpoints without fitting."""
    return P0SourceStateAuthority.from_artifact_bytes(
        P0_ACCEPTED_SOURCE_STATE_BOUNDARIES_JSON.encode("utf-8")
    )


def _current_state(points: float, thresholds: Sequence[float]) -> str:
    if points <= 0:
        return "out"
    state_index = 0
    while state_index < len(thresholds) and points > thresholds[state_index]:
        state_index += 1
    return ("depth", "usable", "starter", "premium", "elite")[state_index]


def _benchmark_percentile(points: float, values: Sequence[float]) -> float:
    """Extend the accepted average-rank percentile to one new observation."""

    if not values:
        raise ValueError("P0 percentile benchmark is empty")
    less = sum(value < points for value in values)
    equal = sum(value == points for value in values)
    # pandas rank(method='average') - .5, divided by n, as used to create P0.
    return (less + equal / 2.0) / len(values)


def build_p0_candidate_source_rows(
    *,
    league_state: LeagueState,
    candidate_facts: Mapping[str, P0CandidateFacts],
    source_state_authority: P0SourceStateAuthority,
    reference_rows: Sequence[P0SourceRow] | None = None,
    evaluation_as_of: datetime | None = None,
) -> dict[str, P0SourceRow]:
    """Assemble source rows for exact-State non-reference players.

    Reference rows are read-only. New player percentiles are evaluated against
    the frozen benchmark distribution so a request for one additional player
    cannot perturb any of the 335 accepted inputs or depend on request order.
    The same existing P0 scorer consumes the returned rows.
    """

    if source_state_authority.artifact_sha256 != P0_ACCEPTED_SOURCE_STATE_AUTHORITY_SHA256:
        raise ValueError("P0 source-state threshold authority digest mismatch")
    cutoff = evaluation_as_of or league_state.as_of
    if cutoff.tzinfo is None:
        raise ValueError("P0 candidate evaluation cutoff must be timezone-aware")
    cutoff = cutoff.astimezone(UTC)
    canonical = {
        player.player_id: player
        for player in league_state.players
        if player.position.value in {"QB", "RB", "WR", "TE"}
    }
    references = tuple(reference_rows or frozen_p0_source_rows())
    # Frozen rows retain legacy current_player_id encoding; compare canonical IDs.
    ref_ids = {row.player_id for row in references}
    if len(references) != 335 or len(ref_ids) != 335:
        raise ValueError("P0 benchmark must remain exactly 335 unique reference players")
    by_position: dict[str, list[float]] = {}
    by_cell: dict[tuple[str, str], list[float]] = {}
    for row in references:
        by_position.setdefault(row.position, []).append(row.standard_y1_points)
        by_cell.setdefault((row.position, row.source_state), []).append(row.standard_y1_points)

    built: dict[str, P0SourceRow] = {}
    for player_id, facts in sorted(candidate_facts.items()):
        state_player = canonical.get(player_id)
        if state_player is None:
            raise ValueError(
                f"P0 candidate is outside exact State or unsupported position: {player_id}"
            )
        if player_id in ref_ids:
            raise ValueError(f"P0 candidate cannot replace frozen benchmark row: {player_id}")
        if facts.player_id != player_id or facts.current_player_id != player_id:
            raise ValueError(f"P0 candidate canonical identity mismatch: {player_id}")
        if facts.position != state_player.position.value:
            raise ValueError(f"P0 candidate position mismatch: {player_id}")
        if facts.facts_as_of.tzinfo is None or facts.facts_as_of.astimezone(UTC) > cutoff:
            raise ValueError(f"P0 candidate evidence is after evaluation cutoff: {player_id}")
        if (
            not facts.facts_source_version
            or len(facts.facts_digest) != 64
            or any(
                character not in "0123456789abcdef"
                for character in facts.facts_digest.lower()
            )
        ):
            raise ValueError(f"P0 candidate facts lack version/digest: {player_id}")
        # Fantasy scoring can legitimately be negative (e.g. a fumble with
        # minimal production). Keep the signed governed input. P0 itself owns
        # its accepted nonnegative log-feature transformation.
        numeric = (facts.age, facts.standard_y1_points, facts.connected_league_y1_points)
        if any(not math.isfinite(float(value)) for value in numeric):
            raise ValueError(f"P0 candidate has non-finite required facts: {player_id}")
        if (
            facts.age < 0
            or facts.experience < 0
        ):
            raise ValueError(f"P0 candidate has invalid age, experience, or Y1: {player_id}")
        thresholds = source_state_authority.thresholds_by_position.get(facts.position)
        if thresholds is None or len(thresholds) != 4:
            raise ValueError(f"P0 source-state thresholds unavailable for {facts.position}")
        if any(not math.isfinite(float(value)) for value in thresholds):
            raise ValueError(f"P0 source-state thresholds are invalid for {facts.position}")
        source_state = _current_state(facts.standard_y1_points, thresholds)
        position_values = by_position.get(facts.position, [])
        state_values = by_cell.get((facts.position, source_state), [])
        if not position_values:
            raise ValueError(
                "P0 benchmark percentile cell unavailable: "
                f"{facts.position}/{source_state}"
            )
        career_stage = (
            "developmental" if facts.experience <= 3 else
            "established" if facts.experience <= 8 else "veteran"
        )
        age_band = (
            "young" if facts.age <= (25 if facts.position == "QB" else 22) else
            "prime" if facts.age <= (31 if facts.position == "QB" else 27) else "aging"
        )
        digest_payload = {
            "facts": facts.__dict__,
            "source_state_authority": source_state_authority.artifact_sha256,
            "reference_source_sha256": hashlib.sha256(
                json.dumps(
                    [
                        (row.current_player_id, row.standard_y1_points, row.source_state)
                        for row in references
                    ],
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
        }
        evidence_digest = hashlib.sha256(
            json.dumps(digest_payload, sort_keys=True, default=str, separators=(",", ":")).encode()
        ).hexdigest()
        built[player_id] = P0SourceRow(
            player_id=player_id,
            current_player_id=player_id,
            player_name=facts.player_name,
            position=facts.position,
            age=float(facts.age),
            experience=int(facts.experience),
            career_stage=career_stage,
            age_band=age_band,
            mapping_status=facts.mapping_status,
            historical_gsis_id=facts.historical_gsis_id,
            history_status=facts.history_status,
            standard_y1_points=float(facts.standard_y1_points),
            connected_league_y1_points=float(facts.connected_league_y1_points),
            source_state=source_state,
            prior1_points=facts.prior1_points,
            prior1_coverage=int(facts.prior1_coverage),
            source_role_band=facts.source_role_band,
            games=facts.games,
            opportunity_per_game=facts.opportunity_per_game,
            prior_age_state_resid_z=facts.prior_age_state_resid_z,
            prior2_coverage=int(facts.prior2_coverage),
            prior2_mean_age_state_z=facts.prior2_mean_age_state_z,
            prior2_gap_age_state_z=facts.prior2_gap_age_state_z,
            source_percentile=_benchmark_percentile(
                float(facts.standard_y1_points), position_values
            ),
            # An unobserved position/state cell has no empirical percentile.
            # Preserve missingness: the accepted P0 feature builder already
            # omits percentile terms for a non-finite/missing observation.
            # Never substitute another cell, invent a median, or alter the
            # accepted source-state thresholds to manufacture a benchmark.
            state_percentile=(
                _benchmark_percentile(float(facts.standard_y1_points), state_values)
                if state_values else None
            ),
            evidence_as_of=facts.facts_as_of.astimezone(UTC).isoformat(),
            evidence_source_version=facts.facts_source_version,
            evidence_sha256=evidence_digest,
        )
    return built


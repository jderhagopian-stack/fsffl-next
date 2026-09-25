from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from statistics import median

from fsffl.providers.current_projection_rows import CurrentProjectionSnapshot
from fsffl.state.models import LeagueRules, LineupRequirement, Position, RosterSlot, ScoringRule

from .league_scoring import derive_league_fantasy_point_forecasts
from .models import ForecastHorizon, ForecastMetric, ForecastObservation
from .season_uncertainty import SEASON_FANTASY_POINT_ERROR_CALIBRATION


CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION = (
    "current-projection-health-v4:league-agnostic-offense-scale-integrity"
)
LEGACY_COMPATIBLE_PROJECTION_HEALTH_CONTRACT_VERSIONS = frozenset(
    {
        "current-projection-health-v3:revision-agnostic-scale-integrity",
        CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
    }
)

# Source-health scoring is intentionally league-agnostic. It exists only to compare
# provider dataset scale across the same ordinary offensive coordinates; target
# league K/DST, bonus, or custom scoring must never decide whether canonical raw
# QB/RB/WR/TE evidence is healthy enough to enter the shared ensemble.
_SOURCE_HEALTH_RULES = LeagueRules(
    team_count=2,
    roster_size=4,
    lineup=(
        LineupRequirement(slot=RosterSlot.QB, count=1),
        LineupRequirement(slot=RosterSlot.RB, count=1),
        LineupRequirement(slot=RosterSlot.WR, count=1),
        LineupRequirement(slot=RosterSlot.TE, count=1),
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
    ),
)

# The generalized scale threshold is not fitted to any current player or provider.
# It is anchored to the largest already-promoted position-level relative RMSE from
# the retained 2024-2025 multi-source historical Forecast benchmark. A single
# player's forecast can miss by that scale; a broad median shift across many
# players and multiple positions should not. Using the largest promoted RMSE makes
# this gate deliberately conservative.
REVISION_AGNOSTIC_SCALE_RATIO_THRESHOLD = 1.0 + max(
    item.relative_rmse
    for item in SEASON_FANTASY_POINT_ERROR_CALIBRATION.values()
)
REVISION_AGNOSTIC_MIN_COMPARABLE_PLAYERS = 16
REVISION_AGNOSTIC_MIN_PLAYERS_PER_POSITION = 4
REVISION_AGNOSTIC_MIN_POSITIONS = 3


def build_source_health_fantasy_point_forecasts(
    observations: tuple[ForecastObservation, ...],
    *,
    source: str,
) -> tuple[ForecastObservation, ...]:
    """Score a fixed portable offensive fingerprint for provider scale health only."""

    return derive_league_fantasy_point_forecasts(
        observations,
        rules=_SOURCE_HEALTH_RULES,
        source=source,
        model_version=CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
    )


@dataclass(frozen=True)
class RevisionAgnosticScaleHealth:
    disposition: str
    reason: str
    reference_id: str
    comparable_player_count: int
    ratio_threshold: float
    overall_median_ratio: float | None
    position_median_ratios: tuple[tuple[str, float], ...]
    eligible_position_count: int
    inflated_position_count: int


def _season_fantasy_point_map(
    observations: tuple[ForecastObservation, ...],
) -> dict[str, ForecastObservation]:
    return {
        item.player_id: item
        for item in observations
        if item.metric == ForecastMetric.FANTASY_POINTS
        and item.horizon == ForecastHorizon.SEASON
        and item.position in {
            Position.QB,
            Position.RB,
            Position.WR,
            Position.TE,
        }
    }


def evaluate_revision_agnostic_scale_health(
    candidate: tuple[ForecastObservation, ...],
    reference: tuple[ForecastObservation, ...],
    *,
    reference_id: str,
) -> RevisionAgnosticScaleHealth:
    """Detect broad unseen projection-scale inflation without player caps.

    The comparison is provider/dataset level. It uses the median multiplicative
    shift across canonically matched season fantasy-point forecasts and requires
    the same shift across multiple offensive positions. No individual row is
    clipped or repaired, and no provider name participates in the rule.
    """

    candidate_by_player = _season_fantasy_point_map(candidate)
    reference_by_player = _season_fantasy_point_map(reference)
    by_position: dict[Position, list[float]] = {
        Position.QB: [],
        Position.RB: [],
        Position.WR: [],
        Position.TE: [],
    }
    all_ratios: list[float] = []
    for player_id in sorted(set(candidate_by_player) & set(reference_by_player)):
        current = candidate_by_player[player_id]
        prior = reference_by_player[player_id]
        if current.position != prior.position:
            continue
        denominator = float(prior.distribution.mean)
        numerator = float(current.distribution.mean)
        if denominator <= 0.0 or numerator < 0.0:
            continue
        ratio = numerator / denominator
        all_ratios.append(ratio)
        by_position[current.position].append(ratio)

    position_medians = tuple(
        sorted(
            (
                (position.value, float(median(values)))
                for position, values in by_position.items()
                if len(values) >= REVISION_AGNOSTIC_MIN_PLAYERS_PER_POSITION
            ),
            key=lambda item: item[0],
        )
    )
    comparable = len(all_ratios)
    overall = float(median(all_ratios)) if all_ratios else None
    eligible_positions = len(position_medians)
    inflated_positions = sum(
        1
        for _position, value in position_medians
        if value > REVISION_AGNOSTIC_SCALE_RATIO_THRESHOLD
    )

    evaluable = (
        comparable >= REVISION_AGNOSTIC_MIN_COMPARABLE_PLAYERS
        and eligible_positions >= REVISION_AGNOSTIC_MIN_POSITIONS
    )
    quarantined = bool(
        evaluable
        and overall is not None
        and overall > REVISION_AGNOSTIC_SCALE_RATIO_THRESHOLD
        and inflated_positions >= REVISION_AGNOSTIC_MIN_POSITIONS
    )
    if quarantined:
        disposition = "quarantined"
        reason = (
            "broad season-projection scale inflation exceeds the governed "
            "historical-error tolerance across multiple positions"
        )
    elif evaluable:
        disposition = "accepted"
        reason = (
            "broad projection scale is within the governed historical-error "
            "tolerance across the comparable multi-position cohort"
        )
    else:
        disposition = "not_evaluable"
        reason = (
            "insufficient comparable multi-position season fantasy-point evidence "
            "for the revision-agnostic scale check"
        )
    return RevisionAgnosticScaleHealth(
        disposition=disposition,
        reason=reason,
        reference_id=reference_id,
        comparable_player_count=comparable,
        ratio_threshold=REVISION_AGNOSTIC_SCALE_RATIO_THRESHOLD,
        overall_median_ratio=overall,
        position_median_ratios=position_medians,
        eligible_position_count=eligible_positions,
        inflated_position_count=inflated_positions,
    )


@dataclass(frozen=True)
class ProjectionContentWitness:
    player_name: str
    position: str
    nfl_team: str
    stats: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class CurrentProjectionHealthIncident:
    provider: str
    source_version: str
    content_fingerprint_sha256: str
    witness_rows: tuple[ProjectionContentWitness, ...]
    incident_id: str
    evidence_note: str


def _witness(
    player_name: str,
    position: str,
    nfl_team: str,
    **stats: float,
) -> ProjectionContentWitness:
    return ProjectionContentWitness(
        player_name=player_name,
        position=position,
        nfl_team=nfl_team,
        stats=tuple(sorted((key, float(value)) for key, value in stats.items())),
    )


# The exact full 562-row malformed payload was not durably preserved. The completed
# numerical trace did, however, preserve exact pre-normalization CurrentProjectionSnapshot
# stat values for this 12-player cross-position sample. The incident fingerprint below is
# therefore a bounded content-witness signature over only those preserved row/field values.
# It is intentionally independent of capture/effective timestamps, row ordering, and row
# count. It must not be described as a hash of the full provider payload.
_RAZZBALL_20260920_WITNESSES = (
    _witness(
        "Josh Allen",
        "QB",
        "BUF",
        pass_int=22.8,
        pass_td=47.9,
        pass_yd=7682.0,
        rec=0.0,
        rec_td=0.0,
        rec_yd=0.0,
        rush_td=21.9,
        rush_yd=1134.0,
    ),
    _witness(
        "Dak Prescott",
        "QB",
        "DAL",
        pass_int=16.2,
        pass_td=49.3,
        pass_yd=7934.0,
        rec=0.0,
        rec_td=0.0,
        rec_yd=0.0,
        rush_td=6.0,
        rush_yd=459.0,
    ),
    _witness(
        "Deshaun Watson",
        "QB",
        "CLE",
        pass_int=23.6,
        pass_td=41.5,
        pass_yd=7314.0,
        rec=0.0,
        rec_td=0.0,
        rec_yd=0.0,
        rush_td=2.4,
        rush_yd=465.0,
    ),
    _witness(
        "Jahmyr Gibbs",
        "RB",
        "DET",
        pass_int=0.0,
        pass_td=0.0,
        pass_yd=0.0,
        rec=119.0,
        rec_td=4.7,
        rec_yd=991.0,
        rush_td=22.7,
        rush_yd=2665.0,
    ),
    _witness(
        "Tony Pollard",
        "RB",
        "TEN",
        pass_int=0.0,
        pass_td=0.0,
        pass_yd=0.0,
        rec=51.0,
        rec_td=1.0,
        rec_yd=347.0,
        rush_td=10.0,
        rush_yd=2234.0,
    ),
    _witness(
        "Tyjae Spears",
        "RB",
        "TEN",
        pass_int=0.0,
        pass_td=0.0,
        pass_yd=0.0,
        rec=67.0,
        rec_td=3.0,
        rec_yd=544.0,
        rush_td=8.0,
        rush_yd=746.0,
    ),
    _witness(
        "Puka Nacua",
        "WR",
        "LAR",
        pass_int=0.0,
        pass_td=0.0,
        pass_yd=0.0,
        rec=223.0,
        rec_td=17.0,
        rec_yd=2926.0,
        rush_td=0.9,
        rush_yd=114.0,
    ),
    _witness(
        "CeeDee Lamb",
        "WR",
        "DAL",
        pass_int=0.0,
        pass_td=0.0,
        pass_yd=0.0,
        rec=171.0,
        rec_td=12.0,
        rec_yd=2276.0,
        rush_td=0.2,
        rush_yd=22.0,
    ),
    _witness(
        "Matthew Golden",
        "WR",
        "GB",
        pass_int=0.0,
        pass_td=0.0,
        pass_yd=0.0,
        rec=111.0,
        rec_td=6.5,
        rec_yd=1427.0,
        rush_td=1.3,
        rush_yd=173.0,
    ),
    _witness(
        "Brock Bowers",
        "TE",
        "LV",
        pass_int=0.0,
        pass_td=0.0,
        pass_yd=0.0,
        rec=124.0,
        rec_td=8.5,
        rec_yd=1279.0,
        rush_td=0.1,
        rush_yd=15.0,
    ),
    _witness(
        "Kyle Pitts",
        "TE",
        "ATL",
        pass_int=0.0,
        pass_td=0.0,
        pass_yd=0.0,
        rec=138.0,
        rec_td=6.5,
        rec_yd=1366.0,
        rush_td=0.0,
        rush_yd=0.0,
    ),
    _witness(
        "Dallas Goedert",
        "TE",
        "PHI",
        pass_int=0.0,
        pass_td=0.0,
        pass_yd=0.0,
        rec=122.0,
        rec_td=12.0,
        rec_yd=1236.0,
        rush_td=0.0,
        rush_yd=0.0,
    ),
)



_RAZZBALL_20260921_WITNESSES = (
    _witness(
        "Josh Allen", "QB", "BUF",
        pass_int=22.8, pass_td=48.0, pass_yd=7684.0,
        rec=0.0, rec_td=0.0, rec_yd=0.0,
        rush_td=22.0, rush_yd=1134.0,
    ),
    _witness(
        "Dak Prescott", "QB", "DAL",
        pass_int=16.2, pass_td=49.3, pass_yd=7939.0,
        rec=0.0, rec_td=0.0, rec_yd=0.0,
        rush_td=6.0, rush_yd=459.0,
    ),
    _witness(
        "Deshaun Watson", "QB", "CLE",
        pass_int=23.6, pass_td=41.6, pass_yd=7320.0,
        rec=0.0, rec_td=0.0, rec_yd=0.0,
        rush_td=2.4, rush_yd=466.0,
    ),
    _witness(
        "Jahmyr Gibbs", "RB", "DET",
        pass_int=0.0, pass_td=0.0, pass_yd=0.0,
        rec=119.0, rec_td=4.7, rec_yd=989.0,
        rush_td=22.7, rush_yd=2665.0,
    ),
    _witness(
        "Tony Pollard", "RB", "TEN",
        pass_int=0.0, pass_td=0.0, pass_yd=0.0,
        rec=50.0, rec_td=1.0, rec_yd=346.0,
        rush_td=9.9, rush_yd=2227.0,
    ),
    _witness(
        "Tyjae Spears", "RB", "TEN",
        pass_int=0.0, pass_td=0.0, pass_yd=0.0,
        rec=68.0, rec_td=3.0, rec_yd=547.0,
        rush_td=8.0, rush_yd=748.0,
    ),
    _witness(
        "Puka Nacua", "WR", "LAR",
        pass_int=0.0, pass_td=0.0, pass_yd=0.0,
        rec=217.0, rec_td=16.5, rec_yd=2840.0,
        rush_td=0.8, rush_yd=109.0,
    ),
    _witness(
        "CeeDee Lamb", "WR", "DAL",
        pass_int=0.0, pass_td=0.0, pass_yd=0.0,
        rec=171.0, rec_td=12.0, rec_yd=2275.0,
        rush_td=0.2, rush_yd=22.0,
    ),
    _witness(
        "Matthew Golden", "WR", "GB",
        pass_int=0.0, pass_td=0.0, pass_yd=0.0,
        rec=112.0, rec_td=6.5, rec_yd=1428.0,
        rush_td=1.3, rush_yd=173.0,
    ),
    _witness(
        "Brock Bowers", "TE", "LV",
        pass_int=0.0, pass_td=0.0, pass_yd=0.0,
        rec=124.0, rec_td=8.5, rec_yd=1283.0,
        rush_td=0.1, rush_yd=15.0,
    ),
    _witness(
        "Kyle Pitts", "TE", "ATL",
        pass_int=0.0, pass_td=0.0, pass_yd=0.0,
        rec=136.0, rec_td=6.3, rec_yd=1341.0,
        rush_td=0.0, rush_yd=0.0,
    ),
    _witness(
        "Dallas Goedert", "TE", "PHI",
        pass_int=0.0, pass_td=0.0, pass_yd=0.0,
        rec=122.0, rec_td=12.0, rec_yd=1235.0,
        rush_td=0.0, rush_yd=0.0,
    ),
)


_KNOWN_BAD_CURRENT_REVISIONS = (
    CurrentProjectionHealthIncident(
        provider="razzball",
        source_version="razzball-season-projections-html-v3:horizon-isolated",
        content_fingerprint_sha256=(
            "0545b6c585712165997dca191169596d000aa30435f4e2ccde6d3f55c6877e3d"
        ),
        witness_rows=_RAZZBALL_20260920_WITNESSES,
        incident_id="razzball-full-season-upstream-inflation-20260920",
        evidence_note=(
            "completed numerical trace preserved 12 exact malformed pre-normalization "
            "CurrentProjectionSnapshot rows; full 562-row payload was not preserved"
        ),
    ),
    CurrentProjectionHealthIncident(
        provider="razzball",
        source_version="razzball-season-projections-html-v3:horizon-isolated",
        content_fingerprint_sha256=(
            "580e2bf8cfc1256336b6496202c37f598e192e31f063129f83fce8b2686ec334"
        ),
        witness_rows=_RAZZBALL_20260921_WITNESSES,
        incident_id="razzball-full-season-upstream-inflation-20260921",
        evidence_note=(
            "corrective live numerical trace preserved 12 exact malformed "
            "pre-normalization CurrentProjectionSnapshot rows from the later 624-row revision"
        ),
    ),
)


def current_projection_payload_sha256(
    snapshot: CurrentProjectionSnapshot,
) -> str:
    """Hash provider content without transport timestamps or row ordering.

    This digest is provenance identity only. Source-health authority remains the
    incident-specific witness gate below.
    """

    rows = sorted(
        (
            {
                "provider": row.provider,
                "external_id": row.external_id,
                "player_name": row.player_name,
                "position": row.position.value,
                "nfl_team": row.nfl_team,
                "stats": [
                    [key, float(value)]
                    for key, value in sorted(row.stats.items())
                ],
            }
            for row in snapshot.rows
        ),
        key=lambda item: (
            str(item["external_id"]),
            str(item["player_name"]),
            str(item["position"]),
            str(item["nfl_team"]),
            json.dumps(item["stats"], separators=(",", ":")),
        ),
    )
    encoded = json.dumps(
        {
            "provider": snapshot.provider,
            "source_version": snapshot.source_version,
            "usage_class": snapshot.usage_class,
            "rows": rows,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_witness_payload(
    *,
    provider: str,
    source_version: str,
    witness_rows: tuple[ProjectionContentWitness, ...],
) -> bytes:
    payload = {
        "provider": provider,
        "source_version": source_version,
        "witness_rows": [
            {
                "player_name": witness.player_name,
                "position": witness.position,
                "nfl_team": witness.nfl_team,
                "stats": [[key, value] for key, value in witness.stats],
            }
            for witness in sorted(
                witness_rows,
                key=lambda item: (item.player_name, item.position, item.nfl_team),
            )
        ],
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _snapshot_witness_fingerprint(
    snapshot: CurrentProjectionSnapshot,
    *,
    incident: CurrentProjectionHealthIncident,
) -> str | None:
    if (
        snapshot.provider != incident.provider
        or snapshot.source_version != incident.source_version
    ):
        return None

    rows_by_identity: dict[tuple[str, str, str], list[object]] = {}
    for row in snapshot.rows:
        key = (
            row.player_name.strip(),
            row.position.value,
            row.nfl_team.strip().upper(),
        )
        rows_by_identity.setdefault(key, []).append(row)

    observed: list[ProjectionContentWitness] = []
    for witness in incident.witness_rows:
        matches = rows_by_identity.get(
            (witness.player_name, witness.position, witness.nfl_team),
            [],
        )
        if len(matches) != 1:
            return None
        row = matches[0]
        stats: list[tuple[str, float]] = []
        for stat, _expected in witness.stats:
            if stat not in row.stats:
                return None
            stats.append((stat, float(row.stats[stat])))
        observed.append(
            ProjectionContentWitness(
                player_name=witness.player_name,
                position=witness.position,
                nfl_team=witness.nfl_team,
                stats=tuple(stats),
            )
        )

    encoded = _canonical_witness_payload(
        provider=snapshot.provider,
        source_version=snapshot.source_version,
        witness_rows=tuple(observed),
    )
    return hashlib.sha256(encoded).hexdigest()


def validate_current_projection_snapshot_health(
    snapshot: CurrentProjectionSnapshot,
) -> None:
    """Secondary forensic gate for specifically preserved malformed incidents.

    Revision-agnostic scale integrity is evaluated separately before this function
    in the current runtime. These fingerprints are defense-in-depth only: they make
    known bad content auditable across timestamp/order/count drift but are not the
    primary source-health authority.
    """

    for incident in _KNOWN_BAD_CURRENT_REVISIONS:
        fingerprint = _snapshot_witness_fingerprint(snapshot, incident=incident)
        if fingerprint == incident.content_fingerprint_sha256:
            raise ValueError(
                "current projection source content quarantined by governed "
                f"numerical-integrity incident {incident.incident_id}: "
                f"content_sha256={fingerprint}; {incident.evidence_note}"
            )

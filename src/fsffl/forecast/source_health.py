from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from fsffl.providers.current_projection_rows import CurrentProjectionSnapshot


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
)


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
    """Fail closed for provider content with durable numerical-integrity evidence.

    This gate is incident-specific rather than provider-wide. Known malformed content
    remains quarantined if republished under a different timestamp, row order, or row
    count. Corrected content remains eligible for the normal governed live path.
    """

    for incident in _KNOWN_BAD_CURRENT_REVISIONS:
        fingerprint = _snapshot_witness_fingerprint(snapshot, incident=incident)
        if fingerprint == incident.content_fingerprint_sha256:
            raise ValueError(
                "current projection source content quarantined by governed "
                f"numerical-integrity incident {incident.incident_id}: "
                f"content_sha256={fingerprint}; {incident.evidence_note}"
            )

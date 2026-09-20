from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fsffl.providers.current_projection_rows import CurrentProjectionSnapshot


@dataclass(frozen=True)
class CurrentProjectionHealthIncident:
    provider: str
    source_version: str
    effective_at: datetime
    row_count: int
    incident_id: str
    evidence_note: str


# Bounded operational quarantine for the exact upstream Razzball revision proven
# malformed by the completed 2026-09-20 numerical trace. This is not a Forecast
# coefficient, provider weight, clipping rule, divisor, or learned health model.
# A later provider revision (different effective_at and/or row payload) continues
# through the normal governed live path.
_KNOWN_BAD_CURRENT_REVISIONS = (
    CurrentProjectionHealthIncident(
        provider="razzball",
        source_version="razzball-season-projections-html-v3:horizon-isolated",
        effective_at=datetime(2026, 9, 20, 13, 48, 44, tzinfo=UTC),
        row_count=562,
        incident_id="razzball-full-season-upstream-inflation-20260920",
        evidence_note=(
            "completed numerical trace proved source-page raw stats were already "
            "inflated before FSFFL parsing/normalization"
        ),
    ),
)


def validate_current_projection_snapshot_health(
    snapshot: CurrentProjectionSnapshot,
) -> None:
    """Fail closed for a revision with durable numerical-integrity evidence.

    The health gate is intentionally revision-specific. It does not infer that a
    provider is generally unhealthy and does not compare providers, rescale values,
    or alter ensemble weights. Valid later revisions remain eligible for the normal
    >=2-independent-source live Forecast contract.
    """

    effective_at = snapshot.effective_at.astimezone(UTC)
    for incident in _KNOWN_BAD_CURRENT_REVISIONS:
        if (
            snapshot.provider == incident.provider
            and snapshot.source_version == incident.source_version
            and effective_at == incident.effective_at
            and len(snapshot.rows) == incident.row_count
        ):
            raise ValueError(
                "current projection source revision quarantined by governed "
                f"numerical-integrity incident {incident.incident_id}: "
                f"{incident.evidence_note}"
            )

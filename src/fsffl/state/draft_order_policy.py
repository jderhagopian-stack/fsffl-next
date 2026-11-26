from __future__ import annotations

from datetime import datetime

from .models import (
    DraftOrderParameterValue,
    DraftOrderPolicyEvidence,
    DraftOrderPolicyParameter,
)

# Policy vocabulary is State configuration; Simulation owns execution.
STANDARD_DRAFT_ORDER_MECHANISM_V1 = "standard_record_h2h_pf_then_playoff_elimination_v1"
STANDARD_REGULAR_SEASON_TIEBREAK = "worse_record_then_resolvable_head_to_head_then_lower_points_for"
STANDARD_PLAYOFF_ORDER = "round_eliminated_then_regular_season_tiebreaks_runner_up_champion"


def resolve_draft_order_policy(
    policies: tuple[DraftOrderPolicyEvidence, ...],
    *,
    league_id: str,
    draft_season: int,
    as_of: datetime,
) -> DraftOrderPolicyEvidence | None:
    """Return the latest explicit policy both effective and knowable at as_of.

    Standard fallback authority belongs to Simulation and is used only when this
    resolver returns no explicit league evidence.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    candidates = [
        item
        for item in policies
        if item.league_id == league_id
        and item.draft_season == draft_season
        and item.effective_at <= as_of
        and item.available_at <= as_of
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            item.effective_at,
            item.available_at,
            item.version,
        ),
    )


__all__ = [
    "DraftOrderParameterValue",
    "DraftOrderPolicyEvidence",
    "DraftOrderPolicyParameter",
    "resolve_draft_order_policy",
]

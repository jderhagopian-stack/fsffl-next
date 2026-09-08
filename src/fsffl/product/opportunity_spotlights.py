from __future__ import annotations

from typing import Iterable


_FEASIBILITY_ORDER = {
    "mutual_gain_candidate": 0,
    "mixed": 1,
    "neutral": 2,
    "counterparty_dominated": 3,
    "incomplete": 4,
    None: 5,
}

_SIDE_ORDER = {
    "uniform_gain": 0,
    "mixed": 1,
    "neutral": 2,
    "uniform_loss": 3,
    "incomplete": 4,
    None: 5,
}


def _candidate_identity(row: dict[str, object]) -> dict[str, object]:
    """Return presentation-safe identity without copying model authority."""

    return {
        "counterparty_team_id": row.get("counterparty_team_id"),
        "counterparty_name": row.get("counterparty_name"),
        "send": row.get("send") or [],
        "receive": row.get("receive") or [],
        "package_shape": row.get("package_shape"),
        "market_gap_ratio": row.get("market_gap_ratio"),
        "search_distance": row.get("search_distance"),
        "decision_shape": row.get("decision_shape"),
        "focal_decision_shape": row.get("focal_decision_shape"),
        "counterparty_decision_shape": row.get("counterparty_decision_shape"),
        "negotiation_feasibility_shape": row.get("negotiation_feasibility_shape"),
    }


def _decision_priority(row: dict[str, object], search_rank: int) -> tuple[int, int, int, int]:
    """Categorical lexicographic selection; never a scalar opportunity score.

    Bilateral feasibility is considered first because this spotlight is meant to find
    a practical lead among rows already evaluated by Decision. Focal and counterparty
    directional shapes then break ties. Original Search rank is the final deterministic
    tie-breaker only. No channel is numerically blended with another.
    """

    feasibility = row.get("negotiation_feasibility_shape")
    focal = row.get("focal_decision_shape")
    counterparty = row.get("counterparty_decision_shape")
    return (
        _FEASIBILITY_ORDER.get(str(feasibility) if feasibility is not None else None, 5),
        _SIDE_ORDER.get(str(focal) if focal is not None else None, 5),
        _SIDE_ORDER.get(str(counterparty) if counterparty is not None else None, 5),
        search_rank,
    )


def build_trade_spotlights(candidates: Iterable[dict[str, object]]) -> dict[str, object]:
    """Separate market closeness from Decision-evaluated opportunity quality.

    Candidate order is assumed to be the existing governed Search order. The closest
    market match is therefore the first row. The most promising evaluated lead is
    selected only from rows that actually have bilateral Decision evidence, using the
    categorical lexicographic ordering above. This function does not create action
    authority, acceptance odds, valuation, or a recommendation score.
    """

    rows = list(candidates)
    closest = _candidate_identity(rows[0]) if rows else None

    evaluated = [
        (index, row)
        for index, row in enumerate(rows)
        if row.get("bilateral_decision_evaluated")
    ]
    promising_pair = min(
        evaluated,
        key=lambda item: _decision_priority(item[1], item[0]),
        default=None,
    )
    promising = _candidate_identity(promising_pair[1]) if promising_pair is not None else None

    return {
        "closest_market_match": closest,
        "most_promising_evaluated": promising,
        "same_candidate": bool(
            closest is not None
            and promising is not None
            and closest.get("counterparty_team_id") == promising.get("counterparty_team_id")
            and closest.get("send") == promising.get("send")
            and closest.get("receive") == promising.get("receive")
        ),
        "selection_basis": (
            "Closest market match follows governed Search order. Most promising evaluated lead "
            "uses categorical bilateral feasibility, then focal and counterparty Decision shapes, "
            "with Search rank only as a final tie-breaker. No composite opportunity score is used."
        ),
        "recommendation_authority": False,
        "acceptance_probability": None,
    }

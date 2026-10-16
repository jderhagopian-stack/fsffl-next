"""Presentation-only Career ruler; never an input to economic calculations."""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from math import isfinite
from typing import Mapping

CAREER_PRESENTATION_VERSION = "career-index-v1:active-reference-empirical-midrank"


@dataclass(frozen=True)
class CareerPresentationCoordinate:
    """Exact publication's accepted reference game, independent of roster expansion.

    Equal raw values share their average rank. Distinct anchors interpolate
    linearly between their midranks. Values outside the reference range clamp
    to 0/10,000; a completely tied reference maps to its midpoint. A new
    reference/rules calculation creates a new fingerprint, never a hidden
    moving roster/query-based universe. Raw economic quantities stay unchanged.
    """

    reference: tuple[tuple[str, float], ...]

    def __post_init__(self):
        if len(self.reference) < 2:
            raise ValueError("Career display requires a complete reference game of at least two players")
        if len({key for key, _ in self.reference}) != len(self.reference):
            raise ValueError("Career display reference identities must be unique")
        if not all(isfinite(value) for _, value in self.reference):
            raise ValueError("Career display reference values must be finite")

    @classmethod
    def from_reference(cls, raw_values: Mapping[str, float], *, reference_ids: frozenset[str]):
        if not reference_ids.issubset(raw_values):
            raise ValueError("Career display reference is incomplete")
        return cls(tuple((key, float(raw_values[key])) for key in sorted(reference_ids)))

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(
            [CAREER_PRESENTATION_VERSION, self.reference], separators=(",", ":"), allow_nan=False,
        ).encode()).hexdigest()

    def index(self, raw: float | None) -> float | None:
        if raw is None or not isfinite(raw):
            return None
        values = sorted(value for _, value in self.reference)
        if raw < values[0]:
            return 0.0
        if raw > values[-1]:
            return 10_000.0
        left, right = bisect_left(values, raw), bisect_right(values, raw)
        denominator = len(values) - 1
        if left != right:
            return 10_000.0 * (left + right - 1) / (2 * denominator)
        low, high = values[left - 1], values[left]
        low_rank = (bisect_left(values, low) + bisect_right(values, low) - 1) / 2
        high_rank = (bisect_left(values, high) + bisect_right(values, high) - 1) / 2
        return 10_000.0 * (low_rank + (raw - low) / (high - low) * (high_rank - low_rank)) / denominator

    def summary(self) -> dict[str, object]:
        values = [value for _, value in self.reference]
        return {
            "version": CAREER_PRESENTATION_VERSION,
            "input_fingerprint": self.fingerprint,
            "reference_universe": "Current-owned active accepted Foundation 4 reference game",
            "reference_player_ids": [key for key, _ in self.reference],
            "reference_count": len(self.reference),
            "raw_minimum": min(values), "raw_maximum": max(values),
            "tie_policy": "average rank; linear interpolation between distinct raw anchors",
            "outside_reference_policy": "clamp to 0 or 10000",
            "presentation_only": True, "market_inputs_used": False,
            "economic_gap_subtraction_allowed": False,
            "minimum_index": 0, "maximum_index": 10_000,
        }


@lru_cache(maxsize=1)
def career_reference_player_ids() -> frozenset[str]:
    from .foundation4_shadow_inputs import provide_foundation4_terminal_features
    return frozenset(provide_foundation4_terminal_features())


def career_reference_ids_from_current(record) -> frozenset[str]:
    if (record is None or getattr(record.status, "value", None) != "completed"
            or record.contract is None):
        return frozenset()
    return career_reference_player_ids() & {row.player_id for row in record.contract.estimates}


def career_lens_for_publication(record, *, served_state_id: str,
                                reference_ids: frozenset[str] | None = None) -> tuple[dict, dict]:
    """Present an already published exact-State authority, never request a build."""
    unavailable = {"status": "unavailable", "label": "Career Intrinsic",
                   "reason": "No completed Career authority matches the served State."}
    if (record is None or getattr(record.status, "value", None) != "completed"
            or record.contract is None or record.league_state_id != served_state_id):
        return unavailable, {}
    raw = {row.player_id: row.raw_career_forward_reference for row in record.contract.estimates}
    # Current explicitly owns the active reference game. No roster/free-agent
    # query can contribute anchors to this fixed reference authority.
    # Expected anchors come from the independent governed Current game, not
    # from whichever Career rows happened to arrive. An incomplete reference
    # fails closed rather than silently recalibrating on a smaller universe.
    reference_ids = career_reference_player_ids() if reference_ids is None else reference_ids
    try:
        coordinate = CareerPresentationCoordinate.from_reference(raw, reference_ids=frozenset(reference_ids))
    except ValueError as exc:
        return {**unavailable, "reason": str(exc)}, {}
    return ({"status": "ready", "label": "Career Intrinsic", "league_state_id": served_state_id,
             "input_fingerprint": getattr(record.contract, "input_fingerprint", None),
             "dependency_fingerprint": getattr(record, "intrinsic_input_fingerprint", None),
             "model_version": getattr(record.contract, "model_version", None),
             "contract_version": getattr(record.contract, "contract_version", None),
             "presentation": coordinate.summary()},
            {pid: {"career_intrinsic_index": coordinate.index(value),
                   "raw_career_forward_reference": value, "career_status": "ready"}
             for pid, value in raw.items()})


def attach_career_player_lenses(payload: dict, *, record, current_state_id: str,
                               current_generation_id: str | None = None,
                               reference_ids: frozenset[str] | None = None) -> dict:
    """Overlay optional product evidence without changing other Value lenses."""
    served = (payload.get("presentation_continuity") or {}).get("served_league_state_id") or payload.get("league_state_id")
    served_generation = payload.get("publication_generation_id")
    generation_matches = served_generation is None or served_generation == current_generation_id
    summary, rows = career_lens_for_publication(
        record if served == current_state_id and generation_matches else None,
        served_state_id=served, reference_ids=reference_ids,
    )
    summary["publication_generation_id"] = (
        current_generation_id if served_generation is None else served_generation
    )
    result = {**payload, "career_intrinsic": summary}
    if "fsffl_intrinsic" in result:
        result["fsffl_intrinsic"] = {**result["fsffl_intrinsic"], "label": "3-Year Intrinsic"}
    result["players"] = [{**row, **rows.get(row["player_id"], {
        "career_intrinsic_index": None, "raw_career_forward_reference": None,
        "career_status": "unavailable",
    })} for row in payload.get("players", ())]
    return result

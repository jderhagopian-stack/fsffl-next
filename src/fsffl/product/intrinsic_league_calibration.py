"""Research-only, fail-closed league-configuration Intrinsic reference resolution.

Call on league sign-in with canonical league rule inputs. This module does not
derive caps from current-player maxima or install itself in production.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Mapping

from fsffl.product.intrinsic_magnitude_shadow import MagnitudeRuler


def configuration_fingerprint(rules: Mapping[str, object]) -> str:
    """Canonicalize governed scoring, starters, flex, team count and roster rules."""
    if not rules:
        raise ValueError("league rules are required")
    required = ("team_count", "scoring", "starting_slots", "roster_slots")
    if any(key not in rules for key in required):
        raise ValueError("incomplete league calibration input")
    raw = json.dumps({key: rules[key] for key in required}, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CalibrationReference:
    configuration_id: str
    three_year_anchor: float
    career_anchor: float
    version: str
    approval: str

    def __post_init__(self) -> None:
        if not self.version or self.approval != "approved":
            raise ValueError("only approved, versioned calibration references are usable")
        for horizon, anchor in (("three_year", self.three_year_anchor), ("career", self.career_anchor)):
            MagnitudeRuler(horizon, anchor, "linear", self.version)


def resolve_league_calibration(
    rules: Mapping[str, object],
    approved_references: Mapping[str, CalibrationReference],
) -> tuple[MagnitudeRuler, MagnitudeRuler] | None:
    """Resolve approved league-format reference or return unavailable (never guess)."""
    key = configuration_fingerprint(rules)
    record = approved_references.get(key)
    if record is None:
        return None
    if record.configuration_id != key:
        raise ValueError("reference configuration mismatch")
    return (
        MagnitudeRuler("three_year", record.three_year_anchor, "linear", record.version),
        MagnitudeRuler("career", record.career_anchor, "linear", record.version),
    )

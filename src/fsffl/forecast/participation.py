"""Accepted participation evidence shared by live Forecast consumers.

Receipt eligibility and historical capture fences are unchanged from the
Intrinsic Year-1 integration. No acquisition or fantasy-point calculation.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Mapping
from fsffl.state.models import LeagueState

@dataclass(frozen=True)
class StatusBasedZeroRosEvidence:
    """Explicit recorded evidence that a player has no expected 2026 participation."""

    player_id: str
    status: str
    source: str
    source_version: str
    observed_at: datetime
    no_expected_2026_participation: bool
    season: int = 2026
    entire_season_unavailable: bool = False

    def validate(self) -> None:
        if self.status not in {"out_for_season", "unsigned_no_expected_2026_participation"}:
            raise ValueError("status evidence does not establish season-long nonparticipation")
        if not self.source.strip() or not self.source_version.strip():
            raise ValueError("status evidence lacks source provenance")
        if self.observed_at.tzinfo is None:
            raise ValueError("status evidence timestamp must be timezone-aware")
        if not self.no_expected_2026_participation:
            raise ValueError("status evidence does not confirm no expected 2026 participation")


STATUS_BASED_YEAR_ONE_SCORING_VERSION = "status-y1-v2:verified-whole-season-no-residual"
UNSIGNED_YTD_POLICY_VERSION = "career-ytd-only-v2:universal-catalog-team-null-20261024"
UNSIGNED_YTD_POLICY_APPROVED_AT = datetime(2026, 10, 24, 20, 19, 21, tzinfo=UTC)
IR_NO_PROJECTION_POLICY_VERSION = "career-ytd-only-v2:exact-state-ir-no-projection-20261024"
IR_NO_PROJECTION_POLICY_APPROVED_AT = datetime(2026, 10, 24, 20, 19, 21, tzinfo=UTC)

# User-directed correction. Earlier publications/replays retain their prior
# source-policy identity; a subsequent governed capture admits this rule.
ROS_FALLBACK_POLICY_VERSION = "career-ros-fallback-v3:unsigned-priority-single-source-fumbles"
ROS_FALLBACK_POLICY_APPROVED_AT = datetime(2026, 11, 8, 13, 13, 56, tzinfo=UTC)


def ros_fallback_policy_version(as_of: datetime) -> str | None:
    if as_of.tzinfo is None:
        raise ValueError("ROS fallback policy cutoff must be timezone-aware")
    return (ROS_FALLBACK_POLICY_VERSION
            if as_of >= ROS_FALLBACK_POLICY_APPROVED_AT else None)


def _unsigned_ytd_override(
    player_id: str, *, roles: Mapping[str, Any],
    receipts: Mapping[str, YtdOnlyYearOneEvidence], as_of: datetime,
) -> YtdOnlyYearOneEvidence | None:
    """Current NFL unsigned evidence owns ROS; a provider row cannot sign a player."""
    if ros_fallback_policy_version(as_of) is None:
        return None
    role = roles.get(player_id)
    receipt = receipts.get(player_id)
    if (role is None or role.status != "unsigned" or receipt is None
            or role.captured_at > as_of or receipt.observed_at > as_of):
        return None
    return (receipt if receipt.source_version.endswith(ROS_FALLBACK_POLICY_VERSION)
            else replace(receipt, source_version=receipt.source_version + ":" + ROS_FALLBACK_POLICY_VERSION))



def recorded_status_based_zero_ros_evidence(
    league_state: LeagueState, *, as_of: datetime,
) -> dict[str, StatusBasedZeroRosEvidence]:
    """Admit captured official facts for exact roster identities and cutoff.

    No provider fetch, fantasy-slot inference, or unsigned-player assumption.
    A newly acquired receipt cannot change a pre-capture replay/publication.
    """
    from fsffl.providers.nfl_status_evidence import SEASON_UNAVAILABILITY_RECEIPTS

    if as_of.tzinfo is None:
        raise ValueError("NFL status admission cutoff must be timezone-aware")
    roster_ids = {entry.player_id for team in league_state.team_states for entry in team.roster}
    players = {player.player_id: player for player in league_state.players}
    return {
        receipt.player_id: StatusBasedZeroRosEvidence(
            player_id=receipt.player_id, status="out_for_season",
            source=receipt.source_url,
            source_version=f"official-season-unavailability-v1:{receipt.fingerprint}",
            observed_at=receipt.captured_at,
            no_expected_2026_participation=True, season=receipt.season,
            entire_season_unavailable=True,
        )
        for receipt in SEASON_UNAVAILABILITY_RECEIPTS
        if receipt.season == league_state.league.season
        and receipt.captured_at <= as_of.astimezone(UTC)
        and receipt.player_id in roster_ids
        and receipt.player_id in players
        and players[receipt.player_id].position.value == receipt.position
    }


@dataclass(frozen=True)
class YtdOnlyYearOneEvidence:
    """Approved low-confidence input assumption; never an NFL absence fact."""

    player_id: str
    season: int
    source: str
    source_version: str
    observed_at: datetime
    status: str = "low_confidence_ytd_only_no_additional_production_assumed"

    def validate(self) -> None:
        if (not self.source or not self.source_version or self.observed_at.tzinfo is None
                or self.status != "low_confidence_ytd_only_no_additional_production_assumed"):
            raise ValueError("YTD-only assumption lacks approved provenance")


def recorded_ytd_only_year_one_evidence(
    league_state: LeagueState, *, as_of: datetime,
    verified_roles: Mapping[str, object] | None = None,
) -> dict[str, YtdOnlyYearOneEvidence]:
    from fsffl.providers.nfl_status_evidence import (
        recorded_nfl_role_receipts, YTD_ONLY_APPROVED_ROLES,
        YTD_ONLY_POLICY_VERSION, YTD_ONLY_POLICY_APPROVED_AT,
    )
    # Preserve the pinned historical receipt read for deterministic replay and
    # dependency accounting; fresh acquired receipts are an additive override.
    roles = dict(recorded_nfl_role_receipts(league_state, as_of=as_of))
    if verified_roles is not None:
        roles.update(verified_roles)
    if as_of < YTD_ONLY_POLICY_APPROVED_AT:
        return {}
    result = {}
    for pid, row in roles.items():
        if row.status == "unsigned" and YTD_ONLY_APPROVED_ROLES.get(pid) == row.status:
            version, approved_at = YTD_ONLY_POLICY_VERSION, YTD_ONLY_POLICY_APPROVED_AT
        elif row.status == "unsigned":
            if as_of < UNSIGNED_YTD_POLICY_APPROVED_AT:
                continue
            version, approved_at = UNSIGNED_YTD_POLICY_VERSION, UNSIGNED_YTD_POLICY_APPROVED_AT
        elif YTD_ONLY_APPROVED_ROLES.get(pid) == row.status:
            version, approved_at = YTD_ONLY_POLICY_VERSION, YTD_ONLY_POLICY_APPROVED_AT
        else:
            continue
        result[pid] = YtdOnlyYearOneEvidence(
            player_id=pid, season=row.season, source=row.source_url,
            source_version=f"{version}:{row.fingerprint}",
            observed_at=max(row.captured_at, approved_at),
        )
    return result


def recorded_ir_no_projection_year_one_evidence(
    league_state: LeagueState, *, player_id: str, as_of: datetime,
    available_projection_rows: tuple[object, ...],
) -> YtdOnlyYearOneEvidence | None:
    """Use the exact-State IR slot as low-confidence zero-ROS evidence only when no projection exists."""
    if as_of.tzinfo is None or as_of < IR_NO_PROJECTION_POLICY_APPROVED_AT:
        return None
    if any(row.player_id == player_id for row in available_projection_rows):
        return None
    on_ir = any(
        entry.player_id == player_id
        and getattr(entry.slot, "value", entry.slot) == "IR"
        for team in league_state.team_states for entry in team.roster
    )
    if not on_ir or player_id not in {player.player_id for player in league_state.players}:
        return None
    return YtdOnlyYearOneEvidence(
        player_id=player_id, season=league_state.league.season,
        source="fsffl:exact-state-ir-no-projection",
        source_version=f"{IR_NO_PROJECTION_POLICY_VERSION}:{league_state.as_of.isoformat()}",
        observed_at=as_of,
    )



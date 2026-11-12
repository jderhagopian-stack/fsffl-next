"""Accepted participation evidence shared by live Forecast consumers.

Receipt eligibility and historical capture fences are unchanged from the
Intrinsic Year-1 integration. No acquisition or fantasy-point calculation.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
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
PRACTICE_SQUAD_POLICY_VERSION = "practice-squad-no-ros-v1:verified-role-no-provider-rows"
PRACTICE_SQUAD_POLICY_APPROVED_AT = datetime(2026, 11, 12, 5, 27, 51, tzinfo=UTC)


def practice_squad_policy_version(as_of: datetime) -> str | None:
    if as_of.tzinfo is None:
        raise ValueError("practice-squad cutoff must be timezone-aware")
    return PRACTICE_SQUAD_POLICY_VERSION if as_of >= PRACTICE_SQUAD_POLICY_APPROVED_AT else None


def practice_squad_no_projection_receipt(player_id, *, receipts, available_projection_rows, source_ready):
    """A missing row in a healthy cohort, not a source outage or partial row."""
    receipt = receipts.get(player_id)
    if (receipt is None or not receipt.source_version.startswith(PRACTICE_SQUAD_POLICY_VERSION)
            or not source_ready or not available_projection_rows
            or any(row.player_id == player_id for row in available_projection_rows)):
        return None
    return receipt

# User-directed correction. Earlier publications/replays retain their prior
# source-policy identity; a subsequent governed capture admits this rule.
ROS_FALLBACK_POLICY_VERSION = "career-ros-fallback-v3:unsigned-priority-single-source-fumbles"
ROS_FALLBACK_POLICY_APPROVED_AT = datetime(2026, 11, 8, 13, 13, 56, tzinfo=UTC)

# Correct the remaining Career-only backup-role restriction on the accepted
# single-source completion rule. Earlier replay/capture identities stay intact.
SINGLE_SOURCE_COMPLETION_VERSION = "single-source-completion-v1:role-independent-strict-scoring"
SINGLE_SOURCE_COMPLETION_EFFECTIVE_AT = datetime(2026, 11, 11, 1, 10, 39, tzinfo=UTC)


def single_source_completion_policy_version(as_of: datetime) -> str | None:
    if as_of.tzinfo is None:
        raise ValueError("single-source completion cutoff must be timezone-aware")
    return (SINGLE_SOURCE_COMPLETION_VERSION
            if as_of >= SINGLE_SOURCE_COMPLETION_EFFECTIVE_AT else None)


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
            entire_season_unavailable=receipt.first_unavailable_week == 1,
        )
        for receipt in SEASON_UNAVAILABILITY_RECEIPTS
        if receipt.season == league_state.league.season
        and 1 <= receipt.first_unavailable_week <= (league_state.completed_through_week or 0) + 1
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
    ps_policy = practice_squad_policy_version(as_of)
    if ps_policy is not None:
        from fsffl.providers.nfl_status_evidence import canonical_practice_squad_role_receipts
        for pid, row in canonical_practice_squad_role_receipts(league_state, as_of=as_of).items():
            if pid not in roles or row.captured_at >= roles[pid].captured_at:
                roles[pid] = row
    if verified_roles is not None:
        for pid, row in verified_roles.items():
            old = roles.get(pid)
            if (ps_policy is not None and old is not None
                    and "practice_squad" in (old.status, row.status)
                    and row.captured_at < old.captured_at):
                continue
            roles[pid] = row
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
        elif row.status == "practice_squad":
            player = next((p for p in league_state.players if p.player_id == pid), None)
            owned = any(r.player_id == pid for team in league_state.team_states for r in team.roster)
            if (ps_policy is None or not owned or player is None or not row.nfl_team
                    or player.nfl_team != row.nfl_team or player.position.value != row.position
                    or league_state.league.season != row.season
                    or not row.captured_at <= as_of < row.captured_at + timedelta(hours=6)):
                continue
            version, approved_at = ps_policy, PRACTICE_SQUAD_POLICY_APPROVED_AT
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




# User-directed universal fallback, effective only for subsequent captures.
SPARSE_PRODUCTION_POLICY_VERSION = "sparse-production-no-ros-v1:4w-5opp-50yd-0td"
SPARSE_PRODUCTION_POLICY_APPROVED_AT = datetime(2026, 11, 10, 13, 12, 49, tzinfo=UTC)
SPARSE_PRODUCTION_INJURY_POLICY_VERSION = "sparse-production-no-ros-v2:4w-5opp-50yd-0td:coarse-injury-flag"
SPARSE_PRODUCTION_INJURY_POLICY_APPROVED_AT = datetime(2026, 11, 10, 15, 41, 53, tzinfo=UTC)


def sparse_production_policy_version(as_of: datetime) -> str | None:
    if as_of.tzinfo is None:
        raise ValueError("sparse-production cutoff must be timezone-aware")
    if as_of >= SPARSE_PRODUCTION_INJURY_POLICY_APPROVED_AT:
        return SPARSE_PRODUCTION_INJURY_POLICY_VERSION
    return (SPARSE_PRODUCTION_POLICY_VERSION
            if as_of >= SPARSE_PRODUCTION_POLICY_APPROVED_AT else None)


class SparseProductionEvidence:
    """Bounded counters from already acquired full weekly cohorts; no raw copies.

    Missing player rows can support an explicit assumption only when every
    completed week has a nonempty, identity/cutoff-valid source response.
    Empty/failed feeds never establish absence. Counts are scoring-independent.
    """
    _keys = ("pass_att", "rush_att", "rec_tgt", "rec", "pass_yd", "rush_yd",
             "rec_yd", "pass_td", "rush_td", "rec_td")

    def __init__(self, state: LeagueState):
        self.state = state
        self.weeks: set[int] = set()
        self.totals: dict[str, dict[str, float]] = {}
        self.captured_at: datetime | None = None
        self.valid = True
        self.player_ids = {p.player_id for p in state.players}

    def add_week(self, week: int, lines) -> None:
        import math
        if not lines or week in self.weeks:
            self.valid = False
        self.weeks.add(week)
        for line in lines:
            if (line.season != self.state.league.season or line.week != week
                    or line.captured_at.tzinfo is None):
                self.valid = False
                continue
            self.captured_at = max(self.captured_at or line.captured_at, line.captured_at)
            if line.player_id not in self.player_ids:
                continue
            totals = self.totals.setdefault(line.player_id, dict.fromkeys(self._keys, 0.0))
            for key in self._keys:
                try:
                    value = float(line.stats.get(key, 0.0))
                except (TypeError, ValueError):
                    self.valid = False
                    continue
                if not math.isfinite(value):
                    self.valid = False
                # Avoid cancellation from negative corrections hiding participation.
                totals[key] += abs(value)

    def receipts(self, *, as_of: datetime, available_projection_rows,
                 source_ready: bool) -> dict[str, YtdOnlyYearOneEvidence]:
        import hashlib
        import json
        version = sparse_production_policy_version(as_of)
        completed = self.state.completed_through_week
        if (version is None or not source_ready or not self.valid
                or completed is None or not 4 <= completed < 18
                or self.weeks != set(range(1, completed + 1))
                or self.captured_at is None or self.captured_at > as_of
                or self.state.as_of > as_of):
            return {}
        allowed_statuses = {"active", "inactive", "practice_squad"}
        policy_admitted_at = SPARSE_PRODUCTION_POLICY_APPROVED_AT
        if as_of >= SPARSE_PRODUCTION_INJURY_POLICY_APPROVED_AT:
            # Coarse injury flags do not quantify future participation. Under
            # the same sparse-production/no-source evidence, retain the explicit
            # low-confidence assumption instead of treating this flag as a veto.
            allowed_statuses.update({"injured", "pup"})
            policy_admitted_at = SPARSE_PRODUCTION_INJURY_POLICY_APPROVED_AT
        projected = {r.player_id for r in available_projection_rows}
        statuses = {p.player_id: p for p in self.state.player_states}
        state_id = self.state.state_id
        result = {}
        for player in self.state.players:
            status = statuses.get(player.player_id)
            if (player.position.value not in {"QB", "RB", "WR", "TE"}
                    or not player.nfl_team or player.nfl_team.upper() in {"FA", "N/A", "NONE"}
                    or player.player_id in projected or status is None
                    or status.as_of > as_of or status.status.value not in allowed_statuses):
                continue
            t = self.totals.get(player.player_id, {})
            # Receptions also bound participation if a feed omits target counts.
            opportunities = t.get("pass_att", 0) + t.get("rush_att", 0) + max(t.get("rec_tgt", 0), t.get("rec", 0))
            yards = sum(t.get(k, 0) for k in ("pass_yd", "rush_yd", "rec_yd"))
            touchdowns = sum(t.get(k, 0) for k in ("pass_td", "rush_td", "rec_td"))
            if opportunities > 5 or yards > 50 or touchdowns != 0:
                continue
            identity = {"state": state_id, "player": player.player_id,
                        "week": completed, "totals": t, "captured_at": self.captured_at.isoformat()}
            digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
            result[player.player_id] = YtdOnlyYearOneEvidence(
                player_id=player.player_id, season=self.state.league.season,
                source="fsffl:completed-week-sparse-production-no-projection",
                source_version=f"{version}:{digest}",
                observed_at=max(self.captured_at, policy_admitted_at),
            )
        return result

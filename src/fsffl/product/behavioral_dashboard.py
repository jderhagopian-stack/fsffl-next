from __future__ import annotations

from collections.abc import Iterable

from fsffl.behavioral.models import OwnerBehaviorProfile
from fsffl.state.models import LeagueState


_DASHBOARD_MODEL_VERSION = "behavioral-intelligence-dashboard-v2:end-state-contract"
_CONTEXT_UNAVAILABLE_REASON = (
    "Context-controlled inference requires strictly pre-action canonical LeagueState "
    "coverage for historical owner actions. The hosted runtime does not yet persist "
    "that historical state coverage, so FSFFL will not substitute current-state or "
    "post-action evidence."
)


def _share(count: int, total: int) -> float | None:
    return count / total if total > 0 else None


def _sorted_counts(values: dict[str, int]) -> list[dict[str, object]]:
    return [
        {"key": key, "count": count}
        for key, count in sorted(values.items(), key=lambda item: (-item[1], item[0]))
    ]


def _team_by_owner(
    league_state: LeagueState,
    current_owner_by_roster: Iterable[tuple[int, str]],
) -> dict[str, tuple[str, str]]:
    roster_to_team = {}
    for team in league_state.teams:
        sleeper_ref = next((ref for ref in team.provider_refs if ref.provider == "sleeper"), None)
        if sleeper_ref is None:
            continue
        try:
            roster_to_team[int(sleeper_ref.external_id)] = team
        except ValueError:
            continue
    return {
        owner_id: (roster_to_team[roster_id].team_id, roster_to_team[roster_id].display_name)
        for roster_id, owner_id in current_owner_by_roster
        if roster_id in roster_to_team
    }


def _capabilities() -> dict[str, object]:
    return {
        "observed_history": {
            "status": "ready",
            "label": "Observed history",
            "reason": None,
        },
        "context_controlled_position_preference": {
            "status": "unavailable",
            "label": "Context-controlled position preference",
            "reason": _CONTEXT_UNAVAILABLE_REASON,
            "model_version": "owner-historical-context-controlled-preference-v2",
        },
        "context_controlled_trade_shape": {
            "status": "unavailable",
            "label": "Context-controlled trade shape",
            "reason": _CONTEXT_UNAVAILABLE_REASON,
            "model_version": "owner-trade-shape-preference-v1",
        },
        "inference_quality": {
            "status": "unavailable",
            "label": "Inference quality",
            "reason": "Coverage, confidence and stability become available when context-controlled historical inference is estimable.",
            "model_version": "owner-behavior-inference-quality-v1",
        },
        "team_owner_adjusted_value": {
            "status": "not_estimated",
            "label": "Team/Owner-Adjusted Value",
            "reason": "The governed contract is available, but production will not move Market Value until context-controlled owner evidence and bounded cardinal policy are both available.",
            "model_version": "team-owner-adjusted-value-v1",
        },
        "proposal_fit": {
            "status": "proposal_required",
            "label": "Proposal fit",
            "reason": "Proposal-specific Behavioral evidence is evaluated in Trade Center when a concrete bilateral package is submitted.",
            "model_version": "owner-trade-shape-proposal-fit-v1",
        },
        "acceptance_probability": {
            "status": "not_estimated",
            "label": "Acceptance probability",
            "reason": "No calibrated acceptance model has been promoted to production authority. FSFFL exposes evidence instead of fabricating odds.",
        },
    }


def _owner_payload(
    profile: OwnerBehaviorProfile,
    *,
    current_team_id: str | None,
    current_team_name: str | None,
) -> dict[str, object]:
    shapes = [
        ("consolidation", profile.consolidation_trade_count),
        ("diversification", profile.diversification_trade_count),
        ("balanced", profile.balanced_trade_count),
    ]
    counterparties = _sorted_counts(profile.counterparty_trade_counts)
    return {
        "owner_id": profile.owner_id,
        "current_team_id": current_team_id,
        "current_team_name": current_team_name,
        "observed": {
            "as_of": profile.as_of.isoformat(),
            "first_observed_at": profile.first_observed_at.isoformat() if profile.first_observed_at is not None else None,
            "seasons_observed": list(profile.seasons_observed),
            "event_count": profile.event_count,
            "trade_count": profile.trade_count,
            "waiver_count": profile.waiver_count,
            "free_agent_count": profile.free_agent_count,
            "players": {
                "acquired": profile.acquired_player_count,
                "disposed": profile.disposed_player_count,
            },
            "picks": {
                "acquired": profile.acquired_pick_count,
                "disposed": profile.disposed_pick_count,
            },
            "faab": {
                "acquired": profile.acquired_faab,
                "disposed": profile.disposed_faab,
            },
            "positions": {
                "acquired": _sorted_counts(profile.acquired_positions),
                "disposed": _sorted_counts(profile.disposed_positions),
            },
            "trade_shape": [
                {"shape": shape, "count": count, "share": _share(count, profile.trade_count)}
                for shape, count in shapes
            ],
            "counterparties": counterparties,
            "model_version": profile.model_version,
        },
        "inference": {
            "position_preferences": {
                "status": "unavailable",
                "positions": [],
                "reason": _CONTEXT_UNAVAILABLE_REASON,
            },
            "trade_shape_preferences": {
                "status": "unavailable",
                "shapes": [],
                "reason": _CONTEXT_UNAVAILABLE_REASON,
            },
            "quality": {
                "status": "unavailable",
                "event_coverage_rate": None,
                "acquisition_coverage_rate": None,
                "stability": None,
                "reason": "Inference quality is intentionally separate from raw history and cannot be inferred from transaction counts alone.",
            },
        },
        "decision_use": {
            "owner_adjusted_value": {
                "status": "not_estimated",
                "delta_mean": None,
                "interval_low": None,
                "interval_high": None,
                "reason": "Universal FSFFL Market Value remains the baseline until governed owner-specific evidence is estimable.",
            },
            "proposal_fit": {
                "status": "proposal_required",
                "reason": "Open Trade Center and submit a bilateral package to evaluate proposal-specific Behavioral evidence.",
            },
            "acceptance_probability": {
                "status": "not_estimated",
                "probability": None,
                "interval_low": None,
                "interval_high": None,
                "reason": "Acceptance probability remains unavailable until a governed acceptance model is promoted.",
            },
        },
        "provenance": {
            "league_family_id": profile.league_family_id,
            "profile_model_version": profile.model_version,
            "dashboard_model_version": _DASHBOARD_MODEL_VERSION,
        },
    }


def build_behavioral_intelligence_dashboard(
    league_state: LeagueState,
    *,
    profiles: Iterable[OwnerBehaviorProfile],
    current_owner_by_roster: Iterable[tuple[int, str]],
    status: str,
) -> dict[str, object]:
    """Build the production Behavioral dashboard contract without inventing model truth.

    The product layer may organize and label governed evidence, but it does not
    estimate owner preference, adjusted Value, or acceptance probability. Those
    fields remain explicitly unavailable until their authoritative model outputs
    exist in the hosted runtime.
    """

    owners = _team_by_owner(league_state, current_owner_by_roster)
    rows = []
    for profile in profiles:
        team = owners.get(profile.owner_id)
        rows.append(
            _owner_payload(
                profile,
                current_team_id=team[0] if team is not None else None,
                current_team_name=team[1] if team is not None else None,
            )
        )
    rows.sort(key=lambda item: ((item["current_team_name"] or "~").lower(), item["owner_id"]))
    return {
        "status": status,
        "league_id": league_state.league.league_id,
        "state_id": league_state.state_id,
        "as_of": league_state.as_of.isoformat(),
        "owners": rows,
        "capabilities": _capabilities(),
        "model_version": _DASHBOARD_MODEL_VERSION,
    }

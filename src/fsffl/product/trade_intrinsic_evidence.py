"""Read existing raw horizon evidence for a selected legal transaction.

This adapter does not run Forecast/Shapley, create a utility score, convert raw
units into Market units, or change the current trade disposition. The source
owner must validate the exact publication before the evidence is consumed.
"""
from __future__ import annotations

from collections.abc import Callable
from math import isfinite

from fsffl.analytics.dynasty_position_room import build_three_year_intrinsic_player_values
from fsffl.state.models import PlayerAsset
from fsffl.trade_decision import calculate_bilateral_economic_net, summarize_bilateral_trade_economics
from fsffl.trade_decision.models import BilateralTradeProposal
from fsffl.trade_decision.economics import EconomicConcept
from fsffl.value.career_forward_intrinsic import CareerForwardIntrinsicShadowContract
from fsffl.value.models import AssetValueProfile, IntrinsicDynastyValueEstimate, ValueDistribution, ValueScale

from .runtime import UserRuntimeContext


TRADE_INTRINSIC_EVIDENCE_VERSION = "trade-raw-horizon-evidence-v1"
PublicationValidator = Callable[[UserRuntimeContext, object], bool]


def unavailable_trade_intrinsic(reason: str) -> dict[str, object]:
    return {
        "status": "unavailable",
        "reason": reason,
        "three_year": None,
        "career": None,
        "model_version": TRADE_INTRINSIC_EVIDENCE_VERSION,
        "decision_effect": "evidence_only_no_disposition_change",
    }


def build_trade_intrinsic_evidence(
    runtime: UserRuntimeContext,
    proposal: BilateralTradeProposal,
    *,
    record,
    publication_validator: PublicationValidator,
) -> dict[str, object]:
    """Bind same-publication raw asset economics, separately for each horizon.

    Reuse the canonical annual-component validator and Value-owned three-year
    discount. Project only the selected players; the source cohort/fingerprint is
    retained and no new Shapley game is calculated. Package means/net binding use
    existing NEXT-5 contracts. They are asset-ledger deltas, not team utility.
    """
    state = runtime.league_state
    if state is None or runtime.selected_team_id is None:
        return unavailable_trade_intrinsic("A league and managed team are required")
    if runtime.selected_team_id not in {proposal.side_a.team_id, proposal.side_b.team_id}:
        return unavailable_trade_intrinsic("The proposal does not include the managed team")
    if proposal.as_of != state.as_of:
        return unavailable_trade_intrinsic("The proposal does not match the current State time")
    if (
        record is None
        or getattr(record, "user_id", None) != runtime.user_id
        or getattr(record, "league_state_id", None) != state.state_id
        or getattr(getattr(record, "status", None), "value", None) != "completed"
        or not runtime.publication_generation_id
        or not isinstance(getattr(record, "contract", None), CareerForwardIntrinsicShadowContract)
        or not getattr(record, "intrinsic_input_fingerprint", None)
    ):
        return unavailable_trade_intrinsic("Completed matching-State raw Career evidence is unavailable")
    if not publication_validator(runtime, record):
        return unavailable_trade_intrinsic("Raw Intrinsic evidence does not match the published generation")

    contract = record.contract
    # Preserve the original game and dependency identity. This projection only
    # bounds validation/allocation to the transaction, not a revalued cohort.
    selected = {
        asset.player_id
        for leg in (proposal.side_a, proposal.side_b)
        for asset in leg.sends
        if isinstance(asset, PlayerAsset)
    }
    source_rows = tuple(row for row in contract.estimates if row.player_id in selected)
    if contract.player_count != len(contract.estimates) or len({r.player_id for r in contract.estimates}) != len(contract.estimates):
        return unavailable_trade_intrinsic("The raw source cohort identity is inconsistent")
    three_year = {}
    if source_rows:
        projected = contract.model_copy(update={"estimates": source_rows, "player_count": len(source_rows)})
        three_year = {
            row.player_id: row.raw_intrinsic_value
            for row in build_three_year_intrinsic_player_values(
                state, career_forward=projected, career_evidence_state_id=record.league_state_id
            )
        }
    career = {}
    for row in source_rows:
        if row.player_id not in three_year:
            continue
        parts = (row.current_intrinsic_raw_y1_y3, row.long_horizon_raw_y4_y7_reference, row.terminal_raw_y8_plus_reference)
        if (
            all(isfinite(value) for value in (*parts, row.raw_career_forward_reference))
            and abs(sum(parts) - row.raw_career_forward_reference) <= 1e-9
        ):
            career[row.player_id] = row.raw_career_forward_reference

    def horizon(values: dict[str, float], name: str) -> dict[str, object]:
        # This declares the native unit/reference, not a conversion or display
        # ruler. Same-State/source and horizon are required for additive binding.
        scale = ValueScale(
            scale_id=f"raw-shapley:{name}:{state.state_id}:{contract.input_fingerprint}",
            version=contract.contract_version,
            unit_label=f"{name} raw Shapley contribution",
        )
        profiles = {
            player_id: AssetValueProfile(
                asset_id=player_id,
                asset_kind="player",
                intrinsic_value=IntrinsicDynastyValueEstimate(
                    asset_id=player_id,
                    asset_kind="player",
                    distribution=ValueDistribution(mean=value),
                    scale=scale,
                    as_of=state.as_of,
                    model_version=contract.model_version,
                    conversion_model_version="identity-native-raw-horizon-v1",
                ),
            )
            for player_id, value in values.items()
        }
        economics = summarize_bilateral_trade_economics(proposal, profiles)
        net = calculate_bilateral_economic_net(economics)
        sides = (net.side_a.intrinsic, net.side_b.intrinsic)
        return {
            "status": "complete" if all(side.status.value == "complete" for side in sides) else "incomplete",
            "side_a": net.side_a.intrinsic.model_dump(mode="json"),
            "side_b": net.side_b.intrinsic.model_dump(mode="json"),
            "missing_evidence": {
                "side_a": [item.model_dump(mode="json") for item in economics.side_a.missing_evidence if item.concept is EconomicConcept.INTRINSIC_VALUE],
                "side_b": [item.model_dump(mode="json") for item in economics.side_b.missing_evidence if item.concept is EconomicConcept.INTRINSIC_VALUE],
            },
            "package_uncertainty": None,
            "uncertainty_reason": "Package covariance and horizon-wide outcome intervals are not authorized; source uncertainty remains separate",
        }

    horizons = {"three_year": horizon(three_year, "three_year"), "career": horizon(career, "career")}
    return {
        "status": "complete" if all(h["status"] == "complete" for h in horizons.values()) else "partial",
        **horizons,
        "side_a_team_id": proposal.side_a.team_id,
        "side_b_team_id": proposal.side_b.team_id,
        "source": {
            "league_state_id": state.state_id,
            "publication_generation_id": runtime.publication_generation_id,
            "input_fingerprint": contract.input_fingerprint,
            "dependency_fingerprint": record.intrinsic_input_fingerprint,
            "source_player_count": contract.player_count,
            "selected_player_count": len(source_rows),
            "model_version": contract.model_version,
            "contract_version": contract.contract_version,
            "lineup_capacity_signature": contract.lineup_capacity_signature,
            "three_year_basis": "career_current_y1_y3_components_with_canonical_discount",
            "career_basis": contract.aggregation,
            "scoring_coordinate_limitation": contract.scoring_coordinate_limitation,
            "ignored_long_term_residual_rule_stats": list(contract.ignored_long_term_residual_rule_stats),
        },
        "input_assumptions": {pid: contract.player_input_assumptions[pid] for pid in selected if pid in contract.player_input_assumptions},
        "semantics": "raw_asset_contribution_ledger_not_team_specific_utility_or_market_discount",
        "decision_effect": "evidence_only_no_disposition_change",
        "model_version": TRADE_INTRINSIC_EVIDENCE_VERSION,
    }

"""Read existing raw horizon evidence for a selected legal transaction.

This adapter does not run Forecast/Shapley, create a utility score, convert raw
units into Market units, or change the current trade disposition. The source
owner must validate the exact publication before the evidence is consumed.
"""
from __future__ import annotations

from collections.abc import Callable
from math import isfinite
from dataclasses import dataclass
from datetime import datetime
from collections.abc import Mapping
from types import MappingProxyType
from weakref import ReferenceType, ref

from fsffl.analytics.dynasty_position_room import build_three_year_intrinsic_player_values
from fsffl.state.models import FaabAsset, PickAsset, PlayerAsset, LeagueState
from fsffl.trade_decision import calculate_bilateral_economic_net, summarize_bilateral_trade_economics
from fsffl.trade_decision.models import BilateralTradeProposal
from fsffl.trade_decision.economics import EconomicConcept
from fsffl.trade_decision.intrinsic_roster_economics import adjust_bilateral_intrinsic_net_for_mandatory_cuts
from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution
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


@dataclass(frozen=True)
class PublishedTradeHorizonValues:
    """Request-local projection of published evidence, with no retained source graph."""
    user_id: str
    selected_team_id: str
    as_of: datetime
    state_ref: ReferenceType[LeagueState]
    source: Mapping[str, object]
    scales: Mapping[str, ValueScale]
    values: Mapping[str, Mapping[str, float]]
    covered_player_ids: frozenset[str]
    input_assumptions: Mapping[str, str]


def read_published_trade_horizon_values(
    runtime: UserRuntimeContext, *, player_ids: frozenset[str], record,
    publication_validator: PublicationValidator,
) -> PublishedTradeHorizonValues:
    """Validate once and project existing native values for a bounded owned cohort.

    The caller supplies the existing memory-only producer record. This never
    restores, fetches or recalculates it, and does not fabricate a trade to read it.
    """
    state = runtime.league_state
    if state is None or runtime.selected_team_id is None:
        raise ValueError("A league and managed team are required")
    if (
        record is None
        or getattr(record, "user_id", None) != runtime.user_id
        or getattr(record, "league_state_id", None) != state.state_id
        or getattr(getattr(record, "status", None), "value", None) != "completed"
        or not runtime.publication_generation_id
        or not isinstance(getattr(record, "contract", None), CareerForwardIntrinsicShadowContract)
        or not getattr(record, "intrinsic_input_fingerprint", None)
    ):
        raise ValueError("Completed matching-State raw Career evidence is unavailable")
    if not publication_validator(runtime, record):
        raise ValueError("Raw Intrinsic evidence does not match the published generation")

    contract = record.contract
    state_id = state.state_id
    selected = player_ids
    source_rows = tuple(row for row in contract.estimates if row.player_id in selected)
    if contract.player_count != len(contract.estimates) or len({r.player_id for r in contract.estimates}) != len(contract.estimates):
        raise ValueError("The raw source cohort identity is inconsistent")
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

    source = {
            "league_state_id": state_id,
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
        }
    scales = {name: ValueScale(
        scale_id=f"raw-shapley:{name}:{state_id}:{contract.input_fingerprint}",
        version=contract.contract_version, unit_label=f"{name} raw Shapley contribution",
    ) for name in ("three_year", "career")}
    return PublishedTradeHorizonValues(
        user_id=runtime.user_id, selected_team_id=runtime.selected_team_id, as_of=state.as_of, state_ref=ref(state),
        source=MappingProxyType(source), scales=MappingProxyType(scales),
        values=MappingProxyType({"three_year": MappingProxyType(three_year), "career": MappingProxyType(career)}),
        covered_player_ids=frozenset(row.player_id for row in source_rows),
        input_assumptions=MappingProxyType({pid: contract.player_input_assumptions[pid]
            for pid in selected if pid in contract.player_input_assumptions}),
    )


def _selected_players(proposal, roster_resolutions):
    selected = {asset.player_id for leg in (proposal.side_a, proposal.side_b)
                for asset in leg.sends if isinstance(asset, PlayerAsset)}
    if roster_resolutions is not None:
        selected.update(cut.player_id for resolution in roster_resolutions for cut in resolution.cuts)
    return selected


def published_horizons_match_runtime(runtime, read):
    state = runtime.league_state
    return (state is not None and runtime.user_id == read.user_id
        and runtime.selected_team_id == read.selected_team_id
        and read.state_ref() is state
        and runtime.publication_generation_id == read.source["publication_generation_id"]
        and state.as_of == read.as_of)


def build_trade_intrinsic_evidence(
    runtime: UserRuntimeContext, proposal: BilateralTradeProposal, *, record,
    publication_validator: PublicationValidator,
    roster_resolutions: tuple[TeamRosterLegalityResolution, ...] | None = None,
) -> dict[str, object]:
    """Read existing publication and bind the selected transaction's raw ledgers."""
    try:
        read = read_published_trade_horizon_values(runtime,
            player_ids=frozenset(_selected_players(proposal, roster_resolutions)),
            record=record, publication_validator=publication_validator)
    except ValueError as exc:
        return unavailable_trade_intrinsic(str(exc))
    return bind_trade_intrinsic_values(runtime, proposal, read, roster_resolutions=roster_resolutions)


def bind_trade_intrinsic_values(
    runtime: UserRuntimeContext, proposal: BilateralTradeProposal, read: PublishedTradeHorizonValues,
    *, roster_resolutions: tuple[TeamRosterLegalityResolution, ...] | None = None,
) -> dict[str, object]:
    """Reuse one publication projection across bounded candidate analyses."""
    state = runtime.league_state
    if (not published_horizons_match_runtime(runtime, read) or proposal.as_of != read.as_of
        or runtime.selected_team_id not in {proposal.side_a.team_id, proposal.side_b.team_id}):
        return unavailable_trade_intrinsic("Raw horizon projection does not match the request identity")
    selected = _selected_players(proposal, roster_resolutions)
    non_player_ids = {asset.pick_id if isinstance(asset, PickAsset) else f"faab:{asset.amount}"
                     for leg in (proposal.side_a, proposal.side_b) for asset in leg.sends
                     if isinstance(asset, (PickAsset, FaabAsset))}
    if selected & non_player_ids:
        return unavailable_trade_intrinsic("Asset identifiers are ambiguous across asset kinds")
    def horizon(values: dict[str, float], name: str) -> dict[str, object]:
        # This declares the native unit/reference, not a conversion or display
        # ruler. Same-State/source and horizon are required for additive binding.
        scale = read.scales[name]
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
                    model_version=str(read.source["model_version"]),
                    conversion_model_version="identity-native-raw-horizon-v1",
                ),
            )
            for player_id, value in values.items() if player_id in selected
        }
        economics = summarize_bilateral_trade_economics(proposal, profiles)
        net = calculate_bilateral_economic_net(economics)
        sides = (net.side_a.intrinsic, net.side_b.intrinsic)
        adjusted = None
        if roster_resolutions is not None:
            adjusted = adjust_bilateral_intrinsic_net_for_mandatory_cuts(
                net, roster_resolutions, cut_values=values, scale=scale,
            ).model_dump(mode="json")
        return {
            "status": "complete" if all(side.status.value == "complete" for side in sides) else "incomplete",
            "side_a": net.side_a.intrinsic.model_dump(mode="json"),
            "side_b": net.side_b.intrinsic.model_dump(mode="json"),
            "roster_adjusted": adjusted,
            "missing_evidence": {
                "side_a": [item.model_dump(mode="json") for item in economics.side_a.missing_evidence if item.concept is EconomicConcept.INTRINSIC_VALUE],
                "side_b": [item.model_dump(mode="json") for item in economics.side_b.missing_evidence if item.concept is EconomicConcept.INTRINSIC_VALUE],
            },
            "package_uncertainty": None,
            "uncertainty_reason": "Package covariance and horizon-wide outcome intervals are not authorized; source uncertainty remains separate",
        }

    horizons = {"three_year": horizon(read.values["three_year"], "three_year"), "career": horizon(read.values["career"], "career")}
    return {
        "status": "complete" if all(h["status"] == "complete" for h in horizons.values()) else "partial",
        **horizons,
        "side_a_team_id": proposal.side_a.team_id,
        "side_b_team_id": proposal.side_b.team_id,
        "source": {**read.source, "selected_player_count": len(selected & read.covered_player_ids)},
        "input_assumptions": {pid: read.input_assumptions[pid] for pid in selected if pid in read.input_assumptions},
        "semantics": "raw_asset_contribution_ledger_not_team_specific_utility_or_market_discount",
        "decision_effect": "evidence_only_no_disposition_change",
        "model_version": TRADE_INTRINSIC_EVIDENCE_VERSION,
    }

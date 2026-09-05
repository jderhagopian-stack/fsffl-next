from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from fsffl.state.models import FrozenModel
from fsffl.trade_decision import BilateralTradeProposal, TradeLeg

from .frontier import canonical_frontier_point_id
from .trade_universe import TradePackageSeed


class TradePairSearchPolicy(FrozenModel):
    max_candidate_pairs: Annotated[int, Field(ge=1, le=100000)] = 5000


class TradeProposalSeed(FrozenModel):
    point_id: str
    proposal: BilateralTradeProposal
    focal_package_id: str
    counterparty_package_id: str

    @model_validator(mode="after")
    def validate_seed(self) -> "TradeProposalSeed":
        expected = canonical_frontier_point_id(
            self.focal_package_id,
            self.counterparty_package_id,
        )
        if self.point_id != expected:
            raise ValueError("trade proposal seed point_id must be canonical")
        if self.proposal.proposal_id != self.point_id:
            raise ValueError("proposal_id must match search point identity")
        return self


class TradePairGenerationResult(FrozenModel):
    proposals: tuple[TradeProposalSeed, ...]
    total_possible_pairs: Annotated[int, Field(ge=0)]
    truncated: bool
    search_model_version: str = "next6-trade-pair-generation-v1"

    @model_validator(mode="after")
    def validate_result(self) -> "TradePairGenerationResult":
        if not self.search_model_version.strip():
            raise ValueError("search_model_version cannot be blank")
        ids = [seed.point_id for seed in self.proposals]
        if len(ids) != len(set(ids)):
            raise ValueError("generated trade proposal ids must be unique")
        if len(self.proposals) > self.total_possible_pairs:
            raise ValueError("generated proposals cannot exceed total possible pairs")
        if self.truncated != (len(self.proposals) < self.total_possible_pairs):
            raise ValueError("truncation flag must reflect generated coverage")
        return self


def generate_bilateral_trade_proposals(
    focal_packages: tuple[TradePackageSeed, ...],
    counterparty_packages: tuple[TradePackageSeed, ...],
    *,
    as_of: datetime,
    policy: TradePairSearchPolicy = TradePairSearchPolicy(),
    proposal_model_version: str = "next6-generated-trade-proposal-v1",
    search_model_version: str = "next6-trade-pair-generation-v1",
) -> TradePairGenerationResult:
    """Generate a deterministic bounded package cross-product with visible coverage.

    This is structural enumeration only. The cap is a compute budget, not a value
    judgment. If the cross-product exceeds the budget, `truncated=True` prevents
    downstream consumers from mistaking partial exploration for a complete search.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    if not proposal_model_version.strip() or not search_model_version.strip():
        raise ValueError("model versions cannot be blank")

    if focal_packages:
        focal_team_ids = {package.team_id for package in focal_packages}
        if len(focal_team_ids) != 1:
            raise ValueError("focal packages must belong to one team")
    else:
        focal_team_ids = set()
    if counterparty_packages:
        counterparty_team_ids = {package.team_id for package in counterparty_packages}
        if len(counterparty_team_ids) != 1:
            raise ValueError("counterparty packages must belong to one team")
    else:
        counterparty_team_ids = set()
    if focal_team_ids and counterparty_team_ids and focal_team_ids == counterparty_team_ids:
        raise ValueError("bilateral proposal generation requires distinct teams")

    ordered_focal = tuple(sorted(focal_packages, key=lambda package: package.canonical_id))
    ordered_counterparty = tuple(
        sorted(counterparty_packages, key=lambda package: package.canonical_id)
    )
    total_possible = len(ordered_focal) * len(ordered_counterparty)
    seeds: list[TradeProposalSeed] = []

    for focal in ordered_focal:
        for counterparty in ordered_counterparty:
            if len(seeds) >= policy.max_candidate_pairs:
                break
            point_id = canonical_frontier_point_id(
                focal.canonical_id,
                counterparty.canonical_id,
            )
            proposal = BilateralTradeProposal(
                proposal_id=point_id,
                as_of=as_of,
                side_a=TradeLeg(team_id=focal.team_id, sends=focal.assets),
                side_b=TradeLeg(team_id=counterparty.team_id, sends=counterparty.assets),
                model_version=proposal_model_version,
            )
            seeds.append(
                TradeProposalSeed(
                    point_id=point_id,
                    proposal=proposal,
                    focal_package_id=focal.canonical_id,
                    counterparty_package_id=counterparty.canonical_id,
                )
            )
        if len(seeds) >= policy.max_candidate_pairs:
            break

    return TradePairGenerationResult(
        proposals=tuple(seeds),
        total_possible_pairs=total_possible,
        truncated=len(seeds) < total_possible,
        search_model_version=search_model_version,
    )

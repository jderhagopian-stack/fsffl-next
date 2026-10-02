from __future__ import annotations

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, LeagueState
from fsffl.team_utility.future_pick import PickSlotProbability
from fsffl.team_utility.simulation import RegularSeasonSimulationResult
from fsffl.value.pick_variants import PickVariant, PickVariantMarketValue


class SimulationInformedPickProjection(FrozenModel):
    """Governed next-draft pick projection keyed to the pick's origin team.

    Exact slot probabilities are primary Simulation authority. The current owner
    remains a separate State coordinate. Early/mid/late probabilities are retained
    only as summaries for existing market-variant composition.
    """

    pick_id: str
    original_team_id: str
    owner_team_id: str
    season: int
    round: int
    slot_probabilities: tuple[PickSlotProbability, ...]
    expected_slot: float = Field(ge=1.0)
    median_slot: int = Field(ge=1)
    expected_slot_percentile_from_earliest: float = Field(ge=0.0, le=1.0)
    early_probability: float = Field(ge=0.0, le=1.0)
    mid_probability: float = Field(ge=0.0, le=1.0)
    late_probability: float = Field(ge=0.0, le=1.0)
    expected_variant_market_value: float | None = Field(default=None, ge=0.0, le=10000.0)
    low_variant_market_value: float | None = Field(default=None, ge=0.0, le=10000.0)
    high_variant_market_value: float | None = Field(default=None, ge=0.0, le=10000.0)
    simulation_count: int = Field(ge=1)
    simulation_model_version: str
    draft_order_policy_id: str
    draft_order_policy_version: str
    draft_order_policy_authority: str
    draft_order_projection_model_version: str
    market_variant_model_version: str | None = None
    authority_status: str = "governed_team_origin_pick_slot_distribution"
    model_version: str = "next8-next-season-pick-location-v3:explicit-or-derived-draft-order:exact-origin-slot"

    @model_validator(mode="after")
    def validate_projection(self) -> "SimulationInformedPickProjection":
        probability_sum = self.early_probability + self.mid_probability + self.late_probability
        if abs(probability_sum - 1.0) > 1e-9:
            raise ValueError("pick location summary probabilities must sum to one")
        if abs(sum(item.probability for item in self.slot_probabilities) - 1.0) > 1e-9:
            raise ValueError("exact pick slot probabilities must sum to one")
        identifiers = (
            self.pick_id,
            self.original_team_id,
            self.owner_team_id,
            self.simulation_model_version,
            self.draft_order_policy_id,
            self.draft_order_policy_version,
            self.draft_order_policy_authority,
            self.draft_order_projection_model_version,
        )
        if any(not value.strip() for value in identifiers):
            raise ValueError("pick location identifiers cannot be blank")
        return self


def _variant_values(
    variants: tuple[PickVariantMarketValue, ...],
    *,
    season: int,
    round_number: int,
) -> dict[PickVariant, PickVariantMarketValue]:
    return {
        row.variant: row
        for row in variants
        if row.season == season and row.round == round_number
    }


def build_next_season_pick_projections(
    league_state: LeagueState,
    simulation: RegularSeasonSimulationResult,
    *,
    variant_values: tuple[PickVariantMarketValue, ...] = (),
) -> tuple[SimulationInformedPickProjection, ...]:
    next_season = league_state.league.season + 1
    distribution_by_origin = {
        row.original_team_id: row
        for row in getattr(simulation, "future_pick_distributions", ())
        if row.draft_season == next_season
    }
    if not distribution_by_origin:
        return ()

    owner_by_pick = {
        row.pick_id: row.owner_team_id for row in league_state.pick_ownership
    }
    output: list[SimulationInformedPickProjection] = []
    for pick in sorted(
        league_state.draft_picks,
        key=lambda item: (item.season, item.round, item.pick_id),
    ):
        if pick.season != next_season:
            continue
        distribution = distribution_by_origin.get(pick.original_team_id)
        if distribution is None:
            continue
        owner_team_id = owner_by_pick.get(pick.pick_id)
        if owner_team_id is None:
            raise ValueError("canonical pick ownership is required for projected picks")

        market = _variant_values(
            variant_values,
            season=pick.season,
            round_number=pick.round,
        )
        expected_value = None
        low_value = None
        high_value = None
        market_version = None
        if all(variant in market for variant in PickVariant):
            scores = {variant: market[variant].score for variant in PickVariant}
            expected_value = (
                distribution.early_probability * scores[PickVariant.EARLY]
                + distribution.mid_probability * scores[PickVariant.MID]
                + distribution.late_probability * scores[PickVariant.LATE]
            )
            low_value = min(scores.values())
            high_value = max(scores.values())
            market_version = next(iter(market.values())).model_version

        output.append(
            SimulationInformedPickProjection(
                pick_id=pick.pick_id,
                original_team_id=pick.original_team_id,
                owner_team_id=owner_team_id,
                season=pick.season,
                round=pick.round,
                slot_probabilities=distribution.slot_probabilities,
                expected_slot=distribution.expected_slot,
                median_slot=distribution.median_slot,
                expected_slot_percentile_from_earliest=(
                    distribution.expected_slot_percentile_from_earliest
                ),
                early_probability=distribution.early_probability,
                mid_probability=distribution.mid_probability,
                late_probability=distribution.late_probability,
                expected_variant_market_value=expected_value,
                low_variant_market_value=low_value,
                high_variant_market_value=high_value,
                simulation_count=distribution.simulation_count,
                simulation_model_version=distribution.simulation_model_version,
                draft_order_policy_id=distribution.draft_order_policy_id,
                draft_order_policy_version=distribution.draft_order_policy_version,
                draft_order_policy_authority=(
                    distribution.draft_order_policy_authority
                ),
                draft_order_projection_model_version=(
                    distribution.draft_order_projection_model_version
                ),
                market_variant_model_version=market_version,
            )
        )
    return tuple(output)

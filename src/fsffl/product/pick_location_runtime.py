from __future__ import annotations

from pydantic import Field, model_validator

from fsffl.state.models import FrozenModel, LeagueState
from fsffl.team_utility.simulation import RegularSeasonSimulationResult, TeamFinishDistribution
from fsffl.value.pick_variants import PickVariant, PickVariantMarketValue


class SimulationInformedPickProjection(FrozenModel):
    """Diagnostic next-season pick projection from Simulation plus market variants.

    This does not replace authoritative generic Cardinal Value. It makes the known
    original-team context and uncertainty explicit so the challenger can be tested
    before any production promotion.
    """

    pick_id: str
    original_team_id: str
    season: int
    round: int
    early_probability: float = Field(ge=0.0, le=1.0)
    mid_probability: float = Field(ge=0.0, le=1.0)
    late_probability: float = Field(ge=0.0, le=1.0)
    expected_regular_season_finish: float = Field(ge=1.0)
    expected_variant_market_value: float | None = Field(default=None, ge=0.0, le=10000.0)
    low_variant_market_value: float | None = Field(default=None, ge=0.0, le=10000.0)
    high_variant_market_value: float | None = Field(default=None, ge=0.0, le=10000.0)
    simulation_count: int = Field(ge=1)
    simulation_model_version: str
    market_variant_model_version: str | None = None
    authority_status: str = "diagnostic_simulation_informed_pick_projection"
    model_version: str = "next8-next-season-pick-location-v1"

    @model_validator(mode="after")
    def validate_projection(self) -> "SimulationInformedPickProjection":
        probability_sum = self.early_probability + self.mid_probability + self.late_probability
        if abs(probability_sum - 1.0) > 1e-9:
            raise ValueError("pick location probabilities must sum to one")
        if not self.pick_id.strip() or not self.original_team_id.strip() or not self.simulation_model_version.strip():
            raise ValueError("pick location identifiers cannot be blank")
        return self


def _tier_probabilities(distribution: TeamFinishDistribution) -> tuple[float, float, float]:
    """Map regular-season rank to inverse early/mid/late draft-location tiers.

    The best third of regular-season finishes maps to late-pick evidence, the
    middle third to mid, and the worst third to early. This is intentionally a
    tier proxy rather than exact rookie draft order because playoff/draft-order
    rules are not yet encoded in canonical league rules.
    """

    team_count = len(distribution.rank_probabilities)
    early = 0.0
    mid = 0.0
    late = 0.0
    for index, probability in enumerate(distribution.rank_probabilities):
        rank = index + 1
        quantile = (rank - 0.5) / team_count
        if quantile <= 1.0 / 3.0:
            late += probability
        elif quantile <= 2.0 / 3.0:
            mid += probability
        else:
            early += probability
    return early, mid, late


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
    finish_by_team = {row.team_id: row for row in simulation.finish_distributions}
    output: list[SimulationInformedPickProjection] = []
    for pick in sorted(league_state.draft_picks, key=lambda item: (item.season, item.round, item.pick_id)):
        if pick.season != next_season:
            continue
        finish = finish_by_team.get(pick.original_team_id)
        if finish is None:
            continue
        early, mid, late = _tier_probabilities(finish)
        market = _variant_values(variant_values, season=pick.season, round_number=pick.round)
        expected_value = None
        low_value = None
        high_value = None
        market_version = None
        if all(variant in market for variant in PickVariant):
            scores = {variant: market[variant].score for variant in PickVariant}
            expected_value = (
                early * scores[PickVariant.EARLY]
                + mid * scores[PickVariant.MID]
                + late * scores[PickVariant.LATE]
            )
            low_value = min(scores.values())
            high_value = max(scores.values())
            market_version = next(iter(market.values())).model_version
        output.append(
            SimulationInformedPickProjection(
                pick_id=pick.pick_id,
                original_team_id=pick.original_team_id,
                season=pick.season,
                round=pick.round,
                early_probability=early,
                mid_probability=mid,
                late_probability=late,
                expected_regular_season_finish=finish.expected_finish,
                expected_variant_market_value=expected_value,
                low_variant_market_value=low_value,
                high_variant_market_value=high_value,
                simulation_count=finish.simulation_count,
                simulation_model_version=finish.simulation_model_version,
                market_variant_model_version=market_version,
            )
        )
    return tuple(output)

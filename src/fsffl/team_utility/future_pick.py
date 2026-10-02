from __future__ import annotations

from math import ceil
from typing import Annotated, Literal

from pydantic import Field, model_validator

from fsffl.state.draft_order_policy import DraftOrderPolicyEvidence
from fsffl.state.models import FrozenModel


STANDARD_DRAFT_ORDER_MECHANISM_V1 = (
    "standard_record_h2h_pf_then_playoff_elimination_v1"
)
STANDARD_DRAFT_ORDER_POLICY_ID = "governed-standard-draft-order-fallback"
STANDARD_DRAFT_ORDER_POLICY_VERSION = "v1"
STANDARD_REGULAR_SEASON_TIEBREAK = (
    "worse_record_then_resolvable_head_to_head_then_lower_points_for"
)
STANDARD_PLAYOFF_ORDER = (
    "round_eliminated_then_regular_season_tiebreaks_runner_up_champion"
)


class PickSlotProbability(FrozenModel):
    slot_in_round: Annotated[int, Field(ge=1)]
    probability: Annotated[float, Field(ge=0.0, le=1.0)]


class TeamOriginFuturePickDistribution(FrozenModel):
    """Simulation-owned next-draft slot distribution for one origin team."""

    draft_season: Annotated[int, Field(ge=1900)]
    original_team_id: str
    slot_probabilities: tuple[PickSlotProbability, ...]
    expected_slot: Annotated[float, Field(ge=1.0)]
    median_slot: Annotated[int, Field(ge=1)]
    expected_slot_percentile_from_earliest: Annotated[
        float, Field(ge=0.0, le=1.0)
    ]
    early_probability: Annotated[float, Field(ge=0.0, le=1.0)]
    mid_probability: Annotated[float, Field(ge=0.0, le=1.0)]
    late_probability: Annotated[float, Field(ge=0.0, le=1.0)]
    simulation_count: Annotated[int, Field(ge=1)]
    simulation_model_version: str
    draft_order_policy_id: str
    draft_order_policy_version: str
    draft_order_policy_authority: Literal[
        "explicit_league_rule", "derived_standard_fallback"
    ]
    draft_order_projection_model_version: str
    provenance: str

    @model_validator(mode="after")
    def validate_distribution(self) -> "TeamOriginFuturePickDistribution":
        for value in (
            self.original_team_id,
            self.simulation_model_version,
            self.draft_order_policy_id,
            self.draft_order_policy_version,
            self.draft_order_projection_model_version,
            self.provenance,
        ):
            if not value.strip():
                raise ValueError("future-pick identifiers/provenance cannot be blank")
        if not self.slot_probabilities:
            raise ValueError("future-pick distribution requires slot probabilities")
        slots = [row.slot_in_round for row in self.slot_probabilities]
        if len(slots) != len(set(slots)):
            raise ValueError("future-pick slot probabilities must have unique slots")
        if abs(sum(row.probability for row in self.slot_probabilities) - 1.0) > 1e-9:
            raise ValueError("future-pick slot probabilities must sum to one")
        if abs(
            self.early_probability + self.mid_probability + self.late_probability - 1.0
        ) > 1e-9:
            raise ValueError("future-pick tier summaries must sum to one")
        if self.median_slot > max(slots):
            raise ValueError("future-pick median slot exceeds supported slots")
        return self


class SupportedFuturePickDraftOrder(FrozenModel):
    """Compiled explicit league rule or governed standard fallback."""

    draft_season: Annotated[int, Field(ge=1900)]
    policy_id: str
    policy_version: str
    authority: Literal["explicit_league_rule", "derived_standard_fallback"]
    non_playoff_tiebreak_policy: str
    playoff_order_policy: str
    non_playoff_team_count: Annotated[int, Field(ge=1)]
    playoff_team_count: Annotated[int, Field(ge=1)]
    placement_games_affect_order: bool
    placement_games_policy: str | None = None
    origin_slot_carries_across_rounds: bool
    provenance: str

    @model_validator(mode="after")
    def validate_policy(self) -> "SupportedFuturePickDraftOrder":
        if (
            self.placement_games_affect_order
            and not (self.placement_games_policy or "").strip()
        ):
            raise ValueError(
                "placement-games draft order requires an explicit placement policy"
            )
        return self


def _standard_policy(
    *,
    draft_season: int,
    team_count: int,
    playoff_team_count: int | None,
) -> SupportedFuturePickDraftOrder:
    if playoff_team_count is None:
        raise ValueError(
            "governed standard draft-order fallback requires playoff_team_count"
        )
    if playoff_team_count < 1 or playoff_team_count >= team_count:
        raise ValueError(
            "governed standard draft-order fallback requires both playoff and "
            "non-playoff teams"
        )
    return SupportedFuturePickDraftOrder(
        draft_season=draft_season,
        policy_id=STANDARD_DRAFT_ORDER_POLICY_ID,
        policy_version=STANDARD_DRAFT_ORDER_POLICY_VERSION,
        authority="derived_standard_fallback",
        non_playoff_tiebreak_policy=STANDARD_REGULAR_SEASON_TIEBREAK,
        playoff_order_policy=STANDARD_PLAYOFF_ORDER,
        non_playoff_team_count=team_count - playoff_team_count,
        playoff_team_count=playoff_team_count,
        placement_games_affect_order=False,
        placement_games_policy=None,
        origin_slot_carries_across_rounds=True,
        provenance=(
            "governed standard fallback; explicit league draft-order evidence absent; "
            "non-playoff=worse regular-season record -> resolvable head-to-head -> "
            "lower Points For; playoff=round eliminated then same regular-season "
            "tiebreaks; runner-up then champion; placement games ignored unless "
            "explicitly governed"
        ),
    )


def compile_supported_future_pick_policy(
    policy: DraftOrderPolicyEvidence | None,
    *,
    draft_season: int,
    team_count: int,
    playoff_team_count: int | None,
) -> SupportedFuturePickDraftOrder:
    """Use explicit league rules first; otherwise derive the governed standard.

    An explicit but unsupported custom rule never gets silently replaced by the
    fallback. The fallback is used only when no explicit policy evidence exists.
    """

    if policy is None:
        return _standard_policy(
            draft_season=draft_season,
            team_count=team_count,
            playoff_team_count=playoff_team_count,
        )
    if policy.draft_season != draft_season:
        raise ValueError("explicit draft-order policy season conflicts with Simulation")
    if policy.mechanism != STANDARD_DRAFT_ORDER_MECHANISM_V1:
        raise ValueError("unsupported explicit future-pick draft-order mechanism")

    parameters = {item.name: item.value for item in policy.parameters}
    required = {
        "non_playoff_tiebreak_policy": STANDARD_REGULAR_SEASON_TIEBREAK,
        "playoff_order_policy": STANDARD_PLAYOFF_ORDER,
        "origin_slot_carries_across_rounds": True,
    }
    supported_parameter_names = set(required) | {
        "placement_games_affect_order",
        "placement_games_policy",
    }
    unsupported_parameter_names = sorted(
        set(parameters) - supported_parameter_names
    )
    if unsupported_parameter_names:
        raise ValueError(
            "unsupported explicit future-pick parameter: "
            f"{unsupported_parameter_names[0]}"
        )
    for name, expected in required.items():
        if parameters.get(name) != expected:
            raise ValueError(f"unsupported explicit future-pick parameter: {name}")

    if playoff_team_count is None:
        raise ValueError("explicit future-pick policy requires playoff_team_count")
    non_playoff_count = team_count - playoff_team_count
    if non_playoff_count < 1:
        raise ValueError("future-pick policy requires non-playoff teams")

    placement_affects = bool(parameters.get("placement_games_affect_order", False))
    placement_policy = parameters.get("placement_games_policy")
    if placement_affects:
        if placement_policy != "six_team_standard_placement_games_v1":
            raise ValueError(
                "unsupported explicit future-pick placement-games policy"
            )
        if playoff_team_count != 6:
            raise ValueError(
                "supported explicit placement-games policy requires six-team playoffs"
            )

    return SupportedFuturePickDraftOrder(
        draft_season=draft_season,
        policy_id=policy.policy_id,
        policy_version=policy.version,
        authority="explicit_league_rule",
        non_playoff_tiebreak_policy=str(
            parameters["non_playoff_tiebreak_policy"]
        ),
        playoff_order_policy=str(parameters["playoff_order_policy"]),
        non_playoff_team_count=non_playoff_count,
        playoff_team_count=playoff_team_count,
        placement_games_affect_order=placement_affects,
        placement_games_policy=(
            str(placement_policy) if placement_policy is not None else None
        ),
        origin_slot_carries_across_rounds=True,
        provenance=(
            f"{policy.provenance.source}; explicit policy="
            f"{policy.policy_id}:{policy.version}; "
            f"available_at={policy.available_at.isoformat()}"
        ),
    )


def build_team_origin_future_pick_distribution(
    *,
    draft_season: int,
    original_team_id: str,
    slot_counts: tuple[float, ...],
    simulation_count: int,
    simulation_model_version: str,
    policy: SupportedFuturePickDraftOrder,
    draft_order_projection_model_version: str,
) -> TeamOriginFuturePickDistribution:
    if simulation_count < 1 or abs(sum(slot_counts) - simulation_count) > 1e-8:
        raise ValueError("future-pick slot counts must cover every simulation")
    team_count = len(slot_counts)
    if team_count < 2:
        raise ValueError("future-pick distribution requires multiple draft slots")

    probabilities = tuple(
        PickSlotProbability(
            slot_in_round=index,
            probability=count / simulation_count,
        )
        for index, count in enumerate(slot_counts, start=1)
        if count
    )
    expected_slot = sum(
        row.slot_in_round * row.probability for row in probabilities
    )
    cumulative = 0.0
    median_slot = team_count
    for row in probabilities:
        cumulative += row.probability
        if cumulative >= 0.5:
            median_slot = row.slot_in_round
            break

    early_end = ceil(team_count / 3)
    mid_end = ceil(2 * team_count / 3)
    early = sum(
        row.probability for row in probabilities if row.slot_in_round <= early_end
    )
    mid = sum(
        row.probability
        for row in probabilities
        if early_end < row.slot_in_round <= mid_end
    )
    late = sum(
        row.probability for row in probabilities if row.slot_in_round > mid_end
    )
    percentile = (expected_slot - 1.0) / (team_count - 1.0)

    return TeamOriginFuturePickDistribution(
        draft_season=draft_season,
        original_team_id=original_team_id,
        slot_probabilities=probabilities,
        expected_slot=expected_slot,
        median_slot=median_slot,
        expected_slot_percentile_from_earliest=percentile,
        early_probability=early,
        mid_probability=mid,
        late_probability=late,
        simulation_count=simulation_count,
        simulation_model_version=simulation_model_version,
        draft_order_policy_id=policy.policy_id,
        draft_order_policy_version=policy.policy_version,
        draft_order_policy_authority=policy.authority,
        draft_order_projection_model_version=draft_order_projection_model_version,
        provenance=(
            f"{policy.provenance}; per-world regular-season record/head-to-head/"
            "Points For and governed playoff elimination results"
        ),
    )

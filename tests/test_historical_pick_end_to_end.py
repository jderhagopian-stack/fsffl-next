from datetime import UTC, datetime

from fsffl.state.models import DraftPick, LeagueRules
from fsffl.team_utility.draft_order import (
    DraftOrderScenario,
    DraftOrderSimulationResult,
    DraftSlotAssignment,
)
from fsffl.value.historical_pick import reconstruct_historical_pick_coordinate
from fsffl.value.historical_pick_evidence import FrozenDraftedAssetValue, build_historical_pick_evidence
from fsffl.value.historical_pick_simulation import build_slot_forecast_from_draft_order
from fsffl.value.models import ValueDistribution, ValueScale


SCALE = ValueScale(scale_id="generic-dynasty", version="1", unit_label="value units")
RULES = LeagueRules(
    team_count=4,
    roster_size=20,
    rookie_draft_rounds=3,
    lineup=(),
    scoring=(),
)
PICK = DraftPick(
    pick_id="pick-2027-r1-a",
    league_id="league-generic",
    season=2027,
    round=1,
    original_team_id="a",
)
AS_OF = datetime(2026, 9, 1, tzinfo=UTC)


def _frozen(season: int, slot: int, mean: float):
    return FrozenDraftedAssetValue(
        draft_season=season,
        round=1,
        slot_in_round=slot,
        value=ValueDistribution(mean=mean, stddev=5),
        scale=SCALE,
        available_at=datetime(season, 6, 1, tzinfo=UTC),
        model_version=f"frozen-draft-{season}",
        provenance=f"point-in-time drafted asset value {season}",
    )


def test_simulation_scenarios_flow_into_historical_pick_value_without_new_rule_math():
    simulation = DraftOrderSimulationResult(
        league_id="league-generic",
        draft_season=2027,
        as_of=AS_OF,
        scenarios=(
            DraftOrderScenario(
                probability=0.25,
                assignments=(
                    DraftSlotAssignment(team_id="a", slot_in_round=1),
                    DraftSlotAssignment(team_id="b", slot_in_round=2),
                ),
            ),
            DraftOrderScenario(
                probability=0.75,
                assignments=(
                    DraftSlotAssignment(team_id="a", slot_in_round=2),
                    DraftSlotAssignment(team_id="b", slot_in_round=1),
                ),
            ),
        ),
        model_version="historical-competitive-sim-v1",
        rule_policy_version="league-draft-policy-v1",
        provenance="historical state plus explicit league draft-order rules",
    )
    slot_forecast = build_slot_forecast_from_draft_order(
        pick=PICK,
        result=simulation,
        league_rules=RULES,
    )
    evidence = build_historical_pick_evidence(
        pick=PICK,
        as_of=AS_OF,
        league_rules=RULES,
        drafted_asset_values=(
            _frozen(2024, 1, 120),
            _frozen(2025, 1, 100),
            _frozen(2024, 2, 100),
            _frozen(2025, 2, 80),
        ),
        slot_forecast=slot_forecast,
    )
    result = reconstruct_historical_pick_coordinate(
        evidence,
        league_rules=RULES,
        scale=SCALE,
    )

    # Slot 1 prior mean = 110, slot 2 = 90; no default horizon discount.
    # 25% * 110 + 75% * 90 = 95.
    assert result.status == "RECONSTRUCTED"
    assert result.estimate is not None
    assert result.estimate.distribution.mean == 95.0
    assert result.estimate.slot_uncertainty_model_version == (
        "historical-competitive-sim-v1+league-draft-policy-v1"
    )
    assert any("explicit league draft-order rules" in item for item in result.provenance)

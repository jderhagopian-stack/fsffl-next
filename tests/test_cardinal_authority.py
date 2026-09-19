from datetime import UTC, datetime
import json

from fsffl.state.models import DraftPick
from fsffl.value.calibration import DataRightsClass
from fsffl.value.cardinal import NativeMarketMagnitudeObservation
from fsffl.value.cardinal_authority import (
    FSFFL_CARDINAL_SCALE,
    FSFFL_CARDINAL_VALIDATION_HOLDOUT_SIZE,
    build_authoritative_pick_cardinal_scores,
    build_authoritative_player_cardinal_scores,
)
from fsffl.value.models import ValueAssetKind


NOW = datetime(2026, 9, 6, 15, 0, tzinfo=UTC)
CONTEXT = "dynasty:12t:sf:0.5ppr"


def _native(source: str, scale: str, asset: str, value: float) -> NativeMarketMagnitudeObservation:
    return NativeMarketMagnitudeObservation(
        asset_id=asset,
        source_id=source,
        native_scale_id=scale,
        value=value,
        observed_at=NOW,
        market_context_id=CONTEXT,
        rights_class=DataRightsClass.RUNTIME_ONLY,
    )


def test_player_cardinal_authority_uses_only_reference_axis_without_percentile_rescaling() -> None:
    observations = (
        _native("statsguy_market_values", "statsguy-dynasty-value", "p1", 8740),
        _native("dynastydealer_market_values", "dynastydealer-current-value", "p1", 9900),
        _native("fantasycalc_market_values", "fantasycalc-dynasty-value", "p2", 7600),
    )

    scores = build_authoritative_player_cardinal_scores(observations)

    assert len(scores) == 1
    score = scores[0]
    assert score.asset_id == "p1"
    assert score.asset_kind == ValueAssetKind.PLAYER
    assert score.score == 8740
    assert score.scale == FSFFL_CARDINAL_SCALE
    assert score.authority_status == "authoritative_market_cardinal"
    assert score.cross_source_validation_holdout_size == FSFFL_CARDINAL_VALIDATION_HOLDOUT_SIZE


def test_pick_cardinal_authority_uses_generic_round_only_value_when_slot_unknown() -> None:
    picks = (
        DraftPick(
            pick_id="pick-canonical-2027-r1-team-a",
            league_id="league-1",
            season=2027,
            round=1,
            original_team_id="team-a",
        ),
        DraftPick(
            pick_id="pick-canonical-2027-r2-team-a",
            league_id="league-1",
            season=2027,
            round=2,
            original_team_id="team-a",
        ),
    )
    payload = {
        "valuesAsOf": {"sf_dynasty": "2026-09-06T12:00:00Z"},
        "picks": [
            {"id": "pick:2027:1", "year": 2027, "round": 1, "value": {"sf_dynasty": 3100}},
            {"id": "pick:2027:1:early", "year": 2027, "round": 1, "variant": "early", "value": {"sf_dynasty": 4100}},
            {"id": "pick:2027:1:mid", "year": 2027, "round": 1, "variant": "mid", "value": {"sf_dynasty": 3200}},
            {"id": "pick:2027:2", "year": 2027, "round": 2, "value": {"sf_dynasty": 1200}},
        ],
    }

    scores = build_authoritative_pick_cardinal_scores(
        json.dumps(payload),
        draft_picks=picks,
        format_key="sf_dynasty",
        market_context_id=CONTEXT,
        retrieved_at=NOW,
    )

    by_id = {item.asset_id: item for item in scores}
    assert by_id["pick-canonical-2027-r1-team-a"].score == 3100
    assert by_id["pick-canonical-2027-r1-team-a"].source_asset_id == "pick:2027:1"
    assert by_id["pick-canonical-2027-r1-team-a"].slot_certainty == "generic_unknown_slot"
    assert by_id["pick-canonical-2027-r2-team-a"].score == 1200
    assert all(item.asset_kind == ValueAssetKind.PICK for item in scores)


def test_pick_cardinal_authority_keeps_missing_generic_value_missing() -> None:
    pick = DraftPick(
        pick_id="future-pick",
        league_id="league-1",
        season=2029,
        round=3,
        original_team_id="team-a",
    )
    payload = {
        "valuesAsOf": {"sf_dynasty": "2026-09-06T12:00:00Z"},
        "picks": [
            {"id": "pick:2029:3:mid", "year": 2029, "round": 3, "variant": "mid", "value": {"sf_dynasty": 250}},
        ],
    }

    scores = build_authoritative_pick_cardinal_scores(
        json.dumps(payload),
        draft_picks=(pick,),
        format_key="sf_dynasty",
        market_context_id=CONTEXT,
        retrieved_at=NOW,
    )

    assert scores == ()

from datetime import UTC, datetime

import pytest

from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    PlayerStatus,
    Position,
    Provenance,
    Team,
    TeamState,
)
from fsffl.value.calibration import DataRightsClass
from fsffl.value.cardinal import NativeMarketMagnitudeObservation
from fsffl.value.cardinal_consistency import build_cardinal_consistency_audit


NOW = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
CONTEXT = "dynasty:12t:sf:0.5ppr"


def _state() -> LeagueState:
    provenance = Provenance(source="test", retrieved_at=NOW, effective_at=NOW)
    players = (
        Player(player_id="qb1", full_name="QB One", position=Position.QB),
        Player(player_id="qb2", full_name="QB Two", position=Position.QB),
        Player(player_id="wr1", full_name="WR One", position=Position.WR),
        Player(player_id="wr2", full_name="WR Two", position=Position.WR),
    )
    return LeagueState(
        league=League(
            league_id="league",
            name="League",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
        ),
        as_of=NOW,
        teams=(
            Team(team_id="a", league_id="league", display_name="A"),
            Team(team_id="b", league_id="league", display_name="B"),
        ),
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=player.player_id,
                as_of=NOW,
                status=PlayerStatus.ACTIVE,
                provenance=provenance,
            )
            for player in players
        ),
        provenance=(provenance,),
    )


def _native(source: str, asset: str, value: float, *, version: str | None = None) -> NativeMarketMagnitudeObservation:
    scale = "statsguy-dynasty-value" if source == "statsguy_market_values" else "fantasycalc-dynasty-value"
    return NativeMarketMagnitudeObservation(
        asset_id=asset,
        source_id=source,
        native_scale_id=scale,
        value=value,
        observed_at=NOW,
        market_context_id=CONTEXT,
        rights_class=DataRightsClass.RUNTIME_ONLY,
        source_version=version,
    )


def test_position_audit_exposes_qb_cross_source_direction_instead_of_averaging_it_away() -> None:
    observations = (
        _native("statsguy_market_values", "qb1", 7000, version="sf_dynasty"),
        _native("statsguy_market_values", "qb2", 6000, version="sf_dynasty"),
        _native("statsguy_market_values", "wr1", 9000, version="sf_dynasty"),
        _native("statsguy_market_values", "wr2", 8000, version="sf_dynasty"),
        _native("fantasycalc_market_values", "qb1", 9900),
        _native("fantasycalc_market_values", "qb2", 9000),
        _native("fantasycalc_market_values", "wr1", 8000),
        _native("fantasycalc_market_values", "wr2", 7000),
    )

    audit = build_cardinal_consistency_audit(
        _state(),
        observations,
        market_context_id=CONTEXT,
        reference_format_key="sf_dynasty",
    )

    qb = next(row for row in audit.position_comparisons if row.source_id == "fantasycalc_market_values" and row.position == Position.QB)
    wr = next(row for row in audit.position_comparisons if row.source_id == "fantasycalc_market_values" and row.position == Position.WR)
    assert qb.mean_signed_percentile_delta > 0
    assert wr.mean_signed_percentile_delta < 0
    assert audit.authority_effect == "diagnostic_only"
    assert audit.largest_player_disagreements


def test_position_audit_rejects_mixed_reference_format_when_expected_format_is_known() -> None:
    observations = (
        _native("statsguy_market_values", "qb1", 7000, version="sf_dynasty"),
        _native("statsguy_market_values", "qb2", 6000, version="non_sf_dynasty"),
    )
    with pytest.raises(ValueError, match="unexpected format cohort"):
        build_cardinal_consistency_audit(
            _state(),
            observations,
            market_context_id=CONTEXT,
            reference_format_key="sf_dynasty",
        )

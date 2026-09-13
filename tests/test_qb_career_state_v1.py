from datetime import UTC, datetime

import pytest

from fsffl.forecast.qb_career_state import (
    QB_CAREER_STATE_EVIDENCE_VERSION,
    QB_CAREER_STATE_MODEL_VERSION,
    MEANINGFUL_STARTER_PASS_ATTEMPTS,
    model_feature_names,
    rank_percentiles,
)
from fsffl.forecast.qb_career_state_runtime import forecast_qb_career_state_runtime
from fsffl.state.models import Player, PlayerState, Position, Provenance

AS_OF = datetime(2026, 9, 13, tzinfo=UTC)
PROV = Provenance(source="test", retrieved_at=AS_OF, effective_at=AS_OF)


def _player(name: str, age: float = 33.0):
    player = Player(player_id=f"test:{name}", full_name=name, position=Position.QB)
    state = PlayerState(player_id=player.player_id, as_of=AS_OF, age_years=age, provenance=PROV)
    return player, state


def test_frozen_qb_contract_is_explicit():
    assert QB_CAREER_STATE_MODEL_VERSION == "qb-career-state-logit-v1"
    assert QB_CAREER_STATE_EVIDENCE_VERSION == "qb-career-state-evidence-v1"
    assert MEANINGFUL_STARTER_PASS_ATTEMPTS == 200
    assert model_feature_names() == (
        "age", "experience", "draft_pick_pct", "games_pct", "opportunity_pct",
        "role_mean_2", "role_vol_2", "qb_established_starter_seasons",
        "production_percentile", "horizon",
    )


def test_rank_percentile_is_deterministic_and_tie_safe():
    result = rank_percentiles({"a": 100.0, "b": 200.0, "c": 200.0, "d": 300.0})
    assert result["a"] == pytest.approx(0.125)
    assert result["b"] == pytest.approx(result["c"])
    assert result["d"] == pytest.approx(0.875)


def test_current_dak_shape_is_bounded_monotone_and_reproducible():
    player, state = _player("Dak Prescott", 33.0)
    result = forecast_qb_career_state_runtime(
        player=player,
        player_state=state,
        evaluation_season=2026,
        production_percentile=0.90,
    )
    assert result is not None
    assert result.feature_cutoff_season == 2025
    assert 0.0 <= result.year3_probability <= result.year2_probability <= 1.0
    assert result.model_version == QB_CAREER_STATE_MODEL_VERSION


def test_stale_season_fails_closed_instead_of_reusing_2026_artifact():
    player, state = _player("Dak Prescott", 33.0)
    assert forecast_qb_career_state_runtime(
        player=player,
        player_state=state,
        evaluation_season=2027,
        production_percentile=0.90,
    ) is None


def test_unknown_or_ambiguous_identity_fails_closed():
    player, state = _player("Definitely Not An NFL Quarterback", 25.0)
    assert forecast_qb_career_state_runtime(
        player=player,
        player_state=state,
        evaluation_season=2026,
        production_percentile=0.50,
    ) is None


def test_missing_age_fails_closed():
    player = Player(player_id="test:no-age", full_name="Dak Prescott", position=Position.QB)
    state = PlayerState(player_id=player.player_id, as_of=AS_OF, age_years=None, provenance=PROV)
    assert forecast_qb_career_state_runtime(
        player=player,
        player_state=state,
        evaluation_season=2026,
        production_percentile=0.90,
    ) is None

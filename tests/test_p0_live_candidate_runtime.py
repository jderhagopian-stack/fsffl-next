from datetime import UTC, datetime

import pytest

from fsffl.product.p0_candidate_evidence import (
    P0CandidateFacts,
    accepted_p0_source_state_authority,
    build_p0_candidate_source_rows,
)
from fsffl.product.p0_forecast_runtime import frozen_p0_source_rows
from fsffl.product.p0_live_candidate_runtime import out_of_cohort_p0_subject_ids
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
)


def test_out_of_cohort_subject_filter_uses_canonical_reference_ids() -> None:
    reference = frozen_p0_source_rows()
    benchmark_player = reference[0].player_id
    assert benchmark_player.startswith("sleeper:player:")

    candidates = out_of_cohort_p0_subject_ids(
        (benchmark_player, "sleeper:player:999999")
    )

    assert candidates == ("sleeper:player:999999",)


def test_dynamic_assembler_cannot_replace_frozen_canonical_player() -> None:
    now = datetime(2026, 10, 10, tzinfo=UTC)
    reference = frozen_p0_source_rows()[0]
    player_id = reference.player_id
    position = Position(reference.position)
    provenance = Provenance(
        source="fixture", retrieved_at=now, effective_at=now, source_version="fixture"
    )
    player = Player(
        player_id=player_id,
        full_name=reference.player_name,
        position=position,
    )
    state = LeagueState(
        league=League(
            league_id="p0-reference-guard",
            name="P0 reference guard",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
        ),
        as_of=now,
        teams=(),
        team_states=(),
        players=(player,),
        player_states=(
            PlayerState(player_id=player_id, as_of=now, provenance=provenance),
        ),
    )
    facts = P0CandidateFacts(
        player_id=player_id,
        current_player_id=player_id,
        player_name=player.full_name,
        position=position.value,
        age=reference.age,
        experience=reference.experience,
        mapping_status="EXACT_CANONICAL_ID",
        historical_gsis_id=reference.historical_gsis_id,
        history_status=reference.history_status,
        standard_y1_points=reference.standard_y1_points,
        connected_league_y1_points=reference.connected_league_y1_points,
        prior1_points=reference.prior1_points,
        prior1_coverage=reference.prior1_coverage,
        source_role_band=reference.source_role_band,
        games=reference.games,
        opportunity_per_game=reference.opportunity_per_game,
        prior_age_state_resid_z=reference.prior_age_state_resid_z,
        prior2_coverage=reference.prior2_coverage,
        prior2_mean_age_state_z=reference.prior2_mean_age_state_z,
        prior2_gap_age_state_z=reference.prior2_gap_age_state_z,
        facts_as_of=now,
        facts_source_version="fixture-v1",
        facts_digest="a" * 64,
    )

    with pytest.raises(ValueError, match="cannot replace frozen benchmark row"):
        build_p0_candidate_source_rows(
            league_state=state,
            candidate_facts={player_id: facts},
            source_state_authority=accepted_p0_source_state_authority(),
        )

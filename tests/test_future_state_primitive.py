from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from dataclasses import replace

from fsffl.forecast.future_state_primitive import (
    FUTURE_STATE_PRIMITIVE_VERSION,
    build_future_state_probability_materialization,
    frozen_future_state_source_rows,
)
from fsffl.forecast.integrated_i1 import STATE_NAMES
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.product.p0_forecast_runtime import (
    build_p0_standard_future_materialization,
    governed_p0_player_ids,
    frozen_p0_source_rows,
)
from fsffl.product.p0_future_forecast_provider import _candidate_evidence_digest
from fsffl.product.p0_candidate_evidence import (
    P0_ACCEPTED_SOURCE_STATE_AUTHORITY_SHA256,
    P0CandidateFacts,
    P0SourceStateAuthority,
    build_p0_candidate_source_rows,
)
import fsffl.product.p0_candidate_evidence as p0_candidate_evidence
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    ProviderRef,
    Provenance,
)


def _fixture(player_index: int = 0):
    source = frozen_future_state_source_rows()[player_index]
    now = datetime(2026, 9, 1, tzinfo=UTC)
    provenance = Provenance(
        source="future-state-primitive-fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="fixture-v1",
    )
    player = Player(
        player_id="canonical-player",
        full_name=source.player_name,
        position=Position(source.position),
        provider_refs=(
            ProviderRef(
                provider="sleeper",
                external_id=source.sleeper_external_id,
            ),
        ),
    )
    state = LeagueState(
        league=League(
            league_id="future-state-primitive-fixture",
            name="Future state primitive fixture",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=(),
            ),
        ),
        as_of=now,
        teams=(),
        team_states=(),
        players=(player,),
        player_states=(
            PlayerState(
                player_id=player.player_id,
                as_of=now,
                provenance=provenance,
            ),
        ),
    )
    year_one = (
        ForecastObservation(
            player_id=player.player_id,
            position=player.position,
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.FANTASY_POINTS,
            period_start=now,
            period_end=now + timedelta(days=180),
            distribution=ForecastDistribution(
                mean=float(source.standard_y1_points),
                stddev=0.0,
            ),
            source="future-state-primitive-fixture",
            model_version="fixture-v1",
            as_of=now,
            provenance=provenance,
        ),
    )
    return state, year_one


@pytest.mark.parametrize("player_index", (0, 17, 101, 220, 334))
def test_future_state_probability_primitive_matches_legacy_p0_probability_layer_exactly(
    player_index: int,
) -> None:
    state, year_one = _fixture(player_index)
    primitive = build_future_state_probability_materialization(
        league_state=state,
        standard_year_one=year_one,
    )
    legacy = build_p0_standard_future_materialization(
        league_state=state,
        standard_year_one=year_one,
    )

    assert primitive.primitive_version == FUTURE_STATE_PRIMITIVE_VERSION
    assert set(primitive.players) == set(legacy.players) == {"canonical-player"}
    for horizon in (2, 3):
        actual = primitive.players["canonical-player"].probabilities_for(horizon)
        expected = legacy.players["canonical-player"].result_for(horizon).probabilities
        assert set(actual) == set(expected) == set(STATE_NAMES)
        for state_name in STATE_NAMES:
            assert actual[state_name] == pytest.approx(
                expected[state_name],
                abs=1e-15,
            )


def test_future_state_primitive_exposes_probability_only_not_p0_routes_or_point_results() -> None:
    state, year_one = _fixture()
    primitive = build_future_state_probability_materialization(
        league_state=state,
        standard_year_one=year_one,
    )
    player = primitive.players["canonical-player"]

    assert hasattr(player, "probabilities_for")
    assert not hasattr(player, "result_for")
    assert not hasattr(player, "route_for")
    assert not hasattr(player, "routes")
    assert not hasattr(player, "results")


def test_p0_scores_dynamic_canonical_candidate_through_unchanged_model() -> None:
    now = datetime(2026, 9, 1, tzinfo=UTC)
    reference = frozen_p0_source_rows()[42]
    candidate_id = "sleeper:player:999999"
    provenance = Provenance(
        source="approved-candidate-forecast-fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="candidate-fixture-v1",
    )
    player = Player(
        player_id=candidate_id,
        full_name="Candidate Player",
        position=Position(reference.position),
        provider_refs=(ProviderRef(provider="sleeper", external_id="999999"),),
    )
    state = LeagueState(
        league=League(
            league_id="dynamic-p0-fixture",
            name="Dynamic P0 fixture",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
        ),
        as_of=now,
        teams=(),
        team_states=(),
        players=(player,),
        player_states=(PlayerState(player_id=candidate_id, as_of=now, provenance=provenance),),
    )
    candidate = replace(
        reference,
        player_id=candidate_id,
        current_player_id=candidate_id,
        player_name=player.full_name,
        evidence_as_of=now.isoformat(),
        evidence_source_version="approved-candidate-fixture-v1",
        evidence_sha256="a" * 64,
    )
    year_one = ForecastObservation(
        player_id=candidate_id,
        position=player.position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=now,
        period_end=now + timedelta(days=180),
        distribution=ForecastDistribution(mean=reference.standard_y1_points, stddev=0.0),
        source="approved-candidate-forecast-fixture",
        model_version="candidate-fixture-v1",
        as_of=now,
        provenance=provenance,
    )

    assert governed_p0_player_ids(state, {candidate_id: candidate}) == (candidate_id,)
    materialized = build_p0_standard_future_materialization(
        league_state=state,
        standard_year_one=(year_one,),
        candidate_source_rows={candidate_id: candidate},
    )
    assert materialized.player_count == 1
    result = materialized.players[candidate_id]
    assert result.source.current_player_id == candidate_id
    assert result.result_for(2).anticipated_points > 0
    assert result.route_for(2) in {"D0", "D1"}
    candidate_digest = _candidate_evidence_digest({candidate_id: candidate})
    assert candidate_digest == _candidate_evidence_digest({candidate_id: candidate})
    assert candidate_digest != _candidate_evidence_digest(
        {candidate_id: replace(candidate, source_percentile=candidate.source_percentile + 0.001)}
    )


def test_p0_dynamic_candidate_rejects_future_source_evidence() -> None:
    now = datetime(2026, 9, 1, tzinfo=UTC)
    reference = frozen_p0_source_rows()[0]
    player_id = "sleeper:player:999998"
    player = Player(
        player_id=player_id,
        full_name="Future Evidence Player",
        position=Position(reference.position),
    )
    provenance = Provenance(
        source="fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="fixture",
    )
    state = LeagueState(
        league=League(
            league_id="pit-fixture", name="PIT fixture", season=2026,
            rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
        ),
        as_of=now, teams=(), team_states=(), players=(player,),
        player_states=(PlayerState(player_id=player_id, as_of=now, provenance=provenance),),
    )
    future = replace(
        reference, player_id=player_id, current_player_id=player_id,
        evidence_as_of="2026-09-02T00:00:00+00:00",
        evidence_source_version="fixture-v1", evidence_sha256="b" * 64,
    )
    with pytest.raises(ValueError, match="postdates or lacks PIT boundary"):
        governed_p0_player_ids(state, {player_id: future})


def test_p0_candidate_feature_assembly_is_deterministic_and_uses_reference_percentiles(
    monkeypatch,
) -> None:
    now = datetime(2026, 9, 1, tzinfo=UTC)
    reference = frozen_p0_source_rows()[42]
    candidate_id = "sleeper:player:999997"
    provenance = Provenance(
        source="fixture", retrieved_at=now, effective_at=now, source_version="v1"
    )
    player = Player(
        player_id=candidate_id,
        full_name="Candidate Player",
        position=Position(reference.position),
        provider_refs=(ProviderRef(provider="sleeper", external_id="999997"),),
    )
    state = LeagueState(
        league=League(
            league_id="p0-candidate-builder-fixture",
            name="P0 candidate builder fixture",
            season=2026,
            rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=()),
        ),
        as_of=now,
        teams=(),
        team_states=(),
        players=(player,),
        player_states=(PlayerState(player_id=candidate_id, as_of=now, provenance=provenance),),
    )
    facts = P0CandidateFacts(
        player_id=candidate_id,
        current_player_id=candidate_id,
        player_name=player.full_name,
        position=reference.position,
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
        facts_source_version="accepted-feature-input-fixture-v1",
        facts_digest="a" * 64,
    )
    threshold_bytes = json.dumps(
        {"boundaries": {reference.position: {"thresholds": [0, 0, 0, 0]}}}
    ).encode()
    monkeypatch.setattr(
        p0_candidate_evidence,
        "P0_ACCEPTED_SOURCE_STATE_AUTHORITY_SHA256",
        hashlib.sha256(threshold_bytes).hexdigest(),
    )
    authority = P0SourceStateAuthority.from_artifact_bytes(threshold_bytes)

    rows = build_p0_candidate_source_rows(
        league_state=state,
        candidate_facts={candidate_id: facts},
        source_state_authority=authority,
    )
    repeated = build_p0_candidate_source_rows(
        league_state=state,
        candidate_facts={candidate_id: facts},
        source_state_authority=authority,
    )

    assert tuple(rows) == (candidate_id,)
    assert rows == repeated
    assert rows[candidate_id].source_state == "elite"
    assert rows[candidate_id].career_stage == reference.career_stage
    assert rows[candidate_id].age_band == reference.age_band
    assert rows[candidate_id].source_percentile == reference.source_percentile
    elite_values = [
        row.standard_y1_points
        for row in frozen_p0_source_rows()
        if row.position == reference.position and row.source_state == "elite"
    ]
    expected_state_percentile = (
        sum(value < reference.standard_y1_points for value in elite_values)
        + sum(value == reference.standard_y1_points for value in elite_values) / 2
    ) / len(elite_values)
    assert rows[candidate_id].state_percentile == expected_state_percentile
    assert rows[candidate_id].evidence_as_of == now.isoformat()
    assert rows[candidate_id].evidence_sha256 != facts.facts_digest
    year_one = ForecastObservation(
        player_id=candidate_id,
        position=player.position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=now,
        period_end=now + timedelta(days=180),
        distribution=ForecastDistribution(mean=reference.standard_y1_points, stddev=0.0),
        source="accepted-feature-input-fixture",
        model_version="fixture-v1",
        as_of=now,
        provenance=provenance,
    )
    forecast = build_p0_standard_future_materialization(
        league_state=state,
        standard_year_one=(year_one,),
        candidate_source_rows=rows,
    )
    assert set(forecast.players) == {candidate_id}
    assert forecast.players[candidate_id].result_for(2).anticipated_points > 0


def test_p0_candidate_feature_assembly_fails_closed_on_threshold_authority_or_future_facts(
    monkeypatch,
) -> None:
    now = datetime(2026, 9, 1, tzinfo=UTC)
    reference = frozen_p0_source_rows()[0]
    candidate_id = "sleeper:player:999996"
    provenance = Provenance(
        source="fixture", retrieved_at=now, effective_at=now, source_version="v1"
    )
    player = Player(
        player_id=candidate_id,
        full_name="Candidate Player",
        position=Position(reference.position),
    )
    state = LeagueState(
        league=League(league_id="p0-pit-fixture", name="P0 PIT fixture", season=2026,
                      rules=LeagueRules(team_count=2, roster_size=1, lineup=(), scoring=())),
        as_of=now, teams=(), team_states=(), players=(player,),
        player_states=(PlayerState(player_id=candidate_id, as_of=now, provenance=provenance),),
    )
    facts = P0CandidateFacts(
        player_id=candidate_id, current_player_id=candidate_id, player_name=player.full_name,
        position=reference.position, age=reference.age, experience=reference.experience,
        mapping_status="EXACT_CANONICAL_ID", historical_gsis_id=reference.historical_gsis_id,
        history_status=reference.history_status, standard_y1_points=reference.standard_y1_points,
        connected_league_y1_points=reference.connected_league_y1_points,
        prior1_points=reference.prior1_points, prior1_coverage=reference.prior1_coverage,
        source_role_band=reference.source_role_band, games=reference.games,
        opportunity_per_game=reference.opportunity_per_game,
        prior_age_state_resid_z=reference.prior_age_state_resid_z,
        prior2_coverage=reference.prior2_coverage,
        prior2_mean_age_state_z=reference.prior2_mean_age_state_z,
        prior2_gap_age_state_z=reference.prior2_gap_age_state_z,
        facts_as_of=now + timedelta(seconds=1),
        facts_source_version="fixture-v1",
        facts_digest="c" * 64,
    )
    wrong_threshold_bytes = json.dumps(
        {"boundaries": {reference.position: {"thresholds": [1, 2, 3, 4]}}}
    ).encode()
    with pytest.raises(ValueError, match="threshold authority digest mismatch"):
        P0SourceStateAuthority.from_artifact_bytes(wrong_threshold_bytes)
    monkeypatch.setattr(
        p0_candidate_evidence,
        "P0_ACCEPTED_SOURCE_STATE_AUTHORITY_SHA256",
        hashlib.sha256(wrong_threshold_bytes).hexdigest(),
    )
    authority = P0SourceStateAuthority.from_artifact_bytes(wrong_threshold_bytes)
    with pytest.raises(ValueError, match="not point-in-time valid"):
        build_p0_candidate_source_rows(
            league_state=state,
            candidate_facts={candidate_id: facts},
            source_state_authority=authority,
        )

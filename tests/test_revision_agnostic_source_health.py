from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.current_runtime import (
    LiveForecastSourceHealthFailure,
    NamedCurrentProjectionFetcher,
    build_current_live_forecasts,
)
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.forecast.source_health import (
    CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION,
    REVISION_AGNOSTIC_SCALE_RATIO_THRESHOLD,
    evaluate_revision_agnostic_scale_health,
)
from fsffl.providers.current_projection_rows import (
    CurrentProjectionRow,
    CurrentProjectionSnapshot,
)
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
    ScoringRule,
    Team,
    TeamState,
)


NOW = datetime(2026, 9, 21, 16, tzinfo=UTC)
POSITIONS = (Position.QB, Position.RB, Position.WR, Position.TE)


def _fantasy_points(
    *,
    multiplier: float,
    as_of: datetime = NOW,
) -> tuple[ForecastObservation, ...]:
    rows = []
    base = {
        Position.QB: 320.0,
        Position.RB: 220.0,
        Position.WR: 210.0,
        Position.TE: 150.0,
    }
    for position in POSITIONS:
        for index in range(6):
            value = (base[position] + index * 5.0) * multiplier
            rows.append(
                ForecastObservation(
                    player_id=f"{position.value.lower()}-{index}",
                    position=position,
                    horizon=ForecastHorizon.SEASON,
                    metric=ForecastMetric.FANTASY_POINTS,
                    period_start=datetime(2026, 9, 1, tzinfo=UTC),
                    period_end=datetime(2027, 1, 15, tzinfo=UTC),
                    distribution=ForecastDistribution(mean=value, stddev=10.0),
                    source="fixture",
                    model_version="fixture-v1",
                    as_of=as_of,
                    provenance=Provenance(
                        source="fixture",
                        retrieved_at=as_of,
                        effective_at=as_of,
                        source_version="fixture-v1",
                    ),
                )
            )
    return tuple(rows)


def test_unseen_broad_inflation_is_rejected_without_incident_fingerprint() -> None:
    result = evaluate_revision_agnostic_scale_health(
        _fantasy_points(multiplier=1.80),
        _fantasy_points(multiplier=1.00),
        reference_id="synthetic-governed-reference",
    )

    assert result.disposition == "quarantined"
    assert result.overall_median_ratio == pytest.approx(1.80)
    assert result.inflated_position_count == 4
    assert result.ratio_threshold == pytest.approx(
        REVISION_AGNOSTIC_SCALE_RATIO_THRESHOLD
    )
    assert result.reference_id == "synthetic-governed-reference"


def test_healthy_revision_drift_passes_generalized_gate() -> None:
    result = evaluate_revision_agnostic_scale_health(
        _fantasy_points(multiplier=1.05, as_of=NOW + timedelta(days=1)),
        _fantasy_points(multiplier=1.00),
        reference_id="synthetic-governed-reference",
    )

    assert result.disposition == "accepted"
    assert result.overall_median_ratio == pytest.approx(1.05)
    assert result.inflated_position_count == 0


def _state() -> LeagueState:
    provenance = Provenance(
        source="fixture",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture-v1",
    )
    players = tuple(
        Player(
            player_id=f"{position.value.lower()}-{index}",
            full_name=f"{position.value} Player {index}",
            position=position,
            nfl_team="FA",
        )
        for position in POSITIONS
        for index in range(6)
    )
    return LeagueState(
        league=League(
            league_id="health-fixture",
            name="Health Fixture",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=(
                    ScoringRule(stat="pass_yd", points=0.04),
                    ScoringRule(stat="pass_td", points=4.0),
                    ScoringRule(stat="pass_int", points=-1.0),
                    ScoringRule(stat="rush_yd", points=0.1),
                    ScoringRule(stat="rush_td", points=6.0),
                    ScoringRule(stat="rec", points=0.5),
                    ScoringRule(stat="rec_yd", points=0.1),
                    ScoringRule(stat="rec_td", points=6.0),
                ),
            ),
        ),
        as_of=NOW + timedelta(days=2),
        teams=(
            Team(team_id="a", league_id="health-fixture", display_name="A"),
            Team(team_id="b", league_id="health-fixture", display_name="B"),
        ),
        team_states=(
            TeamState(team_id="a", roster=()),
            TeamState(team_id="b", roster=()),
        ),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=player.player_id,
                as_of=NOW,
                nfl_team=player.nfl_team,
                provenance=provenance,
            )
            for player in players
        ),
    )


def _stats(position: Position, *, scale: float, index: int) -> dict[str, float]:
    if position == Position.QB:
        return {
            "pass_yd": (3900.0 + 20.0 * index) * scale,
            "pass_td": (27.0 + index * 0.2) * scale,
            "pass_int": (10.0 + index * 0.1) * scale,
            "rush_yd": (420.0 + 5.0 * index) * scale,
            "rush_td": (5.0 + index * 0.1) * scale,
        }
    if position == Position.RB:
        return {
            "rush_yd": (1050.0 + 15.0 * index) * scale,
            "rush_td": (8.0 + index * 0.1) * scale,
            "rec": (45.0 + index) * scale,
            "rec_yd": (360.0 + 5.0 * index) * scale,
            "rec_td": (2.0 + index * 0.05) * scale,
        }
    if position == Position.WR:
        return {
            "rush_yd": (25.0 + index) * scale,
            "rush_td": 0.2 * scale,
            "rec": (80.0 + index) * scale,
            "rec_yd": (1080.0 + 10.0 * index) * scale,
            "rec_td": (7.0 + index * 0.1) * scale,
        }
    return {
        "rush_yd": 0.0,
        "rush_td": 0.0,
        "rec": (65.0 + index) * scale,
        "rec_yd": (760.0 + 8.0 * index) * scale,
        "rec_td": (5.0 + index * 0.1) * scale,
    }


def _snapshot(
    provider: str,
    *,
    scale: float,
    captured_at: datetime = NOW,
    reverse_rows: bool = False,
    add_unmatched_row: bool = False,
) -> CurrentProjectionSnapshot:
    rows = [
        CurrentProjectionRow(
            provider=provider,
            external_id=f"{provider}:{position.value}:{index}",
            player_name=f"{position.value} Player {index}",
            position=position,
            nfl_team="FA",
            stats=_stats(position, scale=scale, index=index),
        )
        for position in POSITIONS
        for index in range(6)
    ]
    if add_unmatched_row:
        rows.append(
            CurrentProjectionRow(
                provider=provider,
                external_id=f"{provider}:unmatched",
                player_name="Unmatched Fixture",
                position=Position.WR,
                nfl_team="FA",
                stats=_stats(Position.WR, scale=1.0, index=0),
            )
        )
    if reverse_rows:
        rows.reverse()
    return CurrentProjectionSnapshot(
        provider=provider,
        captured_at=captured_at,
        effective_at=captured_at,
        rows=tuple(rows),
        source_version=f"{provider}-fixture-v1",
        usage_class="fixture",
    )


def test_production_runtime_rejects_unseen_two_source_scale_disagreement() -> None:
    state = _state()
    with pytest.raises(LiveForecastSourceHealthFailure) as excinfo:
        build_current_live_forecasts(
            state,
            fetchers=(
                NamedCurrentProjectionFetcher(
                    source_id="source_a",
                    fetch=lambda _season: _snapshot("source_a", scale=1.0),
                ),
                NamedCurrentProjectionFetcher(
                    source_id="source_b",
                    fetch=lambda _season: _snapshot("source_b", scale=1.80),
                ),
            ),
            clock=lambda: NOW + timedelta(days=2),
        )

    error = excinfo.value
    assert "revision-agnostic numerical-integrity gate" in str(error)
    events = error.health_events
    assert {event.provider for event in events} == {"source_a", "source_b"}
    assert all(event.disposition == "quarantined" for event in events)
    assert all(
        event.check == "revision_agnostic_two_source_scale_disagreement"
        for event in events
    )


def test_production_runtime_accepts_benign_revision_drift_and_metadata_changes() -> None:
    state = _state()
    result = build_current_live_forecasts(
        state,
        fetchers=(
            NamedCurrentProjectionFetcher(
                source_id="source_a",
                fetch=lambda _season: _snapshot(
                    "source_a",
                    scale=1.0,
                    captured_at=NOW + timedelta(minutes=5),
                    reverse_rows=True,
                    add_unmatched_row=True,
                ),
            ),
            NamedCurrentProjectionFetcher(
                source_id="source_b",
                fetch=lambda _season: _snapshot(
                    "source_b",
                    scale=1.04,
                    captured_at=NOW + timedelta(minutes=7),
                ),
            ),
        ),
        clock=lambda: NOW + timedelta(days=2),
    )

    assert result.successful_source_ids == ("source_a", "source_b")
    assert len(result.raw_ensemble) > 0
    assert {event.provider for event in result.source_health_events} == {
        "source_a",
        "source_b",
    }
    assert all(event.disposition == "accepted" for event in result.source_health_events)
    assert all(
        event.health_contract_version == CURRENT_PROJECTION_HEALTH_CONTRACT_VERSION
        for event in result.source_health_events
    )

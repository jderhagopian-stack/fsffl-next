from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from fsffl.forecast.integrated_i1 import I1ForecastResult, STATE_NAMES
from fsffl.forecast.league_scoring import derive_league_fantasy_point_forecasts
from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.product.i1_player_scoring_candidate import (
    FUTURE_I1_PLAYER_SCORING_CANDIDATE_VERSION,
    build_future_i1_player_scoring_multipliers,
    player_scoring_multipliers,
    translate_future_i1_result_for_player,
)
from fsffl.product.i1_scoring_bridge import FROZEN_I1_STANDARD_SCORING
from fsffl.state.models import LeagueRules, Position, Provenance, ScoringRule


def _raw_wr(player_id: str, *, receptions: float, yards: float, touchdowns: float):
    now = datetime(2026, 9, 10, tzinfo=UTC)
    provenance = Provenance(
        source="fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="fixture-v1",
    )
    metrics = (
        (ForecastMetric.RECEPTIONS, receptions),
        (ForecastMetric.REC_YARDS, yards),
        (ForecastMetric.REC_TD, touchdowns),
        # Explicit zero is evidence in this synthetic complete-coordinate fixture;
        # production raw projections may not synthesize missing fumble loss.
        (ForecastMetric.FUMBLES_LOST, 0.0),
    )
    return tuple(
        ForecastObservation(
            player_id=player_id,
            position=Position.WR,
            horizon=ForecastHorizon.SEASON,
            metric=metric,
            period_start=now,
            period_end=now + timedelta(days=150),
            distribution=ForecastDistribution(mean=mean, stddev=1.0),
            source="fixture",
            model_version="fixture-v1",
            as_of=now,
            provenance=provenance,
        )
        for metric, mean in metrics
    )


def _rules(*, receptions: float) -> LeagueRules:
    scoring = list(FROZEN_I1_STANDARD_SCORING)
    if receptions:
        scoring.append(ScoringRule(stat="rec", points=receptions))
    return LeagueRules(team_count=2, roster_size=18, lineup=(), scoring=tuple(scoring))


def _result() -> I1ForecastResult:
    probabilities = {
        "out": 0.10,
        "depth": 0.10,
        "usable": 0.20,
        "starter": 0.30,
        "premium": 0.20,
        "elite": 0.10,
    }
    means = {state: float(index * 25) for index, state in enumerate(STATE_NAMES)}
    anticipated = sum(probabilities[state] * means[state] for state in STATE_NAMES)
    return I1ForecastResult(
        probabilities=probabilities,
        persistence_probability=0.83,
        anticipated_points=anticipated,
        state_means=means,
        evidence_path="reduced",
        model_version="frozen-p0-fixture",
    )


def test_player_specific_ratio_preserves_different_stat_mixes_within_position() -> None:
    raw = _raw_wr("wr-high-rec", receptions=100.0, yards=500.0, touchdowns=5.0) + _raw_wr(
        "wr-low-rec", receptions=20.0, yards=900.0, touchdowns=5.0
    )
    rules = _rules(receptions=0.5)
    league = derive_league_fantasy_point_forecasts(raw, rules=rules)
    multipliers = build_future_i1_player_scoring_multipliers(
        raw_forecasts=raw,
        league_year_one=league,
        rules=rules,
    )

    assert multipliers["wr-high-rec"] != pytest.approx(multipliers["wr-low-rec"])
    assert multipliers["wr-high-rec"] > multipliers["wr-low-rec"]


def test_standard_coordinate_is_exact_identity_for_every_player() -> None:
    raw = _raw_wr("p1", receptions=80.0, yards=1000.0, touchdowns=8.0) + _raw_wr(
        "p2", receptions=25.0, yards=450.0, touchdowns=3.0
    )
    rules = _rules(receptions=0.0)
    league = derive_league_fantasy_point_forecasts(raw, rules=rules)
    multipliers = build_future_i1_player_scoring_multipliers(
        raw_forecasts=raw,
        league_year_one=league,
        rules=rules,
    )
    assert multipliers == {"p1": pytest.approx(1.0), "p2": pytest.approx(1.0)}


def test_translation_preserves_p0_semantics_and_scales_points_once() -> None:
    base = _result()
    translated = translate_future_i1_result_for_player(
        "p1", base, multipliers={"p1": 1.25}
    )

    assert translated.probabilities == base.probabilities
    assert translated.persistence_probability == base.persistence_probability
    assert translated.evidence_path == base.evidence_path
    for state in STATE_NAMES:
        assert translated.state_means[state] == pytest.approx(base.state_means[state] * 1.25)
    expected = sum(
        translated.probabilities[state] * translated.state_means[state]
        for state in STATE_NAMES
    )
    assert translated.anticipated_points == pytest.approx(expected)
    assert translated.model_version.count(FUTURE_I1_PLAYER_SCORING_CANDIDATE_VERSION) == 1


def test_translation_preserves_conditional_trajectory_ratio() -> None:
    base = _result()
    translated = translate_future_i1_result_for_player(
        "p1", base, multipliers={"p1": 1.4}
    )
    standard_y1 = 200.0
    league_y1 = standard_y1 * 1.4

    for state in STATE_NAMES:
        assert translated.state_means[state] / league_y1 == pytest.approx(
            base.state_means[state] / standard_y1
        )
    assert translated.anticipated_points / league_y1 == pytest.approx(
        base.anticipated_points / standard_y1
    )


def test_candidate_fails_closed_for_missing_identity_or_zero_denominator() -> None:
    with pytest.raises(ValueError, match="lacks a governed multiplier"):
        translate_future_i1_result_for_player("missing", _result(), multipliers={})

    now = datetime(2026, 9, 10, tzinfo=UTC)
    provenance = Provenance(
        source="fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="fixture-v1",
    )

    def fp(points: float) -> ForecastObservation:
        return ForecastObservation(
            player_id="p1",
            position=Position.WR,
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.FANTASY_POINTS,
            period_start=now,
            period_end=now + timedelta(days=150),
            distribution=ForecastDistribution(mean=points, stddev=1.0),
            source="fixture",
            model_version="fixture-v1",
            as_of=now,
            provenance=provenance,
        )

    with pytest.raises(ValueError, match="zero frozen standard points"):
        player_scoring_multipliers(
            standard_year_one=(fp(0.0),),
            league_year_one=(fp(10.0),),
        )


def _fantasy_points(player_id: str, position: Position, points: float) -> ForecastObservation:
    now = datetime(2026, 9, 10, tzinfo=UTC)
    provenance = Provenance(
        source="validation-fixture",
        retrieved_at=now,
        effective_at=now,
        source_version="validation-fixture-v1",
    )
    return ForecastObservation(
        player_id=player_id,
        position=position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=now,
        period_end=now + timedelta(days=150),
        distribution=ForecastDistribution(mean=points, stddev=1.0),
        source="validation-fixture",
        model_version="validation-fixture-v1",
        as_of=now,
        provenance=provenance,
    )


@pytest.mark.parametrize(
    ("label", "position", "standard_points", "league_points"),
    (
        ("standard_non_ppr", Position.WR, 148.0, 148.0),
        ("half_ppr", Position.WR, 148.0, 188.0),
        ("full_ppr", Position.WR, 148.0, 228.0),
        ("te_premium", Position.TE, 148.0, 268.0),
        ("six_point_passing_td", Position.QB, 340.0, 400.0),
    ),
)
def test_required_scoring_family_candidate_math_is_deterministic(
    label: str,
    position: Position,
    standard_points: float,
    league_points: float,
) -> None:
    standard = (_fantasy_points(label, position, standard_points),)
    league = (_fantasy_points(label, position, league_points),)
    first = player_scoring_multipliers(
        standard_year_one=standard,
        league_year_one=league,
    )
    second = player_scoring_multipliers(
        standard_year_one=standard,
        league_year_one=league,
    )
    assert first == second

    translated = translate_future_i1_result_for_player(
        label,
        _result(),
        multipliers=first,
    )
    assert translated.anticipated_points / league_points == pytest.approx(
        _result().anticipated_points / standard_points
    )

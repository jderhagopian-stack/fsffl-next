from datetime import datetime, timezone

import pytest

from fsffl.forecast.models import ForecastDistribution
from fsffl.research.intrinsic_value_study import (
    IntrinsicCalibrationRow,
    IntrinsicSeasonEvidence,
    discounted_surplus_mean,
)
from fsffl.state.models import Position


AS_OF = datetime(2024, 8, 1, tzinfo=timezone.utc)


def distribution(mean: float) -> ForecastDistribution:
    return ForecastDistribution(mean=mean, stddev=10.0)


def row(*, evidence_cutoff: datetime = AS_OF) -> IntrinsicCalibrationRow:
    return IntrinsicCalibrationRow(
        as_of=AS_OF,
        evidence_cutoff=evidence_cutoff,
        asset_id="player-1",
        position=Position.WR,
        league_context_id="12-team-half-ppr-superflex",
        forecast_model_version="forecast-v1",
        seasons=(
            IntrinsicSeasonEvidence(
                season_offset=0,
                player_forecast=distribution(250.0),
                replacement_forecast=distribution(150.0),
            ),
            IntrinsicSeasonEvidence(
                season_offset=1,
                player_forecast=distribution(220.0),
                replacement_forecast=distribution(160.0),
            ),
        ),
        fold_id="train-through-2023-holdout-2024",
    )


def test_row_rejects_hindsight_evidence() -> None:
    with pytest.raises(ValueError, match="cannot postdate"):
        row(evidence_cutoff=datetime(2024, 8, 2, tzinfo=timezone.utc))


def test_model_a_uses_explicit_multi_year_replacement_adjusted_surplus() -> None:
    assert discounted_surplus_mean(row(), annual_weights=(1.0, 0.5)) == 130.0


def test_model_a_rejects_missing_or_negative_weights() -> None:
    with pytest.raises(ValueError, match="cover every"):
        discounted_surplus_mean(row(), annual_weights=(1.0,))
    with pytest.raises(ValueError, match="cannot be negative"):
        discounted_surplus_mean(row(), annual_weights=(1.0, -0.5))

from __future__ import annotations

from fsffl.state.models import FrozenModel, Position, Provenance

from .models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation


class SeasonFantasyPointErrorCalibration(FrozenModel):
    """Governed empirical residual scale for full-season fantasy-point forecasts."""

    position: Position
    sample_size: int
    seasons: tuple[int, ...]
    relative_rmse: float
    evidence_study: str
    evidence_workflow_run: int
    evidence_artifact_digest: str
    method: str
    model_version: str = "next2-live-season-fp-uncertainty-v1"


# Derived from the retained NEXT-2 modern historical benchmark artifact produced by
# workflow run 33958374013. For each season/player/position with at least two
# independent provider projections, the equal-weight projection was compared with
# realized season fantasy points. 2024 and 2025 rows are pooled by position and the
# calibration scale is RMSE / mean projected points. This ratio is intentionally
# used instead of an absolute fantasy-point RMSE so the calibration remains usable
# under different league scoring systems after canonical league scoring.
#
# The artifact itself remains research evidence rather than a production data
# dependency. These explicit versioned parameters are therefore replaceable when
# a broader historical study is promoted.
_EVIDENCE_DIGEST = "sha256:c9206cca041f3fbf924bc287e56ac004c4c92260ecced17c2655f10cbbbc1b44"
_METHOD = (
    "pooled_2024_2025_equal_weight_players_with_2plus_sources:"
    "position_rmse_divided_by_position_mean_projection"
)

SEASON_FANTASY_POINT_ERROR_CALIBRATION: dict[Position, SeasonFantasyPointErrorCalibration] = {
    Position.QB: SeasonFantasyPointErrorCalibration(
        position=Position.QB,
        sample_size=142,
        seasons=(2024, 2025),
        relative_rmse=0.5381838389517043,
        evidence_study="NEXT-2 modern multi-source historical projection benchmark",
        evidence_workflow_run=33958374013,
        evidence_artifact_digest=_EVIDENCE_DIGEST,
        method=_METHOD,
    ),
    Position.RB: SeasonFantasyPointErrorCalibration(
        position=Position.RB,
        sample_size=250,
        seasons=(2024, 2025),
        relative_rmse=0.567843238263934,
        evidence_study="NEXT-2 modern multi-source historical projection benchmark",
        evidence_workflow_run=33958374013,
        evidence_artifact_digest=_EVIDENCE_DIGEST,
        method=_METHOD,
    ),
    Position.WR: SeasonFantasyPointErrorCalibration(
        position=Position.WR,
        sample_size=378,
        seasons=(2024, 2025),
        relative_rmse=0.5171510218429248,
        evidence_study="NEXT-2 modern multi-source historical projection benchmark",
        evidence_workflow_run=33958374013,
        evidence_artifact_digest=_EVIDENCE_DIGEST,
        method=_METHOD,
    ),
    Position.TE: SeasonFantasyPointErrorCalibration(
        position=Position.TE,
        sample_size=217,
        seasons=(2024, 2025),
        relative_rmse=0.5653631138046966,
        evidence_study="NEXT-2 modern multi-source historical projection benchmark",
        evidence_workflow_run=33958374013,
        evidence_artifact_digest=_EVIDENCE_DIGEST,
        method=_METHOD,
    ),
}


def apply_empirical_season_fantasy_point_uncertainty(
    observations: tuple[ForecastObservation, ...],
    *,
    model_version: str = "next2-live-season-fp-uncertainty-v1",
) -> tuple[ForecastObservation, ...]:
    """Calibrate live full-season fantasy-point uncertainty from realized error.

    Provider disagreement remains visible in the incoming distribution, but it is
    not sufficient by itself for simulation-grade uncertainty. The empirical
    historical residual scale therefore acts as a floor. We use ``max`` rather
    than adding variances, because historical forecast error already includes
    model/source disagreement and adding both would risk double counting.
    """

    calibrated: list[ForecastObservation] = []
    for observation in observations:
        if observation.metric != ForecastMetric.FANTASY_POINTS:
            raise ValueError("season fantasy-point uncertainty requires fantasy-point observations")
        if observation.horizon != ForecastHorizon.SEASON:
            raise ValueError("season fantasy-point uncertainty requires SEASON horizon")
        evidence = SEASON_FANTASY_POINT_ERROR_CALIBRATION.get(observation.position)
        if evidence is None:
            raise ValueError(
                f"no promoted season fantasy-point uncertainty calibration for {observation.position.value}"
            )

        empirical_floor = abs(observation.distribution.mean) * evidence.relative_rmse
        calibrated_stddev = max(observation.distribution.stddev, empirical_floor)
        provenance = Provenance(
            source=f"{observation.provenance.source}:empirical-season-uncertainty",
            retrieved_at=observation.provenance.retrieved_at,
            effective_at=observation.provenance.effective_at,
            provider_ref=observation.provenance.provider_ref,
            source_version=model_version,
        )
        calibrated.append(
            observation.model_copy(
                update={
                    "distribution": ForecastDistribution(
                        mean=observation.distribution.mean,
                        stddev=calibrated_stddev,
                        p10=observation.distribution.p10,
                        p50=observation.distribution.p50,
                        p90=observation.distribution.p90,
                    ),
                    "model_version": f"{observation.model_version}:{model_version}",
                    "provenance": provenance,
                }
            )
        )

    return tuple(calibrated)

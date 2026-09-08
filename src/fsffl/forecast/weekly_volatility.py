from __future__ import annotations

from dataclasses import dataclass

from fsffl.state.models import Position


@dataclass(frozen=True)
class WeeklyVolatilityCalibration:
    """Empirical week-to-week fantasy scoring volatility owned by Forecast.

    This is deliberately separate from season forecast uncertainty.  The
    calibration describes ordinary weekly scoring dispersion around an expected
    active-game mean; it is not uncertainty about a player's full-season total.

    The current calibration is a governed provisional promotion of the method
    re-derived from 13,046 historical weekly offensive observations from the
    2023-2025 seasons, scored under the current FSFFL half-PPR rules.  The
    coefficients are retained as evidence-backed provisional inputs while NEXT
    builds a league-scoring-aware historical recalibration pipeline.
    """

    coefficient_of_variation_by_position: tuple[tuple[Position, float], ...]
    observation_count: int
    evidence_seasons: tuple[int, ...]
    evidence_source: str
    model_version: str
    scoring_scope: str

    def coefficient_of_variation(self, position: Position) -> float:
        mapping = dict(self.coefficient_of_variation_by_position)
        try:
            return mapping[position]
        except KeyError as exc:
            raise ValueError(f"weekly volatility calibration unavailable for {position.value}") from exc


# PROVISIONAL_GOVERNED.  These values were produced from the legacy research
# corpus by a method we have independently reviewed and elected to re-derive in
# NEXT: 2023-2025 actual weekly outcomes, 13,046 offensive player-weeks, robust
# position CV with player-history shrinkage in the legacy implementation.  NEXT
# uses only the position evidence here; player-specific shrinkage will be added
# only after the historical data pipeline is native to NEXT.
FSFFL_2023_2025_WEEKLY_VOLATILITY = WeeklyVolatilityCalibration(
    coefficient_of_variation_by_position=(
        (Position.QB, 0.53135),
        (Position.RB, 0.83363),
        (Position.WR, 0.77162),
        (Position.TE, 0.74474),
    ),
    observation_count=13_046,
    evidence_seasons=(2023, 2024, 2025),
    evidence_source=(
        "legacy-fsffl:data/simulator/2026/outputs/weekly_projection_audit.json; "
        "method reviewed for NEXT promotion"
    ),
    model_version="next2-weekly-volatility-v1:2023-2025-position-cv",
    scoring_scope="FSFFL half-PPR offensive scoring; provisional until scoring-aware recalibration",
)


def active_game_distribution(
    *,
    season_mean: float,
    position: Position,
    calibration: WeeklyVolatilityCalibration = FSFFL_2023_2025_WEEKLY_VOLATILITY,
    games_per_team: int = 17,
) -> tuple[float, float]:
    """Return (weekly mean, weekly stddev) for an active NFL game.

    The mean is the season projection distributed over the structural 17-game
    NFL schedule.  Weekly standard deviation comes from empirical week-to-week
    scoring volatility, never from the season forecast-error distribution.
    """

    if games_per_team < 1:
        raise ValueError("games_per_team must be positive")
    if season_mean < 0:
        raise ValueError("season_mean cannot be negative")

    weekly_mean = season_mean / games_per_team
    weekly_stddev = weekly_mean * calibration.coefficient_of_variation(position)
    return weekly_mean, weekly_stddev

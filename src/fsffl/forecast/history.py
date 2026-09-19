from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .models import ForecastHorizon, ForecastMetric, ForecastObservation


@dataclass
class InMemoryForecastStore:
    """Reference point-in-time store for normalized forecast observations.

    The store is provider-neutral. It never substitutes a later forecast for an
    earlier historical query: callers receive only observations whose ``as_of``
    timestamp is at or before the requested cutoff.
    """

    _observations: list[ForecastObservation] = field(default_factory=list)

    def save(self, observations: tuple[ForecastObservation, ...]) -> None:
        self._observations.extend(observations)

    def latest(
        self,
        *,
        player_id: str,
        source: str,
        horizon: ForecastHorizon,
        metric: ForecastMetric,
        period_start: datetime,
        period_end: datetime,
        as_of: datetime,
    ) -> ForecastObservation | None:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        eligible = [
            observation
            for observation in self._observations
            if observation.player_id == player_id
            and observation.source == source
            and observation.horizon == horizon
            and observation.metric == metric
            and observation.period_start == period_start
            and observation.period_end == period_end
            and observation.as_of <= as_of
        ]
        if not eligible:
            return None
        return max(eligible, key=lambda observation: observation.as_of)

    def available_at(
        self,
        *,
        as_of: datetime,
        player_id: str | None = None,
    ) -> tuple[ForecastObservation, ...]:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        eligible = [
            observation
            for observation in self._observations
            if observation.as_of <= as_of
            and (player_id is None or observation.player_id == player_id)
        ]
        return tuple(
            sorted(
                eligible,
                key=lambda observation: (
                    observation.player_id,
                    observation.source,
                    observation.horizon,
                    observation.metric,
                    observation.period_start,
                    observation.period_end,
                    observation.as_of,
                ),
            )
        )

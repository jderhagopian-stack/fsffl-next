from __future__ import annotations

from datetime import datetime
from typing import Protocol

from fsffl.state.models import LeagueState

from .models import ForecastObservation


class ForecastProvider(Protocol):
    """Provider-neutral forecast source boundary.

    Implementations may wrap public projection feeds, internal models, or
    historical snapshots. Provider-specific payloads must be normalized before
    forecast observations cross this boundary.
    """

    provider_name: str

    def observations(
        self,
        *,
        state: LeagueState,
        as_of: datetime,
    ) -> tuple[ForecastObservation, ...]:
        """Return only forecasts that were knowable at ``as_of``."""
        ...

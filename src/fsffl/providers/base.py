from __future__ import annotations

from datetime import datetime
from typing import Protocol

from fsffl.state.models import LeagueState


class LeagueStateProvider(Protocol):
    """Boundary implemented by Sleeper and future league providers.

    Provider-specific payloads must be normalized before crossing this boundary.
    Downstream model code consumes only canonical LeagueState objects.
    """

    provider_name: str

    def materialize_state(self, *, league_external_id: str, as_of: datetime) -> LeagueState:
        """Return the canonical state knowable at ``as_of``.

        Historical implementations must not use facts that became knowable after
        the requested timestamp.
        """
        ...

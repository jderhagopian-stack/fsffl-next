from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from fsffl.providers.acquisition import ProviderSnapshot
from fsffl.providers.sleeper import SleeperNormalizer, SleeperPayloadBundle
from fsffl.state.models import LeagueState


class SleeperSnapshotNormalizer:
    """Bridge an acquired Sleeper snapshot into the pure Sleeper normalizer."""

    provider_name = "sleeper"

    def __init__(self) -> None:
        self._normalizer = SleeperNormalizer()

    def normalize_snapshot(self, snapshot: ProviderSnapshot, *, as_of) -> LeagueState:
        if snapshot.provider_name != self.provider_name:
            raise ValueError("snapshot provider must be sleeper")
        payload = snapshot.payload
        required = ("league", "users", "rosters", "players")
        missing = [key for key in required if key not in payload]
        if missing:
            raise ValueError(f"Sleeper snapshot missing required payloads: {', '.join(missing)}")

        bundle = SleeperPayloadBundle(
            league=payload["league"],
            users=payload["users"],
            rosters=payload["rosters"],
            players=payload["players"],
            traded_picks=payload.get("traded_picks", ()),
            retrieved_at=snapshot.captured_at,
        )
        return self._normalizer.normalize(bundle, as_of=as_of)

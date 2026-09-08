from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from fsffl.state.models import Position


@dataclass(frozen=True)
class CurrentProjectionRow:
    provider: str
    external_id: str
    player_name: str
    position: Position
    nfl_team: str
    stats: Mapping[str, float]


@dataclass(frozen=True)
class CurrentProjectionSnapshot:
    provider: str
    captured_at: datetime
    effective_at: datetime
    rows: tuple[CurrentProjectionRow, ...]
    source_version: str
    usage_class: str

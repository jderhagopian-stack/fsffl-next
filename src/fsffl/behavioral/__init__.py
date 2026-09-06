"""Shared Behavioral Intelligence evidence for FSFFL NEXT.

Behavioral evidence is descriptive input to downstream Decision/Search/Analytics.
It does not own market Value, competitive simulation, or recommendation authority.
"""

from .models import (
    BehavioralAsset,
    BehavioralAssetKind,
    BehavioralEventKind,
    OwnerBehaviorEvent,
    OwnerBehaviorProfile,
)
from .profiles import build_owner_behavior_profiles
from .service import BehavioralIntelligenceService, BehavioralSyncResult
from .sleeper_history import SleeperBehaviorHistorySource, SleeperLeagueHistory
from .store import BehavioralIntelligenceStore

__all__ = [
    "BehavioralAsset",
    "BehavioralAssetKind",
    "BehavioralEventKind",
    "OwnerBehaviorEvent",
    "OwnerBehaviorProfile",
    "SleeperBehaviorHistorySource",
    "SleeperLeagueHistory",
    "BehavioralIntelligenceStore",
    "BehavioralIntelligenceService",
    "BehavioralSyncResult",
    "build_owner_behavior_profiles",
]

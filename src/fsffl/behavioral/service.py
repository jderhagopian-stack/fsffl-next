from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fsffl.state.models import LeagueState

from .models import OwnerBehaviorProfile
from .profiles import build_owner_behavior_profiles
from .sleeper_history import SleeperBehaviorHistorySource
from .store import BehavioralIntelligenceStore


@dataclass(frozen=True)
class BehavioralSyncResult:
    league_family_id: str
    profile_count: int
    total_event_count: int
    inserted_event_count: int
    reused_historical_league_ids: tuple[str, ...]
    scanned_league_ids: tuple[str, ...]
    profiles: tuple[OwnerBehaviorProfile, ...]


class BehavioralIntelligenceService:
    """Incrementally maintain reusable league/owner behavioral evidence."""

    def __init__(
        self,
        *,
        source: SleeperBehaviorHistorySource,
        store: BehavioralIntelligenceStore,
    ) -> None:
        self.source = source
        self.store = store

    def sync_sleeper_league(
        self,
        league_state: LeagueState,
        *,
        sleeper_league_external_id: str,
        as_of: datetime | None = None,
    ) -> BehavioralSyncResult:
        completed = self.store.complete_league_ids()
        positions: dict[str, str] = {}
        for player in league_state.players:
            for ref in player.provider_refs:
                if ref.provider == "sleeper":
                    positions[ref.external_id] = player.position.value

        history = self.source.fetch_history(
            sleeper_league_external_id,
            skip_league_ids=completed,
            player_positions=positions,
        )
        inserted = self.store.put_events(history.events)

        # All non-current leagues in a Sleeper family are immutable historical
        # seasons. Once scanned successfully they can be reused on every later
        # login; only the current league is rescanned for new transactions.
        scanned_ids = {event.league_external_id for event in history.events}
        current = history.current_league_external_id
        for league_id in history.league_chain:
            if league_id == current or league_id in completed:
                continue
            # A season with zero relevant owner events is still a successfully
            # scanned historical season, so mark it complete as well.
            season = next(
                (
                    event.season
                    for event in history.events
                    if event.league_external_id == league_id
                ),
                league_state.league.season - (len(history.league_chain) - 1 - history.league_chain.index(league_id)),
            )
            self.store.mark_season_complete(history.league_family_id, league_id, season)

        all_events = self.store.load_events(history.league_family_id)
        cutoff = as_of or league_state.as_of
        profiles = build_owner_behavior_profiles(all_events, as_of=cutoff)
        self.store.put_profiles(profiles)

        reused = tuple(league_id for league_id in history.league_chain if league_id in completed)
        scanned = tuple(league_id for league_id in history.league_chain if league_id not in completed)
        return BehavioralSyncResult(
            league_family_id=history.league_family_id,
            profile_count=len(profiles),
            total_event_count=len(all_events),
            inserted_event_count=inserted,
            reused_historical_league_ids=reused,
            scanned_league_ids=scanned,
            profiles=profiles,
        )

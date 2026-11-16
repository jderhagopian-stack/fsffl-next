from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from .models import CompletedTradeActivity, BehavioralAssetKind, BehavioralEventKind, OwnerBehaviorEvent, OwnerBehaviorProfile


def build_owner_behavior_profiles(
    events: tuple[OwnerBehaviorEvent, ...] | list[OwnerBehaviorEvent],
    *,
    as_of: datetime | None = None,
) -> tuple[OwnerBehaviorProfile, ...]:
    """Aggregate point-in-time owner events into descriptive evidence profiles.

    No coefficients, preference weights, or recommendation thresholds are used.
    Trade shape is purely structural: disposing more discrete assets than acquired
    is consolidation; acquiring more is diversification; equal counts are balanced.
    """

    cutoff = as_of or datetime.now(UTC)
    if cutoff.tzinfo is None:
        raise ValueError("behavioral profile cutoff must be timezone-aware")
    admissible = [event for event in events if event.occurred_at <= cutoff]
    grouped: dict[tuple[str, str], list[OwnerBehaviorEvent]] = {}
    for event in admissible:
        grouped.setdefault((event.league_family_id, event.owner_id), []).append(event)

    profiles: list[OwnerBehaviorProfile] = []
    for (family_id, owner_id), owner_events in sorted(grouped.items()):
        ordered = sorted(owner_events, key=lambda item: (item.occurred_at, item.event_id))
        kinds = Counter(event.kind for event in ordered)
        acquired_positions: Counter[str] = Counter()
        disposed_positions: Counter[str] = Counter()
        counterparties: Counter[str] = Counter()
        acquired_players = disposed_players = 0
        acquired_picks = disposed_picks = 0
        acquired_faab = disposed_faab = 0
        consolidation = diversification = balanced = 0
        trade_acquired_positions = Counter(); trade_disposed_positions = Counter()
        trade_acquired_picks = trade_disposed_picks = 0
        trades_acquiring_picks = trades_sending_picks = 0

        for event in ordered:
            for asset in event.acquired:
                if asset.kind == BehavioralAssetKind.PLAYER:
                    acquired_players += 1
                    if asset.position:
                        acquired_positions[asset.position] += 1
                elif asset.kind == BehavioralAssetKind.PICK:
                    acquired_picks += 1
                elif asset.kind == BehavioralAssetKind.FAAB:
                    acquired_faab += asset.faab_amount or 0
            for asset in event.disposed:
                if asset.kind == BehavioralAssetKind.PLAYER:
                    disposed_players += 1
                    if asset.position:
                        disposed_positions[asset.position] += 1
                elif asset.kind == BehavioralAssetKind.PICK:
                    disposed_picks += 1
                elif asset.kind == BehavioralAssetKind.FAAB:
                    disposed_faab += asset.faab_amount or 0
            if event.kind == BehavioralEventKind.TRADE:
                trade_buys = sum(a.kind == BehavioralAssetKind.PICK for a in event.acquired)
                trade_sells = sum(a.kind == BehavioralAssetKind.PICK for a in event.disposed)
                trade_acquired_picks += trade_buys; trade_disposed_picks += trade_sells
                trades_acquiring_picks += bool(trade_buys); trades_sending_picks += bool(trade_sells)
                trade_acquired_positions.update(a.position for a in event.acquired if a.kind == BehavioralAssetKind.PLAYER and a.position)
                trade_disposed_positions.update(a.position for a in event.disposed if a.kind == BehavioralAssetKind.PLAYER and a.position)
                counterparties.update(event.counterparty_owner_ids)
                sent_count = len(event.disposed)
                received_count = len(event.acquired)
                if sent_count > received_count:
                    consolidation += 1
                elif received_count > sent_count:
                    diversification += 1
                else:
                    balanced += 1

        profiles.append(
            OwnerBehaviorProfile(
                league_family_id=family_id,
                owner_id=owner_id,
                as_of=cutoff,
                first_observed_at=ordered[0].occurred_at if ordered else None,
                event_count=len(ordered),
                trade_count=kinds[BehavioralEventKind.TRADE],
                waiver_count=kinds[BehavioralEventKind.WAIVER],
                free_agent_count=kinds[BehavioralEventKind.FREE_AGENT],
                acquired_player_count=acquired_players,
                disposed_player_count=disposed_players,
                acquired_pick_count=acquired_picks,
                disposed_pick_count=disposed_picks,
                acquired_faab=acquired_faab,
                disposed_faab=disposed_faab,
                consolidation_trade_count=consolidation,
                diversification_trade_count=diversification,
                balanced_trade_count=balanced,
                completed_trade_activity=CompletedTradeActivity(
                    acquired_pick_count=trade_acquired_picks, disposed_pick_count=trade_disposed_picks,
                    trades_acquiring_picks=trades_acquiring_picks, trades_sending_picks=trades_sending_picks,
                    acquired_positions=dict(sorted(trade_acquired_positions.items())),
                    disposed_positions=dict(sorted(trade_disposed_positions.items()))),
                acquired_positions=dict(sorted(acquired_positions.items())),
                disposed_positions=dict(sorted(disposed_positions.items())),
                counterparty_trade_counts=dict(sorted(counterparties.items())),
                seasons_observed=tuple(sorted({event.season for event in ordered})),
            )
        )
    return tuple(profiles)

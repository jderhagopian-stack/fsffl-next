from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Mapping, Sequence
from urllib.request import Request, urlopen

from .models import BehavioralAsset, BehavioralAssetKind, BehavioralEventKind, OwnerBehaviorEvent


JsonGetter = Callable[[str], Any]


@dataclass(frozen=True)
class SleeperLeagueHistory:
    league_family_id: str
    current_league_external_id: str
    league_chain: tuple[str, ...]
    events: tuple[OwnerBehaviorEvent, ...]


class SleeperBehaviorHistorySource:
    """Acquire completed Sleeper transaction history as Behavioral evidence.

    This source performs provider acquisition/normalization only. It does not
    infer owner preferences, team utility, market Value, or recommendation odds.
    Historical seasons are linked using Sleeper's previous_league_id chain.
    """

    base_url = "https://api.sleeper.app/v1"

    def __init__(self, *, http_get_json: JsonGetter | None = None, max_workers: int = 6) -> None:
        self._http_get_json = http_get_json or _default_get_json
        self.max_workers = max(1, max_workers)

    def fetch_history(
        self,
        current_league_external_id: str,
        *,
        skip_league_ids: frozenset[str] = frozenset(),
        player_positions: Mapping[str, str] | None = None,
    ) -> SleeperLeagueHistory:
        current = current_league_external_id.strip()
        if not current:
            raise ValueError("current Sleeper league id cannot be blank")

        chain_payloads: list[Mapping[str, Any]] = []
        seen: set[str] = set()
        league_id: str | None = current
        while league_id:
            if league_id in seen:
                raise ValueError("Sleeper previous_league_id chain contains a cycle")
            seen.add(league_id)
            league = self._get(f"/league/{league_id}")
            if not isinstance(league, Mapping):
                raise ValueError("Sleeper league history payload must be an object")
            chain_payloads.append(league)
            previous = league.get("previous_league_id")
            league_id = str(previous).strip() if previous else None

        oldest = str(chain_payloads[-1].get("league_id") or "").strip()
        if not oldest:
            raise ValueError("Sleeper league history is missing league_id")
        family_id = f"sleeper-family:{oldest}"
        events: list[OwnerBehaviorEvent] = []
        for league in reversed(chain_payloads):
            external_id = str(league.get("league_id") or "").strip()
            if not external_id or external_id in skip_league_ids:
                continue
            events.extend(
                self._league_events(
                    family_id,
                    league,
                    player_positions=player_positions or {},
                )
            )

        return SleeperLeagueHistory(
            league_family_id=family_id,
            current_league_external_id=current,
            league_chain=tuple(str(row.get("league_id")) for row in reversed(chain_payloads)),
            events=tuple(sorted(events, key=lambda item: (item.occurred_at, item.event_id))),
        )

    def _league_events(
        self,
        family_id: str,
        league: Mapping[str, Any],
        *,
        player_positions: Mapping[str, str],
    ) -> list[OwnerBehaviorEvent]:
        external_id = str(league["league_id"])
        season = int(league["season"])
        rosters = self._get(f"/league/{external_id}/rosters")
        if not isinstance(rosters, Sequence) or isinstance(rosters, (str, bytes)):
            raise ValueError("Sleeper historical rosters must be a sequence")
        owner_by_roster: dict[int, str] = {}
        for roster in rosters:
            if not isinstance(roster, Mapping):
                continue
            owner = roster.get("owner_id")
            roster_id = roster.get("roster_id")
            if owner is None or roster_id is None:
                continue
            owner_by_roster[int(roster_id)] = str(owner)

        # Sleeper exposes transactions by week. Fetching them independently keeps
        # the expensive first build parallelizable; completed historical seasons
        # can then be skipped entirely by the persistent store on later logins.
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            week_rows = list(
                pool.map(
                    lambda week: self._get(f"/league/{external_id}/transactions/{week}"),
                    range(1, 19),
                )
            )

        normalized: list[OwnerBehaviorEvent] = []
        seen_transactions: set[str] = set()
        for rows in week_rows:
            if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
                continue
            for raw in rows:
                if not isinstance(raw, Mapping):
                    continue
                transaction_id = str(raw.get("transaction_id") or "").strip()
                if not transaction_id or transaction_id in seen_transactions:
                    continue
                seen_transactions.add(transaction_id)
                status = str(raw.get("status") or "").lower()
                if status not in {"complete", "completed"}:
                    continue
                kind_raw = str(raw.get("type") or "").lower()
                if kind_raw == "trade":
                    kind = BehavioralEventKind.TRADE
                elif kind_raw == "waiver":
                    kind = BehavioralEventKind.WAIVER
                elif kind_raw in {"free_agent", "free agent"}:
                    kind = BehavioralEventKind.FREE_AGENT
                else:
                    continue
                created = raw.get("created")
                if created is None:
                    continue
                occurred_at = datetime.fromtimestamp(float(created) / 1000.0, tz=UTC)
                roster_ids = tuple(
                    int(value)
                    for value in (raw.get("roster_ids") or ())
                    if value is not None
                )
                if not roster_ids:
                    involved = set()
                    involved.update(int(value) for value in (raw.get("adds") or {}).values())
                    involved.update(int(value) for value in (raw.get("drops") or {}).values())
                    roster_ids = tuple(sorted(involved))

                for roster_id in roster_ids:
                    owner_id = owner_by_roster.get(roster_id)
                    if owner_id is None:
                        continue
                    acquired: list[BehavioralAsset] = []
                    disposed: list[BehavioralAsset] = []
                    for player_id, receiving_roster in (raw.get("adds") or {}).items():
                        if int(receiving_roster) == roster_id:
                            acquired.append(
                                BehavioralAsset(
                                    kind=BehavioralAssetKind.PLAYER,
                                    asset_ref=f"sleeper:player:{player_id}",
                                    position=player_positions.get(str(player_id)),
                                )
                            )
                    for player_id, sending_roster in (raw.get("drops") or {}).items():
                        if int(sending_roster) == roster_id:
                            disposed.append(
                                BehavioralAsset(
                                    kind=BehavioralAssetKind.PLAYER,
                                    asset_ref=f"sleeper:player:{player_id}",
                                    position=player_positions.get(str(player_id)),
                                )
                            )
                    for pick in raw.get("draft_picks") or ():
                        if not isinstance(pick, Mapping):
                            continue
                        try:
                            pick_season = int(pick["season"])
                            pick_round = int(pick["round"])
                            original = int(pick["roster_id"])
                            new_owner = int(pick["owner_id"])
                            previous_owner = int(pick["previous_owner_id"])
                        except (KeyError, TypeError, ValueError):
                            continue
                        asset = BehavioralAsset(
                            kind=BehavioralAssetKind.PICK,
                            asset_ref=f"sleeper:pick:{pick_season}:{pick_round}:{original}",
                            pick_season=pick_season,
                            pick_round=pick_round,
                        )
                        if new_owner == roster_id:
                            acquired.append(asset)
                        if previous_owner == roster_id:
                            disposed.append(asset)
                    for faab in raw.get("waiver_budget") or ():
                        if not isinstance(faab, Mapping):
                            continue
                        try:
                            sender = int(faab["sender"])
                            receiver = int(faab["receiver"])
                            amount = int(faab["amount"])
                        except (KeyError, TypeError, ValueError):
                            continue
                        asset = BehavioralAsset(
                            kind=BehavioralAssetKind.FAAB,
                            asset_ref=f"sleeper:faab:{transaction_id}:{sender}:{receiver}",
                            faab_amount=max(amount, 0),
                        )
                        if receiver == roster_id:
                            acquired.append(asset)
                        if sender == roster_id:
                            disposed.append(asset)
                    counterparties = tuple(
                        sorted(
                            {
                                owner_by_roster[other]
                                for other in roster_ids
                                if other != roster_id and other in owner_by_roster
                            }
                        )
                    )
                    normalized.append(
                        OwnerBehaviorEvent(
                            event_id=f"sleeper:{external_id}:{transaction_id}:roster:{roster_id}",
                            league_family_id=family_id,
                            league_external_id=external_id,
                            season=season,
                            owner_id=owner_id,
                            roster_id=roster_id,
                            occurred_at=occurred_at,
                            kind=kind,
                            acquired=tuple(acquired),
                            disposed=tuple(disposed),
                            counterparty_owner_ids=counterparties,
                        )
                    )
        return normalized

    def _get(self, path: str) -> Any:
        return self._http_get_json(f"{self.base_url}{path}")


def _default_get_json(url: str) -> Any:
    request = Request(url, headers={"User-Agent": "fsffl-next/0.1"})
    with urlopen(request, timeout=30) as response:  # nosec B310 - fixed HTTPS provider base
        return json.loads(response.read().decode("utf-8"))

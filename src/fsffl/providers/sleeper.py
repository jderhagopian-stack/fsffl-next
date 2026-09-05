from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from fsffl.state.models import (
    DraftPick,
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    PickOwnership,
    Player,
    PlayerState,
    PlayerStatus,
    Position,
    Provenance,
    ProviderRef,
    RosterEntry,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)


@dataclass(frozen=True)
class SleeperPayloadBundle:
    league: Mapping[str, Any]
    users: Sequence[Mapping[str, Any]]
    rosters: Sequence[Mapping[str, Any]]
    players: Mapping[str, Mapping[str, Any]]
    traded_picks: Sequence[Mapping[str, Any]] = ()
    retrieved_at: datetime | None = None


class SleeperNormalizer:
    """Pure mapping layer from Sleeper-shaped payloads to canonical FSFFL state.

    Network access is intentionally outside this class. This keeps historical
    replay and tests independent from live-provider behavior.
    """

    provider_name = "sleeper"

    _slot_map = {
        "QB": RosterSlot.QB,
        "RB": RosterSlot.RB,
        "WR": RosterSlot.WR,
        "TE": RosterSlot.TE,
        "FLEX": RosterSlot.FLEX,
        "SUPER_FLEX": RosterSlot.SUPERFLEX,
        "K": RosterSlot.K,
        "DEF": RosterSlot.DST,
    }

    _position_map = {
        "QB": Position.QB,
        "RB": Position.RB,
        "WR": Position.WR,
        "TE": Position.TE,
        "K": Position.K,
        "DEF": Position.DST,
    }

    @staticmethod
    def _age_years(raw_age: Any) -> float | None:
        """Preserve explicit provider age without inferring or backfilling it."""

        if isinstance(raw_age, bool) or raw_age is None:
            return None
        try:
            age = float(raw_age)
        except (TypeError, ValueError):
            return None
        return age if age >= 0 else None

    def normalize(self, bundle: SleeperPayloadBundle, *, as_of: datetime) -> LeagueState:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        retrieved_at = bundle.retrieved_at or as_of
        if retrieved_at.tzinfo is None:
            raise ValueError("retrieved_at must be timezone-aware")

        league_external_id = str(bundle.league["league_id"])
        league_id = f"sleeper:{league_external_id}"
        settings = bundle.league.get("settings", {})
        roster_positions = list(bundle.league.get("roster_positions", []))
        scoring_settings = bundle.league.get("scoring_settings", {})

        starter_slots = [
            self._slot_map[str(raw_slot)]
            for raw_slot in roster_positions
            if str(raw_slot) in self._slot_map
        ]
        lineup_counts: dict[RosterSlot, int] = {}
        for slot in starter_slots:
            lineup_counts[slot] = lineup_counts.get(slot, 0) + 1

        lineup = tuple(
            LineupRequirement(slot=slot, count=count)
            for slot, count in sorted(lineup_counts.items(), key=lambda item: item[0].value)
        )
        scoring = tuple(
            ScoringRule(stat=str(stat), points=float(points))
            for stat, points in sorted(scoring_settings.items())
            if isinstance(points, (int, float))
        )
        roster_size = int(settings.get("roster_size") or len(roster_positions) or 1)
        team_count = int(settings.get("num_teams") or len(bundle.rosters) or 2)
        faab_budget = int(settings.get("waiver_budget") or 0)

        league = League(
            league_id=league_id,
            name=str(bundle.league.get("name") or "Sleeper League"),
            season=int(bundle.league.get("season")),
            rules=LeagueRules(
                team_count=team_count,
                roster_size=roster_size,
                taxi_size=int(settings.get("taxi_slots") or 0),
                ir_size=int(settings.get("reserve_slots") or 0),
                rookie_draft_rounds=int(settings.get("draft_rounds") or 0),
                lineup=lineup,
                scoring=scoring,
            ),
            provider_refs=(ProviderRef(provider="sleeper", external_id=league_external_id),),
        )

        user_names = {
            str(user.get("user_id")): str(
                user.get("display_name") or user.get("username") or user.get("user_id")
            )
            for user in bundle.users
            if user.get("user_id") is not None
        }

        teams: list[Team] = []
        team_states: list[TeamState] = []
        referenced_player_ids: set[str] = set()
        roster_id_to_team_id: dict[int, str] = {}

        for roster in bundle.rosters:
            roster_id = int(roster["roster_id"])
            team_id = f"{league_id}:team:{roster_id}"
            roster_id_to_team_id[roster_id] = team_id
            owner_id = roster.get("owner_id")
            teams.append(
                Team(
                    team_id=team_id,
                    league_id=league_id,
                    display_name=user_names.get(str(owner_id), f"Team {roster_id}"),
                    provider_refs=(ProviderRef(provider="sleeper", external_id=str(roster_id)),),
                )
            )

            raw_starters = [str(pid) for pid in (roster.get("starters") or []) if pid]
            starter_slot_by_player = {
                pid: starter_slots[index]
                for index, pid in enumerate(raw_starters)
                if index < len(starter_slots)
            }
            reserve = {str(pid) for pid in (roster.get("reserve") or []) if pid}
            taxi = {str(pid) for pid in (roster.get("taxi") or []) if pid}
            entries: list[RosterEntry] = []
            for pid_raw in roster.get("players") or []:
                pid = str(pid_raw)
                referenced_player_ids.add(pid)
                if pid in taxi:
                    slot = RosterSlot.TAXI
                elif pid in reserve:
                    slot = RosterSlot.IR
                elif pid in starter_slot_by_player:
                    slot = starter_slot_by_player[pid]
                else:
                    slot = RosterSlot.BENCH
                entries.append(RosterEntry(player_id=f"sleeper:player:{pid}", slot=slot))

            used_faab = int((roster.get("settings") or {}).get("waiver_budget_used") or 0)
            current_faab = max(faab_budget - used_faab, 0) if faab_budget else 0
            team_states.append(
                TeamState(
                    team_id=team_id,
                    roster=tuple(entries),
                    faab_balance=current_faab,
                )
            )

        provenance = Provenance(
            source="sleeper",
            retrieved_at=retrieved_at,
            effective_at=as_of,
            provider_ref=ProviderRef(provider="sleeper", external_id=league_external_id),
        )

        players: list[Player] = []
        player_states: list[PlayerState] = []
        for external_id in sorted(referenced_player_ids):
            raw = bundle.players.get(external_id, {})
            raw_position = str(raw.get("position") or "")
            position = self._position_map.get(raw_position)
            if position is None:
                continue
            player_id = f"sleeper:player:{external_id}"
            full_name = str(
                raw.get("full_name")
                or " ".join(filter(None, [raw.get("first_name"), raw.get("last_name")]))
                or external_id
            )
            nfl_team = raw.get("team")
            players.append(
                Player(
                    player_id=player_id,
                    full_name=full_name,
                    position=position,
                    nfl_team=str(nfl_team) if nfl_team else None,
                    provider_refs=(ProviderRef(provider="sleeper", external_id=external_id),),
                )
            )
            status_raw = str(raw.get("status") or "unknown").lower()
            status = PlayerStatus.ACTIVE if status_raw == "active" else PlayerStatus.UNKNOWN
            player_states.append(
                PlayerState(
                    player_id=player_id,
                    as_of=as_of,
                    age_years=self._age_years(raw.get("age")),
                    nfl_team=str(nfl_team) if nfl_team else None,
                    status=status,
                    provenance=provenance,
                )
            )

        valid_player_ids = {player.player_id for player in players}
        team_states = [
            state.model_copy(
                update={
                    "roster": tuple(
                        entry for entry in state.roster if entry.player_id in valid_player_ids
                    )
                }
            )
            for state in team_states
        ]

        draft_picks: list[DraftPick] = []
        pick_ownership: list[PickOwnership] = []
        rounds = league.rules.rookie_draft_rounds
        for season in range(league.season + 1, league.season + 4):
            for roster_id, original_team_id in roster_id_to_team_id.items():
                for round_number in range(1, rounds + 1):
                    pick_id = f"{league_id}:pick:{season}:{round_number}:{roster_id}"
                    draft_picks.append(
                        DraftPick(
                            pick_id=pick_id,
                            league_id=league_id,
                            season=season,
                            round=round_number,
                            original_team_id=original_team_id,
                        )
                    )
                    pick_ownership.append(
                        PickOwnership(pick_id=pick_id, owner_team_id=original_team_id)
                    )

        ownership_by_pick = {entry.pick_id: entry.owner_team_id for entry in pick_ownership}
        for trade in bundle.traded_picks:
            try:
                season = int(trade["season"])
                round_number = int(trade["round"])
                original_roster_id = int(trade["roster_id"])
                owner_roster_id = int(trade["owner_id"])
            except (KeyError, TypeError, ValueError):
                continue
            pick_id = f"{league_id}:pick:{season}:{round_number}:{original_roster_id}"
            owner_team_id = roster_id_to_team_id.get(owner_roster_id)
            if pick_id in ownership_by_pick and owner_team_id is not None:
                ownership_by_pick[pick_id] = owner_team_id
        pick_ownership = [
            PickOwnership(pick_id=pick_id, owner_team_id=owner_team_id)
            for pick_id, owner_team_id in sorted(ownership_by_pick.items())
        ]

        return LeagueState(
            league=league,
            as_of=as_of.astimezone(UTC),
            teams=tuple(teams),
            team_states=tuple(team_states),
            players=tuple(players),
            player_states=tuple(player_states),
            draft_picks=tuple(draft_picks),
            pick_ownership=tuple(pick_ownership),
            provenance=(provenance,),
        )

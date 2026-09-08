from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from fsffl.state.models import (
    DraftPick,
    League,
    LeagueMatchup,
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
    matchups: Mapping[str, Sequence[Mapping[str, Any]]] | None = None
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

    @staticmethod
    def _points(row: Mapping[str, Any]) -> float | None:
        raw = row.get("custom_points")
        if raw is None:
            raw = row.get("points")
        if raw is None or isinstance(raw, bool):
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _scoring_rules(scoring_settings: Mapping[str, Any]) -> tuple[ScoringRule, ...]:
        """Normalize every explicit Sleeper scoring coefficient or fail closed.

        Provider payloads are usually JSON numbers, but numeric strings are safe to
        normalize. Silently dropping a non-number is not safe because a missing TD,
        reception, or turnover coefficient can materially corrupt every downstream
        fantasy-point forecast while leaving the pipeline apparently healthy.
        """

        rules: list[ScoringRule] = []
        for stat, raw_points in sorted(scoring_settings.items()):
            if isinstance(raw_points, bool) or raw_points is None:
                raise ValueError(f"Sleeper scoring coefficient for {stat} is not numeric")
            try:
                points = float(raw_points)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Sleeper scoring coefficient for {stat} is not numeric"
                ) from exc
            rules.append(ScoringRule(stat=str(stat), points=points))
        return tuple(rules)

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
        if not isinstance(scoring_settings, Mapping):
            raise ValueError("Sleeper scoring_settings must be a mapping")

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
        scoring = self._scoring_rules(scoring_settings)
        roster_size = int(settings.get("roster_size") or len(roster_positions) or 1)
        team_count = int(settings.get("num_teams") or len(bundle.rosters) or 2)
        faab_budget = int(settings.get("waiver_budget") or 0)
        raw_playoff_teams = settings.get("playoff_teams")
        playoff_team_count = int(raw_playoff_teams) if raw_playoff_teams else None

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
                playoff_team_count=playoff_team_count,
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
            players = [str(pid) for pid in (roster.get("players") or []) if pid]
            referenced_player_ids.update(players)

            roster_entries: list[RosterEntry] = []
            for player_external_id in players:
                player_id = f"sleeper:player:{player_external_id}"
                if player_external_id in reserve:
                    slot = RosterSlot.IR
                elif player_external_id in taxi:
                    slot = RosterSlot.TAXI
                else:
                    slot = starter_slot_by_player.get(player_external_id, RosterSlot.BENCH)
                roster_entries.append(RosterEntry(player_id=player_id, slot=slot))

            team_states.append(
                TeamState(
                    team_id=team_id,
                    roster=tuple(roster_entries),
                    faab_budget_remaining=float((roster.get("settings") or {}).get("waiver_budget_used") or faab_budget),
                )
            )

        players: list[Player] = []
        player_states: list[PlayerState] = []
        for external_player_id in sorted(referenced_player_ids):
            raw_player = bundle.players.get(external_player_id)
            if raw_player is None:
                continue
            raw_position = str(raw_player.get("position") or "")
            position = self._position_map.get(raw_position)
            if position is None:
                continue
            player_id = f"sleeper:player:{external_player_id}"
            nfl_team = raw_player.get("team")
            team = str(nfl_team) if nfl_team else None
            full_name = str(
                raw_player.get("full_name")
                or " ".join(
                    part
                    for part in (str(raw_player.get("first_name") or "").strip(), str(raw_player.get("last_name") or "").strip())
                    if part
                )
                or external_player_id
            )
            players.append(
                Player(
                    player_id=player_id,
                    full_name=full_name,
                    position=position,
                    nfl_team=team,
                    age_years=self._age_years(raw_player.get("age")),
                    provider_refs=(ProviderRef(provider="sleeper", external_id=external_player_id),),
                )
            )
            player_states.append(
                PlayerState(
                    player_id=player_id,
                    as_of=as_of,
                    nfl_team=team,
                    status=PlayerStatus.ACTIVE,
                    provenance=Provenance(
                        source="sleeper",
                        retrieved_at=retrieved_at,
                        effective_at=as_of,
                    ),
                )
            )

        traded_picks: dict[tuple[int, int, int], int] = {}
        for traded in bundle.traded_picks:
            traded_picks[(int(traded["season"]), int(traded["round"]), int(traded["roster_id"]))] = int(traded["owner_id"])

        picks: list[DraftPick] = []
        pick_ownership: list[PickOwnership] = []
        current_season = int(bundle.league.get("season"))
        rounds = int(settings.get("draft_rounds") or 0)
        for season in range(current_season + 1, current_season + 4):
            for round_number in range(1, rounds + 1):
                for original_roster_id, original_team_id in sorted(roster_id_to_team_id.items()):
                    pick_id = f"sleeper:pick:{season}:{round_number}:{original_roster_id}"
                    picks.append(
                        DraftPick(
                            pick_id=pick_id,
                            league_id=league_id,
                            season=season,
                            round=round_number,
                            original_team_id=original_team_id,
                            provider_refs=(ProviderRef(provider="sleeper", external_id=f"{season}:{round_number}:{original_roster_id}"),),
                        )
                    )
                    owner_roster_id = traded_picks.get(
                        (season, round_number, original_roster_id),
                        original_roster_id,
                    )
                    owner_team_id = roster_id_to_team_id.get(owner_roster_id)
                    if owner_team_id is None:
                        continue
                    pick_ownership.append(PickOwnership(pick_id=pick_id, team_id=owner_team_id))

        matchups: list[LeagueMatchup] = []
        if bundle.matchups:
            for week_key, week_rows in sorted(bundle.matchups.items(), key=lambda item: int(item[0])):
                week = int(week_key)
                by_matchup: dict[int, list[Mapping[str, Any]]] = {}
                for row in week_rows:
                    matchup_id = row.get("matchup_id")
                    if matchup_id is None:
                        continue
                    by_matchup.setdefault(int(matchup_id), []).append(row)
                for matchup_id, pair in sorted(by_matchup.items()):
                    if len(pair) != 2:
                        continue
                    left, right = pair
                    left_team = roster_id_to_team_id.get(int(left["roster_id"]))
                    right_team = roster_id_to_team_id.get(int(right["roster_id"]))
                    if left_team is None or right_team is None:
                        continue
                    matchups.append(
                        LeagueMatchup(
                            week=week,
                            matchup_id=str(matchup_id),
                            team_a_id=left_team,
                            team_b_id=right_team,
                            team_a_points=self._points(left),
                            team_b_points=self._points(right),
                        )
                    )

        return LeagueState(
            league=league,
            as_of=as_of,
            teams=tuple(teams),
            team_states=tuple(team_states),
            players=tuple(players),
            player_states=tuple(player_states),
            draft_picks=tuple(picks),
            pick_ownership=tuple(pick_ownership),
            matchups=tuple(matchups),
        )

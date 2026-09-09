from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from fsffl.product.runtime import (
    LiveForecastEvidence,
    PrivateBetaRuntimeStore,
    UserRuntimeContext,
    league_material_fingerprint,
)
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    PlayerStatus,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    ScoringRule,
    Team,
    TeamState,
)


BASE = datetime(2026, 9, 9, 12, 0, tzinfo=UTC)


def _state(*, as_of: datetime, p1_status: PlayerStatus = PlayerStatus.ACTIVE) -> LeagueState:
    provenance = Provenance(source="test", retrieved_at=as_of, effective_at=as_of)
    league = League(
        league_id="league:test",
        name="Test League",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=1,
            lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
            scoring=(ScoringRule(stat="pass_yd", points=0.04),),
        ),
    )
    teams = (
        Team(team_id="team:a", league_id=league.league_id, display_name="A"),
        Team(team_id="team:b", league_id=league.league_id, display_name="B"),
    )
    players = (
        Player(player_id="p1", full_name="One", position=Position.QB),
        Player(player_id="p2", full_name="Two", position=Position.QB),
    )
    return LeagueState(
        league=league,
        as_of=as_of,
        teams=teams,
        team_states=(
            TeamState(team_id="team:a", roster=(RosterEntry(player_id="p1", slot=RosterSlot.QB),)),
            TeamState(team_id="team:b", roster=(RosterEntry(player_id="p2", slot=RosterSlot.QB),)),
        ),
        players=players,
        player_states=(
            PlayerState(player_id="p1", as_of=as_of, status=p1_status, provenance=provenance),
            PlayerState(player_id="p2", as_of=as_of, status=PlayerStatus.ACTIVE, provenance=provenance),
        ),
        provenance=(provenance,),
    )


def test_material_fingerprint_ignores_snapshot_timestamp_and_provenance_time() -> None:
    first = _state(as_of=BASE)
    later = _state(as_of=BASE + timedelta(minutes=5))
    assert first.state_id != later.state_id
    assert league_material_fingerprint(first) == league_material_fingerprint(later)


def test_material_fingerprint_changes_when_player_status_changes() -> None:
    active = _state(as_of=BASE)
    injured = _state(as_of=BASE + timedelta(minutes=5), p1_status=PlayerStatus.INJURED)
    assert league_material_fingerprint(active) != league_material_fingerprint(injured)


def test_same_material_state_preserves_existing_intelligence_and_team_selection() -> None:
    store = PrivateBetaRuntimeStore()
    original = _state(as_of=BASE)
    fake_forecast = cast(LiveForecastEvidence, object())
    store._contexts["u"] = UserRuntimeContext(
        user_id="u",
        league_state=original,
        selected_team_id="team:a",
        forecast_evidence=fake_forecast,
    )

    returned = store.set_league_state("u", _state(as_of=BASE + timedelta(minutes=5)))

    assert returned.league_state is original
    assert returned.forecast_evidence is fake_forecast
    assert returned.selected_team_id == "team:a"
    assert returned.intelligence_reused is True


def test_material_change_invalidates_intelligence_but_preserves_valid_team_selection() -> None:
    store = PrivateBetaRuntimeStore()
    original = _state(as_of=BASE)
    fake_forecast = cast(LiveForecastEvidence, object())
    store._contexts["u"] = UserRuntimeContext(
        user_id="u",
        league_state=original,
        selected_team_id="team:a",
        forecast_evidence=fake_forecast,
    )
    changed = _state(as_of=BASE + timedelta(minutes=5), p1_status=PlayerStatus.INJURED)

    returned = store.set_league_state("u", changed)

    assert returned.league_state is changed
    assert returned.forecast_evidence is None
    assert returned.selected_team_id == "team:a"
    assert returned.intelligence_reused is False

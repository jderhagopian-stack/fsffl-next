from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

from fsffl.product.runtime import (
    LiveForecastEvidence,
    PrivateBetaRuntimeStore,
    UserRuntimeContext,
    forecast_input_fingerprint,
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


def _state(
    *,
    as_of: datetime,
    p1_status: PlayerStatus = PlayerStatus.ACTIVE,
    pass_yard_points: float = 0.04,
    lineup: tuple[LineupRequirement, ...] | None = None,
) -> LeagueState:
    provenance = Provenance(source="test", retrieved_at=as_of, effective_at=as_of)
    league = League(
        league_id="league:test",
        name="Test League",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=1,
            lineup=lineup or (LineupRequirement(slot=RosterSlot.QB, count=1),),
            scoring=(ScoringRule(stat="pass_yd", points=pass_yard_points),),
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


def _empty_forecast() -> LiveForecastEvidence:
    return cast(
        LiveForecastEvidence,
        SimpleNamespace(raw_forecasts=(), league_scored_forecasts=()),
    )


def _complete_context(state: LeagueState) -> tuple[UserRuntimeContext, object, object, object]:
    fake_forecast = _empty_forecast()
    fake_simulation = cast(Any, object())
    fake_value = cast(Any, object())
    return (
        UserRuntimeContext(
            user_id="u",
            league_state=state,
            selected_team_id="team:a",
            forecast_evidence=fake_forecast,
            simulation_analytics=fake_simulation,
            value_evidence=fake_value,
        ),
        fake_forecast,
        fake_simulation,
        fake_value,
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


def test_forecast_input_fingerprint_ignores_status_and_snapshot_time() -> None:
    active = _state(as_of=BASE)
    injured = _state(as_of=BASE + timedelta(minutes=5), p1_status=PlayerStatus.INJURED)
    assert forecast_input_fingerprint(active) == forecast_input_fingerprint(injured)


def test_forecast_input_fingerprint_changes_when_scoring_changes() -> None:
    standard = _state(as_of=BASE)
    changed_scoring = _state(as_of=BASE + timedelta(minutes=5), pass_yard_points=0.05)
    assert forecast_input_fingerprint(standard) != forecast_input_fingerprint(changed_scoring)


def test_forecast_input_fingerprint_changes_when_active_lineup_domains_change() -> None:
    qb_only = _state(as_of=BASE)
    with_kicker = _state(
        as_of=BASE + timedelta(minutes=5),
        lineup=(
            LineupRequirement(slot=RosterSlot.QB, count=1),
            LineupRequirement(slot=RosterSlot.K, count=1),
        ),
    )
    assert forecast_input_fingerprint(qb_only) != forecast_input_fingerprint(with_kicker)


def test_same_material_state_preserves_completed_intelligence_and_team_selection() -> None:
    store = PrivateBetaRuntimeStore()
    original = _state(as_of=BASE)
    context, fake_forecast, fake_simulation, fake_value = _complete_context(original)
    store._contexts["u"] = context

    returned = store.set_league_state("u", _state(as_of=BASE + timedelta(minutes=5)))

    assert returned.league_state is original
    assert returned.forecast_evidence is fake_forecast
    assert returned.simulation_analytics is fake_simulation
    assert returned.value_evidence is fake_value
    assert returned.selected_team_id == "team:a"
    assert returned.intelligence_reused is True


def test_forecast_compatible_material_change_preserves_forecast_only() -> None:
    store = PrivateBetaRuntimeStore()
    original = _state(as_of=BASE)
    context, fake_forecast, _, _ = _complete_context(original)
    store._contexts["u"] = context
    changed = _state(as_of=BASE + timedelta(minutes=5), p1_status=PlayerStatus.INJURED)

    returned = store.set_league_state("u", changed)

    assert returned.league_state is changed
    assert returned.forecast_evidence is fake_forecast
    assert returned.simulation_analytics is None
    assert returned.value_evidence is None
    assert returned.selected_team_id == "team:a"
    assert returned.intelligence_reused is False


def test_forecast_input_change_invalidates_forecast_and_downstream_intelligence() -> None:
    store = PrivateBetaRuntimeStore()
    original = _state(as_of=BASE)
    context, _, _, _ = _complete_context(original)
    store._contexts["u"] = context
    changed = _state(as_of=BASE + timedelta(minutes=5), pass_yard_points=0.05)

    returned = store.set_league_state("u", changed)

    assert returned.league_state is changed
    assert returned.forecast_evidence is None
    assert returned.simulation_analytics is None
    assert returned.value_evidence is None
    assert returned.selected_team_id == "team:a"
    assert returned.intelligence_reused is False


def test_older_replacement_state_does_not_reuse_future_forecast_evidence() -> None:
    store = PrivateBetaRuntimeStore()
    original = _state(as_of=BASE + timedelta(minutes=10))
    future_observation = SimpleNamespace(as_of=BASE + timedelta(minutes=10))
    forecast = cast(
        LiveForecastEvidence,
        SimpleNamespace(raw_forecasts=(future_observation,), league_scored_forecasts=()),
    )
    store._contexts["u"] = UserRuntimeContext(
        user_id="u",
        league_state=original,
        selected_team_id="team:a",
        forecast_evidence=forecast,
    )
    replacement = _state(as_of=BASE, p1_status=PlayerStatus.INJURED)

    returned = store.set_league_state("u", replacement)

    assert forecast_input_fingerprint(original) == forecast_input_fingerprint(replacement)
    assert returned.league_state is replacement
    assert returned.forecast_evidence is None

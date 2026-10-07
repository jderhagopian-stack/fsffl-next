from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from fsffl.forecast.models import (
    ForecastDistribution,
    ForecastHorizon,
    ForecastMetric,
    ForecastObservation,
)
from fsffl.product import current_position_depth
from fsffl.product.current_position_depth import (
    build_current_position_depth_from_outlook,
    build_governed_current_position_depth,
)
from fsffl.product.runtime import PrivateBetaRuntimeStore
from fsffl.product.webapp import create_app
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    Position,
    Provenance,
    RosterEntry,
    RosterSlot,
    Team,
    TeamState,
)


NOW = datetime(2026, 10, 6, 18, 0, tzinfo=UTC)
PERIOD_START = datetime(2026, 9, 1, tzinfo=UTC)
PERIOD_END = datetime(2027, 3, 1, tzinfo=UTC)


def _forecast(player_id: str, position: Position, points: float) -> ForecastObservation:
    provenance = Provenance(
        source="fsffl:completed-actuals-plus-ros",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="next2-completed-actuals-plus-ros-v1",
    )
    return ForecastObservation(
        player_id=player_id,
        position=position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        distribution=ForecastDistribution(mean=points, stddev=12.0),
        source="fsffl:completed-actuals-plus-ros",
        model_version="next2-completed-actuals-plus-ros-v1",
        as_of=NOW,
        provenance=provenance,
    )


def _state() -> LeagueState:
    league = League(
        league_id="league-current-position-depth",
        name="Current Position Depth Fixture",
        season=2026,
        rules=LeagueRules(
            team_count=2,
            roster_size=8,
            lineup=(
                LineupRequirement(slot=RosterSlot.RB, count=1),
                LineupRequirement(slot=RosterSlot.WR, count=1),
                LineupRequirement(slot=RosterSlot.FLEX, count=1),
                LineupRequirement(slot=RosterSlot.K, count=1),
                LineupRequirement(slot=RosterSlot.DST, count=1),
            ),
            scoring=(),
        ),
    )
    players = (
        Player(player_id="a-rb1", full_name="A RB1", position=Position.RB, nfl_team="A"),
        Player(player_id="a-rb2", full_name="A RB2", position=Position.RB, nfl_team="A"),
        Player(player_id="a-wr1", full_name="A WR1", position=Position.WR, nfl_team="A"),
        Player(player_id="a-k1", full_name="A K1", position=Position.K, nfl_team="A"),
        Player(player_id="a-dst1", full_name="A DST", position=Position.DST, nfl_team="A"),
        Player(player_id="b-rb1", full_name="B RB1", position=Position.RB, nfl_team="B"),
        Player(player_id="b-wr1", full_name="B WR1", position=Position.WR, nfl_team="B"),
        Player(player_id="b-wr2", full_name="B WR2", position=Position.WR, nfl_team="B"),
        Player(player_id="b-k1", full_name="B K1", position=Position.K, nfl_team="B"),
        Player(player_id="b-dst1", full_name="B DST", position=Position.DST, nfl_team="B"),
    )
    provenance = Provenance(
        source="fixture",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture",
    )
    return LeagueState(
        league=league,
        as_of=NOW,
        teams=(
            Team(team_id="a", league_id=league.league_id, display_name="Alpha"),
            Team(team_id="b", league_id=league.league_id, display_name="Beta"),
        ),
        team_states=(
            TeamState(
                team_id="a",
                roster=tuple(
                    RosterEntry(player_id=player_id, slot=RosterSlot.BENCH)
                    for player_id in ("a-rb1", "a-rb2", "a-wr1", "a-k1", "a-dst1")
                ),
            ),
            TeamState(
                team_id="b",
                roster=tuple(
                    RosterEntry(player_id=player_id, slot=RosterSlot.BENCH)
                    for player_id in ("b-rb1", "b-wr1", "b-wr2", "b-k1", "b-dst1")
                ),
            ),
        ),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=player.player_id,
                as_of=NOW,
                nfl_team=player.nfl_team,
                provenance=provenance,
            )
            for player in players
        ),
    )


def _outlook() -> tuple[ForecastObservation, ...]:
    return (
        _forecast("a-rb1", Position.RB, 100.0),
        _forecast("a-rb2", Position.RB, 80.0),
        _forecast("a-wr1", Position.WR, 90.0),
        _forecast("b-rb1", Position.RB, 70.0),
        _forecast("b-wr1", Position.WR, 100.0),
        _forecast("b-wr2", Position.WR, 80.0),
    )


def test_current_strength_attributes_flex_to_flex_not_actual_position() -> None:
    contract = build_current_position_depth_from_outlook(
        _state(),
        season_outlook=_outlook(),
        evidence_basis="current_rest_of_season",
        completed_through_week=4,
    )
    strengths = {
        (row.team_id, row.slot.value): row
        for row in contract.strengths
    }

    assert strengths[("a", "RB")].expected_points == 100.0
    assert strengths[("a", "WR")].expected_points == 90.0
    assert strengths[("a", "FLEX")].expected_points == 80.0
    assert strengths[("b", "RB")].expected_points == 70.0
    assert strengths[("b", "WR")].expected_points == 100.0
    assert strengths[("b", "FLEX")].expected_points == 80.0

    # The FLEX winner's actual position does not get the FLEX points.
    assert strengths[("a", "RB")].expected_points != 180.0
    assert strengths[("b", "WR")].expected_points != 180.0


def test_current_grid_follows_configured_slots_and_k_fails_closed_without_authority() -> None:
    contract = build_current_position_depth_from_outlook(
        _state(),
        season_outlook=_outlook(),
        evidence_basis="current_rest_of_season",
        completed_through_week=4,
    )
    slots = {row.slot.value: row for row in contract.slots}

    assert [slot.value for slot in contract.slot_order] == ["RB", "WR", "FLEX", "K", "DST"]
    assert slots["RB"].status == "ready"
    assert slots["WR"].status == "ready"
    assert slots["FLEX"].status == "ready"
    assert slots["K"].status == "unavailable"
    assert slots["DST"].status == "unavailable"
    assert "missing evidence is not scored as zero" in (slots["K"].reason or "")
    assert contract.status == "partial"


def test_current_player_evidence_keeps_depth_separate_from_slot_strength() -> None:
    contract = build_current_position_depth_from_outlook(
        _state(),
        season_outlook=_outlook(),
        evidence_basis="current_rest_of_season",
        completed_through_week=4,
    )
    players = {
        (row.team_id, row.player_id): row
        for row in contract.players
    }

    assert players[("a", "a-rb1")].assigned_slot == RosterSlot.RB
    assert players[("a", "a-rb2")].assigned_slot == RosterSlot.FLEX
    assert players[("a", "a-rb2")].season_outlook_points == 80.0
    assert players[("a", "a-k1")].assigned_slot is None
    assert players[("a", "a-k1")].season_outlook_points is None


def test_league_team_views_exposes_current_position_depth_without_replacing_team_views(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FSFFL_BETA_AUTH", "0")
    state = _state()
    contract = build_current_position_depth_from_outlook(
        state,
        season_outlook=_outlook(),
        evidence_basis="current_rest_of_season",
        completed_through_week=4,
    )
    store = PrivateBetaRuntimeStore()
    store.set_league_state("local-beta-user", state)
    app = create_app(
        runtime_store=store,
        current_position_depth_provider=lambda _state: contract,
    )

    response = TestClient(app).get("/api/league/team-views")
    assert response.status_code == 200
    payload = response.json()

    assert len(payload["team_views"]) == 2
    assert payload["current_position_depth"]["evidence_basis"] == "current_rest_of_season"
    assert payload["current_position_depth"]["completed_through_week"] == 4
    assert payload["current_position_depth"]["slot_order"] == ["RB", "WR", "FLEX", "K", "DST"]


def test_superflex_is_ranked_as_its_own_configured_slot() -> None:
    base = _state()
    league = base.league.model_copy(
        update={
            "rules": base.league.rules.model_copy(
                update={
                    "lineup": (
                        LineupRequirement(slot=RosterSlot.QB, count=1),
                        LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
                    )
                }
            )
        }
    )
    players = (
        Player(player_id="a-qb1", full_name="A QB1", position=Position.QB, nfl_team="A"),
        Player(player_id="a-qb2", full_name="A QB2", position=Position.QB, nfl_team="A"),
        Player(player_id="b-qb1", full_name="B QB1", position=Position.QB, nfl_team="B"),
        Player(player_id="b-qb2", full_name="B QB2", position=Position.QB, nfl_team="B"),
    )
    provenance = Provenance(
        source="fixture",
        retrieved_at=NOW,
        effective_at=NOW,
        source_version="fixture",
    )
    state = base.model_copy(
        update={
            "league": league,
            "players": players,
            "player_states": tuple(
                PlayerState(
                    player_id=player.player_id,
                    as_of=NOW,
                    nfl_team=player.nfl_team,
                    provenance=provenance,
                )
                for player in players
            ),
            "team_states": (
                TeamState(
                    team_id="a",
                    roster=(
                        RosterEntry(player_id="a-qb1", slot=RosterSlot.BENCH),
                        RosterEntry(player_id="a-qb2", slot=RosterSlot.BENCH),
                    ),
                ),
                TeamState(
                    team_id="b",
                    roster=(
                        RosterEntry(player_id="b-qb1", slot=RosterSlot.BENCH),
                        RosterEntry(player_id="b-qb2", slot=RosterSlot.BENCH),
                    ),
                ),
            ),
        }
    )
    outlook = (
        _forecast("a-qb1", Position.QB, 300.0),
        _forecast("a-qb2", Position.QB, 240.0),
        _forecast("b-qb1", Position.QB, 280.0),
        _forecast("b-qb2", Position.QB, 220.0),
    )

    contract = build_current_position_depth_from_outlook(
        state,
        season_outlook=outlook,
        evidence_basis="current_rest_of_season",
        completed_through_week=4,
    )
    strengths = {(row.team_id, row.slot.value): row for row in contract.strengths}

    assert [slot.value for slot in contract.slot_order] == ["QB", "SUPERFLEX"]
    assert strengths[("a", "QB")].expected_points == 300.0
    assert strengths[("a", "SUPERFLEX")].expected_points == 240.0
    assert strengths[("b", "QB")].expected_points == 280.0
    assert strengths[("b", "SUPERFLEX")].expected_points == 220.0


def test_governed_current_builder_consumes_existing_in_season_outlook(monkeypatch) -> None:
    state = _state()
    governed = SimpleNamespace(
        season_outlook=_outlook(),
        evidence_basis="current_rest_of_season",
        completed_through_week=4,
    )
    calls = []

    def fake_outlook(league_state, **kwargs):
        calls.append((league_state.state_id, kwargs))
        return governed

    monkeypatch.setattr(
        current_position_depth,
        "build_governed_in_season_outlook",
        fake_outlook,
    )

    contract = build_governed_current_position_depth(
        state,
        preseason_season_forecasts=(),
        history_writer="history-writer",
    )

    assert calls == [
        (
            state.state_id,
            {
                "preseason_season_forecasts": (),
                "history_writer": "history-writer",
            },
        )
    ]
    assert contract.evidence_basis == "current_rest_of_season"
    assert contract.completed_through_week == 4

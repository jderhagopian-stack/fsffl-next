from datetime import UTC, datetime, timedelta

from fsffl.forecast.models import ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation
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
    Team,
    TeamState,
)
from fsffl.team_utility import marginal_lineup_impact, optimize_team_lineup


AS_OF = datetime(2026, 9, 5, 15, 0, tzinfo=UTC)
PROVENANCE = Provenance(source="sanity-test", retrieved_at=AS_OF, effective_at=AS_OF)


def _player(player_id: str, position: Position) -> Player:
    return Player(player_id=player_id, full_name=player_id, position=position)


def _forecast(player_id: str, position: Position, points: float) -> ForecastObservation:
    return ForecastObservation(
        player_id=player_id,
        position=position,
        horizon=ForecastHorizon.SEASON,
        metric=ForecastMetric.FANTASY_POINTS,
        period_start=AS_OF,
        period_end=AS_OF + timedelta(days=120),
        distribution=ForecastDistribution(mean=points, stddev=2.0),
        source="next2-sanity",
        model_version="forecast-v1",
        as_of=AS_OF,
        provenance=PROVENANCE,
    )


def _state(team1_players: tuple[Player, ...], team2_players: tuple[Player, ...] = ()) -> LeagueState:
    all_players = team1_players + team2_players
    return LeagueState(
        league=League(
            league_id="league:sanity",
            name="Sanity League",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=max(1, len(all_players)),
                lineup=(
                    LineupRequirement(slot=RosterSlot.QB, count=1),
                    LineupRequirement(slot=RosterSlot.SUPERFLEX, count=1),
                    LineupRequirement(slot=RosterSlot.WR, count=1),
                ),
                scoring=(),
            ),
        ),
        as_of=AS_OF,
        teams=(
            Team(team_id="team:1", league_id="league:sanity", display_name="One"),
            Team(team_id="team:2", league_id="league:sanity", display_name="Two"),
        ),
        team_states=(
            TeamState(
                team_id="team:1",
                roster=tuple(RosterEntry(player_id=p.player_id, slot=RosterSlot.BENCH) for p in team1_players),
            ),
            TeamState(
                team_id="team:2",
                roster=tuple(RosterEntry(player_id=p.player_id, slot=RosterSlot.BENCH) for p in team2_players),
            ),
        ),
        players=all_players,
        player_states=tuple(
            PlayerState(
                player_id=p.player_id,
                as_of=AS_OF,
                status=PlayerStatus.ACTIVE,
                provenance=PROVENANCE,
            )
            for p in all_players
        ),
    )


def test_elite_qb_is_more_important_when_qb_depth_is_weak() -> None:
    players_weak = (
        _player("elite_qb", Position.QB),
        _player("qb2", Position.QB),
        _player("qb3_weak", Position.QB),
        _player("wr1", Position.WR),
    )
    forecasts_weak = (
        _forecast("elite_qb", Position.QB, 30.0),
        _forecast("qb2", Position.QB, 22.0),
        _forecast("qb3_weak", Position.QB, 8.0),
        _forecast("wr1", Position.WR, 18.0),
    )
    weak_impact = marginal_lineup_impact(
        _state(players_weak),
        forecasts_weak,
        team_id="team:1",
        player_id="elite_qb",
        as_of=AS_OF,
        horizon=ForecastHorizon.SEASON,
    )

    players_strong = (
        _player("elite_qb", Position.QB),
        _player("qb2", Position.QB),
        _player("qb3_strong", Position.QB),
        _player("wr1", Position.WR),
    )
    forecasts_strong = (
        _forecast("elite_qb", Position.QB, 30.0),
        _forecast("qb2", Position.QB, 22.0),
        _forecast("qb3_strong", Position.QB, 20.0),
        _forecast("wr1", Position.WR, 18.0),
    )
    strong_impact = marginal_lineup_impact(
        _state(players_strong),
        forecasts_strong,
        team_id="team:1",
        player_id="elite_qb",
        as_of=AS_OF,
        horizon=ForecastHorizon.SEASON,
    )

    assert weak_impact.marginal_expected_points > strong_impact.marginal_expected_points
    assert weak_impact.marginal_expected_points == 22.0
    assert strong_impact.marginal_expected_points == 10.0


def test_better_depth_cannot_lower_optimized_lineup_points() -> None:
    base_players = (
        _player("qb1", Position.QB),
        _player("qb2", Position.QB),
        _player("wr1", Position.WR),
    )
    base_forecasts = (
        _forecast("qb1", Position.QB, 25.0),
        _forecast("qb2", Position.QB, 20.0),
        _forecast("wr1", Position.WR, 15.0),
    )
    base = optimize_team_lineup(
        _state(base_players),
        base_forecasts,
        team_id="team:1",
        as_of=AS_OF,
        horizon=ForecastHorizon.SEASON,
    )

    improved_players = base_players + (_player("wr2", Position.WR),)
    improved_forecasts = base_forecasts + (_forecast("wr2", Position.WR, 19.0),)
    improved = optimize_team_lineup(
        _state(improved_players),
        improved_forecasts,
        team_id="team:1",
        as_of=AS_OF,
        horizon=ForecastHorizon.SEASON,
    )

    assert improved.expected_points >= base.expected_points
    assert improved.expected_points == 64.0

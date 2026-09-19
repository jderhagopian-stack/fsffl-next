from datetime import UTC, datetime

import pytest

from fsffl.forecast.i1_current_facts import (
    I1_CURRENT_FACTS_SCHEMA_VERSION,
    CurrentI1FactsArtifact,
    CurrentI1SourceFact,
    map_current_i1_facts,
)
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    LineupRequirement,
    Player,
    PlayerState,
    Position,
    ProviderRef,
    Provenance,
    RosterSlot,
    Team,
    TeamState,
)


def _provenance() -> Provenance:
    now = datetime(2026, 9, 15, 12, tzinfo=UTC)
    return Provenance(source="fixture", retrieved_at=now, effective_at=now, source_version="fixture-v1")


def _league_state(*players: Player, season: int = 2026) -> LeagueState:
    rules = LeagueRules(
        team_count=2,
        roster_size=18,
        lineup=(LineupRequirement(slot=RosterSlot.QB, count=1),),
        scoring=(),
    )
    league = League(league_id="league", name="Fixture", season=season, rules=rules)
    teams = (
        Team(team_id="a", league_id="league", display_name="A"),
        Team(team_id="b", league_id="league", display_name="B"),
    )
    now = datetime(2026, 9, 15, 12, tzinfo=UTC)
    return LeagueState(
        league=league,
        as_of=now,
        teams=teams,
        team_states=(TeamState(team_id="a", roster=()), TeamState(team_id="b", roster=())),
        players=tuple(players),
        player_states=tuple(
            PlayerState(player_id=player.player_id, as_of=now, provenance=_provenance()) for player in players
        ),
    )


def _row(
    source_player_id: str,
    display_name: str,
    *,
    position: Position = Position.WR,
    provider: str | None = None,
    external_id: str | None = None,
    source_season: int = 2025,
    role_band: str | None = "established",
) -> CurrentI1SourceFact:
    return CurrentI1SourceFact(
        source_player_id=source_player_id,
        display_name=display_name,
        position=position,
        source_season=source_season,
        current_fantasy_points=180.0,
        prior_fantasy_points=145.0,
        age_years=24.5,
        experience_years=3,
        current_state="starter",
        games=17.0,
        opportunity_per_game=7.5,
        role_band=role_band,
        source_version="facts-v1",
        identity_provider=provider,
        identity_external_id=external_id,
    )


def _artifact(
    *rows: CurrentI1SourceFact,
    evaluation_season: int = 2026,
    source_season_complete: bool = True,
) -> CurrentI1FactsArtifact:
    return CurrentI1FactsArtifact(
        schema_version=I1_CURRENT_FACTS_SCHEMA_VERSION,
        evaluation_season=evaluation_season,
        completed_source_season=evaluation_season - 1,
        source_season_complete=source_season_complete,
        state_boundary_version="bounds-v1",
        source_version="facts-v1",
        rows=tuple(rows),
        metadata={"fixture": True},
    )


def test_mapping_prefers_stable_identity_then_unique_name_fallback_and_preserves_target_years() -> None:
    p1 = Player(
        player_id="p1",
        full_name="Stable Identity",
        position=Position.WR,
        provider_refs=(ProviderRef(provider="sleeper", external_id="111"),),
    )
    p2 = Player(player_id="p2", full_name="Name Fallback", position=Position.WR)
    state = _league_state(p1, p2)
    artifact = _artifact(
        _row("s1", "Different Provider Name", provider="sleeper", external_id="111"),
        _row("s2", "Name Fallback"),
    )

    result = map_current_i1_facts(state, artifact)

    assert result.mapped_count == 2
    assert result.mapped_source_ids == {"p1": "s1", "p2": "s2"}
    assert result.target_seasons == (2026, 2027, 2028)
    assert result.target_season(1) == result.evaluation_season
    assert result.target_is_after_evaluation(1) is False
    assert result.target_is_after_evaluation(2) is True
    assert result.target_is_after_evaluation(3) is True
    for player_id in ("p1", "p2"):
        horizon_1, horizon_2, horizon_3 = result.inputs[player_id]
        assert (horizon_1.horizon, horizon_2.horizon, horizon_3.horizon) == (1, 2, 3)
        assert horizon_1.evidence.roster_coverage is False
        assert horizon_1.evidence.injury_coverage is False
        assert horizon_1.evidence.participation_coverage is False
        # Direct h=3 uses the identical completed-source facts, never an h=1/h=2 prediction.
        assert horizon_3.current_points == horizon_2.current_points == horizon_1.current_points == 180.0
        assert horizon_3.prior_points == horizon_2.prior_points == horizon_1.prior_points == 145.0


def test_missing_source_fact_fails_closed_without_inventing_zero() -> None:
    player = Player(player_id="p1", full_name="No Source Row", position=Position.RB)
    result = map_current_i1_facts(_league_state(player), _artifact())

    assert result.mapped_count == 0
    assert result.unmapped_player_ids == ("p1",)
    assert "p1" not in result.inputs


def test_duplicate_provider_identity_is_ambiguous_not_last_write_wins() -> None:
    player = Player(
        player_id="p1",
        full_name="Canonical Player",
        position=Position.WR,
        provider_refs=(ProviderRef(provider="sleeper", external_id="111"),),
    )
    artifact = _artifact(
        _row("s1", "Candidate One", provider="sleeper", external_id="111"),
        _row("s2", "Candidate Two", provider="sleeper", external_id="111"),
    )

    result = map_current_i1_facts(_league_state(player), artifact)

    assert result.mapped_count == 0
    assert result.ambiguous_player_ids == ("p1",)
    assert set(result.source_rows_unmatched) == {"s1", "s2"}


def test_source_rows_must_match_declared_completed_source_season() -> None:
    with pytest.raises(ValueError, match="completed source season"):
        _artifact(_row("s1", "Wrong Season", source_season=2024))


def test_partial_active_season_cannot_be_declared_completed_source() -> None:
    with pytest.raises(ValueError, match="partial active season"):
        _artifact(_row("s1", "Partial Season"), source_season_complete=False)


def test_role_band_is_governed_when_role_evidence_is_present() -> None:
    with pytest.raises(ValueError, match="role band"):
        _row("s1", "Bad Role", role_band="alpha")


def test_evaluation_season_must_match_live_league_season() -> None:
    player = Player(player_id="p1", full_name="Season Mismatch", position=Position.TE)
    with pytest.raises(ValueError, match="does not match league season"):
        map_current_i1_facts(_league_state(player, season=2026), _artifact(evaluation_season=2027))


def test_only_supported_i1_horizons_have_calendar_targets() -> None:
    result = map_current_i1_facts(
        _league_state(Player(player_id="p1", full_name="Mapped", position=Position.WR)),
        _artifact(_row("s1", "Mapped")),
    )
    assert result.target_season(3) == 2028
    with pytest.raises(ValueError, match="horizon must be 1, 2, or 3"):
        result.target_season(4)

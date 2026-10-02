from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fsffl.product.pick_location_runtime import build_next_season_pick_projections
from fsffl.state.draft_order_policy import (
    DraftOrderPolicyEvidence,
    DraftOrderPolicyParameter,
)
from fsffl.state.models import (
    DraftPick,
    League,
    LeagueRules,
    LeagueState,
    PickOwnership,
    Provenance,
    ProviderRef,
    Team,
    TeamState,
)
from fsffl.team_utility.future_pick import (
    STANDARD_DRAFT_ORDER_MECHANISM_V1,
    STANDARD_PLAYOFF_ORDER,
    STANDARD_REGULAR_SEASON_TIEBREAK,
)
from fsffl.team_utility.simulation import (
    CompletedMatchup,
    RegularSeasonSimulationInput,
    TeamScoringDistribution,
    WeeklyTeamScoringDistribution,
    _settings_derived_playoff_rules,
    simulate_regular_season,
)


AS_OF = datetime(2026, 10, 2, tzinfo=UTC)
PROV = Provenance(
    source="test",
    retrieved_at=AS_OF,
    effective_at=AS_OF,
    provider_ref=ProviderRef(provider="test", external_id="future-pick"),
)


def _explicit_policy(*, placement_games: bool = False) -> DraftOrderPolicyEvidence:
    parameters = [
        DraftOrderPolicyParameter(
            name="non_playoff_tiebreak_policy",
            value=STANDARD_REGULAR_SEASON_TIEBREAK,
        ),
        DraftOrderPolicyParameter(
            name="playoff_order_policy",
            value=STANDARD_PLAYOFF_ORDER,
        ),
        DraftOrderPolicyParameter(
            name="origin_slot_carries_across_rounds",
            value=True,
        ),
        DraftOrderPolicyParameter(
            name="placement_games_affect_order",
            value=placement_games,
        ),
    ]
    if placement_games:
        parameters.append(
            DraftOrderPolicyParameter(
                name="placement_games_policy",
                value="six_team_standard_placement_games_v1",
            )
        )
    return DraftOrderPolicyEvidence(
        league_id="league:test",
        draft_season=2027,
        effective_at=datetime(2026, 1, 1, tzinfo=UTC),
        available_at=datetime(2026, 10, 1, tzinfo=UTC),
        policy_id="explicit-test-draft-order",
        version="2026-v1",
        mechanism=STANDARD_DRAFT_ORDER_MECHANISM_V1,
        description="Explicit test league draft-order bylaw",
        parameters=tuple(parameters),
        provenance=PROV,
    )


def _six_team_playoff_request(
    *,
    explicit_policy: DraftOrderPolicyEvidence | None = None,
) -> RegularSeasonSimulationInput:
    team_ids = tuple("abcdefghijkl")
    rules = _settings_derived_playoff_rules(6, 15)
    assert rules is not None

    # a-f finish 1-0 and make the playoffs. g-l finish 0-1. The PF values
    # intentionally make d rank earlier than c within a same-round playoff tie.
    completed = (
        CompletedMatchup(week=1, home_team_id="a", away_team_id="g", home_points=160, away_points=60),
        CompletedMatchup(week=1, home_team_id="b", away_team_id="h", home_points=150, away_points=50),
        CompletedMatchup(week=1, home_team_id="c", away_team_id="i", home_points=100, away_points=40),
        CompletedMatchup(week=1, home_team_id="d", away_team_id="j", home_points=90, away_points=30),
        CompletedMatchup(week=1, home_team_id="e", away_team_id="k", home_points=80, away_points=20),
        CompletedMatchup(week=1, home_team_id="f", away_team_id="l", home_points=70, away_points=10),
    )
    playoff_means = {
        # c(seed3) and d(seed4) lose in round one.
        15: {"a": 50, "b": 50, "c": 10, "d": 20, "e": 90, "f": 100},
        # If an explicit placement policy is enabled, d beats c in the 5th-place game.
        16: {"a": 200, "b": 190, "c": 50, "d": 100, "e": 80, "f": 70},
        17: {"a": 200, "b": 100, "c": 1, "d": 1, "e": 90, "f": 80},
    }
    playoff_weekly = tuple(
        WeeklyTeamScoringDistribution(
            week=week,
            team_id=team_id,
            mean_points=float(playoff_means[week].get(team_id, 1.0)),
            stddev_points=0.0,
            model_version="pick-placement-test",
        )
        for week in rules.round_weeks
        for team_id in team_ids
    )
    return RegularSeasonSimulationInput(
        scoring=tuple(
            TeamScoringDistribution(
                team_id=team_id,
                mean_points=100.0,
                stddev_points=0.0,
                model_version="pick-test",
            )
            for team_id in team_ids
        ),
        completed_matchups=completed,
        schedule=(),
        playoff_team_count=6,
        playoff_rules=rules,
        playoff_weekly_scoring=playoff_weekly,
        future_pick_draft_season=2027,
        future_pick_draft_order_policy=explicit_policy,
        simulation_count=50,
        seed=7,
        model_version="future-pick-test-v2",
    )


def _slots(result) -> dict[str, int]:
    output = {}
    for row in result.future_pick_distributions:
        assert len(row.slot_probabilities) == 1
        assert row.slot_probabilities[0].probability == 1.0
        output[row.original_team_id] = row.slot_probabilities[0].slot_in_round
    return output


def test_standard_fallback_orders_nonplayoff_by_record_then_pf_and_playoffs_by_elimination() -> None:
    result = simulate_regular_season(_six_team_playoff_request())
    slots = _slots(result)

    # All non-playoff teams share the same 0-1 record and have no resolvable H2H,
    # so lower regular-season Points For breaks the tie.
    assert {team: slots[team] for team in "lkjihg"} == {
        "l": 1,
        "k": 2,
        "j": 3,
        "i": 4,
        "h": 5,
        "g": 6,
    }

    # c/d are eliminated in the same opening round. Placement games are ignored
    # by the standard fallback, so regular-season PF orders d before c.
    assert slots["d"] == 7
    assert slots["c"] == 8
    # Runner-up is penultimate and champion is last.
    assert slots["b"] == 11
    assert slots["a"] == 12

    by_team = {row.original_team_id: row for row in result.future_pick_distributions}
    assert by_team["a"].draft_order_policy_authority == "derived_standard_fallback"
    assert by_team["a"].draft_order_policy_id == "governed-standard-draft-order-fallback"
    assert "placement games ignored unless explicitly governed" in by_team["a"].provenance
    assert result.future_pick_unavailability_reason is None


def test_resolvable_head_to_head_precedes_points_for_for_tied_nonplayoff_records() -> None:
    rules = _settings_derived_playoff_rules(2, 4)
    assert rules is not None
    # Final records: a=2-1, b=2-1, c=1-2, d=1-2.
    # c beat d head-to-head, so d (worse H2H) drafts earlier even though d has
    # higher Points For than c.
    completed = (
        CompletedMatchup(week=1, home_team_id="a", away_team_id="c", home_points=100, away_points=40),
        CompletedMatchup(week=1, home_team_id="d", away_team_id="a", home_points=120, away_points=50),
        CompletedMatchup(week=2, home_team_id="b", away_team_id="c", home_points=100, away_points=40),
        CompletedMatchup(week=2, home_team_id="b", away_team_id="d", home_points=100, away_points=90),
        CompletedMatchup(week=3, home_team_id="c", away_team_id="d", home_points=30, away_points=20),
        CompletedMatchup(week=3, home_team_id="a", away_team_id="b", home_points=100, away_points=90),
    )
    playoff_weekly = tuple(
        WeeklyTeamScoringDistribution(
            week=4,
            team_id=team_id,
            mean_points=100.0 if team_id == "a" else 90.0,
            stddev_points=0.0,
            model_version="h2h-test",
        )
        for team_id in "abcd"
    )
    request = RegularSeasonSimulationInput(
        scoring=tuple(
            TeamScoringDistribution(
                team_id=team_id,
                mean_points=100,
                stddev_points=0,
                model_version="h2h-test",
            )
            for team_id in "abcd"
        ),
        completed_matchups=completed,
        schedule=(),
        playoff_team_count=2,
        playoff_rules=rules,
        playoff_weekly_scoring=playoff_weekly,
        future_pick_draft_season=2027,
        simulation_count=20,
        seed=3,
        model_version="h2h-test-v1",
    )

    slots = _slots(simulate_regular_season(request))
    assert slots["d"] == 1
    assert slots["c"] == 2


def test_unresolved_exact_tie_splits_slot_probability_without_hidden_tiebreak() -> None:
    rules = _settings_derived_playoff_rules(2, 3)
    assert rules is not None
    completed = (
        CompletedMatchup(week=1, home_team_id="a", away_team_id="c", home_points=100, away_points=50),
        CompletedMatchup(week=1, home_team_id="b", away_team_id="d", home_points=100, away_points=50),
    )
    playoff_weekly = tuple(
        WeeklyTeamScoringDistribution(
            week=3,
            team_id=team_id,
            mean_points=100.0 if team_id == "a" else 90.0,
            stddev_points=0.0,
            model_version="tie-test",
        )
        for team_id in "abcd"
    )
    request = RegularSeasonSimulationInput(
        scoring=tuple(
            TeamScoringDistribution(
                team_id=team_id,
                mean_points=100,
                stddev_points=0,
                model_version="tie-test",
            )
            for team_id in "abcd"
        ),
        completed_matchups=completed,
        schedule=(),
        playoff_team_count=2,
        playoff_rules=rules,
        playoff_weekly_scoring=playoff_weekly,
        future_pick_draft_season=2027,
        simulation_count=20,
        seed=3,
        model_version="tie-test-v1",
    )
    result = simulate_regular_season(request)
    by_team = {row.original_team_id: row for row in result.future_pick_distributions}

    for team_id in ("c", "d"):
        probabilities = {row.slot_in_round: row.probability for row in by_team[team_id].slot_probabilities}
        assert probabilities == {1: pytest.approx(0.5), 2: pytest.approx(0.5)}
        assert by_team[team_id].expected_slot == pytest.approx(1.5)


def test_explicit_policy_precedes_fallback_and_placement_games_only_then_affect_order() -> None:
    derived = simulate_regular_season(_six_team_playoff_request())
    explicit = simulate_regular_season(
        _six_team_playoff_request(
            explicit_policy=_explicit_policy(placement_games=True)
        )
    )
    derived_slots = _slots(derived)
    explicit_slots = _slots(explicit)

    # Standard fallback ignores placement games: d's lower PF makes it earlier.
    assert (derived_slots["d"], derived_slots["c"]) == (7, 8)
    # Explicit policy says the placement game counts; d wins 5th, c is 6th.
    assert (explicit_slots["c"], explicit_slots["d"]) == (7, 8)

    row = next(item for item in explicit.future_pick_distributions if item.original_team_id == "a")
    assert row.draft_order_policy_authority == "explicit_league_rule"
    assert row.draft_order_policy_id == "explicit-test-draft-order"


def test_unsupported_explicit_policy_does_not_get_silently_replaced_by_fallback() -> None:
    bad = _explicit_policy().model_copy(update={"mechanism": "custom_lottery_v1"})
    result = simulate_regular_season(
        _six_team_playoff_request(explicit_policy=bad)
    )

    assert result.future_pick_distributions == ()
    assert result.future_pick_unavailability_reason == (
        "unsupported explicit future-pick draft-order mechanism"
    )


def _projection_state() -> LeagueState:
    league_id = "league:test"
    team_ids = tuple("abcdefghijkl")
    teams = tuple(
        Team(team_id=team_id, league_id=league_id, display_name=team_id.upper())
        for team_id in team_ids
    )
    league = League(
        league_id=league_id,
        name="Test League",
        season=2026,
        rules=LeagueRules(
            team_count=12,
            roster_size=1,
            rookie_draft_rounds=3,
            playoff_team_count=6,
            lineup=(),
            scoring=(),
        ),
    )
    picks = tuple(
        DraftPick(
            pick_id=f"{league_id}:pick:2027:{round_number}:a",
            league_id=league_id,
            season=2027,
            round=round_number,
            original_team_id="a",
        )
        for round_number in (1, 2, 3)
    )
    ownership = tuple(
        PickOwnership(
            pick_id=pick.pick_id,
            owner_team_id=("b" if pick.round == 1 else "a"),
        )
        for pick in picks
    )
    return LeagueState(
        league=league,
        as_of=AS_OF,
        teams=teams,
        team_states=tuple(
            TeamState(team_id=team.team_id, roster=()) for team in teams
        ),
        players=(),
        player_states=(),
        draft_picks=picks,
        pick_ownership=ownership,
        provenance=(PROV,),
    )


def test_pick_projection_preserves_origin_slot_across_rounds_owner_and_policy_provenance() -> None:
    result = simulate_regular_season(_six_team_playoff_request())
    projections = build_next_season_pick_projections(_projection_state(), result)
    by_round = {row.round: row for row in projections}

    assert by_round[1].owner_team_id == "b"
    assert by_round[2].owner_team_id == "a"
    assert by_round[3].owner_team_id == "a"
    assert {row.original_team_id for row in projections} == {"a"}
    assert {row.expected_slot for row in projections} == {12.0}
    assert all(row.slot_probabilities[0].slot_in_round == 12 for row in projections)
    assert {
        row.draft_order_policy_authority for row in projections
    } == {"derived_standard_fallback"}
    assert {
        row.draft_order_projection_model_version for row in projections
    } == {"record-h2h-points-for-plus-playoff-elimination-v1"}

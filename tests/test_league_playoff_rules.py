from __future__ import annotations

import pytest

from fsffl.state.models import (
    LeaguePlayoffRules,
    PlayoffMatchupRule,
    PlayoffParticipantRef,
)
from fsffl.team_utility import (
    RegularSeasonSimulationInput,
    ScheduledMatchup,
    TeamScoringDistribution,
    simulate_regular_season,
)


def _seed(number: int) -> PlayoffParticipantRef:
    return PlayoffParticipantRef(seed_number=number)


def _winner(matchup_id: str) -> PlayoffParticipantRef:
    return PlayoffParticipantRef(winner_of_matchup_id=matchup_id)


def _configured_rules(
    *,
    team_count: int,
    start_week: int,
    round_weeks: tuple[int, ...],
    bye_seeds: tuple[int, ...],
    matchups: tuple[PlayoffMatchupRule, ...],
    championship_matchup_id: str,
) -> LeaguePlayoffRules:
    return LeaguePlayoffRules(
        playoff_team_count=team_count,
        playoff_start_week=start_week,
        round_count=len(round_weeks),
        round_weeks=round_weeks,
        bye_count=len(bye_seeds),
        bye_seeds=bye_seeds,
        seeding_policy="overall_standings",
        standings_tiebreak_policy="wins_then_points_for_then_team_id_v1",
        reseeding_policy="fixed_bracket",
        matchups=matchups,
        championship_round_number=len(round_weeks),
        championship_week=round_weeks[-1],
        championship_matchup_id=championship_matchup_id,
        playoff_scoring_policy="same_as_league_regular_season",
        matchup_tiebreak_policy="higher_original_seed",
    )


SIX_TEAM_BYE_BRACKET = _configured_rules(
    team_count=6,
    start_week=15,
    round_weeks=(15, 16, 17),
    bye_seeds=(1, 2),
    matchups=(
        PlayoffMatchupRule(matchup_id="qf-a", round_number=1, week=15, participant_a=_seed(3), participant_b=_seed(6)),
        PlayoffMatchupRule(matchup_id="qf-b", round_number=1, week=15, participant_a=_seed(4), participant_b=_seed(5)),
        PlayoffMatchupRule(matchup_id="sf-a", round_number=2, week=16, participant_a=_seed(1), participant_b=_winner("qf-b")),
        PlayoffMatchupRule(matchup_id="sf-b", round_number=2, week=16, participant_a=_seed(2), participant_b=_winner("qf-a")),
        PlayoffMatchupRule(matchup_id="final", round_number=3, week=17, participant_a=_winner("sf-a"), participant_b=_winner("sf-b")),
    ),
    championship_matchup_id="final",
)

FOUR_TEAM_NO_BYE_BRACKET = _configured_rules(
    team_count=4,
    start_week=16,
    round_weeks=(16, 18),
    bye_seeds=(),
    matchups=(
        PlayoffMatchupRule(matchup_id="semi-a", round_number=1, week=16, participant_a=_seed(1), participant_b=_seed(4)),
        PlayoffMatchupRule(matchup_id="semi-b", round_number=1, week=16, participant_a=_seed(2), participant_b=_seed(3)),
        PlayoffMatchupRule(matchup_id="title", round_number=2, week=18, participant_a=_winner("semi-a"), participant_b=_winner("semi-b")),
    ),
    championship_matchup_id="title",
)

FIVE_TEAM_THREE_BYE_BRACKET = _configured_rules(
    team_count=5,
    start_week=13,
    round_weeks=(13, 14, 15),
    bye_seeds=(1, 2, 3),
    matchups=(
        PlayoffMatchupRule(matchup_id="play-in", round_number=1, week=13, participant_a=_seed(4), participant_b=_seed(5)),
        PlayoffMatchupRule(matchup_id="semi-a", round_number=2, week=14, participant_a=_seed(1), participant_b=_winner("play-in")),
        PlayoffMatchupRule(matchup_id="semi-b", round_number=2, week=14, participant_a=_seed(2), participant_b=_seed(3)),
        PlayoffMatchupRule(matchup_id="title", round_number=3, week=15, participant_a=_winner("semi-a"), participant_b=_winner("semi-b")),
    ),
    championship_matchup_id="title",
)


@pytest.mark.parametrize(
    "rules, expected",
    (
        (SIX_TEAM_BYE_BRACKET, (6, 15, 2, (1, 2))),
        (FOUR_TEAM_NO_BYE_BRACKET, (4, 16, 0, ())),
        (FIVE_TEAM_THREE_BYE_BRACKET, (5, 13, 3, (1, 2, 3))),
    ),
)
def test_playoff_rules_retain_league_specific_size_timing_and_byes(rules, expected) -> None:
    assert (
        rules.playoff_team_count,
        rules.playoff_start_week,
        rules.bye_count,
        rules.bye_seeds,
    ) == expected
    assert rules.round_weeks[-1] == rules.championship_week
    assert rules.simulation_unavailability_reason() is None


def _simulation_request(
    team_count: int,
    *,
    rules: LeaguePlayoffRules | None = None,
) -> RegularSeasonSimulationInput:
    request = RegularSeasonSimulationInput(
        scoring=tuple(
            TeamScoringDistribution(
                team_id=f"team-{index}",
                mean_points=100.0 + index,
                stddev_points=0,
                model_version="playoff-rules-test",
            )
            for index in range(team_count)
        ),
        schedule=(ScheduledMatchup(week=1, home_team_id="team-0", away_team_id="team-1"),),
        playoff_team_count=team_count,
        playoff_rules=rules,
        simulation_count=10,
        seed=17,
        model_version="playoff-rules-test",
    )
    return request


def test_current_style_sleeper_rule_gap_fails_closed_for_postseason_outputs() -> None:
    request = _simulation_request(6)

    result = simulate_regular_season(request)

    assert all(row.playoff_probability is None for row in result.outcomes)
    assert all(row.championship_probability is None for row in result.outcomes)
    assert {
        row.playoff_unavailability_reason for row in result.outcomes
    } == {"playoff_rules_unavailable"}
    assert {
        row.championship_unavailability_reason for row in result.outcomes
    } == {"playoff_rules_unavailable"}


def test_unsupported_reseeding_keeps_qualification_but_withholds_title() -> None:
    reseeded = SIX_TEAM_BYE_BRACKET.model_copy(
        update={"reseeding_policy": "highest_remaining_seed_each_round"}
    )
    result = simulate_regular_season(_simulation_request(6, rules=reseeded))

    assert all(row.playoff_probability is not None for row in result.outcomes)
    assert all(row.championship_probability is None for row in result.outcomes)
    assert {row.playoff_unavailability_reason for row in result.outcomes} == {None}
    assert {
        row.championship_unavailability_reason for row in result.outcomes
    } == {"playoff_rules_unsupported:reseeding_policy"}


def test_unsupported_qualification_seeding_withholds_both_playoff_outputs() -> None:
    division_seeded = FIVE_TEAM_THREE_BYE_BRACKET.model_copy(
        update={"seeding_policy": "division_winners_then_overall_standings"}
    )
    result = simulate_regular_season(
        _simulation_request(5, rules=division_seeded)
    )

    assert all(row.playoff_probability is None for row in result.outcomes)
    assert all(row.championship_probability is None for row in result.outcomes)
    assert {
        row.playoff_unavailability_reason for row in result.outcomes
    } == {"playoff_rules_unsupported:seeding_policy"}


def test_nonstandard_five_team_bracket_is_replayed_from_canonical_rules() -> None:
    teams = tuple(f"team-{index}" for index in range(5))
    request = RegularSeasonSimulationInput(
        scoring=tuple(
            TeamScoringDistribution(
                team_id=team_id,
                mean_points=100.0 + index * 10,
                stddev_points=0,
                model_version="five-team-playoff-test",
            )
            for index, team_id in enumerate(teams)
        ),
        schedule=(
            ScheduledMatchup(week=1, home_team_id="team-0", away_team_id="team-1"),
            ScheduledMatchup(week=1, home_team_id="team-2", away_team_id="team-3"),
            ScheduledMatchup(week=2, home_team_id="team-0", away_team_id="team-2"),
            ScheduledMatchup(week=2, home_team_id="team-1", away_team_id="team-4"),
        ),
        playoff_team_count=5,
        playoff_rules=FIVE_TEAM_THREE_BYE_BRACKET,
        simulation_count=200,
        seed=2026,
        model_version="five-team-playoff-test",
    )

    first = simulate_regular_season(request)
    replay = simulate_regular_season(request)

    assert first == replay
    assert sum(row.championship_probability or 0 for row in first.outcomes) == 1
    assert all(row.championship_unavailability_reason is None for row in first.outcomes)


def test_reseeding_policy_is_retained_but_not_silently_treated_as_fixed_bracket() -> None:
    reseeded = FIVE_TEAM_THREE_BYE_BRACKET.model_copy(
        update={"reseeding_policy": "highest_remaining_seed_each_round"}
    )
    assert reseeded.simulation_unavailability_reason() == (
        "playoff_rules_unsupported:reseeding_policy"
    )


def test_division_seeding_is_retained_but_fails_closed_until_supported() -> None:
    division_seeded = FIVE_TEAM_THREE_BYE_BRACKET.model_copy(
        update={"seeding_policy": "division_winners_then_overall_standings"}
    )
    assert division_seeded.simulation_unavailability_reason() == (
        "playoff_rules_unsupported:seeding_policy"
    )


def test_bye_seed_cannot_skip_an_additional_playoff_round() -> None:
    payload = FIVE_TEAM_THREE_BYE_BRACKET.model_dump(mode="json")
    for matchup in payload["matchups"]:
        if matchup["matchup_id"] == "semi-a":
            matchup["participant_a"] = {"winner_of_matchup_id": "play-in"}
        elif matchup["matchup_id"] == "title":
            matchup["participant_a"] = {"seed_number": 1}

    with pytest.raises(ValueError, match="bye seeds must enter in the first playoff round"):
        LeaguePlayoffRules.model_validate(payload)


def test_playoff_participant_reference_must_be_unambiguous() -> None:
    with pytest.raises(ValueError, match="exactly one seed or prior winner"):
        PlayoffParticipantRef()

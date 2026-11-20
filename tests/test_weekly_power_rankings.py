from math import isclose

import pytest

from fsffl.analytics.weekly_power_rankings import (
    POWER_INDEX_RESEARCH_VERSION,
    PowerIndexEvidence,
    PowerIndexWeights,
    rank_weekly_power,
)


def _team(name, mean, season=0.5, recent=0.5, earlier=0.5, record=0.5, sd=20.0):
    return PowerIndexEvidence(name, mean, sd, season, recent, earlier, record)


def test_two_equal_teams_rank_stably_at_neutral_model_probability():
    result = rank_weekly_power((_team('b', 100), _team('a', 100)))
    assert [row.team_id for row in result] == ['a', 'b']
    assert all(isclose(row.neutral_model_win_rate, 0.5) for row in result)
    assert all(isclose(row.score, 50.0) for row in result)
    assert all(row.model_version == POWER_INDEX_RESEARCH_VERSION for row in result)


def test_momentum_rewards_improvement_not_only_high_recent_scoring():
    result = rank_weekly_power((
        _team('improving', 100, recent=.7, earlier=.4),
        _team('flat', 100, recent=.8, earlier=.8),
    ))
    assert result[0].team_id == 'improving'
    assert result[0].momentum_change == pytest.approx(.65)
    assert result[1].momentum_change == pytest.approx(.5)


def test_peer_relative_strength_uses_both_means_and_uncertainty():
    result = rank_weekly_power((_team('high', 130), _team('mid', 110), _team('low', 90)))
    assert [row.team_id for row in result] == ['high', 'mid', 'low']
    assert sum(row.neutral_model_win_rate for row in result) == pytest.approx(1.5)


def test_ties_in_model_scoring_have_half_win_probability():
    result = rank_weekly_power((_team('a', 100, sd=0), _team('b', 100, sd=0)))
    assert all(row.neutral_model_win_rate == .5 for row in result)


@pytest.mark.parametrize('weights', [(0.4,.35,.15,.11),(-.1,.85,.15,.10)])
def test_invalid_weights_rejected(weights):
    with pytest.raises(ValueError, match='weights'):
        PowerIndexWeights(*weights)


def test_duplicate_ids_rejected():
    with pytest.raises(ValueError, match='exactly once'):
        rank_weekly_power((_team('same',100),_team('same',120)))


def test_nonfinite_and_invalid_fractions_rejected():
    with pytest.raises(ValueError, match='within'):
        _team('bad',100,season=1.01)
    with pytest.raises(ValueError, match='finite'):
        _team('bad',float('nan'))


def test_single_team_rejected():
    with pytest.raises(ValueError,match='at least two'):
        rank_weekly_power((_team('a',100),))

from dataclasses import replace
import pytest
from fsffl.behavioral.context_inputs import (
    FEATURE_NAMES, PartialPositionContext, PartialRosterContext, context_feature_readiness,
)
from fsffl.behavioral.context_expectation_v2 import _full_context_features
from tests.test_behavioral_context_expectation_v2 import context


def test_full_native_context_retains_frozen_feature_vector_and_ignores_unused_faab():
    original = context('trade', 'owner', 2, rb_active=2)
    expected = (0.,0.,2,1., -2.,-2.,0,2., 0.,0.,2,3., 0.,0.,1,1., 1.,1.,18.,18.,6.)
    assert _full_context_features(original) == expected
    partial_shape = PartialRosterContext(positions=original.positions, flex_slot_count=1,
        superflex_slot_count=1, roster_size=18, active_roster_size=18, owned_pick_count=6)
    report = context_feature_readiness(partial_shape)
    assert report.complete and report.require_complete() == expected
    assert _full_context_features(original.model_copy(update={'faab_balance':0})) == expected
    assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES)) == 21


def test_partial_membership_and_settings_preserve_known_inputs_without_inventing_active_or_picks():
    partial = PartialRosterContext(positions=tuple(
        PartialPositionContext(position=p, rostered_count=n, league_average_rostered_count=avg,
            direct_starter_requirement=required)
        for p,n,avg,required in [('QB',3,3.,1),('RB',2,4.,2),('WR',5,5.,3),('TE',2,2.,1)]),
        flex_slot_count=1, superflex_slot_count=1, roster_size=18)
    report = context_feature_readiness(partial)
    assert len(report.missing_features) == 10
    assert report.values[:4] == (0., None, None, 1.)
    assert 'owned_pick_count' in report.missing_features
    assert 'active_roster_size' in report.missing_features
    assert 'RB.relative_rostered_count' not in report.missing_features
    with pytest.raises(ValueError, match='owned_pick_count'):
        report.require_complete()
    # Zero picks is legitimate evidence when supplied, not an unknown default.
    assert 'owned_pick_count' not in context_feature_readiness(replace(partial,owned_pick_count=0)).missing_features
    assert partial.owned_pick_count is None


def test_membership_only_does_not_imply_position_or_full_model_readiness():
    report = context_feature_readiness(PartialRosterContext(roster_size=22))
    assert not report.complete and len(report.missing_features) == 20
    assert report.values[18] == 22.
    assert report.values[:16] == (None,)*16
    assert 'QB.direct_starter_requirement' in report.missing_features


@pytest.mark.parametrize('bad', [float('nan'),float('inf'),-1,True,1.5])
def test_invalid_counts_never_become_model_features(bad):
    with pytest.raises(ValueError):
        context_feature_readiness(PartialRosterContext(roster_size=bad))


def test_duplicate_and_inconsistent_counts_are_rejected():
    p = PartialPositionContext('WR',rostered_count=2,active_rostered_count=3)
    with pytest.raises(ValueError,match='exceeds'):
        context_feature_readiness(PartialRosterContext(positions=(p,)))
    with pytest.raises(ValueError,match='duplicate'):
        context_feature_readiness(PartialRosterContext(positions=(p,p)))
    with pytest.raises(ValueError,match='exceeds'):
        context_feature_readiness(PartialRosterContext(roster_size=2,active_roster_size=3))

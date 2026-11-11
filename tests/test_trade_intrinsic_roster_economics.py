import pytest

from fsffl.product.trade_intrinsic_evidence import build_trade_intrinsic_evidence
from fsffl.trade_decision.roster_legality import TeamRosterLegalityResolution, MandatoryRosterCut
from tests.test_trade_intrinsic_evidence import fixture
from tests.test_dynasty_position_room import _career_current_components


def resolutions(player=None):
    return tuple(TeamRosterLegalityResolution(team_id=team,
        active_roster_before_resolution=2 if team == 'alpha' and player else 1,
        roster_limit=1, required_cut_count=int(team == 'alpha' and bool(player)),
        cuts=(MandatoryRosterCut(player_id=player),) if team == 'alpha' and player else (),
        status='resolved' if team == 'alpha' and player else 'not_required')
        for team in ('alpha', 'beta'))


def build(cuts, cut_annual=None):
    runtime, record, proposal = fixture()
    if cut_annual is not None:
        source = _career_current_components(runtime.league_state,
            {'a1': (10.,20.,30.), 'b1': (20.,30.,40.), 'a2': cut_annual})
        record.contract = source.model_copy(update={'estimates': tuple(row.model_copy(update={
            'long_horizon_raw_y4_y7_reference': 800., 'terminal_raw_y8_plus_reference': 200.,
        }) for row in source.estimates)})
    before = record.contract.model_dump(mode='json')
    result = build_trade_intrinsic_evidence(runtime, proposal, record=record,
        publication_validator=lambda c,r: True, roster_resolutions=cuts)
    assert record.contract.model_dump(mode='json') == before
    return result


def test_required_cuts_charge_once_in_each_native_horizon_and_read_same_source():
    result = build(resolutions('a2'), (1.,2.,3.))
    for name in ('three_year', 'career'):
        raw = result[name]['side_a']['mean_delta']
        adjusted = result[name]['roster_adjusted']['side_a']
        assert adjusted['status'] == 'complete'
        assert adjusted['roster_adjusted_intrinsic_delta'] == raw - adjusted['mandatory_cut_intrinsic_cost']
        assert adjusted['cut_player_ids'] == ['a2']
        assert result[name]['roster_adjusted']['side_b']['mandatory_cut_intrinsic_cost'] == 0
    assert result['source']['selected_player_count'] == 3
    assert result['three_year']['roster_adjusted']['side_a']['scale'] != result['career']['roster_adjusted']['side_a']['scale']


@pytest.mark.parametrize('annual', [(0.,0.,0.), (-1.,-2.,-3.)])
def test_zero_and_signed_cut_values_preserved(annual):
    result = build(resolutions('a2'), annual)
    row = result['three_year']['roster_adjusted']['side_a']
    assert row['mandatory_cut_intrinsic_cost'] <= 0
    assert row['roster_adjusted_intrinsic_delta'] >= row['raw_trade_intrinsic_delta']


def test_unknown_cut_never_free_and_no_resolution_not_assumed_no_cut():
    result = build(resolutions('a2'))
    for name in ('three_year', 'career'):
        row = result[name]['roster_adjusted']['side_a']
        assert row['status'] == 'incomplete'
        assert row['roster_adjusted_intrinsic_delta'] is None
        assert row['missing_cut_player_ids'] == ['a2']
        assert result[name]['side_a']['mean_delta'] is not None
    assert build(None)['career']['roster_adjusted'] is None
    assert build(resolutions())['career']['roster_adjusted']['side_a']['mandatory_cut_intrinsic_cost'] == 0


def test_malformed_cut_identity_and_count_rejected():
    rows = resolutions('a2')
    for cuts in ((rows[0], rows[0]), (rows[0],),
                 (rows[0].model_copy(update={'required_cut_count': 2}), rows[1]),
                 (rows[0], rows[1].model_copy(update={'required_cut_count': 1, 'cuts': rows[0].cuts}))):
        with pytest.raises(ValueError): build(cuts)


def test_core_rejects_wrong_scale_and_preserves_nonfinite_missing():
    from fsffl.trade_decision.intrinsic_roster_economics import adjust_bilateral_intrinsic_net_for_mandatory_cuts
    from fsffl.trade_decision.economic_net import BilateralTradeEconomicNet, TradeLegEconomicNet, ExpectedEconomicNetDelta
    from fsffl.value.models import ValueScale
    result = build(None)
    a = ExpectedEconomicNetDelta.model_validate(result['three_year']['side_a'])
    b = ExpectedEconomicNetDelta.model_validate(result['three_year']['side_b'])
    market = ExpectedEconomicNetDelta(concept='market_price', status='unavailable')
    net = BilateralTradeEconomicNet(proposal_id='test',
        side_a=TradeLegEconomicNet(team_id='alpha', intrinsic=a, market=market),
        side_b=TradeLegEconomicNet(team_id='beta', intrinsic=b, market=market))
    with pytest.raises(ValueError, match='native scale'):
        adjust_bilateral_intrinsic_net_for_mandatory_cuts(net, resolutions(), cut_values={},
            scale=ValueScale(scale_id='career', version='v1', unit_label='different horizon'))
    for value in (float('nan'), float('inf'), -float('inf')):
        adjusted = adjust_bilateral_intrinsic_net_for_mandatory_cuts(net, resolutions('a2'),
            cut_values={'a2': value}, scale=a.scale)
        assert adjusted.side_a.mandatory_cut_intrinsic_cost is None
        assert adjusted.side_a.roster_adjusted_intrinsic_delta is None
        assert adjusted.side_a.missing_cut_player_ids == ('a2',)

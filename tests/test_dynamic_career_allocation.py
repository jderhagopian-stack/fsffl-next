"""Keep accepted Career inputs identical while releasing discarded graphs."""
from types import SimpleNamespace as NS
import weakref
import pytest

from fsffl.product import dynamic_career_composition as bridge
from fsffl.product.foundation4_shadow_inputs import (
    FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING,
    provide_foundation4_long_horizon_forecast_contract_for_rules,
)
from fsffl.forecast.long_horizon_contract import LongHorizonForecastAuthorityContract
from fsffl.state.models import LeagueRules


@pytest.mark.parametrize("use_loader", [False, True])
def test_composition_preserves_validated_board_without_serializing_discarded_rows(monkeypatch, use_loader):
    rules = LeagueRules(team_count=12, roster_size=18, lineup=(),
                        scoring=FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING)
    frozen = provide_foundation4_long_horizon_forecast_contract_for_rules(rules)
    base_ids = {r.player_id for r in frozen.forecasts}
    template_id = frozen.forecasts[0].player_id
    candidate_rows = tuple(r.model_copy(update={'player_id': 'candidate'})
                           for r in frozen.forecasts if r.player_id == template_id)
    expected = LongHorizonForecastAuthorityContract.model_validate({
        **frozen.model_dump(exclude={'provenance'}),
        'forecasts': frozen.forecasts + candidate_rows,
        'provenance': {
            **bridge._scalar_provenance(frozen.provenance),
            'dynamic_candidate_ids': '["candidate"]',
            'dynamic_materializer': 'accepted-foundation4-dynamic-candidate-materializer',
        },
    }).model_dump_json()
    dumps = []
    original_dump = LongHorizonForecastAuthorityContract.model_dump

    def checked_dump(self, *args, **kwargs):
        if self is frozen:
            dumps.append(kwargs.get('exclude'))
        return original_dump(self, *args, **kwargs)

    monkeypatch.setattr(LongHorizonForecastAuthorityContract, 'model_dump', checked_dump)
    monkeypatch.setattr(bridge, 'provide_foundation4_long_horizon_forecast_contract_for_rules',
                        lambda rules: frozen)
    monkeypatch.setattr(bridge, 'provide_foundation4_terminal_features', lambda: {})
    monkeypatch.setattr(bridge, 'align_foundation4_cohort', lambda **kw: (frozen, {}))
    board_ref = []
    long_result = object()

    def long_value(board, *, rules):
        assert board.model_dump_json() == expected
        board_ref.append(weakref.ref(board))
        return long_result

    def forbidden(*args, **kwargs):
        pytest.fail('Injected reuse owner must handle expanded Value calculation')
    monkeypatch.setattr(bridge, 'build_long_term_intrinsic_shadow',
                        forbidden if use_loader else long_value)
    candidate_tail = object()
    final_result = object()
    expanded_current = NS(estimates=[NS(player_id=p) for p in base_ids | {'candidate'}])

    def career(current, long_term, tails):
        assert board_ref[0]() is None, 'Consumed policy board retained during final allocation'
        assert current is expanded_current
        assert long_term is long_result
        assert tails == {'candidate': candidate_tail}
        return final_result

    monkeypatch.setattr(bridge, 'build_career_forward_intrinsic_shadow', career)
    monkeypatch.setattr(bridge, 'append_dynamic_career_estimates',
                        lambda reference, expanded, **kwargs: expanded)
    result, failures = bridge._compose_dynamic_career_contract(
        context=NS(league_state=NS(league=NS(rules=rules))),
        frozen_reference=NS(estimates=[NS(player_id=p) for p in base_ids]),
        expanded_current=expanded_current, candidate_ids=('candidate',),
        long_term_loader=long_value if use_loader else None,
        components=bridge.DynamicCareerComponents(
            y4_y7={'candidate': candidate_rows},
            y8_plus={'candidate': candidate_tail}, failures={}),
    )
    assert result is final_result
    assert failures == {}
    assert dumps == [{'provenance', 'forecasts'}]

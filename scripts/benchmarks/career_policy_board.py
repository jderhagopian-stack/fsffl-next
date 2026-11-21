"""Compare equivalent Career policy-board assembly; no fitting or Shapley run.

Run: PYTHONPATH=src python scripts/benchmarks/career_policy_board.py
Python traced allocation is not total RSS or a full-refresh benchmark.
"""
import gc
from statistics import median
from time import perf_counter
import tracemalloc

from fsffl.forecast.long_horizon_contract import LongHorizonForecastAuthorityContract
from fsffl.product.dynamic_career_composition import _scalar_provenance
from fsffl.product.foundation4_shadow_inputs import (
    FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING,
    provide_foundation4_long_horizon_forecast_contract_for_rules,
)
from fsffl.state.models import LeagueRules


def main():
    rules = LeagueRules(team_count=12, roster_size=18, lineup=(),
                        scoring=FOUNDATION4_FSFFL_PLAYER_OFFENSE_SCORING)
    frozen = provide_foundation4_long_horizon_forecast_contract_for_rules(rules)
    player_id = frozen.forecasts[0].player_id
    candidates = tuple(row.model_copy(update={'player_id': 'benchmark-candidate'})
                       for row in frozen.forecasts if row.player_id == player_id)

    def assemble(exclude):
        return LongHorizonForecastAuthorityContract.model_validate({
            **frozen.model_dump(exclude=exclude),
            'forecasts': frozen.forecasts + candidates,
            'provenance': _scalar_provenance(frozen.provenance),
        })

    assert assemble({'provenance'}) == assemble({'provenance', 'forecasts'})
    for name, exclude in [('original', {'provenance'}),
                          ('optimized', {'provenance', 'forecasts'})]:
        elapsed = []
        for _ in range(5):
            start = perf_counter()
            assemble(exclude)
            elapsed.append(perf_counter() - start)
        gc.collect()
        tracemalloc.start()
        result = assemble(exclude)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(name, 'rows=', len(result.forecasts),
              'median_seconds=', round(median(elapsed), 6),
              'python_peak_bytes=', peak)
        del result


if __name__ == '__main__':
    main()

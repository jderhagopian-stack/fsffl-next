"""Bounded synthetic identity-only benchmark; never acquires source data or models.

Run: PYTHONPATH=src python scripts/benchmarks/future_state_identity.py
Reported Python allocation peak is not process RSS or hosted refresh memory.
"""
from statistics import median
from time import perf_counter
from types import SimpleNamespace
import tracemalloc

from fsffl.forecast.future_state_primitive import (
    frozen_future_state_source_rows,
    governed_future_state_source_row,
    governed_future_state_source_rows,
)
from fsffl.state.models import Player, Position, ProviderRef


def main():
    players = [Player(
        player_id=r.current_player_id, full_name=r.player_name,
        position=Position(r.position), provider_refs=(ProviderRef(
            provider='sleeper', external_id=r.sleeper_external_id),),
    ) for r in frozen_future_state_source_rows()]
    players.extend(players[0].model_copy(update={
        'player_id': f'unknown-{i}', 'provider_refs': (),
    }) for i in range(2165))
    state = SimpleNamespace(players=tuple(players))

    def original():
        rows = {}
        for player in state.players:
            try:
                rows[player.player_id] = governed_future_state_source_row(state, player.player_id)
            except ValueError:
                pass
        return rows

    def batched():
        return governed_future_state_source_rows(state)

    assert original() == batched()
    for name, resolve in [('original', original), ('batched', batched)]:
        elapsed = []
        for _ in range(5):
            started = perf_counter()
            resolve()
            elapsed.append(perf_counter() - started)
        tracemalloc.start()
        resolve()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(name, 'catalog=', len(players), 'governed=', len(batched()),
              'median_seconds=', round(median(elapsed), 6), 'python_peak_bytes=', peak)


if __name__ == '__main__':
    main()

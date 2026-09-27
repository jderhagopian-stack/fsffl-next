from __future__ import annotations

import os
from time import sleep


_DEFAULT_EVERY = 32
_DEFAULT_SECONDS = 0.004


def cooperative_cpu_yield(
    index: int,
    *,
    every: int = _DEFAULT_EVERY,
    seconds: float | None = None,
) -> None:
    """Yield bounded CPU time during long pure-Python background loops.

    This is execution policy only. It does not alter model inputs, iteration order,
    arithmetic, random seeds, or outputs. The hosted free-tier instance has a small
    CPU share, so a serialized heavy worker must periodically release CPU for
    foreground read threads instead of consuming the process quota continuously.
    """

    if index <= 0 or every <= 0 or index % every:
        return
    delay = (
        float(os.getenv("FSFFL_HEAVY_CPU_YIELD_SECONDS", str(_DEFAULT_SECONDS)))
        if seconds is None
        else float(seconds)
    )
    if delay > 0:
        sleep(delay)

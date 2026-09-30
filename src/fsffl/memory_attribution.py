"""Opt-in, low-overhead process RSS and retained-object attribution.

The hosted free instance has a tight memory envelope. This module deliberately
uses /proc sampling and shallow Python object-graph walking instead of tracing
every allocation, which would itself materially raise peak memory.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from enum import Enum
import logging
import os
import resource
import sys
from threading import Event, Thread
from time import monotonic
from typing import Iterator

_logger = logging.getLogger("uvicorn.error")
_ENV_KEY = "FSFFL_MEMORY_ATTRIBUTION"
_PROC_STATUS = "/proc/self/status"
_PROC_STATM = "/proc/self/statm"
_PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")


def current_rss_bytes() -> int:
    """Read current resident pages without importing product/runtime packages."""
    try:
        with open(_PROC_STATUS, encoding="ascii") as status:
            for line in status:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
        with open(_PROC_STATM, encoding="ascii") as statm:
            return int(statm.read().split()[1]) * _PAGE_SIZE
    except (OSError, ValueError, IndexError):
        return 0


def process_peak_rss_bytes() -> int:
    """Return process high-water RSS, matching Linux ru_maxrss bytes."""
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value * (1024 if sys.platform != "darwin" else 1))


def enabled() -> bool:
    return os.getenv(_ENV_KEY, "").strip().lower() in {"1", "true", "yes", "on"}


@contextmanager
def sample_rss_phase(label: str, *, interval_seconds: float = 0.1) -> Iterator[None]:
    """Sample process RSS during one synchronous phase when explicitly enabled."""

    if not enabled():
        yield
        return

    started = monotonic()
    before_rss = current_rss_bytes()
    before_peak = process_peak_rss_bytes()
    stop = Event()
    sample_state = {"max_rss": before_rss, "max_peak": before_peak, "samples": 0}

    def sample() -> None:
        while not stop.wait(interval_seconds):
            rss = current_rss_bytes()
            peak = process_peak_rss_bytes()
            sample_state["max_rss"] = max(sample_state["max_rss"], rss)
            sample_state["max_peak"] = max(sample_state["max_peak"], peak)
            sample_state["samples"] += 1

    thread = Thread(target=sample, name="fsffl-memory-attribution", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=max(0.2, interval_seconds * 2))
        after_rss = current_rss_bytes()
        after_peak = process_peak_rss_bytes()
        _logger.info(
            "FSFFL memory attribution phase=%s elapsed=%.3f rss_before=%s "
            "rss_sampled_peak=%s rss_after=%s peak_before=%s peak_after=%s "
            "peak_increment=%s samples=%s",
            label,
            monotonic() - started,
            before_rss,
            sample_state["max_rss"],
            after_rss,
            before_peak,
            max(sample_state["max_peak"], after_peak),
            max(0, after_peak - before_peak),
            sample_state["samples"],
        )


def object_graph_size(root: object, *, max_nodes: int = 20_000) -> tuple[int, int, bool]:
    """Return unique shallow bytes/node count reachable from a selected root.

    Shared children are counted once. Buffer objects expose their backing size
    through ``nbytes``; nested Forecast/Pydantic models are traversed via their
    instance dictionaries. The bounded walk avoids creating a large profiler.
    """

    pending = [root]
    seen: set[int] = set()
    size_bytes = 0
    truncated = False
    while pending:
        obj = pending.pop()
        identity = id(obj)
        if identity in seen:
            continue
        seen.add(identity)
        if len(seen) > max_nodes:
            truncated = True
            break
        try:
            size_bytes += sys.getsizeof(obj)
        except TypeError:
            pass
        if isinstance(obj, Mapping):
            pending.extend(obj.keys())
            pending.extend(obj.values())
        elif isinstance(obj, (tuple, list, set, frozenset)):
            pending.extend(obj)
        elif isinstance(obj, (str, bytes, bytearray, memoryview, Enum)):
            continue
        else:
            # Numeric buffers can own memory not included by sys.getsizeof.
            nbytes = getattr(obj, "nbytes", None)
            if isinstance(nbytes, int):
                size_bytes += max(0, nbytes - sys.getsizeof(obj))
            fields = getattr(obj, "__dict__", None)
            if isinstance(fields, dict):
                pending.append(fields)
    return size_bytes, len(seen), truncated


def log_object_graph(label: str, **roots: object) -> None:
    """Log bounded unique object-graph sizes for explicitly selected roots."""

    if not enabled():
        return
    for name, root in roots.items():
        size, nodes, truncated = object_graph_size(root)
        _logger.info(
            "FSFFL memory attribution objects=%s root=%s bytes=%s nodes=%s truncated=%s",
            label,
            name,
            size,
            nodes,
            truncated,
        )

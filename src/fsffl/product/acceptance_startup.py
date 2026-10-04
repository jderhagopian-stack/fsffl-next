from __future__ import annotations

from collections.abc import Mapping
import os


_TRUTHY = frozenset({"1", "true", "yes", "on"})
_ACCEPTANCE_RUN_FLAGS = (
    "FSFFL_RUN_RUNTIME_AVAILABILITY_ACCEPTANCE",
    "FSFFL_RUN_STATE_FIRST_ACCEPTANCE",
)


def production_acceptance_startup_enabled(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Require a dedicated engineering gate as well as an acceptance workload flag.

    Production customer cold starts stay restore-only by default. Engineering
    acceptance must be separately and explicitly enabled on an isolated run.
    """
    values = os.environ if environ is None else environ
    if values.get("FSFFL_ENABLE_PRODUCTION_ACCEPTANCE_STARTUP", "0").strip().lower() not in _TRUTHY:
        return False
    return any(values.get(name, "0").strip().lower() in _TRUTHY for name in _ACCEPTANCE_RUN_FLAGS)

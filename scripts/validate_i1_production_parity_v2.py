from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import fsffl
import fsffl.forecast
import fsffl.value
from fsffl.state.models import Position


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _research_root_from_argv() -> Path:
    try:
        index = sys.argv.index("--research-root")
        return Path(sys.argv[index + 1]).resolve()
    except (ValueError, IndexError) as exc:
        raise RuntimeError("--research-root is required before loading the frozen research oracle") from exc


def _append_research_only_package_paths(research_root: Path) -> None:
    """Make research-only modules importable without replacing production modules.

    The frozen research scripts import several modules that never existed on the
    production main branch (for example non_qb_career_state and
    intrinsic_economics). The parity process already has the production package
    loaded because that is the implementation under test. Append, rather than
    prepend, the frozen research package directories so existing production
    modules keep their identity while research-only dependencies can resolve.

    Any semantic drift in shared modules is still caught by the predeclared
    probability/production/Shapley parity tolerances; this is an import bridge,
    not a calibration or behavior override.
    """

    research_pkg = research_root / "src" / "fsffl"
    additions = (
        (fsffl.__path__, research_pkg),
        (fsffl.forecast.__path__, research_pkg / "forecast"),
        (fsffl.value.__path__, research_pkg / "value"),
    )
    for package_path, candidate in additions:
        text = str(candidate)
        if candidate.exists() and text not in package_path:
            package_path.append(text)


if __name__ == "__main__":
    here = Path(__file__).parent
    research_root = _research_root_from_argv()
    _append_research_only_package_paths(research_root)

    validator = _load(here / "validate_i1_production_parity.py", "i1_production_parity_v1")
    original_load = validator.load

    def load_with_position(path: Path, name: str):
        module = original_load(path, name)
        if path.name == "run_integrated_multivariate_forecast.py":
            # Research harness uses string positions and does not itself expose the
            # canonical Position enum. The production validator needs only this
            # type binding; no research behavior or result is changed.
            module.Position = Position
        return module

    validator.load = load_with_position
    validator.main()

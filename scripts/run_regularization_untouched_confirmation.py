from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--career-panel", type=Path, required=True)
    ap.add_argument("--usage-panel", type=Path, required=True)
    ap.add_argument("--qb-results", type=Path, required=True)
    ap.add_argument("--prior-integrated-json", type=Path, required=True)
    ap.add_argument("--prior-event-json", type=Path, required=True)
    ap.add_argument("--prior-persistence-json", type=Path, required=True)
    ap.add_argument("--freeze", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rr = load(Path(__file__).with_name("run_regularization_developmental_calibration.py"), "rr_confirmation")
    freeze = json.loads(args.freeze.read_text())
    if not freeze.get("global_frozen") or not freeze.get("stage_frozen") or not freeze.get("confirmation_authorized"):
        raise RuntimeError("selection is not frozen for confirmation")
    if float(freeze["global_C"]) != 0.25 or freeze.get("developmental_C") is not None:
        raise RuntimeError("optimized confirmation is valid only for frozen global C=0.25 with no developmental override")

    im, A, checks = rr.context(args)
    rows = [r for r in im.evalfold(*A, 2023, 0.25, 0.25, arches=("I1",)) if int(r["horizon"]) == 1]
    resolved = [r for r in rows if r.get("factual_state") is not None]
    dev_rows = [r for r in resolved if rr.dev(r)]
    result = {
        "mode": "untouched-confirmation-single-fit",
        "source_season": 2023,
        "horizon": 1,
        "target_season": 2024,
        "global_C": 0.25,
        "developmental_C": None,
        "checks": checks,
        "summary": rr.summary(im, rows),
        "coverage": {
            "rows": len(rows),
            "resolved": len(resolved),
            "resolved_share": len(resolved) / len(rows) if rows else None,
            "developmental": len(dev_rows),
            "developmental_successes": sum(r["factual_state"] in rr.USE for r in dev_rows),
        },
        "selection_was_frozen_before_confirmation": True,
        "candidate_changed_after_confirmation": False,
    }
    pd.DataFrame(rows).to_csv(args.output_dir / "confirmation_rows.csv", index=False)
    (args.output_dir / "confirmation_results.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

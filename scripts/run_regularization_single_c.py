from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--C", type=float, required=True)
    ap.add_argument("--career-panel", type=Path, required=True)
    ap.add_argument("--usage-panel", type=Path, required=True)
    ap.add_argument("--qb-results", type=Path, required=True)
    ap.add_argument("--prior-integrated-json", type=Path, required=True)
    ap.add_argument("--prior-event-json", type=Path, required=True)
    ap.add_argument("--prior-persistence-json", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    helper = load(Path(__file__).with_name("run_regularization_developmental_calibration.py"), "rdc_single_helper")
    im, A, checks = helper.context(args)
    rows = helper.run_rows(im, A, args.C)
    result = {
        "mode": "global-single-c",
        "C": args.C,
        "checks": checks,
        "overall": helper.summary(im, rows),
        "folds": helper.folds(im, rows),
        "coverage": helper.coverage(rows),
    }
    pd.DataFrame(helper.add_meta(rows, mode="global", global_C=args.C, treatment="global")).to_csv(
        args.output_dir / f"global_C_{args.C:g}_rows.csv", index=False
    )
    (args.output_dir / f"global_C_{args.C:g}_results.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({"C": args.C, "state_brier": result["overall"]["state_brier"], "n": result["overall"]["n"]}, indent=2))


if __name__ == "__main__":
    main()

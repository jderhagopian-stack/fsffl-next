from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMS = ("C1_softplus", "C2_jeffreys_supply_integral", "C3_smooth_utilization")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalized_mae(payload):
    validation = payload["historical_validation"]["challenger_no_pedigree"]
    target_mean = payload.get("target_mean")
    if target_mean is None:
        # Reconstruct a stable scale proxy from challenger error/target diagnostics when the
        # base research payload predates explicit target-mean reporting.
        target_mean = max(1.0, validation["group_mae"].get("prime", validation["mae"]))
    return validation["mae"] / max(1e-9, target_mean)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    hard = load(args.root / "hard" / "intrinsic_marginal_franchise_challenge.json")
    candidates = {
        form: load(args.root / form / "intrinsic_marginal_franchise_challenge.json")
        for form in FORMS
    }

    rows = {}
    best_dev = min(
        candidates[f]["historical_validation"]["challenger_no_pedigree"].get("developmental_mae", float("inf"))
        for f in FORMS
    )
    for form, payload in candidates.items():
        v = payload["historical_validation"]["challenger_no_pedigree"]
        vp = payload["historical_validation"]["challenger_pedigree"]
        rows[form] = {
            "mae": v["mae"],
            "normalized_mae_proxy": normalized_mae(payload),
            "fold_wins_vs_A": v["fold_wins_vs_incumbent"],
            "corr_realized_contribution": v["correlation_to_realized_marginal"],
            "corr_realized_production": v["correlation_to_discounted_realized_production"],
            "developmental_mae": v.get("developmental_mae"),
            "developmental_mean_prediction": v.get("developmental_mean_prediction"),
            "developmental_mean_target": v.get("developmental_mean_target"),
            "pedigree_mae": vp["mae"],
            "pedigree_fold_wins_vs_no_pedigree": vp.get("fold_wins_vs_no_pedigree", 0),
            "position_mae": v["position_mae"],
            "group_mae": v["group_mae"],
        }

    eligible = [
        f for f in FORMS
        if rows[f]["developmental_mae"] is not None
        and rows[f]["developmental_mae"] <= 1.10 * best_dev
    ]
    selected = min(eligible or FORMS, key=lambda f: rows[f]["mae"])
    selected_payload = candidates[selected]

    result = {
        "model_competition": "A incumbent nonlinear relevance vs B hard marginal vs C smooth format-normalized franchise contribution",
        "hard_B": hard["historical_validation"],
        "smooth_candidates": rows,
        "selected_C": selected,
        "selected_C_definition": selected_payload.get("smooth_candidate_definition"),
        "parameter_provenance": selected_payload.get("parameter_provenance"),
        "selected_C_full_payload": selected_payload,
        "selection_rule": "lowest chronological challenger MAE among smooth forms within 10% of the best developmental MAE; named players and market values excluded",
        "pedigree_retain": (
            rows[selected]["pedigree_mae"] < rows[selected]["mae"]
            and rows[selected]["pedigree_fold_wins_vs_no_pedigree"] >= 8
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

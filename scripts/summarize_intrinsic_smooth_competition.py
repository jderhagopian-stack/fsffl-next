from __future__ import annotations

import argparse
import json
from pathlib import Path

FORMS = ("C1_softplus", "C2_jeffreys_supply_integral", "C3_smooth_utilization")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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
    for form, payload in candidates.items():
        v = payload["historical_validation"]["challenger_no_pedigree"]
        vp = payload["historical_validation"]["challenger_pedigree"]
        rows[form] = {
            "mae": v["mae"],
            "mean_target": v["mean_target"],
            "normalized_mae": v["normalized_mae"],
            "fold_wins_vs_A": v["fold_wins_vs_incumbent"],
            "corr_realized_contribution": v["correlation_to_realized_marginal"],
            "corr_realized_production": v["correlation_to_discounted_realized_production"],
            "developmental_n": v["developmental_n"],
            "developmental_mae": v["developmental_mae"],
            "developmental_normalized_mae": v["developmental_normalized_mae"],
            "developmental_mean_prediction": v["developmental_mean_prediction"],
            "developmental_mean_target": v["developmental_mean_target"],
            "pedigree_mae": vp["mae"],
            "pedigree_normalized_mae": vp["normalized_mae"],
            "pedigree_fold_wins_vs_no_pedigree": vp.get("fold_wins_vs_no_pedigree", 0),
            "position_mae": v["position_mae"],
            "group_mae": v["group_mae"],
        }

    best_dev = min(rows[f]["developmental_normalized_mae"] for f in FORMS)
    eligible = [f for f in FORMS if rows[f]["developmental_normalized_mae"] <= 1.10 * best_dev]
    selected = min(eligible or FORMS, key=lambda f: rows[f]["normalized_mae"])
    selected_payload = candidates[selected]

    result = {
        "model_competition": "A incumbent nonlinear relevance vs B hard marginal vs C smooth format-normalized franchise contribution",
        "hard_B": hard["historical_validation"],
        "smooth_candidates": rows,
        "selected_C": selected,
        "selected_C_definition": selected_payload.get("smooth_candidate_definition"),
        "parameter_provenance": selected_payload.get("parameter_provenance"),
        "selected_C_full_payload": selected_payload,
        "selection_rule": "lowest chronological normalized MAE among smooth forms within 10% of the best developmental normalized MAE; named players and market values excluded",
        "pedigree_retain": (
            rows[selected]["pedigree_normalized_mae"] < rows[selected]["normalized_mae"]
            and rows[selected]["pedigree_fold_wins_vs_no_pedigree"] >= 8
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

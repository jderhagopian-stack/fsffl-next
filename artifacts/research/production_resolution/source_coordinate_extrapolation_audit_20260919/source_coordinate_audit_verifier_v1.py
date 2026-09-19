from __future__ import annotations
import hashlib
import json
import platform
import time
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent

EXPECTED = {
    "STAGE1_COORDINATE_LINEAGE.csv": "985758dffd707be44a2109583efc3bdaad04839488eed7a68d525c326228ae42",
    "STAGE1_SCORING_EQUIVALENCE_MATRIX.csv": "b1c1735c041c535813e4b93ac7df32350e5521f73b121fe662a5820170a313d0",
    "STAGE1_CURRENT_PLAYER_SCORING_COORDINATE_EFFECT.csv": "b0beaf6166755fbce0d633b4b401d0866314d5231fcd0b1f2c2469a90320ec53",
    "STAGE1_POSITION_SCORING_COORDINATE_EFFECT.csv": "c3afc16096eb7b9360e38f3b68a6cc2e643564c4d8c43bd41bce5ed4dae51eb6",
    "STAGE1_HISTORICAL_AVAILABILITY_POPULATION_EVIDENCE.csv": "7ff3ca1ab86ac9627c69d7fbab1c4dd53f6cd113fc2f143b583de67ddbb82e9c",
    "STAGE1_ACCOUNTING_ONLY_RATIO_EFFECT.csv": "2e9b6900cf555d5a34452083155d012452418f927f658b559d572511c8cf7c2f",
    "STAGE1_SEMANTIC_COORDINATE_AUDIT.json": "a2bcbc329a955474a698e1aebe0d70253a85b563a9bba4a4b212cba6b765b23f",
    "DOWNSTREAM_GATE_NOT_EXECUTED.json": "3e50d65738dea957c31c34370348acc36e2f6940e7b0f8dea975a3a701605276",
    "STAGE1_NAMED_AND_MECHANICAL_EXAMPLES.csv": "1fe5070f3b2abd4bdb8d2de7babb97f92221fbad3418ed61486e1d3a6b9916e6",
    "STAGE1_EXAMPLE_P0_COMPONENTS.csv": "4b22a9036e26350631313c6d92c07e3fe982c162b7ffa9fddb4c56490285c3b5",
}

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    start = time.perf_counter()

    hashes = {name: sha256(BASE / name) for name in EXPECTED}
    hash_pass = all(hashes[k] == v for k, v in EXPECTED.items())

    pos = pd.read_csv(BASE / "STAGE1_POSITION_SCORING_COORDINATE_EFFECT.csv").set_index("position")
    expected_ratios = {
        "QB": 1.0,
        "RB": 1.1097054683463108,
        "WR": 1.2852485043404789,
        "TE": 1.3491829664184194,
    }
    ratio_pass = all(
        abs(float(pos.loc[p, "aggregate_half_ppr_to_standard_ratio"]) - v) <= 1e-12
        for p, v in expected_ratios.items()
    )

    matrix = pd.read_csv(BASE / "STAGE1_SCORING_EQUIVALENCE_MATRIX.csv")
    reception = matrix[matrix["component"].astype(str).str.lower().eq("reception")].iloc[0]
    semantic_pass = (
        str(reception["historical_P0_coordinate"]).strip() in {"0", "0.0", "No reception points"}
        and "0.5" in str(reception["current_governed_Y1_coordinate"])
        and str(reception["status"]).strip().upper() != "MATCH"
    )

    gate = json.loads((BASE / "DOWNSTREAM_GATE_NOT_EXECUTED.json").read_text())
    downstream_pass = all(
        gate[k] == "NOT_EXECUTED"
        for k in (
            "stage2_distribution_support_audit",
            "stage3_response_surface_audit",
            "stage4_diagnostic_counterfactuals",
        )
    )

    elapsed = time.perf_counter() - start
    result = {
        "schema_version": "fsffl-source-coordinate-audit-verifier-v1",
        "pass": bool(hash_pass and ratio_pass and semantic_pass and downstream_pass),
        "hash_pass": hash_pass,
        "position_ratio_pass": ratio_pass,
        "semantic_mismatch_pass": semantic_pass,
        "downstream_gate_pass": downstream_pass,
        "classification": "A - COORDINATE MISMATCH IDENTIFIED",
        "runtime_seconds": elapsed,
        "environment": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "model_fits": 0,
        "tuning_actions": 0,
        "route_changes": 0,
        "production_changes": 0,
    }
    (BASE / "FINAL_AUDIT_VERIFICATION.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
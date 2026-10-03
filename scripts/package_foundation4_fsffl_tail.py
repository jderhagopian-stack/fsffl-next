from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--research-run-id", type=int, required=True)
    args = parser.parse_args()

    evidence = json.loads(Path(args.evidence).read_text())
    supported = tuple(str(x) for x in evidence["supported_models"])
    if supported != ("direct_ridge", "two_part_state"):
        raise SystemExit(
            "FSFFL terminal recalibration changed the governed supported model set: "
            f"{supported}"
        )
    scoring_coordinate = str(evidence.get("scoring_coordinate") or "").strip()
    if scoring_coordinate != "connected_league_fantasy_points":
        raise SystemExit(
            "FSFFL terminal evidence has unexpected scoring coordinate: "
            f"{scoring_coordinate}"
        )

    package = {
        "schema_version": "foundation4-career-tail-runtime-package-v1",
        "target_version": evidence["target_version"],
        "model_version": (
            str(evidence["model_version"])
            + ":fsffl-connected-scoring-recalibration-v1"
        ),
        "scoring_coordinate": scoring_coordinate,
        "supported_models": list(supported),
        "lineup_capacity_signature": evidence["lineup_capacity_signature"],
        "shapley_permutations": evidence["shapley_permutations"],
        "shapley_seed": evidence["shapley_seed"],
        "fitted_models": evidence["fitted_models"],
        "residual_bands": evidence["residual_bands"],
        "validation_governance": evidence["validation_governance"],
        "final_holdout": evidence["final_holdout"],
        "research_run_id": args.research_run_id,
        "source_evidence_sha256": canonical_sha256(evidence),
        "aggregation_semantics": evidence["aggregation_semantics"],
        "coordinate_provenance": (
            "direct historical FSFFL scoring target recalibration; frozen model "
            "families and lineup-capacity Shapley game retained"
        ),
    }
    package["semantic_sha256"] = canonical_sha256(package)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(package, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "out": str(out),
        "semantic_sha256": package["semantic_sha256"],
        "scoring_coordinate": scoring_coordinate,
        "research_run_id": args.research_run_id,
    }, sort_keys=True))


if __name__ == "__main__":
    main()

"""Read-only validation of frozen linear Intrinsic anchors across saved checkpoints.

Input is a JSON list of snapshots. Each snapshot requires checkpoint_id and
estimates, which contain player_id, raw_career_forward_reference and
uncertainty.current_y1_y3[{year_index, raw_shapley_contribution}].
Do not claim exact State identity without a separate State fingerprint.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(snapshots: list[dict], *, three_anchor: float, career_anchor: float) -> list[dict]:
    if not (0 < three_anchor and 0 < career_anchor):
        raise ValueError("anchors must be positive")
    output = []
    for snap in snapshots:
        records = snap["estimates"]
        seen = set()
        raw_three, raw_career = [], []
        for estimate in records:
            pid = estimate["player_id"]
            if pid in seen:
                raise ValueError(f"duplicate player ID in snapshot {snap['checkpoint_id']}")
            seen.add(pid)
            years = estimate["uncertainty"]["current_y1_y3"]
            contributions = {int(x["year_index"]): float(x["raw_shapley_contribution"]) for x in years}
            if set(contributions) != {1, 2, 3}:
                raise ValueError(f"missing or duplicated horizon years for {pid}")
            raw_three.append(sum(contributions[i] * (0.85 ** (i - 1)) for i in (1, 2, 3)))
            raw_career.append(float(estimate["raw_career_forward_reference"]))
        output.append({
            "checkpoint_id": snap["checkpoint_id"],
            "count": len(seen),
            "max_three_year": max(raw_three, default=None),
            "max_career": max(raw_career, default=None),
            "clipped_three_year": sum(x >= three_anchor for x in raw_three),
            "clipped_career": sum(x >= career_anchor for x in raw_career),
            "three_year_anchor": three_anchor,
            "career_anchor": career_anchor,
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--three-anchor", type=float, required=True)
    parser.add_argument("--career-anchor", type=float, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    if not isinstance(data, list):
        raise ValueError("input must be a list of snapshots")
    result = validate(data, three_anchor=args.three_anchor, career_anchor=args.career_anchor)
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()

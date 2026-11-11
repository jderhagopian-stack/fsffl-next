"""Strict read-only same-State Intrinsic calibration comparison.

Input JSON is supplied by a separately governed extractor. This utility
never retrieves data, changes production scores, or substitutes missing values.
"""
from __future__ import annotations

import json
from pathlib import Path

from fsffl.product.intrinsic_magnitude_shadow import MagnitudeRuler


def compare_same_state(document: dict) -> dict:
    required = ("league_state_id", "forecast_cutoff", "three_year", "career", "published")
    if any(not document.get(k) for k in required):
        raise ValueError("missing required exact-State comparison envelope")
    state, cutoff = document["league_state_id"], document["forecast_cutoff"]
    for key in ("three_year", "career", "published"):
        item = document[key]
        if item.get("league_state_id") != state or item.get("forecast_cutoff") != cutoff:
            raise ValueError(f"{key} State/cutoff mismatch: refusing comparison")
        if not isinstance(item.get("players"), dict):
            raise ValueError(f"{key} player map missing")
    rulers = {
        "three_year": MagnitudeRuler("three_year", document["anchors"]["three_year"], document["curve"], document["reference_version"]),
        "career": MagnitudeRuler("career", document["anchors"]["career"], document["curve"], document["reference_version"]),
    }
    rows = []
    identities = set().union(*(set(document[key]["players"]) for key in ("three_year", "career", "published")))
    for pid in sorted(identities):
        three = document["three_year"]["players"].get(pid)
        career = document["career"]["players"].get(pid)
        published = document["published"]["players"].get(pid)
        if not all(isinstance(item, dict) for item in (three, career, published)):
            rows.append({"player_id": pid, "status": "missing_source", "missing": [key for key, row in (("three_year", three), ("career", career), ("published", published)) if row is None]})
            continue
        v3, vc = three.get("raw"), career.get("raw")
        rows.append({
            "player_id": pid,
            "name": published.get("name"),
            "position": published.get("position"),
            "age": published.get("age"),
            "raw_three_year": v3,
            "raw_career": vc,
            "career_y1_y3": career.get("current_y1_y3"),
            "career_y4_y7": career.get("y4_y7"),
            "career_y8_plus": career.get("y8_plus"),
            "published_three_year": published.get("three_year"),
            "published_career": published.get("career"),
            "shadow_three_year": rulers["three_year"].score(v3),
            "shadow_career": rulers["career"].score(vc),
            "status": "complete" if v3 is not None and vc is not None else "unsupported_raw",
        })
    return {
        "league_state_id": state, "forecast_cutoff": cutoff,
        "reference_version": document["reference_version"],
        "rulers": {k: ruler.fingerprint for k, ruler in rulers.items()},
        "player_count": len(rows),
        "complete_count": sum(row["status"] == "complete" for row in rows),
        "rows": rows,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    result = compare_same_state(json.loads(args.input_json.read_text()))
    args.output_json.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()

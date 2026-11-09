"""Versioned age-input correction around the unchanged accepted materializer.

Use --prepare-only for the bounded feature gate. Otherwise pass the existing
materialize_foundation4_fsffl_coordinate.py arguments as well. Outputs go to a
new directory; this command never replaces packaged or historical artifacts.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
from importlib.resources import files
import importlib.util
import json
from pathlib import Path
import sys

import pandas as pd

from fsffl.forecast.feature_origin import (
    FORECAST_ORIGIN_AGE_VERSION, age_at_forecast_origin, age_date,
)


def reference_age_origins(board: pd.DataFrame) -> dict[str, date]:
    """Bind the recovered date ledger to its exact source age/identity cohort."""
    manifest = json.loads(files("fsffl.forecast").joinpath(
        "data/foundation4_reference_age_origins_2026.json"
    ).read_text())
    rows = board.sort_values("player_id")
    material = "\n".join(
        f"{row.player_id}|{row.position}|{row.age:.9f}" for row in rows.itertuples()
    )
    if (len(board) != manifest["source_player_count"]
            or hashlib.sha256(material.encode()).hexdigest()
            != manifest["source_age_coordinate_sha256"]):
        raise ValueError("reference age evidence does not match this input cohort")
    overrides = manifest["source_age_as_of_overrides"]
    return {str(pid): age_date(overrides.get(str(pid), manifest["source_age_default_as_of"]))
            for pid in board.player_id}


def align_board_ages(
    board: pd.DataFrame, players: pd.DataFrame, *, evaluation_season: int,
) -> pd.DataFrame:
    """Keep every subject and source fact; supply the model's dated age feature."""
    if board.player_id.isna().any() or board.player_id.duplicated().any():
        raise ValueError("age alignment requires unique nonmissing player identities")
    if "age_feature_version" in board:
        if set(board.age_feature_version) != {FORECAST_ORIGIN_AGE_VERSION}:
            raise ValueError("unknown age feature version")
    metadata: dict[str, date] = {}
    for row in players[["gsis_id", "birth_date"]].itertuples(index=False):
        dob = age_date(row.birth_date)
        if pd.isna(row.gsis_id) or dob is None:
            continue
        key = str(row.gsis_id)
        if key in metadata and metadata[key] != dob:
            raise ValueError(f"conflicting birth-date evidence for {key}")
        metadata[key] = dob

    explicit_dates = "source_age_as_of" in board or "age_as_of" in board or "state_as_of" in board
    origins = {}
    if not explicit_dates:
        try:
            origins = reference_age_origins(board)
        except ValueError:
            # A new subject with governed DOB needs no inherited reference
            # date. An undated age alone still cannot borrow that cohort's date.
            if not all(str(row.get("historical_gsis_id", "")) in metadata
                       for row in board.to_dict("records")):
                raise
    result = board.copy()
    records = []
    for row in board.to_dict("records"):
        pid = str(row["player_id"])
        source_age = float(row.get("source_age_years", row["age"]))
        source_date = age_date(row.get("source_age_as_of", row.get("age_as_of", row.get("state_as_of"))))
        source_date = source_date if source_date is not None else origins.get(pid)
        dob = metadata.get(str(row.get("historical_gsis_id", "")))
        age = age_at_forecast_origin(
            evaluation_season=evaluation_season, source_age_years=source_age,
            source_age_as_of=source_date, birth_date=dob,
        )
        records.append((age, source_age, source_date.isoformat() if source_date else None,
                        "governed_DOB" if dob else "governed_dated_age"))
    for index, column in enumerate(("age", "source_age_years", "source_age_as_of", "age_evidence")):
        result[column] = [row[index] for row in records]
    result["age_as_of"] = date(evaluation_season, 9, 1).isoformat()
    result["age_feature_version"] = FORECAST_ORIGIN_AGE_VERSION
    return result


def run_materializer(arguments: list[str], *, corrected_board: Path, players: Path, output: Path) -> None:
    """Reuse accepted fitting/scoring code, with a distinct output identity."""
    path = Path(__file__).with_name("materialize_foundation4_fsffl_coordinate.py")
    spec = importlib.util.spec_from_file_location("foundation4_origin_materializer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("accepted materializer is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.MODEL_VERSION = f"{module.MODEL_VERSION}:{FORECAST_ORIGIN_AGE_VERSION}"
    original_argv = sys.argv
    try:
        sys.argv = [str(path), *arguments, "--board", str(corrected_board),
                    "--players", str(players), "--out-dir", str(output)]
        module.main()
    finally:
        sys.argv = original_argv


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path, required=True)
    parser.add_argument("--players", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--evaluation-season", type=int, default=2026)
    parser.add_argument("--prepare-only", action="store_true")
    args, remaining = parser.parse_known_args(argv)
    # The accepted historical materializer is explicitly a 2026 package. The
    # generic age adapter supports rollover; this wrapper must not relabel fits.
    if not args.prepare_only and args.evaluation_season != 2026:
        parser.error("accepted Foundation 4 materialization supports evaluation season 2026 only")
    if args.prepare_only and remaining:
        parser.error("unexpected materializer arguments with --prepare-only")
    board = pd.read_csv(args.board)
    players = pd.read_csv(args.players, dtype={"gsis_id": str})
    corrected = align_board_ages(board, players, evaluation_season=args.evaluation_season)
    args.out_dir.mkdir(parents=True, exist_ok=False)
    target = args.out_dir / "FORECAST_ORIGIN_INPUT_BOARD.csv"
    corrected.to_csv(target, index=False)
    manifest = {
        "feature_origin_version": FORECAST_ORIGIN_AGE_VERSION,
        "evaluation_season": args.evaluation_season,
        "age_as_of": date(args.evaluation_season, 9, 1).isoformat(),
        "source_board_sha256": hashlib.sha256(args.board.read_bytes()).hexdigest(),
        "identity_metadata_sha256": hashlib.sha256(args.players.read_bytes()).hexdigest(),
        "corrected_board_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "players": len(corrected),
        "age_evidence_counts": corrected.age_evidence.value_counts().to_dict(),
        "source_ages_preserved": True,
        "experience_changed": False,
        "prepare_only": args.prepare_only,
        "materialization_complete": False,
    }
    receipt = args.out_dir / "FEATURE_ORIGIN_MANIFEST.json"
    receipt.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    if not args.prepare_only:
        run_materializer(remaining, corrected_board=target, players=args.players,
                         output=args.out_dir / "materialized")
        manifest["materialization_complete"] = True
        receipt.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()

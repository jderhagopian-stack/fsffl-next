from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

EXPECTED_UNIVERSE_SHA256 = "c668b74b9010809904c14366d992137f7b038b299d6d3f031b07eea0d63c0b3f"
EXPECTED_MANIFEST_SHA256 = "828126f0476c2bf18a84344e5a9672cda518b105e2ceff5b035766ffa50249a6"
EXPECTED_COORDINATE_ID = "year1-current-governed-2026:2026-09-18T09:42:31.889752+00:00"
SOURCE_RUN_ID = 35330898624
SOURCE_HEAD_SHA = "92eb9cb4cc1f5c61909e55d6c5491eb0292d4bb6"
SOURCE_ARTIFACT_ID = 10541375155
SOURCE_ARTIFACT_ZIP_SHA256 = "c23fed641c4ad689513510022f187e6ea05cab2dc88d457d545be9afc1f49ee7"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--dest-dir", type=Path, required=True)
    args = parser.parse_args()

    source = args.source_dir
    dest = args.dest_dir

    required = {
        "governed_year1_universe.json",
        "governed_year1_universe_manifest.json",
        "reload_verification.json",
        "report.md",
    }
    missing = sorted(name for name in required if not (source / name).is_file())
    if missing:
        raise SystemExit(f"missing frozen refresh files: {missing}")

    universe_path = source / "governed_year1_universe.json"
    manifest_path = source / "governed_year1_universe_manifest.json"
    verification_path = source / "reload_verification.json"

    universe_sha = sha256(universe_path)
    manifest_sha = sha256(manifest_path)
    if universe_sha != EXPECTED_UNIVERSE_SHA256:
        raise SystemExit(f"universe SHA mismatch: {universe_sha}")
    if manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise SystemExit(f"manifest SHA mismatch: {manifest_sha}")

    universe = json.loads(universe_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verification = json.loads(verification_path.read_text(encoding="utf-8"))

    expected_positions = {"QB": 61, "RB": 88, "TE": 64, "WR": 122}
    if universe["coordinate_id"] != EXPECTED_COORDINATE_ID:
        raise SystemExit("coordinate ID mismatch")
    if universe["row_count"] != 335 or len(universe["rows"]) != 335:
        raise SystemExit("row-count mismatch")
    if universe["position_counts"] != expected_positions:
        raise SystemExit(f"position counts mismatch: {universe['position_counts']}")
    if universe["source_governance"]["successful_source_ids"] != ["fftoday", "razzball"]:
        raise SystemExit("governed live-source rule mismatch")
    if universe["downstream_coordinate"]["mapped_completed_source_players"] != 335:
        raise SystemExit("completed-source mapping is not complete")
    if manifest["artifact_sha256"] != universe_sha or manifest["row_count"] != 335:
        raise SystemExit("manifest does not verify frozen universe")
    if verification["status"] != "PASS":
        raise SystemExit("refresh reload verification is not PASS")
    if verification["artifact_sha256_first_write"] != universe_sha:
        raise SystemExit("refresh first-write hash mismatch")
    if verification["artifact_sha256_fresh_reload"] != universe_sha:
        raise SystemExit("refresh reload hash mismatch")
    if verification["row_count_fresh_reload"] != 335:
        raise SystemExit("refresh reload row count mismatch")

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in sorted(required):
        shutil.copyfile(source / name, dest / name)

    provenance = {
        "schema_version": "fsffl-governed-year1-persistence-source-v1",
        "coordinate_id": EXPECTED_COORDINATE_ID,
        "source_workflow_run_id": SOURCE_RUN_ID,
        "source_workflow_head_sha": SOURCE_HEAD_SHA,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_name": "governed-year1-evaluation-universe",
        "source_artifact_zip_sha256": SOURCE_ARTIFACT_ZIP_SHA256,
        "universe_sha256": EXPECTED_UNIVERSE_SHA256,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "note": "Exact bytes copied from the already-completed data-refresh workflow; no live provider refetch occurred during persistence.",
    }
    (dest / "source_run.json").write_text(canonical_json(provenance), encoding="utf-8")

    repo_universe = dest / "governed_year1_universe.json"
    repo_manifest = dest / "governed_year1_universe_manifest.json"
    repo_universe_sha = sha256(repo_universe)
    repo_manifest_sha = sha256(repo_manifest)
    reloaded = json.loads(repo_universe.read_text(encoding="utf-8"))

    if repo_universe_sha != EXPECTED_UNIVERSE_SHA256:
        raise SystemExit("repository-copy universe hash changed")
    if repo_manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise SystemExit("repository-copy manifest hash changed")
    if reloaded["row_count"] != 335 or len(reloaded["rows"]) != 335:
        raise SystemExit("repository-copy row count changed")
    if reloaded["position_counts"] != expected_positions:
        raise SystemExit("repository-copy position counts changed")

    checkpoint = f"""# FSFFL NEXT - New Governed Downstream Evaluation Universe Checkpoint

Status: **PASS - ROW-COMPLETE CURRENT YEAR-1 COORDINATE DURABLY PERSISTED AND RELOADED**

- Coordinate: `{reloaded['coordinate_id']}`
- Freeze as-of: `{reloaded['freeze_as_of']}`
- Row count: **{reloaded['row_count']}**
- Position counts: `{reloaded['position_counts']}`
- Successful governed live sources: `{reloaded['source_governance']['successful_source_ids']}`
- Failed/ignored sources: `{reloaded['source_governance']['failed_sources']}`
- Universe path: `{repo_universe}`
- Manifest path: `{repo_manifest}`
- Universe SHA-256: `{repo_universe_sha}`
- Manifest SHA-256: `{repo_manifest_sha}`
- Source workflow run: `{SOURCE_RUN_ID}`
- Source artifact id: `{SOURCE_ARTIFACT_ID}`
- Source artifact ZIP digest: `{SOURCE_ARTIFACT_ZIP_SHA256}`
- Exact repository-copy reload: **PASS**
- No live refetch occurred during persistence; these are the exact bytes produced by the completed data-refresh run.
- No Intrinsic/Shapley evaluation was executed.
- Frozen Forecast candidate and settled Intrinsic/Shapley architecture were not modified.

**STOP.** This checkpoint establishes the new governed downstream Year-1 coordinate only. Do not run Intrinsic/Shapley or inspect final downstream rankings without a new management authorization.
"""
    (dest / "CHECKPOINT.md").write_text(checkpoint, encoding="utf-8")

    print(checkpoint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

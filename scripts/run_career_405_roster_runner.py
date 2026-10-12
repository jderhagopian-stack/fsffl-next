"""Nonproduction roster-only Career P0/Shapley runner for GitHub Actions.

The input is a ZIP supplied through a repository Actions secret. The database is
opened read-only to resolve the latest persisted exact State. Results are
encrypted before they can be uploaded from this public repository.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
import zipfile

from fsffl.persistence.state_history import PostgresStateSnapshotStore

STATE_NAMES = ("out", "depth", "usable", "starter", "premium", "elite")
MAX_INPUT_BYTES = 2_000_000


def decode_private_input(encoded_zip: str) -> tuple[dict, bytes]:
    if not encoded_zip:
        raise ValueError("missing CAREER_ROSTER_P0_ZIP_B64 Actions secret")
    try:
        archive_bytes = base64.b64decode(encoded_zip, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("CAREER_ROSTER_P0_ZIP_B64 is not valid base64") from exc
    if len(archive_bytes) > MAX_INPUT_BYTES:
        raise ValueError("private roster input exceeds the 2 MB safety limit")
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        if len(files) != 1 or files[0].file_size > MAX_INPUT_BYTES:
            raise ValueError("private ZIP must contain one bounded roster JSON file")
        if Path(files[0].filename).name != files[0].filename:
            raise ValueError("private ZIP may not contain directory paths")
        payload_bytes = archive.read(files[0])
    payload = json.loads(payload_bytes)
    if not isinstance(payload, dict) or payload.get("schema_version") != "fsffl-career-roster-p0-checkpoint-v1":
        raise ValueError("private input has an unsupported roster checkpoint schema")
    return payload, payload_bytes


def current_roster_identity(state) -> dict[str, dict[str, str]]:
    positions = {
        str(player.player_id): str(player.position.value)
        for player in state.players
        if str(player.position.value) in {"QB", "RB", "WR", "TE"}
    }
    roster: dict[str, dict[str, str]] = {}
    for team in state.team_states:
        for entry in team.roster:
            player_id = str(entry.player_id)
            if player_id not in positions:
                continue
            if player_id in roster:
                raise ValueError("exact State contains a duplicate roster subject")
            roster[player_id] = {
                "position": positions[player_id],
                "team_id": str(team.team_id),
                "roster_slot": str(entry.slot.value),
            }
    return roster


def validate_exact_roster(artifact: dict, state) -> dict[str, dict]:
    if artifact.get("state_hash") != state.state_id:
        raise ValueError("private roster artifact State hash differs from latest persisted State")
    if str(artifact.get("state_as_of")) != state.as_of.isoformat():
        artifact_time = str(artifact.get("state_as_of", "")).replace("Z", "+00:00")
        state_time = state.as_of.isoformat()
        if artifact_time != state_time:
            raise ValueError("private roster artifact State timestamp differs from latest persisted State")
    rows = artifact.get("players")
    if not isinstance(rows, list) or not rows:
        raise ValueError("private roster checkpoint has no player records")
    roster = current_roster_identity(state)
    indexed = {}
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("player_id", "")).strip():
            raise ValueError("private roster checkpoint contains an invalid player record")
        player_id = str(row["player_id"])
        if player_id in indexed:
            raise ValueError("private roster checkpoint contains duplicate player records")
        exact = roster.get(player_id)
        if exact is None:
            raise ValueError("private roster checkpoint contains a player outside the latest State roster")
        if any(str(row.get(field, "")) != exact[field] for field in exact):
            raise ValueError("private roster checkpoint identity differs from latest State")
        if row.get("state_hash") != state.state_id:
            raise ValueError("player record State hash differs from latest persisted State")
        indexed[player_id] = row
    return indexed


def _future_row(player_id: str, packet: dict) -> dict:
    probabilities = packet.get("probabilities")
    means = packet.get("conditional_means")
    if not isinstance(probabilities, dict) or not isinstance(means, dict):
        raise ValueError("accepted Y2/Y3 packet lacks six-state probabilities or means")
    if set(probabilities) != set(STATE_NAMES) or set(means) != set(STATE_NAMES):
        raise ValueError("accepted Y2/Y3 packet state geometry differs from the contract")
    scenarios = [
        {
            "scenario_id": state,
            "probability": float(probabilities[state]),
            "fantasy_points": float(means[state]),
        }
        for state in STATE_NAMES
    ]
    expectation = sum(item["probability"] * item["fantasy_points"] for item in scenarios)
    supplied_expectation = float(packet["central_expectation"])
    if (
        not all(math.isfinite(item["probability"]) and math.isfinite(item["fantasy_points"]) for item in scenarios)
        or not math.isfinite(supplied_expectation)
        or abs(expectation - supplied_expectation) > 1e-7
    ):
        raise ValueError("accepted Y2/Y3 expectation does not reconcile to its six-state packet")
    return {
        "player_id": player_id,
        "position": str(packet["position"]),
        "year_index": int(packet["year_index"]),
        "target_season": int(packet["target_season"]),
        # The packet's saved point expectation can differ by a few float-rounding
        # ULPs. Canonically recompute it from the accepted six-state distribution.
        "central_expectation": expectation,
        "scoring_coordinate": str(packet["scoring_coordinate"]),
        "model_version": str(packet["model_version"]),
        "source": str(packet["source"]),
        "scenarios": scenarios,
    }


def to_composer_artifact(artifact: dict, exact_rows: dict[str, dict]) -> dict:
    successes: dict[str, dict] = {}
    failures: dict[str, dict] = {}
    year_one: dict[str, dict[str, float]] = {}
    future: list[dict] = []
    for player_id, row in exact_rows.items():
        if row.get("status") == "p0_failure":
            failure = row.get("failure")
            failures[player_id] = failure if isinstance(failure, dict) else {
                "failure_code": "explicit_p0_failure_record_missing",
                "failure_detail": "Saved per-player evidence failure is malformed.",
                "evidence_checked": [],
                "provenance": {},
            }
            continue
        source = row.get("p0_input")
        packets = source.get("p0_canonical_packets") if isinstance(source, dict) else None
        if not isinstance(packets, dict) or not isinstance(packets.get("Y2"), dict) or not isinstance(packets.get("Y3"), dict):
            failures[player_id] = {
                "failure_code": "accepted_future_y2_y3_packet_missing",
                "failure_detail": "Saved P0 input lacks accepted Y2/Y3 six-state packets.",
                "evidence_checked": ["private_rostered_p0_checkpoint"],
                "provenance": row.get("provenance", {}),
            }
            continue
        if packets["Y2"].get("player_id") != player_id or packets["Y3"].get("player_id") != player_id:
            failures[player_id] = {
                "failure_code": "accepted_future_packet_identity_mismatch",
                "failure_detail": "Saved Y2/Y3 packet identity differs from its roster record.",
                "evidence_checked": ["private_rostered_p0_checkpoint"],
                "provenance": row.get("provenance", {}),
            }
            continue
        try:
            future.extend((_future_row(player_id, packets["Y2"]), _future_row(player_id, packets["Y3"])))
            y1 = float(source["league_y1_points"])
            if y1 < 0:
                raise ValueError("negative Year-1 points")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            future = [item for item in future if item["player_id"] != player_id]
            failures[player_id] = {
                "failure_code": "accepted_candidate_input_invalid",
                "failure_detail": f"{type(exc).__name__}: {exc}",
                "evidence_checked": ["private_rostered_p0_checkpoint"],
                "provenance": row.get("provenance", {}),
            }
            continue
        successes[player_id] = {
            "current_player_id": player_id,
            "position": str(row["position"]),
            "connected_league_y1_points": y1,
        }
        year_one[player_id] = {"league": y1}

    if set(successes) | set(failures) != set(exact_rows):
        raise ValueError("roster runner did not account for every input player exactly once")
    return {
        "schema_version": "fsffl.rostered-p0-batch.v1",
        "saved_state_hash": artifact["state_hash"],
        "saved_state_as_of": artifact["state_as_of"],
        "evaluation_as_of": artifact["evaluation_as_of"],
        "candidate_ids": sorted(exact_rows),
        "candidate_source_rows": successes,
        "year_one_points": year_one,
        "future_forecasts": future,
        "failures": failures,
    }


def encrypt_result(payload: bytes, key_b64: str) -> bytes:
    try:
        key = base64.b64decode(key_b64, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("CAREER_RUN_OUTPUT_KEY_B64 is not valid base64") from exc
    if len(key) != 32:
        raise ValueError("CAREER_RUN_OUTPUT_KEY_B64 must decode to 32 bytes")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise RuntimeError("encrypted output requires the cryptography package") from exc
    nonce = os.urandom(12)
    return b"C405AESGCM1" + nonce + AESGCM(key).encrypt(nonce, payload, b"career-405-roster")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--league-id", required=True)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    database_url = os.environ.get("FSFFL_DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("required Actions secret FSFFL_DATABASE_URL is unavailable")
    artifact, artifact_bytes = decode_private_input(os.environ.get("CAREER_ROSTER_P0_ZIP_B64", ""))

    def read_only_connection():
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(
            database_url,
            row_factory=dict_row,
            options="-c default_transaction_read_only=on",
        )

    store = PostgresStateSnapshotStore(database_url, connect_factory=read_only_connection)
    from datetime import datetime, timezone

    state = store.latest_at_or_before(args.league_id, datetime.now(timezone.utc))
    if state is None:
        raise SystemExit("no persisted exact State exists for the configured league")
    exact_rows = validate_exact_roster(artifact, state)
    composer_artifact = to_composer_artifact(artifact, exact_rows)

    temp_input = Path("/tmp/career405-p0-input.json")
    temp_input.write_text(json.dumps(composer_artifact, sort_keys=True, allow_nan=False))
    temp_input.chmod(0o600)
    root = args.source_root.resolve()
    if not (root / "scripts/compose_rostered_p0_expanded_shapley.py").is_file():
        raise SystemExit("selected Career source ref lacks the accepted roster composer")
    sys.path.insert(0, str(root))
    from scripts.compose_rostered_p0_expanded_shapley import compose_saved_rostered_p0

    frozen_board = root / "artifacts/implementation/final_forecast_route_implementation_20260920/FINAL_CONNECTED_LEAGUE_BOARD_335.csv"
    rules = root / "artifacts/implementation/forecast_source_coordinate_20260919/CONNECTED_LEAGUE_RULES.json"
    # The semantic fixture archive is sanitized and committed to the repository.
    import base64 as b64
    import tempfile

    fixture_zip = root / "tests/fixtures/career_coverage/frozen_335_numeric_reference.zip.b64"
    with tempfile.TemporaryDirectory(prefix="career405-reference-") as tmpdir:
        archive = Path(tmpdir) / "frozen.zip"
        archive.write_bytes(b64.b64decode(fixture_zip.read_bytes()))
        with zipfile.ZipFile(archive) as zf:
            zf.extract("SHAPLEY_CURRENT_BOARD_335.csv", tmpdir)
        frozen_shapley = Path(tmpdir) / "SHAPLEY_CURRENT_BOARD_335.csv"
        result = compose_saved_rostered_p0(
            artifact_path=temp_input,
            frozen_board_path=frozen_board,
            frozen_shapley_path=frozen_shapley,
            rules_path=rules,
        )
    result["explicit_p0_failures"] = composer_artifact["failures"]
    result["input_sha256"] = hashlib.sha256(artifact_bytes).hexdigest()
    result["current_state_as_of"] = state.as_of.isoformat()
    result["current_state_hash"] = state.state_id
    result["run_source_ref"] = os.environ.get("CAREER_CODE_REF", "")
    result["run_source_sha"] = os.environ.get("CAREER_CODE_SHA", "")
    result["provider_acquisition_performed"] = False
    result["production_write_performed"] = False
    plaintext = (json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    output_key = os.environ.get("CAREER_RUN_OUTPUT_KEY_B64", "")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encrypt_result(plaintext, output_key))
    args.output.chmod(0o600)
    print(json.dumps({
        "roster_player_count": len(exact_rows),
        "supported_shapley_count": result["candidate_count"],
        "explicit_failure_count": len(result["explicit_p0_failures"]),
        "frozen_335_max_delta": result["frozen_base_max_abs_component_delta"],
        "input_sha256": result["input_sha256"],
        "state_hash": state.state_id,
        "state_as_of": state.as_of.isoformat(),
        "encrypted_output": str(args.output),
        "provider_acquisition_performed": False,
        "production_write_performed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()

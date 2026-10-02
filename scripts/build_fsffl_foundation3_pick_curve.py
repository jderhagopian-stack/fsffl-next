from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from fsffl.state.models import LeagueRules
from fsffl.value.calibration import CalibrationPanel
from fsffl.value.historical_draft_value import (
    HistoricalDraftSelection,
    HistoricalDraftValuePolicy,
    freeze_historical_draft_values,
)
from fsffl.value.historical_pick import (
    build_governed_draft_slot_value_curve,
)
from fsffl.value.historical_pick_evidence import build_draft_slot_observations
from fsffl.value.models import ValueScale
from fsffl.value.sources import normalize_dynastyprocess_values


SLEEPER_BASE = "https://api.sleeper.app/v1"
DYNASTYPROCESS_REPO = "https://github.com/dynastyprocess/data.git"
VALUES_PATH = "files/values.csv"
PLAYER_IDS_PATH = "files/db_playerids.csv"
SOURCE_ID = "dynastyprocess_market_values"
FORMAT_CONTEXT_ID = "dynasty:2qb"
SCALE = ValueScale(
    scale_id="dynastyprocess-2qb-pit",
    version="foundation3-v1",
    unit_label="DynastyProcess 2QB value units",
)


def _json(url: str):
    request = Request(url, headers={"User-Agent": "fsffl-next-foundation3/1.0"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - governed public API
        return json.loads(response.read().decode("utf-8"))


def _league(league_id: str) -> dict[str, object]:
    payload = _json(f"{SLEEPER_BASE}/league/{league_id}")
    if not isinstance(payload, dict) or not payload.get("league_id"):
        raise RuntimeError(f"Sleeper league lookup failed for {league_id}")
    return payload


def _league_chain(current_league_id: str) -> dict[int, dict[str, object]]:
    by_season: dict[int, dict[str, object]] = {}
    seen: set[str] = set()
    league_id = current_league_id
    while league_id and league_id != "0" and league_id not in seen:
        seen.add(league_id)
        row = _league(league_id)
        season = int(row["season"])
        by_season[season] = row
        league_id = str(row.get("previous_league_id") or "")
    return by_season


def _rookie_draft(league_id: str, *, rookie_rounds: int) -> dict[str, object]:
    payload = _json(f"{SLEEPER_BASE}/league/{league_id}/drafts")
    candidates = [
        row
        for row in payload
        if isinstance(row, dict)
        and row.get("status") == "complete"
        and int((row.get("settings") or {}).get("rounds") or 0) == rookie_rounds
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected exactly one completed {rookie_rounds}-round rookie draft "
            f"for league {league_id}; found {len(candidates)}"
        )
    return candidates[0]


def _draft_selections(
    draft: dict[str, object],
    *,
    season: int,
    team_count: int,
    rookie_rounds: int,
) -> tuple[HistoricalDraftSelection, ...]:
    draft_id = str(draft["draft_id"])
    start_ms = int(draft.get("start_time") or 0)
    if start_ms <= 0:
        raise RuntimeError(f"Sleeper draft {draft_id} lacks start_time")
    boundary = datetime.fromtimestamp(start_ms / 1000, tz=UTC)
    picks = _json(f"{SLEEPER_BASE}/draft/{draft_id}/picks")
    rows: list[HistoricalDraftSelection] = []
    for pick in picks:
        if not isinstance(pick, dict):
            continue
        round_number = int(pick.get("round") or 0)
        if not 1 <= round_number <= rookie_rounds:
            continue
        pick_no = int(pick.get("pick_no") or 0)
        player_id = str(pick.get("player_id") or "").strip()
        if pick_no <= 0 or not player_id:
            raise RuntimeError(f"Sleeper draft {draft_id} has incomplete rookie pick")
        slot = ((pick_no - 1) % team_count) + 1
        rows.append(
            HistoricalDraftSelection(
                draft_season=season,
                round=round_number,
                slot_in_round=slot,
                player_id=player_id,
                selected_at=boundary,
                provenance=(
                    f"Sleeper completed rookie draft {draft_id}; values frozen at "
                    f"draft start {boundary.isoformat()}"
                ),
            )
        )
    expected = team_count * rookie_rounds
    if len(rows) != expected:
        raise RuntimeError(
            f"Sleeper rookie draft {draft_id} expected {expected} selections; "
            f"found {len(rows)}"
        )
    keys = {(row.round, row.slot_in_round) for row in rows}
    if len(keys) != expected:
        raise RuntimeError(f"Sleeper rookie draft {draft_id} has duplicate round/slot")
    return tuple(sorted(rows, key=lambda item: (item.round, item.slot_in_round)))


def _run(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _ensure_dynastyprocess_repo(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    subprocess.run(
        ["git", "clone", "--filter=blob:none", "--no-checkout", DYNASTYPROCESS_REPO, str(path)],
        check=True,
    )
    return path


def _crosswalk(repo: Path) -> dict[str, str]:
    text = _run(repo, "show", f"origin/master:{PLAYER_IDS_PATH}")
    reader = csv.DictReader(text.splitlines())
    fields = set(reader.fieldnames or ())
    fp_column = (
        "fantasypros_id"
        if "fantasypros_id" in fields
        else "fp_id"
        if "fp_id" in fields
        else None
    )
    if fp_column is None or "sleeper_id" not in fields:
        raise RuntimeError(
            "DynastyProcess player-id file lacks fantasypros_id/fp_id + sleeper_id"
        )
    result: dict[str, str] = {}
    for row in reader:
        fp_id = str(row.get(fp_column) or "").strip()
        sleeper_id = str(row.get("sleeper_id") or "").strip()
        if fp_id and fp_id.upper() != "NA" and sleeper_id and sleeper_id.upper() != "NA":
            result[fp_id] = sleeper_id
    if not result:
        raise RuntimeError("DynastyProcess player-id crosswalk produced no usable rows")
    return result


def _snapshot_before(repo: Path, boundary: datetime) -> tuple[str, str]:
    before = boundary.astimezone(UTC).isoformat()
    sha = _run(
        repo,
        "log",
        "-1",
        "--format=%H",
        f"--before={before}",
        "--",
        VALUES_PATH,
    ).strip()
    if not sha:
        raise RuntimeError(f"no DynastyProcess values snapshot before {before}")
    return sha, _run(repo, "show", f"{sha}:{VALUES_PATH}")


def _curve_payload(curve) -> dict[str, object]:
    return {
        "round": curve.round,
        "as_of": curve.as_of.isoformat(),
        "scale": curve.scale.model_dump(mode="json"),
        "model_version": curve.model_version,
        "slots": [row.model_dump(mode="json") for row in curve.slots],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build retained FSFFL exact-slot pick economics through the Historical Pick Coordinate pipeline."
    )
    parser.add_argument("--league-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-season", type=int, default=2023)
    parser.add_argument("--max-season", type=int, default=2026)
    parser.add_argument("--rookie-rounds", type=int, default=3)
    parser.add_argument("--max-observation-age-days", type=int, default=14)
    parser.add_argument("--dynastyprocess-repo", type=Path, default=None)
    args = parser.parse_args()

    if args.min_season > args.max_season:
        raise ValueError("min-season cannot exceed max-season")
    if args.rookie_rounds < 1:
        raise ValueError("rookie-rounds must be positive")

    chain = _league_chain(args.league_id)
    current = chain[max(chain)]
    team_count = int(current.get("total_rosters") or 0)
    if team_count < 2:
        raise RuntimeError("Sleeper league total_rosters is unavailable")
    roster_size = len(current.get("roster_positions") or ()) or 1
    rules = LeagueRules(
        team_count=team_count,
        roster_size=roster_size,
        rookie_draft_rounds=args.rookie_rounds,
        lineup=(),
        scoring=(),
    )

    seasons = [
        season
        for season in sorted(chain)
        if args.min_season <= season <= args.max_season
    ]
    if not seasons:
        raise RuntimeError("no FSFFL seasons matched requested evidence window")

    selections: list[HistoricalDraftSelection] = []
    draft_records: list[dict[str, object]] = []
    for season in seasons:
        league = chain[season]
        draft = _rookie_draft(
            str(league["league_id"]),
            rookie_rounds=args.rookie_rounds,
        )
        season_rows = _draft_selections(
            draft,
            season=season,
            team_count=team_count,
            rookie_rounds=args.rookie_rounds,
        )
        selections.extend(season_rows)
        draft_records.append(
            {
                "season": season,
                "league_id": str(league["league_id"]),
                "draft_id": str(draft["draft_id"]),
                "draft_start": season_rows[0].selected_at.isoformat(),
                "selection_count": len(season_rows),
            }
        )

    temp_root = None
    if args.dynastyprocess_repo is None:
        temp_root = tempfile.TemporaryDirectory(prefix="fsffl-foundation3-")
        dp_repo = Path(temp_root.name) / "dynastyprocess-data"
        _ensure_dynastyprocess_repo(dp_repo)
    else:
        dp_repo = args.dynastyprocess_repo
    try:
        fp_to_sleeper = _crosswalk(dp_repo)
        panel_rows = []
        source_snapshots: list[dict[str, object]] = []
        for record in draft_records:
            boundary = datetime.fromisoformat(str(record["draft_start"]))
            sha, csv_text = _snapshot_before(dp_repo, boundary)
            normalized = normalize_dynastyprocess_values(
                csv_text,
                asset_id_by_fp_id=fp_to_sleeper,
                source_version=sha,
                provenance_uri=f"github:dynastyprocess/data@{sha}:{VALUES_PATH}",
            )
            two_qb_rows = tuple(
                row
                for row in normalized.observations
                if row.format_context_id == FORMAT_CONTEXT_ID
            )
            panel_rows.extend(two_qb_rows)
            source_snapshots.append(
                {
                    "season": record["season"],
                    "draft_start": record["draft_start"],
                    "commit": sha,
                    "observation_count_2qb": len(two_qb_rows),
                    "snapshot_observed_at": (
                        max(row.observed_at for row in two_qb_rows).isoformat()
                        if two_qb_rows
                        else None
                    ),
                    "rows_seen": normalized.rows_seen,
                    "rows_imported": normalized.rows_imported,
                    "rows_unmapped": normalized.rows_unmapped,
                }
            )

        if not panel_rows:
            raise RuntimeError("retained DynastyProcess evidence produced no 2QB observations")
        panel = CalibrationPanel(
            observations=tuple(panel_rows),
            as_of=max(row.observed_at for row in panel_rows),
            panel_version="foundation3-fsffl-dynastyprocess-pit-v1",
        )
        policy = HistoricalDraftValuePolicy(
            source_ids=(SOURCE_ID,),
            metric="market_value",
            scale=SCALE,
            format_context_id=FORMAT_CONTEXT_ID,
            max_observation_age_days=args.max_observation_age_days,
            model_version="foundation3-fsffl-historical-draft-freeze-v1",
            provenance=(
                "DynastyProcess 2QB point-in-time player value frozen before each "
                "completed FSFFL rookie draft; weekly public git history"
            ),
        )
        frozen = freeze_historical_draft_values(
            selections=tuple(selections),
            panel=panel,
            policy=policy,
            as_of=max(row.selected_at for row in selections),
        )
        observations = build_draft_slot_observations(
            frozen.values,
            league_rules=rules,
            as_of=max(row.selected_at for row in selections),
        )

        curve_as_of = datetime.now(UTC)
        curves = tuple(
            build_governed_draft_slot_value_curve(
                observations,
                round=round_number,
                as_of=curve_as_of,
                scale=SCALE,
                league_rules=rules,
            )
            for round_number in range(1, args.rookie_rounds + 1)
        )
        missing_slots_by_round = {
            str(curve.round): [
                slot
                for slot in range(1, team_count + 1)
                if curve.value_for_slot(slot) is None
            ]
            for curve in curves
        }
        payload = {
            "schema_version": "foundation3-fsffl-pick-slot-evidence-v1",
            "generated_at": curve_as_of.isoformat(),
            "current_league_id": args.league_id,
            "league_name": current.get("name"),
            "team_count": team_count,
            "rookie_draft_rounds": args.rookie_rounds,
            "evidence_seasons_requested": seasons,
            "source": {
                "source_id": SOURCE_ID,
                "format_context_id": FORMAT_CONTEXT_ID,
                "scale": SCALE.model_dump(mode="json"),
                "rights_class": "research_only",
                "repository": DYNASTYPROCESS_REPO,
                "values_path": VALUES_PATH,
                "player_ids_path": PLAYER_IDS_PATH,
                "max_observation_age_days": args.max_observation_age_days,
            },
            "drafts": draft_records,
            "source_snapshots": source_snapshots,
            "selection_count": len(selections),
            "frozen_value_count": len(frozen.values),
            "missing_player_ids": list(frozen.missing_player_ids),
            "stale_player_ids": list(frozen.stale_player_ids),
            "slot_observation_count": len(observations),
            "curves": [_curve_payload(curve) for curve in curves],
            "missing_slots_by_round": missing_slots_by_round,
            "full_curve_supported": all(
                not missing for missing in missing_slots_by_round.values()
            ),
            "pipeline": [
                "Sleeper completed rookie-draft selections",
                "DynastyProcess pre-draft 2QB PIT snapshot",
                "freeze_historical_draft_values",
                "build_draft_slot_observations",
                "build_governed_draft_slot_value_curve",
            ],
            "no_broad_market_pick_variants_used": True,
            "no_class_strength_adjustment_used": True,
            "no_horizon_adjustment_used": True,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(
            "Foundation 3 FSFFL exact-slot evidence: "
            f"seasons={seasons} selections={len(selections)} "
            f"frozen={len(frozen.values)} missing={len(frozen.missing_player_ids)} "
            f"stale={len(frozen.stale_player_ids)} full={payload['full_curve_supported']}"
        )
        for curve in curves:
            means = ", ".join(
                f"{row.slot_in_round}:{row.value.mean:.2f}" for row in curve.slots
            )
            print(f"round {curve.round}: {means}")
        if not payload["full_curve_supported"]:
            raise SystemExit(2)
    finally:
        if temp_root is not None:
            temp_root.cleanup()


if __name__ == "__main__":
    main()

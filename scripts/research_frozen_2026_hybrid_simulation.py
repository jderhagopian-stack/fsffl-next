"""2026 Sept-4 source-frozen hybrid: run CURRENT FSFFL NEXT Simulation 2.0.

Research only. This is NOT a modern Forecast/Intrinsic replay:
- Historical Sleeper State and legacy preseason Forecast inputs are fetched
  from a *public, immutable, before-kickoff* Git commit with fixed blob hashes.
- Today's accepted NEXT-4 simulator provides the competitive outcome model.
- External projection terms in the legacy input are PERSONAL_RESEARCH only.
- No Supabase/Render network, no writes to user runtime, no live provider fetch,
  no training on 2026 outcomes, no change to accepted model authority.

An emitted title probability is a HYBRID RESEARCH result, NOT a fully modern
almanac-grade model prediction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from urllib.error import HTTPError, URLError
from datetime import UTC, datetime
from math import sqrt
from pathlib import Path
from urllib.request import Request, urlopen

from fsffl.providers.acquisition import ProviderSnapshot
from fsffl.providers.sleeper_snapshot import SleeperSnapshotNormalizer
from fsffl.forecast.models import (
    ForecastDistribution, ForecastHorizon, ForecastMetric, ForecastObservation,
)
from fsffl.state.models import Provenance, Position
from fsffl.product.simulation_runtime import build_live_simulation_analytics
from fsffl.team_utility.simulation import NUMPY_PCG64_BATCHED_GAUSS_V1
from research_2026_sept9_reconstruction import AS_OF as SEPT9_AS_OF, reconstruct_sept9_sources


ARCHIVE_REPOSITORY = "jderhagopian-stack/sleeper-league-data"
ARCHIVE_COMMIT = "72c926cdcf9450d1ba1dcb53f67d698851b54cfb"
ARCHIVE_CAPTURE = datetime(2026, 9, 4, 15, 23, 53, tzinfo=UTC)
PREGAME_CUTOFF = datetime(2026, 9, 10, 0, 20, tzinfo=UTC)
LEAGUE_EXTERNAL_ID = "1312071960615731200"
# Git object SHA1 *hash of blob*, not SHA256 of bytes.
PINNED_BLOBS = {
    "data/league.json": "07b25de4b1b3e4ccca691b78a4716149f07371cd",
    "data/rosters.json": "d9d153751da68ed10cc1a2fe2555d454f2733033",
    "data/users.json": "fc95681aa14102b1453f93d58570608b0f7a29dc",
    "data/players.json": "c751359031d7feeadab78e86a6b274c29e48d878",
    "data/traded_picks.json": "1cd900618f7705ca2d30fd6b65ac8cbadb5da799",
    "data/nfl_state.json": "d57612666d8aa35b72f222fab67e333f7ea46c58",
    "data/stats/fsffl/2026/league_matchups_raw.json": "02cbb15709b9aa5c8f884fe0cd6bdda0724e04aa",
    "data/simulator/2026/sources/nfl_schedule.json": "a19cb1c00b7fb0ae1611bf34b417ab8b02288837",
    "data/simulator/2026/sources/preseason_fsffl_points.json": "619ac3751560d616882b566dc9910c0815289f76",
    "data/simulator/2026/inputs/player_weekly_projections.json": "3a031c330cf9e41d326c044ba8a2bcbf9d0aefb9",
}
SOURCE_LIMIT_BYTES = 7_000_000

# Audited separately published pre-kickoff correction. The Sep-4 Git snapshot
# retained an NFL team field that was already stale on Aug 30. Publication
# date is the evidence-availability clock; this record was recovered later.
# This exceptional personal-research correction MUST NOT be generalized to
# unverified current player statuses.
PREKICKOFF_TEAM_CORRECTIONS = (
    {
        "player_id": "sleeper:player:12504", "full_name": "Kaleb Johnson",
        "expected_stale_team": "PIT", "verified_team": "GB",
        "publicly_effective_at": "2026-08-30T23:59:59Z",
        "source_url": "https://www.packers.com/news/packers-announce-roster-moves-aug-30-2026",
        "source_kind": "dated_original_club_announcement",
    },
)


def apply_dated_pregame_player_corrections(state):
    """Update only publicly dated pre-kickoff facts, keeping lineage explicit."""
    players = {p.player_id: p for p in state.players}
    statuses = {p.player_id: p for p in state.player_states}
    applied = []
    for correction in PREKICKOFF_TEAM_CORRECTIONS:
        pid = correction["player_id"]
        player, old_status = players.get(pid), statuses.get(pid)
        if player is None or old_status is None:
            raise ValueError(f"dated source correction subject not present: {pid}")
        evidence_at = datetime.fromisoformat(correction["publicly_effective_at"].replace("Z","+00:00"))
        if evidence_at > state.as_of or evidence_at > PREGAME_CUTOFF:
            raise ValueError("correction did not exist by historical preseason cutoff")
        if player.nfl_team != correction["expected_stale_team"]:
            raise ValueError("source correction's original historical team no longer matches")
        # Provenance reports real retrospective retrieval rather than backdating
        # the recovered web record. Only its published fact is pre-cutoff.
        recovered = datetime.now(UTC)
        prov = Provenance(
            source=correction["source_url"],
            retrieved_at=recovered, effective_at=evidence_at,
        )
        players[pid] = player.model_copy(update={"nfl_team": correction["verified_team"]})
        statuses[pid] = old_status.model_copy(update={
            "nfl_team": correction["verified_team"], "provenance": prov,
        })
        applied.append({
            "player_id":pid, "name":correction["full_name"],
            "from":correction["expected_stale_team"], "to":correction["verified_team"],
            "source_kind":correction["source_kind"],
            "published_at":correction["publicly_effective_at"],
            "source_url":correction["source_url"],
            "retrospective_recovery":True,
        })
    return state.model_copy(update={
        "players":tuple(sorted(players.values(),key=lambda p:p.player_id)),
        "player_states":tuple(sorted(statuses.values(),key=lambda p:p.player_id)),
    }),applied



def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_pinned_sources() -> dict[str, object]:
    """Fetch once per offline research job; verify each cached byte string every use.

    Cache is optional, scratch-only and never committed. No cache trust:
    source bytes are hash-checked on both fetch and reuse. Retry only
    temporary fetch errors with a bounded, short backoff.
    """
    if ARCHIVE_CAPTURE >= PREGAME_CUTOFF:
        raise ValueError("historical source revision does not predate opening kickoff")
    root = os.getenv("FSFFL_HISTORICAL_SOURCE_CACHE_DIR", "").strip()
    cache_dir = Path(root) if root else None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for path, sha in PINNED_BLOBS.items():
        cached = cache_dir / path if cache_dir is not None else None
        if cached is not None and cached.exists():
            if cached.stat().st_size > SOURCE_LIMIT_BYTES:
                raise ValueError(f"historical cache exceeds bounded limit: {path}")
            raw = cached.read_bytes()
        else:
            url = f"https://raw.githubusercontent.com/{ARCHIVE_REPOSITORY}/{ARCHIVE_COMMIT}/{path}"
            req = Request(url, headers={"User-Agent": "fsffl-historical-offline-research/1"})
            raw = None
            for attempt in range(3):
                try:
                    with urlopen(req, timeout=45) as response:
                        raw = response.read(SOURCE_LIMIT_BYTES + 1)
                    break
                except (HTTPError, URLError) as exc:
                    code = getattr(exc, "code", None)
                    if attempt == 2 or (code is not None and code not in (429, 500, 502, 503, 504)):
                        raise
                    time.sleep(2 * (attempt + 1))
            if raw is None:
                raise ValueError(f"historical fetch did not return source: {path}")
        if len(raw) > SOURCE_LIMIT_BYTES:
            raise ValueError(f"archived source exceeds bounded size: {path}")
        actual = _git_blob_sha1(raw)
        if actual != sha:
            raise ValueError(f"source content hash mismatch at {path}: {actual}")
        if cached is not None and not cached.exists():
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(raw)
        results[path] = json.loads(raw)
    return results


def _load_issued(raw: object, *, description: str) -> datetime:
    if not isinstance(raw, str):
        raise ValueError(f"source clock missing for {description}")
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt > ARCHIVE_CAPTURE:
        raise ValueError(f"source date is not at or before archival commit: {description}")
    return dt


def assemble_vintage_state_and_forecasts(source: dict, *, state_as_of: datetime = ARCHIVE_CAPTURE):
    """Use the accepted provider normalizer; no hand-created fantasy roster truth."""
    league = source["data/league.json"]
    if league.get("league_id") != LEAGUE_EXTERNAL_ID or int(league.get("season") or 0) != 2026:
        raise ValueError("archive does not describe the intended historical league")
    schedule = source["data/simulator/2026/sources/nfl_schedule.json"]
    if schedule.get("season") != 2026 or schedule.get("regular_season_game_count") != 272:
        raise ValueError("preseason NFL schedule evidence is incomplete")
    _load_issued(schedule.get("generated_at_utc"), description="NFL schedule")
    fantasy = source["data/simulator/2026/sources/preseason_fsffl_points.json"]
    weekly = source["data/simulator/2026/inputs/player_weekly_projections.json"]
    issued = _load_issued(fantasy.get("generated_at_utc"), description="legacy projections")
    if fantasy.get("governance", {}).get("production_scope") != "PRIVATE_PERSONAL_FSFFL_ONLY":
        raise ValueError("legacy preseason source rights changed; confirm before use")
    if weekly.get("season") != "2026" and weekly.get("season") != 2026:
        raise ValueError("weekly fantasy projection season mismatch")
    if fantasy.get("season") not in (2026, "2026"):
        raise ValueError("legacy source is not the 2026 preseason set")
    payload = {
        "league": league,
        "rosters": source["data/rosters.json"],
        "users": source["data/users.json"],
        "players": source["data/players.json"],
        "traded_picks": source["data/traded_picks.json"],
        "nfl_state": source["data/nfl_state.json"],
        "matchups": source["data/stats/fsffl/2026/league_matchups_raw.json"],
        "nfl_schedule": schedule["games"],
    }
    state = SleeperSnapshotNormalizer(include_unrostered_players=False).normalize_snapshot(
        ProviderSnapshot(provider_name="sleeper", league_external_id=LEAGUE_EXTERNAL_ID,
                         captured_at=ARCHIVE_CAPTURE, payload=payload),
        as_of=state_as_of,
    )
    state,dated_corrections = apply_dated_pregame_player_corrections(state)
    if len(state.teams) != 12 or len(state.nfl_team_byes) != 32:
        raise ValueError("canonical league or NFL schedule normalization incomplete")
    if state.completed_through_week not in (None, 0):
        raise ValueError("preseason snapshot was polluted by completed NFL weeks")
    if not state.matchups or len(state.matchups) != 84:
        raise ValueError(f"requires 84 scheduled fantasy games, found {len(state.matchups)}")
    if any(m.team_a_points is not None or m.team_b_points is not None for m in state.matchups):
        # Exact archived pregame raw matchup rows can legitimately carry 0s;
        # but the canonical State must be score-free before any simulation.
        raise ValueError("archived provider State exposed scored fantasy matchups")

    all_players = {p.player_id: p for p in state.players}
    provenance = Provenance(
        source=f"legacy-fsffl:sha:{ARCHIVE_COMMIT}:preseason-projection",
        retrieved_at=ARCHIVE_CAPTURE, effective_at=issued,
    )
    rows = []
    coverage = {"raw_projection_rows": len(fantasy["players"]),
                "usable_direct_forecasts": 0, "not_in_canonical_state": 0,
                "missing_weekly_uncertainty": 0}
    for sleeper_id, row in sorted(fantasy["players"].items()):
        pid = f"sleeper:player:{sleeper_id}"
        p = all_players.get(pid)
        if p is None or p.position.value not in {"QB", "RB", "WR", "TE"}:
            coverage["not_in_canonical_state"] += 1
            continue
        weekly_row = weekly["players"].get(sleeper_id)
        if not isinstance(weekly_row, dict):
            coverage["missing_weekly_uncertainty"] += 1
            continue
        # Explicit research bridge, NOT claimed modern Forecast uncertainty.
        # Old preseason file retained game-level SD; independent 17-game
        # aggregation is supplied only to validate typed Forecast input.
        eligible_games = [v for v in weekly_row.get("weeks", {}).values()
                          if isinstance(v, dict) and not v.get("is_bye")
                          and float(v.get("active_probability", 0)) > 0
                          and v.get("sd") is not None]
        if not eligible_games:
            coverage["missing_weekly_uncertainty"] += 1
            continue
        game_sd = sum(float(g["sd"]) for g in eligible_games) / len(eligible_games)
        mean = float(row["fsffl_projected_points"])
        if mean < 0 or game_sd < 0:
            raise ValueError("legacy forecast contains negative projection or uncertainty")
        rows.append(ForecastObservation(
            player_id=pid, position=p.position,
            horizon=ForecastHorizon.SEASON,
            metric=ForecastMetric.FANTASY_POINTS,
            period_start=datetime(2026, 9, 1, tzinfo=UTC),
            period_end=datetime(2027, 3, 1, tzinfo=UTC),
            distribution=ForecastDistribution(mean=mean, stddev=sqrt(17) * game_sd),
            source="legacy-fsffl:preseason-points:provisional-personal-research",
            model_version=f"historical-legacy-ensemble:commit:{ARCHIVE_COMMIT}",
            as_of=ARCHIVE_CAPTURE,
            provenance=provenance,
        ))
    coverage["usable_direct_forecasts"] = len(rows)
    if len(rows) < 200:
        raise ValueError("preseason personal-use source coverage too small")
    # Modern current-runner may supply governed explicit same-position floor
    # forecasts for rostered players who never received direct projections.
    coverage["dated_source_corrections"] = dated_corrections
    return state, tuple(rows), coverage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--trials", type=int, default=50_000)
    parser.add_argument("--vintage", choices=("sept4", "sept9"), default="sept4")
    args = parser.parse_args()
    if args.trials < 1000 or args.trials > 50_000:
        raise ValueError("trials must be 1,000 to 50,000 for bounded research")
    source = load_pinned_sources()
    sept9_receipt = None
    state_date = ARCHIVE_CAPTURE
    if args.vintage == "sept9":
        source, sept9_receipt = reconstruct_sept9_sources(source)
        state_date = SEPT9_AS_OF
    state, forecasts, coverage = assemble_vintage_state_and_forecasts(source, state_as_of=state_date)
    rostered = {x.player_id for t in state.team_states for x in t.roster}
    direct = len(rostered & {f.player_id for f in forecasts})
    meta = {
        "status": "source_frozen_modern_simulation_legacy_forecast_hybrid_research",
        "publication_ready": False,
        "source_revision": ARCHIVE_COMMIT,
        "source_capture_utc": ARCHIVE_CAPTURE.isoformat(),
        "state_as_of": state_date.isoformat(),
        "state_vintage": args.vintage,
        "reconstruction_receipt": sept9_receipt,
        "historical_cutoff_utc": PREGAME_CUTOFF.isoformat(),
        "source_blob_shas": PINNED_BLOBS,
        "source_rights": "legacy_personal_research_only_not_commercial_release",
        "model_boundary": "today_SIMULATION_2.0_on_2026_09_03_legacy_preseason_projection",
        "state": {"teams": len(state.teams), "rostered_players": len(rostered),
                  "fantasy_matchups": len(state.matchups), "nfl_byes": len(state.nfl_team_byes),
                  "future_pick_owners": len(state.pick_ownership),
                  "completed_through_week": state.completed_through_week},
        "coverage": {**coverage,"direct_rostered":direct,
                     "rostered_missing_direct":len(rostered)-direct},
    }
    if args.validate_only:
        args.output.write_text(json.dumps(meta, indent=2)+"\n")
        print("SOURCE_PREFLIGHT_OK", json.dumps(meta["state"]),json.dumps(meta["coverage"]))
        return
    result = build_live_simulation_analytics(
        state, forecasts=forecasts,
        forecast_model_version="legacy-2026-preseason-ensemble-hybrid-research",
        forecast_as_of=ARCHIVE_CAPTURE,
        simulation_count=args.trials, seed=20260905,
        rng_protocol=NUMPY_PCG64_BATCHED_GAUSS_V1, rng_batch_size=500,
    )
    v = result.league_view
    simulation = result.simulation_result
    totals = {o.team_id:o for o in simulation.outcomes}
    ranking=[]
    for t in v.teams:
        o=totals[t.team_id]
        ranking.append({
            "team_id":t.team_id,"provider_display_name":t.display_name,
            "expected_wins":o.expected_wins,"playoff_probability":o.playoff_probability,
            "championship_probability":o.championship_probability,
            "projected_points":t.optimized_expected_points,
        })
    ranking.sort(key=lambda x:(-x["expected_wins"],x["team_id"]))
    meta["simulation"]={
        "trials":simulation.simulation_count,
        "model_version":simulation.model_version,
        "seed":simulation.seed,
        "rankings":ranking,
        "warnings":[{"code":w.code,"message":w.message} for w in v.context.warnings],
    }
    if abs(sum(x["expected_wins"] for x in ranking)-84)>0.1:
        raise ValueError("league expected win mass invalid")
    if any(x["championship_probability"] is None for x in ranking):
        raise ValueError("league champion simulation not supported; no reported title probabilities")
    if abs(sum(x["championship_probability"] for x in ranking)-1)>0.001:
        raise ValueError("championship probability mass invalid")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+"\n")
    print("HYBRID_MODERN_SIMULATION_COMPLETED",simulation.simulation_count)
    for i,x in enumerate(ranking,1):
        print(f"{i:2d} {x['team_id'].rsplit(':',1)[-1]:>2} "
              f"W={x['expected_wins']:.2f} PO={x['playoff_probability']:.1%} "
              f"CH={x['championship_probability']:.1%}")


if __name__=="__main__":
    main()

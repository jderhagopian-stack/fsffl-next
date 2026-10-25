from __future__ import annotations

"""Build the season-scoped live evidence artifact for the frozen QB career-state model.

This is an offline build step. It uses only nflverse football/draft identity data and
writes the prior-season role features required by the already-validated challenger.
The production runtime consumes the compact artifact and never downloads historical
stats on a request path. Evidence is keyed by GSIS identity; live State preserves
that provider identity from the Sleeper player payload when available.
"""

import argparse
import csv
import json
import urllib.request
from collections import defaultdict
from pathlib import Path

STATS_URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_{season}.csv"
PLAYERS_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
ARTIFACT_VERSION = "qb-career-state-evidence-v1"
MODEL_VERSION = "qb-career-state-logit-v1"


def safe_float(value, default=0.0):
    try:
        if value in (None, "", "NA", "NaN", "nan"):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def download(url: str, path: Path) -> Path:
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "FSFFL-NEXT-offline-artifact/1.0"})
    with urllib.request.urlopen(req, timeout=120) as src, path.open("wb") as dst:
        while chunk := src.read(1024 * 1024):
            dst.write(chunk)
    return path


def rank_percentiles(items: list[tuple[str, float]]) -> dict[str, float]:
    if not items:
        return {}
    ordered = sorted(items, key=lambda x: (x[1], x[0]))
    out: dict[str, float] = {}
    n = len(ordered)
    i = 0
    while i < n:
        j = i + 1
        while j < n and ordered[j][1] == ordered[i][1]:
            j += 1
        rank = (i + j - 1) / 2.0
        pct = (rank + 0.5) / n
        for k in range(i, j):
            out[ordered[k][0]] = pct
        i = j
    return out


def player_metadata(cache: Path) -> dict[str, dict]:
    path = download(PLAYERS_URL, cache / "players.csv")
    by_gsis: dict[str, dict] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            gsis = str(raw.get("gsis_id") or raw.get("player_id") or "").strip()
            if not gsis:
                continue
            pick = safe_float(raw.get("draft_number") or raw.get("draft_pick") or raw.get("draft_overall"), 0.0)
            rnd = safe_float(raw.get("draft_round"), 0.0)
            undrafted = pick <= 0 and rnd <= 0
            if pick <= 0 and rnd > 0:
                pick = min(260.0, (rnd - 1.0) * 32.0 + 16.0)
            pick_pct = 0.0 if undrafted else max(0.0, min(1.0, 1.0 - (pick - 1.0) / 259.0))
            rookie = safe_float(raw.get("rookie_year") or raw.get("rookie_season") or raw.get("entry_year") or raw.get("draft_year"), 0.0)
            by_gsis[gsis] = {
                "draft_pick_pct": pick_pct,
                "rookie_year": int(rookie) if rookie > 0 else None,
                "display_name": str(raw.get("display_name") or raw.get("full_name") or raw.get("football_name") or "").strip(),
            }
    return by_gsis


def season_qb_stats(season: int, cache: Path) -> dict[str, dict[str, float]]:
    path = download(STATS_URL.format(season=season), cache / f"stats_player_reg_{season}.csv")
    rows: dict[str, dict[str, float]] = {}
    max_games = 0.0
    attempts_for_rank: list[tuple[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            pos = str(raw.get("position") or raw.get("position_group") or "").upper()
            if pos != "QB":
                continue
            pid = str(raw.get("player_id") or raw.get("gsis_id") or "").strip()
            if not pid:
                continue
            games = safe_float(raw.get("games"), 0.0)
            attempts = safe_float(raw.get("attempts"), 0.0)
            if games <= 0 and attempts > 0:
                games = 1.0
            rows[pid] = {"games": games, "attempts": attempts}
            max_games = max(max_games, games)
            attempts_for_rank.append((pid, attempts))
    pcts = rank_percentiles(attempts_for_rank)
    for pid, row in rows.items():
        row["games_pct"] = row["games"] / max_games if max_games > 0 else 0.0
        row["opportunity_pct"] = pcts.get(pid, 0.0)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation-season", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args()
    evaluation_season = args.evaluation_season
    prior_season = evaluation_season - 1
    metadata = player_metadata(args.cache)

    established_count: defaultdict[str, int] = defaultdict(int)
    prior2: dict[str, dict[str, float]] = {}
    prior1: dict[str, dict[str, float]] = {}
    for season in range(1999, prior_season + 1):
        rows = season_qb_stats(season, args.cache)
        ranked = sorted(rows.items(), key=lambda kv: (-kv[1].get("attempts", 0.0), kv[0]))
        for pid, row in ranked[:32]:
            if row.get("attempts", 0.0) > 0:
                established_count[pid] += 1
        if season == prior_season - 1:
            prior2 = rows
        if season == prior_season:
            prior1 = rows

    evidence: dict[str, dict] = {}
    for gsis, row in prior1.items():
        prev = prior2.get(gsis)
        opp = float(row.get("opportunity_pct", 0.0))
        games = float(row.get("games_pct", 0.0))
        if prev is None:
            role_mean_2 = opp
            role_vol_2 = 0.0
        else:
            prev_opp = float(prev.get("opportunity_pct", 0.0))
            role_mean_2 = (opp + prev_opp) / 2.0
            role_vol_2 = abs(opp - prev_opp)
        meta = metadata.get(gsis, {})
        rookie_year = meta.get("rookie_year")
        experience = max(0, evaluation_season - int(rookie_year)) if rookie_year else 0
        evidence[gsis] = {
            "display_name": meta.get("display_name", ""),
            "experience": experience,
            "draft_pick_pct": float(meta.get("draft_pick_pct", 0.0)),
            "games_pct": games,
            "opportunity_pct": opp,
            "role_mean_2": role_mean_2,
            "role_vol_2": role_vol_2,
            "qb_established_starter_seasons": float(established_count.get(gsis, 0)),
            "feature_cutoff_season": prior_season,
        }

    payload = {
        "artifact_version": ARTIFACT_VERSION,
        "model_version": MODEL_VERSION,
        "identity_key": "gsis_id",
        "evaluation_season": evaluation_season,
        "feature_cutoff_season": prior_season,
        "sources": {
            "stats": "nflverse stats_player regular-season releases",
            "players": "nflverse players release",
        },
        "player_count": len(evidence),
        "players": dict(sorted(evidence.items())),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "artifact_version": ARTIFACT_VERSION,
        "model_version": MODEL_VERSION,
        "evaluation_season": evaluation_season,
        "feature_cutoff_season": prior_season,
        "player_count": len(evidence),
        "output_bytes": args.output.stat().st_size,
    }, indent=2))
    if len(evidence) < 50:
        raise SystemExit(f"insufficient QB evidence coverage: {len(evidence)}")


if __name__ == "__main__":
    main()

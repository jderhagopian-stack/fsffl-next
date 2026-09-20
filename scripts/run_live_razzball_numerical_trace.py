from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fsffl.forecast.current_normalization import (
    current_snapshot_from_razzball,
    normalize_current_projection_snapshot,
)
from fsffl.forecast.current_runtime import (
    NamedCurrentProjectionFetcher,
    build_current_live_forecasts,
)
from fsffl.forecast.league_scoring import derive_league_fantasy_point_forecasts
from fsffl.forecast.models import ForecastMetric
from fsffl.providers.cbs_live import CBSLiveProjectionSource
from fsffl.providers.current_projection_rows import CurrentProjectionSnapshot
from fsffl.providers.fftoday_live import FFTodayLiveProjectionSource
from fsffl.providers.nfl_fantasy_live import NFLFantasyLiveProjectionSource
from fsffl.providers.razzball_season_live import RazzballSeasonProjectionSource
from fsffl.state.models import (
    League,
    LeagueRules,
    LeagueState,
    Player,
    PlayerState,
    Position,
    Provenance,
    ScoringRule,
    Team,
    TeamState,
)


OUT = Path("artifacts/diagnostics/live_razzball_numerical_trace_20260920")
OUT.mkdir(parents=True, exist_ok=True)

SAMPLE = (
    ("Josh Allen", Position.QB, "BUF"),
    ("Dak Prescott", Position.QB, "DAL"),
    ("Deshaun Watson", Position.QB, "CLE"),
    ("Jahmyr Gibbs", Position.RB, "DET"),
    ("Tony Pollard", Position.RB, "TEN"),
    ("Tyjae Spears", Position.RB, "TEN"),
    ("Puka Nacua", Position.WR, "LAR"),
    ("CeeDee Lamb", Position.WR, "DAL"),
    ("Matthew Golden", Position.WR, "GB"),
    ("Brock Bowers", Position.TE, "LV"),
    ("Kyle Pitts", Position.TE, "ATL"),
    ("Dallas Goedert", Position.TE, "PHI"),
)

STAT_TO_METRIC = {
    "pass_yd": "pass_yards",
    "pass_td": "pass_td",
    "pass_int": "interceptions",
    "rush_yd": "rush_yards",
    "rush_td": "rush_td",
    "rec": "receptions",
    "rec_yd": "rec_yards",
    "rec_td": "rec_td",
    "fum_lost": "fumbles_lost",
}

SCORING = (
    ScoringRule(stat="pass_yd", points=0.04),
    ScoringRule(stat="pass_td", points=4.0),
    ScoringRule(stat="pass_int", points=-2.0),
    ScoringRule(stat="rush_yd", points=0.1),
    ScoringRule(stat="rush_td", points=6.0),
    ScoringRule(stat="rec", points=0.5),
    ScoringRule(stat="rec_yd", points=0.1),
    ScoringRule(stat="rec_td", points=6.0),
    ScoringRule(stat="fum_lost", points=-2.0),
)


def key_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def build_state() -> LeagueState:
    now = datetime.now(UTC)
    provenance = Provenance(
        source="live-razzball-numerical-trace",
        retrieved_at=now,
        effective_at=now,
        source_version="20260920",
    )
    players = tuple(
        Player(
            player_id=f"trace:{key_name(name)}",
            full_name=name,
            position=position,
            nfl_team=team,
        )
        for name, position, team in SAMPLE
    )
    return LeagueState(
        league=League(
            league_id="trace-league",
            name="Razzball numerical trace",
            season=2026,
            rules=LeagueRules(
                team_count=2,
                roster_size=1,
                lineup=(),
                scoring=SCORING,
            ),
        ),
        as_of=now,
        teams=(
            Team(team_id="a", league_id="trace-league", display_name="A"),
            Team(team_id="b", league_id="trace-league", display_name="B"),
        ),
        team_states=(
            TeamState(team_id="a", roster=()),
            TeamState(team_id="b", roster=()),
        ),
        players=players,
        player_states=tuple(
            PlayerState(
                player_id=player.player_id,
                as_of=now,
                nfl_team=player.nfl_team,
                provenance=provenance,
            )
            for player in players
        ),
    )


def current_row_map(snapshot: CurrentProjectionSnapshot) -> dict[tuple[str, str], Any]:
    out = {}
    for row in snapshot.rows:
        out[(key_name(row.player_name), row.position.value)] = row
    return out


def raw_razz_map(rows) -> dict[tuple[str, str], Any]:
    out = {}
    for row in rows:
        out[(key_name(str(row.get("Name") or "")), str(row.get("Pos") or "").upper())] = row
    return out


STAT_TO_METRIC_VALUE = {
    "pass_yd": ForecastMetric.PASS_YARDS.value,
    "pass_td": ForecastMetric.PASS_TD.value,
    "pass_int": ForecastMetric.INTERCEPTIONS.value,
    "rush_yd": ForecastMetric.RUSH_YARDS.value,
    "rush_td": ForecastMetric.RUSH_TD.value,
    "rec": ForecastMetric.RECEPTIONS.value,
    "rec_yd": ForecastMetric.REC_YARDS.value,
    "rec_td": ForecastMetric.REC_TD.value,
    "fum_lost": ForecastMetric.FUMBLES_LOST.value,
}


def observation_map(observations) -> dict[tuple[str, str], float]:
    return {
        (row.player_id, row.metric.value): float(row.distribution.mean)
        for row in observations
    }


def fantasy_map(observations) -> dict[str, float]:
    return {
        row.player_id: float(row.distribution.mean)
        for row in observations
        if row.metric == ForecastMetric.FANTASY_POINTS
    }


def duplicate_summary_razz(rows) -> dict[str, Any]:
    keys = [
        (
            key_name(str(row.get("Name") or "")),
            str(row.get("Pos") or "").upper(),
            str(row.get("Team") or "").upper(),
        )
        for row in rows
    ]
    counts = Counter(keys)
    dup = {str(k): v for k, v in counts.items() if v > 1}
    return {
        "row_count": len(rows),
        "unique_identity_count": len(counts),
        "duplicate_identity_count": len(dup),
        "max_identity_multiplicity": max(counts.values(), default=0),
        "duplicates": dup,
    }


def duplicate_summary_current(snapshot: CurrentProjectionSnapshot) -> dict[str, Any]:
    keys = [(row.external_id, row.provider) for row in snapshot.rows]
    counts = Counter(keys)
    dup = {str(k): v for k, v in counts.items() if v > 1}
    return {
        "row_count": len(snapshot.rows),
        "unique_external_id_count": len(counts),
        "duplicate_external_id_count": len(dup),
        "max_external_id_multiplicity": max(counts.values(), default=0),
        "duplicates": dup,
    }


def duplicate_summary_observations(observations) -> dict[str, Any]:
    keys = [
        (row.player_id, row.metric.value, row.horizon.value, row.source)
        for row in observations
    ]
    counts = Counter(keys)
    dup = {str(k): v for k, v in counts.items() if v > 1}
    return {
        "observation_count": len(observations),
        "unique_key_count": len(counts),
        "duplicate_observation_key_count": len(dup),
        "max_observation_key_multiplicity": max(counts.values(), default=0),
        "duplicates": dup,
    }


def listed_half_ppr(raw: dict[str, str]) -> float | None:
    for label in ("1/2PPR PTS", "1/2 PPR PTS", "HALF PPR PTS"):
        value = raw.get(label)
        if value not in (None, ""):
            try:
                return float(str(value).replace(",", ""))
            except ValueError:
                return None
    return None


def clean_ratio(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or abs(b) < 1e-12:
        return None
    return a / b


def main() -> None:
    state = build_state()
    providers: dict[str, CurrentProjectionSnapshot] = {}
    failures: dict[str, str] = {}
    raw_razz = None

    try:
        rz_snapshot = RazzballSeasonProjectionSource().fetch_latest(season=2026)
        raw_razz = rz_snapshot
        providers["razzball"] = current_snapshot_from_razzball(rz_snapshot)
    except Exception as exc:
        failures["razzball"] = f"{type(exc).__name__}: {exc}"

    for source_id, source in (
        ("fftoday", FFTodayLiveProjectionSource()),
        ("cbs", CBSLiveProjectionSource()),
        ("nfl_fantasy", NFLFantasyLiveProjectionSource()),
    ):
        try:
            providers[source_id] = source.fetch_latest(season=2026)
        except Exception as exc:
            failures[source_id] = f"{type(exc).__name__}: {exc}"

    if "razzball" not in providers or raw_razz is None:
        raise RuntimeError(f"Razzball acquisition failed: {failures.get('razzball')}")

    evaluation_as_of = max(
        datetime.now(UTC),
        *(snap.captured_at.astimezone(UTC) for snap in providers.values()),
        *(snap.effective_at.astimezone(UTC) for snap in providers.values()),
    )

    normalized: dict[str, tuple] = {}
    provider_fp: dict[str, dict[str, float]] = {}
    for source_id, snapshot in providers.items():
        obs = normalize_current_projection_snapshot(
            snapshot,
            league_state=state,
            season=2026,
            evaluation_as_of=evaluation_as_of,
        )
        normalized[source_id] = obs
        provider_fp[source_id] = fantasy_map(
            derive_league_fantasy_point_forecasts(
                obs,
                rules=state.league.rules,
                source=f"trace:{source_id}:league_scored",
                model_version=f"trace:{source_id}:league_scored",
            )
        )

    def replay(source_id: str):
        snapshot = providers[source_id]
        return lambda season: snapshot

    runtime = build_current_live_forecasts(
        state,
        fetchers=tuple(
            NamedCurrentProjectionFetcher(source_id=source_id, fetch=replay(source_id))
            for source_id in sorted(providers)
        ),
        clock=lambda: evaluation_as_of,
        minimum_independent_sources=2,
    )

    raw_rz_by_player = raw_razz_map(raw_razz.rows)
    current_by_source = {source_id: current_row_map(snapshot) for source_id, snapshot in providers.items()}
    normalized_by_source = {source_id: observation_map(obs) for source_id, obs in normalized.items()}
    ensemble_map = observation_map(runtime.raw_ensemble)
    display_fp = fantasy_map(runtime.fantasy_point_forecasts)

    player_id_by_key = {
        (key_name(player.full_name), player.position.value): player.player_id
        for player in state.players
    }

    rows = []
    details = []
    for name, position, team in SAMPLE:
        k = (key_name(name), position.value)
        player_id = player_id_by_key[k]
        rz_raw = raw_rz_by_player.get(k)
        rz_current = current_by_source["razzball"].get(k)
        if rz_raw is None or rz_current is None:
            continue

        provider_rows = {}
        for source_id in sorted(providers):
            source_row = current_by_source[source_id].get(k)
            if source_row is not None:
                provider_rows[source_id] = dict(source_row.stats)

        metric_rows = []
        for metric, rz_value in sorted(rz_current.stats.items()):
            forecast_metric = STAT_TO_METRIC[metric]
            normalized_value = normalized_by_source["razzball"].get((player_id, forecast_metric))
            ensemble_value = ensemble_map.get((player_id, forecast_metric))
            comparisons = {}
            for source_id in sorted(providers):
                other = current_by_source[source_id].get(k)
                other_value = float(other.stats[metric]) if other is not None and metric in other.stats else None
                comparisons[source_id] = {
                    "value": other_value,
                    "razzball_ratio": clean_ratio(float(rz_value), other_value),
                }
            metric_rows.append(
                {
                    "metric": metric,
                    "source_record_value": float(str(rz_raw.get({
                        "pass_yd": "Pass Yds",
                        "pass_td": "Pass TD",
                        "pass_int": "Int",
                        "rush_yd": "Rush Yds",
                        "rush_td": "Run TD",
                        "rec": "Rec",
                        "rec_yd": "Rec Yds",
                        "rec_td": "Rec TD",
                        "fum_lost": "Fum Lst",
                    }[metric])).replace(",", "")) if rz_raw.get({
                        "pass_yd": "Pass Yds",
                        "pass_td": "Pass TD",
                        "pass_int": "Int",
                        "rush_yd": "Rush Yds",
                        "rush_td": "Run TD",
                        "rec": "Rec",
                        "rec_yd": "Rec Yds",
                        "rec_td": "Rec TD",
                        "fum_lost": "Fum Lst",
                    }[metric]) not in (None, "") else None,
                    "current_snapshot_value": float(rz_value),
                    "normalized_value": normalized_value,
                    "ensemble_value": ensemble_value,
                    "comparisons": comparisons,
                }
            )

        rz_fp = provider_fp["razzball"].get(player_id)
        half = listed_half_ppr(rz_raw)
        fp_comparison = {
            source_id: {
                "fantasy_points": fpmap.get(player_id),
                "razzball_ratio": clean_ratio(rz_fp, fpmap.get(player_id)),
            }
            for source_id, fpmap in sorted(provider_fp.items())
        }

        details.append(
            {
                "player": name,
                "position": position.value,
                "team": team,
                "razzball_raw_row": dict(rz_raw),
                "razzball_current_snapshot_stats": dict(rz_current.stats),
                "provider_current_snapshot_stats": provider_rows,
                "metric_trace": metric_rows,
                "razzball_implied_half_ppr_fsffl_rules": rz_fp,
                "razzball_listed_half_ppr_points": half,
                "fsffl_vs_provider_listed_half_ppr_ratio": clean_ratio(rz_fp, half),
                "provider_fantasy_point_comparison": fp_comparison,
                "displayed_forecast_mean": display_fp.get(player_id),
            }
        )

        rows.append(
            {
                "player": name,
                "pos": position.value,
                "razzball_half_ppr_listed": half,
                "razzball_half_ppr_recomputed": rz_fp,
                "fftoday_half_ppr_recomputed": provider_fp.get("fftoday", {}).get(player_id),
                "cbs_half_ppr_recomputed": provider_fp.get("cbs", {}).get(player_id),
                "nfl_fantasy_half_ppr_recomputed": provider_fp.get("nfl_fantasy", {}).get(player_id),
                "razzball_vs_fftoday_fp_ratio": clean_ratio(rz_fp, provider_fp.get("fftoday", {}).get(player_id)),
                "displayed_ensemble_forecast": display_fp.get(player_id),
            }
        )

    payload = {
        "schema_version": "fsffl-live-razzball-numerical-trace-v1",
        "run_at": datetime.now(UTC).isoformat(),
        "season": 2026,
        "scoring_coordinate": "diagnostic_0.5ppr_4pt_pass_td_minus2_int_standard_yard_td",
        "sample_size": len(SAMPLE),
        "providers_successful": sorted(providers),
        "provider_failures": failures,
        "runtime_successful_source_ids": list(runtime.successful_source_ids),
        "runtime_failed_sources": list(runtime.failed_sources),
        "razzball_source_version": raw_razz.source_version,
        "razzball_source_url": raw_razz.source_url,
        "razzball_captured_at": raw_razz.captured_at.isoformat(),
        "razzball_effective_at": raw_razz.effective_at.isoformat(),
        "duplicate_checks": {
            "razzball_parser_rows": duplicate_summary_razz(raw_razz.rows),
            "razzball_current_snapshot": duplicate_summary_current(providers["razzball"]),
            "razzball_normalized_observations": duplicate_summary_observations(normalized["razzball"]),
        },
        "players": details,
    }
    (OUT / "TRACE.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    if rows:
        with (OUT / "PLAYER_SUMMARY.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    summary = {
        "providers_successful": sorted(providers),
        "provider_failures": failures,
        "duplicates": payload["duplicate_checks"],
        "rows": rows,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock

from fsffl.forecast.future_contract import FutureForecastContract
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.product.p0_future_forecast_provider import build_p0_future_forecast_contract
from fsffl.providers.sleeper_weekly_stats import SleeperWeeklyStatLine, SleeperWeeklyStatsSource
from fsffl.state.models import LeagueRules, Player, Position
from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicContract

from .runtime import UserRuntimeContext
from .value_lens_evidence import build_governed_value_lens_evidence
from .value_presentation import build_value_presentation_coordinate


PLAYER_INTELLIGENCE_CONTRACT_VERSION = "player-intelligence-v1"


def _season_fantasy_observation(
    rows: tuple[ForecastObservation, ...],
    player_id: str,
) -> ForecastObservation | None:
    candidates = [
        row
        for row in rows
        if row.player_id == player_id
        and row.metric == ForecastMetric.FANTASY_POINTS
        and row.horizon == ForecastHorizon.SEASON
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item.as_of, item.model_version, item.source))


def _fantasy_ppg(points: float | None) -> float | None:
    if points is None:
        return None
    # Forecast contracts own season totals but not projected active games. This
    # display rate uses the 17-game NFL team schedule and labels that basis.
    return float(points) / 17.0


class PlayerFutureForecastCache:
    def __init__(self) -> None:
        self._lock = RLock()
        self._key: tuple[str, str, str] | None = None
        self._contract: FutureForecastContract | None = None

    def get(self, runtime: UserRuntimeContext) -> FutureForecastContract | None:
        state = runtime.league_state
        evidence = runtime.forecast_evidence
        if state is None or evidence is None:
            return None
        key = (
            state.state_id,
            evidence.model_version,
            evidence.runtime_result.evaluation_as_of.isoformat(),
        )
        with self._lock:
            if self._key == key and self._contract is not None:
                return self._contract
            year_one = tuple(
                row
                for row in evidence.league_scored_forecasts
                if row.metric == ForecastMetric.FANTASY_POINTS
                and row.horizon == ForecastHorizon.SEASON
            )
            materialized = build_p0_future_forecast_contract(
                league_state=state,
                raw_forecasts=evidence.raw_forecasts,
                league_year_one=year_one,
            )
            self._key = key
            self._contract = materialized.contract
            return self._contract


def _player(runtime: UserRuntimeContext, player_id: str) -> Player:
    state = runtime.league_state
    if state is None:
        raise ValueError("Player Intelligence requires canonical league state")
    player = next((row for row in state.players if row.player_id == player_id), None)
    if player is None:
        raise ValueError(f"player is not present in canonical league state: {player_id}")
    return player


def build_player_intelligence_overview(
    runtime: UserRuntimeContext,
    player_id: str,
    *,
    intrinsic: ShapleyIntrinsicContract | None,
    future_cache: PlayerFutureForecastCache,
) -> dict[str, object]:
    state = runtime.league_state
    if state is None:
        raise ValueError("Player Intelligence requires canonical league state")
    player = _player(runtime, player_id)
    player_state = next(
        (row for row in state.player_states if row.player_id == player_id),
        None,
    )
    evidence = runtime.forecast_evidence
    y1 = (
        _season_fantasy_observation(evidence.league_scored_forecasts, player_id)
        if evidence is not None
        else None
    )

    future_rows = ()
    future_error = None
    try:
        future = future_cache.get(runtime)
        future_rows = future.rows_for_player(player_id) if future is not None else ()
    except Exception as exc:
        future = None
        future_error = f"{type(exc).__name__}: {exc}"

    values = runtime.value_evidence
    market_percentile = None
    market_index = None
    intrinsic_percentile = None
    intrinsic_index = None
    intrinsic_raw = None
    value_presentation = None

    if intrinsic is not None:
        lens = build_governed_value_lens_evidence(runtime, intrinsic)
        market_percentile = lens.market_percentiles.get(player_id)
        intrinsic_percentile = lens.intrinsic_percentiles.get(player_id)
        intrinsic_raw = lens.intrinsic_raw.get(player_id)
        if lens.value_coordinate is not None:
            market_index = lens.value_coordinate.index_for_percentile(market_percentile)
            intrinsic_index = lens.value_coordinate.index_for_percentile(intrinsic_percentile)
            value_presentation = {
                "status": "ready",
                **lens.value_coordinate.summary_payload(),
            }
        else:
            value_presentation = {
                "status": "unavailable",
                "reason": lens.value_coordinate_error or lens.reason,
            }
    elif values is not None:
        market_estimate = next(
            (
                row
                for row in values.estimates
                if row.asset_id == player_id
                and row.scale.scale_id == "dynasty-market-percentile"
            ),
            None,
        )
        if market_estimate is not None:
            market_percentile = max(
                0.0,
                min(1.0, float(market_estimate.distribution.mean)),
            )
        try:
            coordinate = build_value_presentation_coordinate(
                values.native_magnitude_observations
            )
            market_index = coordinate.index_for_percentile(market_percentile)
            value_presentation = {
                "status": "ready",
                **coordinate.summary_payload(),
            }
        except ValueError as exc:
            value_presentation = {"status": "unavailable", "reason": str(exc)}

    forecasts: list[dict[str, object]] = []
    if y1 is not None:
        forecasts.append(
            {
                "year_index": 1,
                "target_season": state.league.season,
                "fantasy_points": float(y1.distribution.mean),
                "fantasy_ppg": _fantasy_ppg(float(y1.distribution.mean)),
                "ppg_basis": "full-season fantasy points / 17 NFL team games",
                "uncertainty": {
                    "kind": "moments",
                    "stddev": float(y1.distribution.stddev),
                    "p10": y1.distribution.p10,
                    "p50": y1.distribution.p50,
                    "p90": y1.distribution.p90,
                },
                "source": y1.source,
                "model_version": y1.model_version,
                "as_of": y1.as_of.isoformat(),
                "evidence_basis": evidence.evidence_basis if evidence is not None else None,
            }
        )

    for row in sorted(future_rows, key=lambda item: item.year_index):
        forecasts.append(
            {
                "year_index": row.year_index,
                "target_season": row.target_season,
                "fantasy_points": float(row.central_expectation),
                "fantasy_ppg": _fantasy_ppg(float(row.central_expectation)),
                "ppg_basis": "full-season fantasy points / 17 NFL team games",
                "uncertainty": {
                    "kind": row.uncertainty_kind.value,
                    "stddev": row.stddev,
                    "p10": row.p10,
                    "p50": row.p50,
                    "p90": row.p90,
                    "scenarios": [
                        scenario.model_dump(mode="json")
                        for scenario in row.scenarios
                    ],
                    "evidence_path": row.evidence_path,
                },
                "source": row.source,
                "model_version": row.model_version,
                "as_of": (
                    evidence.runtime_result.evaluation_as_of.isoformat()
                    if evidence is not None
                    else None
                ),
                "evidence_basis": "governed_future_forecast_contract",
            }
        )

    return {
        "status": "ready",
        "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
        "league_state_id": state.state_id,
        "player": {
            "player_id": player.player_id,
            "full_name": player.full_name,
            "position": player.position.value,
            "nfl_team": player.nfl_team,
            "age_years": player_state.age_years if player_state is not None else None,
        },
        "forecast": {
            "status": "ready" if forecasts else "unavailable",
            "rows": forecasts,
            "future_error": future_error,
            "current_evidence_basis": evidence.evidence_basis if evidence is not None else None,
            "current_model_version": evidence.model_version if evidence is not None else None,
            "current_as_of": (
                evidence.runtime_result.evaluation_as_of.isoformat()
                if evidence is not None
                else None
            ),
            "successful_source_ids": (
                list(evidence.successful_source_ids) if evidence is not None else []
            ),
        },
        "value": {
            "broad_market_value_index": market_index,
            "broad_market_percentile": market_percentile,
            "intrinsic_value_index": intrinsic_index,
            "intrinsic_percentile": intrinsic_percentile,
            "raw_shapley_marginal_points": intrinsic_raw,
            "league_market_value": None,
            "value_presentation": value_presentation,
            "raw_market_and_intrinsic_subtraction_allowed": False,
        },
        "history": {
            "status": "lazy",
            "endpoint": f"/api/player-intelligence/{player_id}/history",
            "season_count": 3,
        },
    }


@dataclass(frozen=True)
class HistoricalPlayerSeason:
    season: int
    games_played: int
    fantasy_points: float
    fantasy_ppg: float | None
    position_rank: int | None
    position_rank_population: int | None
    rank_basis: str | None
    stats: dict[str, float]
    scoring_basis: str
    source: str
    source_version: str
    retrieved_at: str


def _sleeper_external_id(player: Player) -> str | None:
    for ref in player.provider_refs:
        if ref.provider == "sleeper":
            return ref.external_id
    if player.player_id.startswith("sleeper:"):
        return player.player_id.split(":")[-1]
    return None


def _position_stats(position: Position, totals: dict[str, float]) -> dict[str, float]:
    if position == Position.QB:
        keys = ("pass_yd", "pass_td", "pass_int", "rush_yd", "rush_td")
    elif position in {Position.RB, Position.WR, Position.TE}:
        keys = ("rush_yd", "rush_td", "rec", "rec_yd", "rec_td")
    else:
        keys = tuple(sorted(totals))
    return {key: float(totals.get(key, 0.0)) for key in keys}


def _score_stats(totals: dict[str, float], rules: LeagueRules) -> float:
    return float(
        sum(float(rule.points) * float(totals.get(rule.stat, 0.0)) for rule in rules.scoring)
    )


class PlayerHistoryService:
    """Lazy measured-history materializer using the existing Sleeper Data source."""

    def __init__(
        self,
        *,
        source: SleeperWeeklyStatsSource | None = None,
        max_workers: int = 6,
    ) -> None:
        self._source = source or SleeperWeeklyStatsSource()
        self._max_workers = max_workers
        self._lock = RLock()
        self._cache: dict[tuple[str, int], dict[str, dict[str, float | int | str]]] = {}

    def _season(self, runtime: UserRuntimeContext, season: int) -> dict[str, dict[str, float | int | str]]:
        state = runtime.league_state
        if state is None:
            raise ValueError("history requires canonical league state")
        key = (state.league.league_id, season)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        weeks: list[tuple[SleeperWeeklyStatLine, ...]] = []
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {
                executor.submit(self._source.fetch_week, season=season, week=week): week
                for week in range(1, 19)
            }
            for future in as_completed(futures):
                weeks.append(future.result())

        aggregates: dict[str, dict[str, float | int | str]] = {}
        for batch in weeks:
            for row in batch:
                external_id = row.player_id.split(":")[-1]
                target = aggregates.setdefault(
                    external_id,
                    {
                        "games_played": 0,
                        "retrieved_at": row.captured_at.astimezone(UTC).isoformat(),
                    },
                )
                gp = row.stats.get("gp")
                target["games_played"] = int(target["games_played"]) + int(
                    round(float(gp)) if gp is not None else 1
                )
                for stat, value in row.stats.items():
                    if stat == "gp":
                        continue
                    target[stat] = float(target.get(stat, 0.0)) + float(value)

        with self._lock:
            self._cache[key] = aggregates
        return aggregates

    def player_history(
        self,
        runtime: UserRuntimeContext,
        player_id: str,
        *,
        seasons: int = 3,
    ) -> tuple[HistoricalPlayerSeason, ...]:
        state = runtime.league_state
        if state is None:
            raise ValueError("history requires canonical league state")
        player = _player(runtime, player_id)
        external_id = _sleeper_external_id(player)
        if external_id is None:
            raise ValueError("player lacks canonical Sleeper identity for historical stats")

        player_by_external = {
            external: candidate
            for candidate in state.players
            if (external := _sleeper_external_id(candidate)) is not None
        }
        output: list[HistoricalPlayerSeason] = []
        for season in range(state.league.season - seasons, state.league.season):
            aggregates = self._season(runtime, season)
            row = aggregates.get(external_id)
            if row is None:
                continue
            totals = {
                key: float(value)
                for key, value in row.items()
                if key not in {"games_played", "retrieved_at"}
                and isinstance(value, (int, float))
            }
            points = _score_stats(totals, state.league.rules)
            games = max(0, int(row.get("games_played", 0)))

            comparable: list[tuple[str, float]] = []
            for ext, candidate in player_by_external.items():
                if candidate.position != player.position:
                    continue
                candidate_row = aggregates.get(ext)
                if candidate_row is None:
                    continue
                candidate_totals = {
                    key: float(value)
                    for key, value in candidate_row.items()
                    if key not in {"games_played", "retrieved_at"}
                    and isinstance(value, (int, float))
                }
                comparable.append((ext, _score_stats(candidate_totals, state.league.rules)))
            comparable.sort(key=lambda item: (-item[1], item[0]))
            rank = next(
                (index + 1 for index, item in enumerate(comparable) if item[0] == external_id),
                None,
            )

            output.append(
                HistoricalPlayerSeason(
                    season=season,
                    games_played=games,
                    fantasy_points=points,
                    fantasy_ppg=(points / games if games > 0 else None),
                    position_rank=rank,
                    position_rank_population=(len(comparable) if rank is not None else None),
                    rank_basis=(
                        "rank among current canonical player population, scored under current league rules"
                        if rank is not None
                        else None
                    ),
                    stats=_position_stats(player.position, totals),
                    scoring_basis="scored under current league rules",
                    source=self._source.provider_name,
                    source_version=self._source.source_version,
                    retrieved_at=str(row.get("retrieved_at") or ""),
                )
            )
        return tuple(output)

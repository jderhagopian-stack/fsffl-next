from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock

from fsffl.forecast.future_contract import FutureForecastContract
from fsffl.persistence.contracts import (
    ArtifactKey,
    PersistenceStore,
    ReusableArtifactRecord,
    canonical_fingerprint,
    utc_now,
)
from fsffl.forecast.models import ForecastHorizon, ForecastMetric, ForecastObservation
from fsffl.product.p0_forecast_runtime import P0_FORECAST_VERSION
from fsffl.product.p0_future_forecast_provider import build_p0_future_forecast_contract
from fsffl.providers.sleeper_weekly_stats import SleeperWeeklyStatLine, SleeperWeeklyStatsSource
from fsffl.state.models import LeagueRules, Player, Position
from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicContract

from .runtime import UserRuntimeContext
from .value_lens_evidence import build_governed_value_lens_evidence
from .value_presentation import build_value_presentation_coordinate


PLAYER_INTELLIGENCE_CONTRACT_VERSION = "player-intelligence-v2:full-career-history"
PLAYER_HISTORY_MIN_DETAILED_SEASON = 2010
PLAYER_HISTORY_ARTIFACT_KIND = "player_history_season_aggregate"
PLAYER_HISTORY_ARTIFACT_VERSION = "player-history-season-aggregate-v1"


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
    # Current Forecast contracts own full-season expected fantasy points but do
    # not expose expected player games played. PPG therefore fails closed rather
    # than dividing by the NFL team schedule and pretending that is player PPG.
    _ = points
    return None


class PlayerFutureForecastCache:
    def __init__(
        self,
        *,
        future_forecast_builder=build_p0_future_forecast_contract,
        forecast_model_version: str = P0_FORECAST_VERSION,
    ) -> None:
        self._lock = RLock()
        self._future_forecast_builder = future_forecast_builder
        self._forecast_model_version = str(forecast_model_version)
        self._key: tuple[str, str, str, str] | None = None
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
            self._forecast_model_version,
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
            materialized = self._future_forecast_builder(
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
                "ppg_basis": "unavailable: Forecast contract does not expose expected player games",
                "uncertainty": {
                    "kind": "moments",
                    "stddev": float(y1.distribution.stddev),
                    "p10": y1.distribution.p10,
                    "p25": y1.distribution.p25,
                    "p50": y1.distribution.p50,
                    "p75": y1.distribution.p75,
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
                "ppg_basis": "unavailable: Forecast contract does not expose expected player games",
                "uncertainty": {
                    "kind": row.uncertainty_kind.value,
                    "stddev": row.stddev,
                    "p10": row.p10,
                    "p25": row.p25,
                    "p50": row.p50,
                    "p75": row.p75,
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
            "season_count": None,
            "boundary_min_season": PLAYER_HISTORY_MIN_DETAILED_SEASON,
            "boundary_basis": (
                "Sleeper detailed regular-season stats are consumed from the "
                "provider-supported 2010+ range; only seasons with player evidence "
                "are returned."
            ),
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
    more_stats: dict[str, float]
    games_played_basis: str
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


_STANDARD_BOX_STATS = (
    "pass_att",
    "pass_cmp",
    "pass_yd",
    "pass_td",
    "pass_int",
    "rush_att",
    "rush_yd",
    "rush_td",
    "rec_tgt",
    "rec",
    "rec_yd",
    "rec_td",
    "fum",
    "fum_lost",
)
_PRIMARY_BY_POSITION = {
    Position.QB: (
        "pass_att",
        "pass_cmp",
        "pass_yd",
        "pass_td",
        "pass_int",
        "rush_att",
        "rush_yd",
        "rush_td",
        "fum",
        "fum_lost",
    ),
    Position.RB: (
        "rush_att",
        "rush_yd",
        "rush_td",
        "rec_tgt",
        "rec",
        "rec_yd",
        "rec_td",
        "fum",
        "fum_lost",
    ),
    Position.WR: (
        "rec_tgt",
        "rec",
        "rec_yd",
        "rec_td",
        "rush_att",
        "rush_yd",
        "rush_td",
        "fum",
        "fum_lost",
    ),
    Position.TE: (
        "rec_tgt",
        "rec",
        "rec_yd",
        "rec_td",
        "rush_att",
        "rush_yd",
        "rush_td",
        "fum",
        "fum_lost",
    ),
}


def _position_stats(
    position: Position,
    totals: dict[str, float],
) -> tuple[dict[str, float], dict[str, float]]:
    primary_keys = _PRIMARY_BY_POSITION.get(position, _STANDARD_BOX_STATS)
    primary = {
        key: float(totals[key])
        for key in primary_keys
        if key in totals
    }
    more = {
        key: float(totals[key])
        for key in _STANDARD_BOX_STATS
        if key not in primary_keys
        and key in totals
        and abs(float(totals[key])) > 0
    }
    return primary, more


def _score_stats(totals: dict[str, float], rules: LeagueRules) -> float:
    return float(
        sum(float(rule.points) * float(totals.get(rule.stat, 0.0)) for rule in rules.scoring)
    )


class PlayerHistoryService:
    """Measured full-career history with season-level provider/persistence reuse.

    Raw season aggregates are Data-layer evidence. League scoring is applied only
    after a cached aggregate is selected, so the durable artifact never becomes a
    new scoring or Value authority.
    """

    def __init__(
        self,
        *,
        source: SleeperWeeklyStatsSource | None = None,
        max_workers: int = 6,
        persistence_store: PersistenceStore | None = None,
        minimum_season: int = PLAYER_HISTORY_MIN_DETAILED_SEASON,
    ) -> None:
        self._source = source or SleeperWeeklyStatsSource()
        self._max_workers = max(1, max_workers)
        self._persistence_store = persistence_store
        self._minimum_season = minimum_season
        self._lock = RLock()
        self._cache: dict[
            tuple[str, int, str],
            dict[str, dict[str, float | int | str]],
        ] = {}

    def _artifact_key(self, league_id: str, season: int) -> ArtifactKey:
        return ArtifactKey(
            artifact_kind=PLAYER_HISTORY_ARTIFACT_KIND,
            scope_kind="league_season",
            scope_id=f"{league_id}:{season}",
            input_fingerprint=canonical_fingerprint(
                self._source.provider_name,
                self._source.source_version,
                season,
            ),
            model_version=PLAYER_HISTORY_ARTIFACT_VERSION,
        )

    @staticmethod
    def _normalize_persisted_payload(
        payload: object,
    ) -> dict[str, dict[str, float | int | str]] | None:
        if not isinstance(payload, dict):
            return None
        normalized: dict[str, dict[str, float | int | str]] = {}
        for player_id, raw in payload.items():
            if not isinstance(player_id, str) or not isinstance(raw, dict):
                return None
            row: dict[str, float | int | str] = {}
            for key, value in raw.items():
                if isinstance(key, str) and isinstance(value, (int, float, str)):
                    row[key] = value
            normalized[player_id] = row
        return normalized

    def _restore_persisted(
        self,
        league_id: str,
        season: int,
    ) -> dict[str, dict[str, float | int | str]] | None:
        if self._persistence_store is None:
            return None
        record = self._persistence_store.get_reusable_artifact(
            self._artifact_key(league_id, season)
        )
        if record is None:
            return None
        return self._normalize_persisted_payload(dict(record.payload))

    def _persist(
        self,
        league_id: str,
        season: int,
        aggregates: dict[str, dict[str, float | int | str]],
    ) -> None:
        if self._persistence_store is None:
            return
        self._persistence_store.put_artifact(
            ReusableArtifactRecord(
                key=self._artifact_key(league_id, season),
                payload=aggregates,
                computed_at=utc_now(),
            )
        )

    def _weekly_fallback(
        self,
        *,
        season: int,
    ) -> dict[str, dict[str, float | int | str]]:
        """Compatibility fallback for fixtures/older source adapters.

        Provider gp is authoritative when present. If a weekly adapter omits gp, a
        row counts as participation only when it contains non-zero measured
        production; an all-zero/non-participation row is never blindly counted.
        """

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
                        "games_played_basis": "weekly provider gp",
                        "retrieved_at": row.captured_at.astimezone(UTC).isoformat(),
                    },
                )
                gp = row.stats.get("gp")
                if gp is not None:
                    increment = max(0, int(round(float(gp))))
                else:
                    measured = [
                        float(value)
                        for key, value in row.stats.items()
                        if key not in {"gp", "pts_std", "pts_ppr", "pts_half_ppr"}
                    ]
                    increment = 1 if any(abs(value) > 0 for value in measured) else 0
                    target["games_played_basis"] = (
                        "weekly non-zero measured-production fallback; provider gp absent"
                    )
                target["games_played"] = int(target["games_played"]) + increment
                for stat, value in row.stats.items():
                    if stat == "gp":
                        continue
                    target[stat] = float(target.get(stat, 0.0)) + float(value)
        return aggregates

    def _acquire_season(
        self,
        *,
        season: int,
    ) -> dict[str, dict[str, float | int | str]]:
        fetch_season = getattr(self._source, "fetch_season", None)
        if not callable(fetch_season):
            return self._weekly_fallback(season=season)

        rows = fetch_season(season=season)
        aggregates: dict[str, dict[str, float | int | str]] = {}
        for row in rows:
            external_id = row.player_id.split(":")[-1]
            stats = {
                str(key): float(value)
                for key, value in row.stats.items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            }
            gp = stats.pop("gp", None)
            aggregates[external_id] = {
                "games_played": max(0, int(round(gp))) if gp is not None else 0,
                "games_played_basis": (
                    "provider season aggregate gp"
                    if gp is not None
                    else "unavailable: provider season aggregate omitted gp"
                ),
                "retrieved_at": row.captured_at.astimezone(UTC).isoformat(),
                **stats,
            }
        return aggregates

    def _season(
        self,
        runtime: UserRuntimeContext,
        season: int,
    ) -> dict[str, dict[str, float | int | str]]:
        state = runtime.league_state
        if state is None:
            raise ValueError("history requires canonical league state")
        key = (state.league.league_id, season, self._source.source_version)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        persisted = self._restore_persisted(state.league.league_id, season)
        if persisted is not None:
            with self._lock:
                self._cache[key] = persisted
            return persisted

        aggregates = self._acquire_season(season=season)
        self._persist(state.league.league_id, season, aggregates)
        with self._lock:
            self._cache[key] = aggregates
        return aggregates

    def player_history(
        self,
        runtime: UserRuntimeContext,
        player_id: str,
    ) -> tuple[HistoricalPlayerSeason, ...]:
        state = runtime.league_state
        if state is None:
            raise ValueError("history requires canonical league state")
        player = _player(runtime, player_id)
        external_id = _sleeper_external_id(player)
        if external_id is None:
            raise ValueError("player lacks canonical Sleeper identity for historical stats")

        candidate_seasons = tuple(
            range(self._minimum_season, state.league.season)
        )
        by_season: dict[int, dict[str, dict[str, float | int | str]]] = {}
        worker_count = min(self._max_workers, max(1, len(candidate_seasons)))
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="fsffl-player-history-season",
        ) as executor:
            futures = {
                executor.submit(self._season, runtime, season): season
                for season in candidate_seasons
            }
            for future in as_completed(futures):
                by_season[futures[future]] = future.result()

        output: list[HistoricalPlayerSeason] = []
        for season in candidate_seasons:
            row = by_season[season].get(external_id)
            if row is None:
                continue
            totals = {
                key: float(value)
                for key, value in row.items()
                if key not in {
                    "games_played",
                    "games_played_basis",
                    "retrieved_at",
                }
                and isinstance(value, (int, float))
            }
            points = _score_stats(totals, state.league.rules)
            games = max(0, int(row.get("games_played", 0)))
            primary, more = _position_stats(player.position, totals)

            output.append(
                HistoricalPlayerSeason(
                    season=season,
                    games_played=games,
                    fantasy_points=points,
                    fantasy_ppg=(points / games if games > 0 else None),
                    position_rank=None,
                    position_rank_population=None,
                    rank_basis=(
                        "unavailable: complete point-in-time historical position population is not persisted"
                    ),
                    stats=primary,
                    more_stats=more,
                    games_played_basis=str(
                        row.get("games_played_basis")
                        or "unavailable: participation basis missing"
                    ),
                    scoring_basis="scored under current league rules",
                    source=self._source.provider_name,
                    source_version=self._source.source_version,
                    retrieved_at=str(row.get("retrieved_at") or ""),
                )
            )
        return tuple(output)


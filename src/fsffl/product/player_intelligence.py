from __future__ import annotations

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
from fsffl.providers.sleeper_weekly_stats import SleeperWeeklyStatLine, SleeperWeeklyStatsSource
from fsffl.state.models import LeagueRules, Player, Position
from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicContract

from .runtime import UserRuntimeContext
from .value_lens_evidence import build_governed_value_lens_evidence
from .value_presentation import build_value_presentation_coordinate


PLAYER_INTELLIGENCE_CONTRACT_VERSION = "player-intelligence-v2:full-career-history"
PLAYER_HISTORY_MIN_DETAILED_SEASON = 2010
PLAYER_HISTORY_ARTIFACT_KIND = "player_history_season_aggregate"
PLAYER_HISTORY_ARTIFACT_VERSION = "player-history-season-aggregate-v1"  # legacy full-population artifact
PLAYER_HISTORY_PLAYER_SEASON_ARTIFACT_KIND = "player_history_player_season"
PLAYER_HISTORY_PLAYER_SEASON_ARTIFACT_VERSION = "player-history-player-season-v1"
PLAYER_HISTORY_CAREER_ARTIFACT_KIND = "player_history_career"
PLAYER_HISTORY_CAREER_ARTIFACT_VERSION = "player-history-career-v1"
Y1_FULL_SEASON_GAME_BASIS = 17
Y1_FULL_SEASON_GAME_BASIS_REASON = "governed full-season projection schedule basis: 17 NFL games"


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


_PROJECTED_STAT_BY_METRIC = {
    ForecastMetric.PASS_YARDS: "pass_yd",
    ForecastMetric.PASS_TD: "pass_td",
    ForecastMetric.INTERCEPTIONS: "pass_int",
    ForecastMetric.RUSH_YARDS: "rush_yd",
    ForecastMetric.RUSH_TD: "rush_td",
    ForecastMetric.RECEPTIONS: "rec",
    ForecastMetric.REC_YARDS: "rec_yd",
    ForecastMetric.REC_TD: "rec_td",
    ForecastMetric.FUMBLES_LOST: "fum_lost",
}


def _season_projected_stats(
    rows: tuple[ForecastObservation, ...],
    player_id: str,
) -> tuple[dict[str, float], dict[str, dict[str, str]]]:
    """Return only governed full-season football-stat observations.

    This is deliberately a transport helper, not an inference layer. Fields that
    Forecast does not publish (for example pass attempts, rush attempts, targets,
    or expected games played) remain absent instead of being reverse-engineered
    from fantasy points.
    """

    selected: dict[ForecastMetric, ForecastObservation] = {}
    for row in rows:
        if (
            row.player_id != player_id
            or row.horizon != ForecastHorizon.SEASON
            or row.metric not in _PROJECTED_STAT_BY_METRIC
        ):
            continue
        current = selected.get(row.metric)
        if current is None or (
            row.as_of,
            row.model_version,
            row.source,
        ) > (
            current.as_of,
            current.model_version,
            current.source,
        ):
            selected[row.metric] = row

    stats: dict[str, float] = {}
    provenance: dict[str, dict[str, str]] = {}
    for metric, row in selected.items():
        key = _PROJECTED_STAT_BY_METRIC[metric]
        stats[key] = float(row.distribution.mean)
        provenance[key] = {
            "metric": metric.value,
            "source": row.source,
            "model_version": row.model_version,
            "as_of": row.as_of.isoformat(),
        }
    return stats, provenance


def _fantasy_ppg(points: float | None, *, games_basis: int | None = None) -> float | None:
    if points is None or games_basis is None or games_basis <= 0:
        return None
    return float(points) / float(games_basis)


class PlayerFutureForecastCache:
    """Bounded Future Forecast cache with same-league presentation continuity.

    The current State always gets first chance to build its own governed contract.
    While that State is reconciling, a previously built contract may remain visible
    only when the runtime explicitly advertises a same-league served-last-good
    identity and the connected-league scoring rules are unchanged. This is a
    presentation-continuity policy; it does not create or alter Forecast authority.
    """

    def __init__(
        self,
        *,
        future_forecast_builder=None,
        forecast_model_version: str = "future-forecast-provider:unconfigured",
    ) -> None:
        self._lock = RLock()
        self._future_forecast_builder = future_forecast_builder
        self._forecast_model_version = str(forecast_model_version)
        self._key: tuple[str, str, str, str] | None = None
        self._contract: FutureForecastContract | None = None
        self._league_id: str | None = None
        self._rules_fingerprint: str | None = None

    @staticmethod
    def _rules_fingerprint(runtime: UserRuntimeContext) -> str | None:
        state = runtime.league_state
        if state is None:
            return None
        return canonical_fingerprint(state.league.rules.model_dump(mode="json"))

    def _stale_last_good_locked(
        self,
        runtime: UserRuntimeContext,
    ) -> FutureForecastContract | None:
        state = runtime.league_state
        served = runtime.served_intelligence
        if (
            state is None
            or served is None
            or self._contract is None
            or self._key is None
            or served.league_id != state.league.league_id
            or self._league_id != state.league.league_id
            or self._key[0] != served.league_state_id
            or self._rules_fingerprint != self._rules_fingerprint(runtime)
            or self._contract.evaluation_season != state.league.season
        ):
            return None
        return self._contract

    def resolve(
        self,
        runtime: UserRuntimeContext,
    ) -> tuple[FutureForecastContract | None, str]:
        state = runtime.league_state
        evidence = runtime.forecast_evidence
        with self._lock:
            if (
                state is None
                or evidence is None
                or self._future_forecast_builder is None
            ):
                fallback = self._stale_last_good_locked(runtime)
                return (
                    (fallback, "stale_last_good")
                    if fallback is not None
                    else (None, "unavailable")
                )
            key = (
                state.state_id,
                evidence.model_version,
                evidence.runtime_result.evaluation_as_of.isoformat(),
                self._forecast_model_version,
            )
            if self._key == key and self._contract is not None:
                return self._contract, "current"
            year_one = tuple(
                row
                for row in evidence.league_scored_forecasts
                if row.metric == ForecastMetric.FANTASY_POINTS
                and row.horizon == ForecastHorizon.SEASON
            )
            try:
                contract = self._future_forecast_builder(
                    league_state=state,
                    raw_forecasts=evidence.raw_forecasts,
                    league_year_one=year_one,
                )
            except Exception:
                fallback = self._stale_last_good_locked(runtime)
                if fallback is not None:
                    return fallback, "stale_last_good"
                raise
            if not isinstance(contract, FutureForecastContract):
                raise TypeError(
                    "Future Forecast provider must return FutureForecastContract"
                )
            self._key = key
            self._contract = contract
            self._league_id = state.league.league_id
            self._rules_fingerprint = self._rules_fingerprint(runtime)
            return self._contract, "current"

    def get(self, runtime: UserRuntimeContext) -> FutureForecastContract | None:
        contract, _freshness = self.resolve(runtime)
        return contract


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

    projected_stats: dict[str, float] = {}
    projected_stats_provenance: dict[str, dict[str, str]] = {}
    if evidence is not None:
        projected_stats, projected_stats_provenance = _season_projected_stats(
            evidence.raw_forecasts,
            player_id,
        )

    future_rows = ()
    future_error = None
    future_freshness = "unavailable"
    try:
        resolver = getattr(future_cache, "resolve", None)
        if callable(resolver):
            future, future_freshness = resolver(runtime)
        else:
            future = future_cache.get(runtime)
            future_freshness = "current" if future is not None else "unavailable"
        future_rows = future.rows_for_player(player_id) if future is not None else ()
    except Exception as exc:
        future = None
        future_error = f"{type(exc).__name__}: {exc}"
        future_freshness = "unavailable"

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
                "fantasy_ppg": _fantasy_ppg(
                    float(y1.distribution.mean),
                    games_basis=Y1_FULL_SEASON_GAME_BASIS,
                ),
                "projected_games": Y1_FULL_SEASON_GAME_BASIS,
                "ppg_basis": Y1_FULL_SEASON_GAME_BASIS_REASON,
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
            "future_freshness": {
                "status": future_freshness,
                "served_state_id": (
                    runtime.served_intelligence.league_state_id
                    if future_freshness == "stale_last_good"
                    and runtime.served_intelligence is not None
                    else None
                ),
                "target_state_id": state.state_id,
            },
            "current_projected_stats": {
                "season": state.league.season,
                "label": "PROJECTED",
                "stats": projected_stats,
                "fantasy_points": (
                    float(y1.distribution.mean) if y1 is not None else None
                ),
                "fantasy_ppg": _fantasy_ppg(
                    float(y1.distribution.mean) if y1 is not None else None,
                    games_basis=(Y1_FULL_SEASON_GAME_BASIS if y1 is not None else None),
                ),
                "games_played": (
                    Y1_FULL_SEASON_GAME_BASIS if y1 is not None else None
                ),
                "games_played_basis": (
                    Y1_FULL_SEASON_GAME_BASIS_REASON if y1 is not None else None
                ),
                "evidence_basis": (
                    evidence.evidence_basis if evidence is not None else None
                ),
                "source_ids": (
                    sorted(
                        {
                            item["source"]
                            for item in projected_stats_provenance.values()
                        }
                    )
                    if projected_stats_provenance
                    else []
                ),
                "model_versions": (
                    sorted(
                        {
                            item["model_version"]
                            for item in projected_stats_provenance.values()
                        }
                    )
                    if projected_stats_provenance
                    else []
                ),
                "field_provenance": projected_stats_provenance,
            },
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
    """Memory-bounded full-career history for one Player Intelligence subject.

    Historical provider payloads are reduced to one player immediately. Durable
    player-season rows and the final scored career result are the cache boundary;
    full-population season aggregates are neither retained nor written by this path.
    """

    def __init__(
        self,
        *,
        source: SleeperWeeklyStatsSource | None = None,
        max_workers: int = 1,
        persistence_store: PersistenceStore | None = None,
        minimum_season: int = PLAYER_HISTORY_MIN_DETAILED_SEASON,
    ) -> None:
        self._source = source or SleeperWeeklyStatsSource()
        # Kept for constructor compatibility, but season fan-out is intentionally
        # disabled. One player history processes seasons sequentially.
        self._max_workers = 1
        self._persistence_store = persistence_store
        self._minimum_season = minimum_season

    def _player_season_artifact_key(
        self,
        *,
        external_id: str,
        season: int,
    ) -> ArtifactKey:
        return ArtifactKey(
            artifact_kind=PLAYER_HISTORY_PLAYER_SEASON_ARTIFACT_KIND,
            scope_kind="player_season",
            scope_id=f"{external_id}:{season}",
            input_fingerprint=canonical_fingerprint(
                self._source.provider_name,
                self._source.source_version,
                external_id,
                season,
            ),
            model_version=PLAYER_HISTORY_PLAYER_SEASON_ARTIFACT_VERSION,
        )

    def _career_artifact_key(
        self,
        runtime: UserRuntimeContext,
        *,
        player_id: str,
        external_id: str,
    ) -> ArtifactKey:
        state = runtime.league_state
        if state is None:
            raise ValueError("history requires canonical league state")
        return ArtifactKey(
            artifact_kind=PLAYER_HISTORY_CAREER_ARTIFACT_KIND,
            scope_kind="league_player",
            scope_id=f"{state.league.league_id}:{player_id}",
            input_fingerprint=canonical_fingerprint(
                self._source.provider_name,
                self._source.source_version,
                external_id,
                self._minimum_season,
                state.league.season,
                state.league.rules.model_dump(mode="json"),
            ),
            model_version=PLAYER_HISTORY_CAREER_ARTIFACT_VERSION,
        )

    @staticmethod
    def _normalize_player_row(
        payload: object,
    ) -> dict[str, float | int | str] | None:
        if not isinstance(payload, dict):
            return None
        row: dict[str, float | int | str] = {}
        for key, value in payload.items():
            if isinstance(key, str) and isinstance(value, (int, float, str)):
                row[key] = value
        return row or None

    @staticmethod
    def _row_from_line(
        row,
    ) -> dict[str, float | int | str]:
        stats = {
            str(key): float(value)
            for key, value in row.stats.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        gp = stats.pop("gp", None)
        return {
            "games_played": max(0, int(round(gp))) if gp is not None else 0,
            "games_played_basis": (
                "provider season aggregate gp"
                if gp is not None
                else "unavailable: provider season aggregate omitted gp"
            ),
            "retrieved_at": row.captured_at.astimezone(UTC).isoformat(),
            **stats,
        }

    def _restore_player_season(
        self,
        *,
        external_id: str,
        season: int,
    ) -> dict[str, float | int | str] | None:
        if self._persistence_store is None:
            return None
        record = self._persistence_store.get_reusable_artifact(
            self._player_season_artifact_key(
                external_id=external_id,
                season=season,
            )
        )
        if record is None:
            return None
        return self._normalize_player_row(dict(record.payload))

    def _persist_player_season(
        self,
        *,
        external_id: str,
        season: int,
        row: dict[str, float | int | str],
    ) -> None:
        if self._persistence_store is None:
            return
        self._persistence_store.put_artifact(
            ReusableArtifactRecord(
                key=self._player_season_artifact_key(
                    external_id=external_id,
                    season=season,
                ),
                payload=row,
                computed_at=utc_now(),
            )
        )

    @staticmethod
    def _season_payload(row: HistoricalPlayerSeason) -> dict[str, object]:
        return {
            "season": row.season,
            "games_played": row.games_played,
            "fantasy_points": row.fantasy_points,
            "fantasy_ppg": row.fantasy_ppg,
            "position_rank": row.position_rank,
            "position_rank_population": row.position_rank_population,
            "rank_basis": row.rank_basis,
            "stats": row.stats,
            "more_stats": row.more_stats,
            "games_played_basis": row.games_played_basis,
            "scoring_basis": row.scoring_basis,
            "source": row.source,
            "source_version": row.source_version,
            "retrieved_at": row.retrieved_at,
        }

    @staticmethod
    def _season_from_payload(payload: object) -> HistoricalPlayerSeason | None:
        if not isinstance(payload, dict):
            return None
        try:
            stats_raw = payload.get("stats", {})
            more_raw = payload.get("more_stats", {})
            if not isinstance(stats_raw, dict) or not isinstance(more_raw, dict):
                return None
            return HistoricalPlayerSeason(
                season=int(payload["season"]),
                games_played=int(payload["games_played"]),
                fantasy_points=float(payload["fantasy_points"]),
                fantasy_ppg=(
                    float(payload["fantasy_ppg"])
                    if payload.get("fantasy_ppg") is not None
                    else None
                ),
                position_rank=(
                    int(payload["position_rank"])
                    if payload.get("position_rank") is not None
                    else None
                ),
                position_rank_population=(
                    int(payload["position_rank_population"])
                    if payload.get("position_rank_population") is not None
                    else None
                ),
                rank_basis=(
                    str(payload["rank_basis"])
                    if payload.get("rank_basis") is not None
                    else None
                ),
                stats={str(k): float(v) for k, v in stats_raw.items()},
                more_stats={str(k): float(v) for k, v in more_raw.items()},
                games_played_basis=str(payload["games_played_basis"]),
                scoring_basis=str(payload["scoring_basis"]),
                source=str(payload["source"]),
                source_version=str(payload["source_version"]),
                retrieved_at=str(payload["retrieved_at"]),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def _restore_career(
        self,
        runtime: UserRuntimeContext,
        *,
        player_id: str,
        external_id: str,
    ) -> tuple[HistoricalPlayerSeason, ...] | None:
        if self._persistence_store is None:
            return None
        record = self._persistence_store.get_reusable_artifact(
            self._career_artifact_key(
                runtime,
                player_id=player_id,
                external_id=external_id,
            )
        )
        if record is None:
            return None
        seasons_raw = record.payload.get("seasons")
        if not isinstance(seasons_raw, (list, tuple)):
            return None
        seasons: list[HistoricalPlayerSeason] = []
        for raw in seasons_raw:
            parsed = self._season_from_payload(raw)
            if parsed is None:
                return None
            seasons.append(parsed)
        return tuple(sorted(seasons, key=lambda item: item.season))

    def _persist_career(
        self,
        runtime: UserRuntimeContext,
        *,
        player_id: str,
        external_id: str,
        seasons: tuple[HistoricalPlayerSeason, ...],
    ) -> None:
        if self._persistence_store is None:
            return
        state = runtime.league_state
        if state is None:
            raise ValueError("history requires canonical league state")
        self._persistence_store.put_artifact(
            ReusableArtifactRecord(
                key=self._career_artifact_key(
                    runtime,
                    player_id=player_id,
                    external_id=external_id,
                ),
                payload={
                    "league_id": state.league.league_id,
                    "player_id": player_id,
                    "external_id": external_id,
                    "source": self._source.provider_name,
                    "source_version": self._source.source_version,
                    "seasons": [self._season_payload(row) for row in seasons],
                },
                computed_at=utc_now(),
            )
        )

    def _weekly_player_fallback(
        self,
        *,
        season: int,
        external_id: str,
    ) -> dict[str, float | int | str] | None:
        aggregate: dict[str, float | int | str] | None = None
        target_id = f"sleeper:player:{external_id}"
        for week in range(1, 19):
            batch = self._source.fetch_week(season=season, week=week)
            row = next((item for item in batch if item.player_id == target_id), None)
            if row is None:
                continue
            if aggregate is None:
                aggregate = {
                    "games_played": 0,
                    "games_played_basis": "weekly provider gp",
                    "retrieved_at": row.captured_at.astimezone(UTC).isoformat(),
                }
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
                aggregate["games_played_basis"] = (
                    "weekly non-zero measured-production fallback; provider gp absent"
                )
            aggregate["games_played"] = int(aggregate["games_played"]) + increment
            for stat, value in row.stats.items():
                if stat == "gp":
                    continue
                aggregate[stat] = float(aggregate.get(stat, 0.0)) + float(value)
        return aggregate

    def _acquire_player_season(
        self,
        *,
        season: int,
        external_id: str,
    ) -> dict[str, float | int | str] | None:
        fetch_player = getattr(self._source, "fetch_season_player", None)
        if callable(fetch_player):
            line = fetch_player(season=season, player_id=external_id)
            return self._row_from_line(line) if line is not None else None

        fetch_season = getattr(self._source, "fetch_season", None)
        if callable(fetch_season):
            target_id = f"sleeper:player:{external_id}"
            rows = fetch_season(season=season)
            line = next((item for item in rows if item.player_id == target_id), None)
            return self._row_from_line(line) if line is not None else None

        return self._weekly_player_fallback(
            season=season,
            external_id=external_id,
        )

    def _player_season(
        self,
        *,
        season: int,
        external_id: str,
    ) -> dict[str, float | int | str] | None:
        persisted = self._restore_player_season(
            external_id=external_id,
            season=season,
        )
        if persisted is not None:
            return persisted
        row = self._acquire_player_season(
            season=season,
            external_id=external_id,
        )
        if row is not None:
            self._persist_player_season(
                external_id=external_id,
                season=season,
                row=row,
            )
        return row

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

        restored = self._restore_career(
            runtime,
            player_id=player_id,
            external_id=external_id,
        )
        if restored is not None:
            return restored

        output: list[HistoricalPlayerSeason] = []
        for season in range(self._minimum_season, state.league.season):
            row = self._player_season(
                season=season,
                external_id=external_id,
            )
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
                        "unavailable: complete point-in-time historical position "
                        "population is not persisted"
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

        result = tuple(output)
        self._persist_career(
            runtime,
            player_id=player_id,
            external_id=external_id,
            seasons=result,
        )
        return result

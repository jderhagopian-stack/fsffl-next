from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
import logging
from threading import RLock

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from fsffl.persistence.contracts import PersistenceStore
from fsffl.value.shapley_intrinsic_contract import ShapleyIntrinsicAvailability

from .intrinsic_background import IntrinsicBuildStatus, ShapleyIntrinsicBackgroundCoordinator
from .player_intelligence import (
    PLAYER_INTELLIGENCE_CONTRACT_VERSION,
    HistoricalPlayerSeason,
    PlayerFutureForecastCache,
    PlayerHistoryService,
    build_player_intelligence_overview,
)
from .resource_coordinator import HeavyWorkCoordinator
from .runtime import PrivateBetaRuntimeStore, UserRuntimeContext


INVALID_PLAYER_IDS = {"", "null", "undefined", "none"}
_logger = logging.getLogger("uvicorn.error")


def _validated_player_id(player_id: str) -> str:
    cleaned = str(player_id or "").strip()
    if cleaned.lower() in INVALID_PLAYER_IDS:
        raise HTTPException(
            status_code=404,
            detail="Player Intelligence requires a valid player id",
        )
    return cleaned


class PlayerHistoryCapacityError(RuntimeError):
    """Bounded background history queue is busy; callers may retry later."""


class PlayerHistoryBuildStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class PlayerHistoryBuildRecord:
    league_state_id: str
    player_id: str
    status: PlayerHistoryBuildStatus
    created_at: datetime
    updated_at: datetime
    seasons: tuple[HistoricalPlayerSeason, ...] = ()
    error: str | None = None


class PlayerHistoryBackgroundCoordinator:
    """Bound external historical-stat acquisition away from mobile requests."""

    def __init__(
        self,
        service: PlayerHistoryService,
        *,
        max_workers: int = 1,
        max_pending: int = 2,
        max_records: int = 12,
        heavy_work_coordinator: HeavyWorkCoordinator | None = None,
    ) -> None:
        if max_pending < 1 or max_records < max_pending:
            raise ValueError("history queue bounds are invalid")
        self._service = service
        self._max_pending = int(max_pending)
        self._max_records = int(max_records)
        self._heavy_work_coordinator = heavy_work_coordinator
        self._lock = RLock()
        self._records: dict[tuple[str, str], PlayerHistoryBuildRecord] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="fsffl-player-history",
        )

    @staticmethod
    def _key(context: UserRuntimeContext, player_id: str) -> tuple[str, str]:
        if context.league_state is None:
            raise ValueError("Player Intelligence history requires canonical league state")
        return context.league_state.state_id, player_id

    def request(
        self,
        context: UserRuntimeContext,
        player_id: str,
    ) -> PlayerHistoryBuildRecord:
        key = self._key(context, player_id)
        now = datetime.now(UTC)
        with self._lock:
            existing = self._records.get(key)
            if existing is not None:
                return existing
            active_count = sum(
                1
                for item in self._records.values()
                if item.status in {
                    PlayerHistoryBuildStatus.QUEUED,
                    PlayerHistoryBuildStatus.RUNNING,
                }
            )
            if active_count >= self._max_pending:
                raise PlayerHistoryCapacityError(
                    "Player history preparation is busy; retry after current work completes."
                )
            if len(self._records) >= self._max_records:
                terminal = sorted(
                    (
                        (record_key, item)
                        for record_key, item in self._records.items()
                        if item.status in {
                            PlayerHistoryBuildStatus.COMPLETED,
                            PlayerHistoryBuildStatus.FAILED,
                        }
                    ),
                    key=lambda pair: pair[1].updated_at,
                )
                while len(self._records) >= self._max_records and terminal:
                    stale_key, _ = terminal.pop(0)
                    self._records.pop(stale_key, None)
            record = PlayerHistoryBuildRecord(
                league_state_id=key[0],
                player_id=player_id,
                status=PlayerHistoryBuildStatus.QUEUED,
                created_at=now,
                updated_at=now,
            )
            self._records[key] = record
            self._executor.submit(self._run, key, context)
            return record

    def _run(
        self,
        key: tuple[str, str],
        context: UserRuntimeContext,
    ) -> None:
        self._update(key, status=PlayerHistoryBuildStatus.RUNNING)
        try:
            if self._heavy_work_coordinator is None:
                seasons = self._service.player_history(context, key[1])
            else:
                with self._heavy_work_coordinator.claim(
                    kind="player_history",
                    key=f"{key[0]}:{key[1]}",
                ):
                    seasons = self._service.player_history(context, key[1])
        except Exception as exc:
            self._update(
                key,
                status=PlayerHistoryBuildStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
            )
            return
        self._update(
            key,
            status=PlayerHistoryBuildStatus.COMPLETED,
            seasons=seasons,
        )

    def _update(
        self,
        key: tuple[str, str],
        *,
        status: PlayerHistoryBuildStatus,
        seasons: tuple[HistoricalPlayerSeason, ...] = (),
        error: str | None = None,
    ) -> None:
        with self._lock:
            current = self._records[key]
            self._records[key] = replace(
                current,
                status=status,
                seasons=seasons,
                error=error,
                updated_at=datetime.now(UTC),
            )


def install_player_intelligence_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    require_user,
    intrinsic_coordinator: ShapleyIntrinsicBackgroundCoordinator,
    future_cache: PlayerFutureForecastCache | None = None,
    history_coordinator: PlayerHistoryBackgroundCoordinator | None = None,
    persistence_store: PersistenceStore | None = None,
    heavy_work_coordinator: HeavyWorkCoordinator | None = None,
) -> None:
    future_forecasts = future_cache or PlayerFutureForecastCache()
    history = history_coordinator or PlayerHistoryBackgroundCoordinator(
        PlayerHistoryService(persistence_store=persistence_store),
        max_workers=1,
        max_pending=2,
        max_records=12,
        heavy_work_coordinator=heavy_work_coordinator,
    )

    # Acceptance/observability may inspect the exact same bounded coordinator
    # used by the live route. This does not create a second history cache or worker.
    app.state.player_history_coordinator = history

    @app.get("/api/player-intelligence/{player_id}")
    def player_intelligence(
        player_id: str,
        user_id: str = Depends(require_user),
    ):
        player_id = _validated_player_id(player_id)
        runtime = runtime_store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(
                status_code=409,
                detail="Connect a league before requesting Player Intelligence",
            )
        try:
            intrinsic_record = intrinsic_coordinator.request(runtime)
            intrinsic = (
                intrinsic_record.contract
                if intrinsic_record.status == IntrinsicBuildStatus.COMPLETED
                else None
            )
            payload = build_player_intelligence_overview(
                runtime,
                player_id,
                intrinsic=intrinsic,
                future_cache=future_forecasts,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        value = dict(payload["value"])
        value["intrinsic_lifecycle_status"] = intrinsic_record.status.value
        if intrinsic_record.status in {
            IntrinsicBuildStatus.QUEUED,
            IntrinsicBuildStatus.RUNNING,
        }:
            value["intrinsic_status"] = intrinsic_record.status.value
        elif intrinsic_record.status == IntrinsicBuildStatus.FAILED:
            value["intrinsic_status"] = "unavailable"
            value["intrinsic_error"] = (
                intrinsic_record.error
                or "Governed FSFFL Intrinsic background preparation failed."
            )
        elif intrinsic is None:
            value["intrinsic_status"] = "unavailable"
            value["intrinsic_error"] = (
                "Governed FSFFL Intrinsic lifecycle completed without a contract."
            )
        elif (
            intrinsic.status == ShapleyIntrinsicAvailability.UNAVAILABLE
            or not intrinsic.estimates
        ):
            value["intrinsic_status"] = "unavailable"
            value["intrinsic_contract_status"] = intrinsic.status.value
            value["intrinsic_error"] = (
                intrinsic.status_reason
                or "Governed FSFFL Intrinsic contract is explicitly unavailable."
            )
        elif value.get("raw_shapley_marginal_points") is None:
            value["intrinsic_status"] = "unavailable"
            value["intrinsic_contract_status"] = intrinsic.status.value
            value["intrinsic_error"] = (
                "This player is outside the governed H3/Future-I1 subject cohort "
                "or lacks compatible preserved Year-1 evidence."
            )
        else:
            value["intrinsic_status"] = "ready"
            value["intrinsic_contract_status"] = intrinsic.status.value
            value["intrinsic_status_reason"] = intrinsic.status_reason
        payload["value"] = value
        payload["publication_generation_id"] = getattr(
            runtime,
            "publication_generation_id",
            None,
        )
        if intrinsic_record.status in {
            IntrinsicBuildStatus.QUEUED,
            IntrinsicBuildStatus.RUNNING,
        }:
            payload["retry_after_ms"] = 1500
        forecast_years = [
            item.get("year_index")
            for item in payload.get("forecast", {}).get("rows", [])
            if item.get("year_index") is not None
        ]
        _logger.info(
            "FSFFL Player Intelligence served state=%s intrinsic=%s lifecycle=%s forecast_years=%s future_error=%s",
            runtime.league_state.state_id,
            value.get("intrinsic_status"),
            value.get("intrinsic_lifecycle_status"),
            forecast_years,
            bool(payload.get("forecast", {}).get("future_error")),
        )
        return payload

    @app.get("/api/player-intelligence/{player_id}/history")
    def player_intelligence_history(
        player_id: str,
        user_id: str = Depends(require_user),
    ):
        player_id = _validated_player_id(player_id)
        runtime = runtime_store.get(user_id)
        if runtime.league_state is None:
            raise HTTPException(
                status_code=409,
                detail="Connect a league before requesting Player Intelligence history",
            )
        try:
            record = history.request(runtime, player_id)
        except PlayerHistoryCapacityError as exc:
            # Capacity is a bounded admission wait, not a terminal availability
            # failure. Keep the response successful so the existing browser
            # loading/polling contract honors retry_after_ms.
            return JSONResponse(
                status_code=200,
                content={
                    "status": "loading",
                    "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
                    "league_state_id": runtime.league_state.state_id,
                    "publication_generation_id": getattr(
                        runtime,
                        "publication_generation_id",
                        None,
                    ),
                    "player_id": player_id,
                    "build_status": "capacity_wait",
                    "retry_after_ms": 2500,
                    "message": str(exc),
                },
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        if record.status in {
            PlayerHistoryBuildStatus.QUEUED,
            PlayerHistoryBuildStatus.RUNNING,
        }:
            return JSONResponse(
                status_code=202,
                content={
                    "status": "loading",
                    "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
                    "league_state_id": record.league_state_id,
                    "publication_generation_id": getattr(
                        runtime,
                        "publication_generation_id",
                        None,
                    ),
                    "player_id": player_id,
                    "build_status": record.status.value,
                    "retry_after_ms": 2500,
                    "message": "Historical NFL actuals are being prepared server-side.",
                },
            )
        if record.status == PlayerHistoryBuildStatus.FAILED:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unavailable",
                    "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
                    "league_state_id": record.league_state_id,
                    "publication_generation_id": getattr(
                        runtime,
                        "publication_generation_id",
                        None,
                    ),
                    "player_id": player_id,
                    "build_status": record.status.value,
                    "retry_after_ms": None,
                    "message": record.error or "Historical NFL actuals are unavailable.",
                },
            )
        return {
            "status": "ready",
            "contract_version": PLAYER_INTELLIGENCE_CONTRACT_VERSION,
            "league_state_id": record.league_state_id,
            "player_id": player_id,
            "scoring_basis": "scored under current league rules",
            "history_boundary": {
                "minimum_season": 2010,
                "current_season_included": False,
                "basis": (
                    "Sleeper detailed regular-season stats provider-supported "
                    "2010+ range; only seasons with selected-player evidence returned"
                ),
            },
            "seasons": [
                {
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
                for row in record.seasons
            ],
        }

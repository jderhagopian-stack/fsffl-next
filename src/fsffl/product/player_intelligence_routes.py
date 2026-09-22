from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
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
from .runtime import PrivateBetaRuntimeStore, UserRuntimeContext


INVALID_PLAYER_IDS = {"", "null", "undefined", "none"}


def _validated_player_id(player_id: str) -> str:
    cleaned = str(player_id or "").strip()
    if cleaned.lower() in INVALID_PLAYER_IDS:
        raise HTTPException(
            status_code=404,
            detail="Player Intelligence requires a valid player id",
        )
    return cleaned


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
    ) -> None:
        self._service = service
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
) -> None:
    future_forecasts = future_cache or PlayerFutureForecastCache()
    history = history_coordinator or PlayerHistoryBackgroundCoordinator(
        PlayerHistoryService(persistence_store=persistence_store),
        max_workers=1,
    )

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
        else:
            value["intrinsic_status"] = "ready"
            value["intrinsic_contract_status"] = intrinsic.status.value
            value["intrinsic_status_reason"] = intrinsic.status_reason
        payload["value"] = value
        if intrinsic_record.status in {
            IntrinsicBuildStatus.QUEUED,
            IntrinsicBuildStatus.RUNNING,
        }:
            payload["retry_after_ms"] = 1500
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
                    "player_id": player_id,
                    "build_status": record.status.value,
                    "retry_after_ms": 1500,
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

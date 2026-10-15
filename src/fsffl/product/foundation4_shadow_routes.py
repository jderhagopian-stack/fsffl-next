from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from fsffl.analytics.dynasty_position_room import build_dynasty_position_rooms
from .foundation4_career_forward_runtime import CareerIntrinsicLoader
from .career_presentation import CareerPresentationCoordinate
from .foundation4_shadow_inputs import provide_foundation4_terminal_features
from .career_coverage import (
    build_career_position_depth_refresh,
    select_career_coverage,
)
from .intrinsic_background import IntrinsicBuildStatus, ShapleyIntrinsicBackgroundCoordinator
from .presentation_continuity import LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE
from .runtime import PrivateBetaRuntimeStore
from .webapp import require_beta_user


CAREER_INTRINSIC_ENDPOINT = "/api/value/career-intrinsic-v1"
LEGACY_FOUNDATION4_CAREER_FORWARD_ENDPOINT = "/api/value/long-term-intrinsic-shadow-v1"
FOUNDATION4_CAREER_FORWARD_ENDPOINT = CAREER_INTRINSIC_ENDPOINT
FOUNDATION4_Y4_Y7_ENDPOINT = "/api/value/long-horizon-y4-y7-shadow-v1"


@lru_cache(maxsize=1)
def _reference_player_ids() -> frozenset[str]:
    # Retain only small identity data, not the terminal-feature object graph.
    return frozenset(provide_foundation4_terminal_features())


def _building_payload(record) -> dict[str, object]:
    return {
        "status": "building",
        "capability": "career_intrinsic",
        "build_status": record.status.value,
        "league_state_id": record.league_state_id,
        "input_fingerprint": record.intrinsic_input_fingerprint,
        "current_intrinsic_replaced": False,
        "retry_after_ms": 3000,
    }


def _dynasty_rank_readiness(rooms: object) -> dict[str, object]:
    """Report whether every required position has complete league-wide ranks."""

    positions = ("QB", "RB", "WR", "TE")
    room_rows = rooms if isinstance(rooms, list) else []
    coverage: dict[str, dict[str, int]] = {}
    incomplete: list[str] = []
    for position in positions:
        rows = [row for row in room_rows if isinstance(row, dict) and row.get("position") == position]
        first = rows[0] if rows else {}
        team_count = first.get("team_count")
        coverage_count = first.get("coverage_count")
        complete = (
            isinstance(team_count, int) and not isinstance(team_count, bool)
            and team_count > 0 and len(rows) == team_count
            and isinstance(coverage_count, int) and not isinstance(coverage_count, bool)
            and coverage_count == team_count
            and len({row.get("team_id") for row in rows}) == team_count
            and all(row.get("evidence_complete") is True
                    and isinstance(row.get("league_rank"), int)
                    and not isinstance(row.get("league_rank"), bool) for row in rows)
        )
        coverage[position] = {
            "coverage_count": coverage_count if isinstance(coverage_count, int) else 0,
            "team_count": team_count if isinstance(team_count, int) else 0,
        }
        if not complete:
            incomplete.append(position)
    return {"status": "incomplete" if incomplete else "ready",
            "incomplete_positions": incomplete, "coverage": coverage}


def _dynasty_publication_payload(
    context,
    payload: dict[str, object],
) -> dict[str, object]:
    """Bind Dynasty truth to the exact published runtime generation."""

    result = dict(payload)
    result["publication_generation_id"] = context.publication_generation_id
    if result.get("status") == "ready":
        result["dynasty_rank_readiness"] = _dynasty_rank_readiness(result.get("rooms"))
    return result


def _carry_dynasty_last_good(payload: dict[str, object], *, state_id: str) -> dict[str, object]:
    """Carry historical Dynasty estimates without exact-State roster rows."""
    result = dict(payload)
    result["dynasty_evidence_status"] = "last_good"
    result["dynasty_evidence_state_id"] = payload.get("league_state_id")
    result["dynasty_evidence_publication_generation_id"] = payload.get(
        "publication_generation_id"
    )
    result["league_state_id"] = state_id
    for key in (
        "publication_generation_id",
        "intelligence_freshness",
        "presentation_continuity",
        "career_position_depth",
    ):
        result.pop(key, None)
    return result


def _career_position_depth_rows(state, career_forward) -> list[dict[str, object]]:
    """Publish exact-State roster coverage beside Career and Dynasty evidence.

    Career contracts can legitimately have a narrower frozen cohort than the
    connected league State. Emit one QB/RB/WR/TE row per roster identity so a
    missing Career estimate stays visible for that player and cannot suppress
    the rest of the matching-State publication.
    """
    player_by_id = {player.player_id: player for player in state.players}
    roster_rows: list[dict[str, object]] = []
    for team_state in state.team_states:
        for entry in team_state.roster:
            player = player_by_id.get(entry.player_id)
            position = str(player.position.value) if player is not None else ""
            if player is not None and position not in {"QB", "RB", "WR", "TE"}:
                continue
            roster_rows.append({
                "player_id": entry.player_id,
                "position": position,
                "team_id": team_state.team_id,
                "roster_slot": str(entry.slot.value),
                "state_hash": state.state_id,
            })

    state_players = [
        {"player_id": player.player_id, "position": str(player.position.value)}
        for player in state.players
    ]
    subjects = select_career_coverage(
        state_players=state_players,
        roster_rows=roster_rows,
        state_hash=state.state_id,
    )
    estimate_ids = {row.player_id for row in career_forward.estimates}
    roster_ids = {str(row["player_id"]) for row in roster_rows}
    failures = dict(getattr(career_forward, "player_coverage_failures", {}))
    failures.update({
        player_id: "career_estimate_missing_from_exact_state_contract"
        for player_id in roster_ids - estimate_ids
        if player_id not in failures
    })
    rows = build_career_position_depth_refresh(
        state_hash=state.state_id,
        roster_rows=roster_rows,
        subjects=subjects,
        authority={player_id: True for player_id in estimate_ids},
        failures=failures,
    )
    return [dict(row) for row in rows]


def install_career_intrinsic_routes(
    app: FastAPI,
    *,
    runtime_store: PrivateBetaRuntimeStore,
    loader: CareerIntrinsicLoader,
    coordinator: ShapleyIntrinsicBackgroundCoordinator,
    presentation_payload_loader=None,
) -> None:
    def _record(user_id: str):
        context = runtime_store.get(user_id)
        if context.league_state is None:
            raise HTTPException(
                status_code=409,
                detail="Connect a league before requesting Long-Term Intrinsic shadow",
            )
        return context, coordinator.current(context)

    @app.get(LEGACY_FOUNDATION4_CAREER_FORWARD_ENDPOINT)
    @app.get(CAREER_INTRINSIC_ENDPOINT)
    def career_forward_shadow(
        request: Request,
        state_id: str | None = None,
        publication_generation_id: str | None = None,
        user_id: str = Depends(require_beta_user),
    ):
        _context, record = _record(user_id)
        if ((state_id is not None and state_id != _context.league_state.state_id)
                or (publication_generation_id is not None
                    and publication_generation_id != _context.publication_generation_id)):
            return JSONResponse(status_code=409, content={
                "status": "superseded",
                "league_state_id": _context.league_state.state_id,
                "publication_generation_id": _context.publication_generation_id,
                "reason": "Career evidence must match the publication actually displayed.",
            })
        if record is None:
            return JSONResponse(status_code=503, content={
                "status": "refresh_required",
                "league_state_id": _context.league_state.state_id,
                "publication_generation_id": _context.publication_generation_id,
                "reason": "No compatible Career publication is available. Use the explicit intelligence preparation action.",
            })
        if record.status in {IntrinsicBuildStatus.QUEUED, IntrinsicBuildStatus.RUNNING}:
            building = _building_payload(record)
            building["publication_generation_id"] = _context.publication_generation_id
            return JSONResponse(status_code=202, content=building)
        if record.status == IntrinsicBuildStatus.FAILED:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unavailable",
                    "capability": "career_intrinsic",
                    "reason": record.error or "Career Intrinsic build failed",
                    "current_intrinsic_replaced": False,
                },
            )
        if record.contract is None:
            raise HTTPException(
                status_code=503,
                detail="Career Intrinsic lifecycle completed without a governed contract",
            )
        # Product readers need economic totals and provenance, not the full
        # per-horizon uncertainty matrices. Keep the explicit detail endpoint
        # compatible, without allocating those matrices for every browser poll.
        canonical = request.url.path == CAREER_INTRINSIC_ENDPOINT
        payload = record.contract.model_dump(
            mode="json",
            exclude={"estimates": {"__all__": {"uncertainty"}}} if canonical else None,
        )
        if canonical:
            payload["uncertainty_detail_endpoint"] = LEGACY_FOUNDATION4_CAREER_FORWARD_ENDPOINT
        payload["league_state_id"] = record.league_state_id
        payload["publication_generation_id"] = _context.publication_generation_id
        payload["career_position_depth"] = _career_position_depth_rows(
            _context.league_state, record.contract
        )
        # The reference game is Current-owned; dynamic roster additions never
        # change its presentation ruler or participate as Market inputs.
        frozen_ids = _reference_player_ids()
        raw = {row.player_id: row.raw_career_forward_reference for row in record.contract.estimates}
        reference_ids = frozenset(frozen_ids & raw.keys())
        try:
            coordinate = CareerPresentationCoordinate.from_reference(raw, reference_ids=reference_ids)
        except ValueError as exc:
            payload["career_presentation"] = {"status": "unavailable", "reason": str(exc)}
        else:
            payload["career_presentation"] = {"status": "ready", **coordinate.summary(),
                "inactive_reference_player_ids": sorted(frozen_ids - reference_ids)}
            for row in payload["estimates"]:
                row["career_intrinsic_index"] = coordinate.index(row["raw_career_forward_reference"])
        payload["capability"] = "career_intrinsic"
        payload["value_label"] = "Career Intrinsic"
        if request.url.path == CAREER_INTRINSIC_ENDPOINT:
            # Canonical production consumers must not inherit the accepted
            # Foundation 4 contract's historical shadow lifecycle label.
            payload["status"] = "ready"
        return payload

    @app.get("/api/league/dynasty-position-rooms")
    def dynasty_position_rooms(
        state_id: str,
        publication_generation_id: str,
        user_id: str = Depends(require_beta_user),
    ):
        """Return Dynasty rooms only for the exact League Atlas publication requested."""

        context = runtime_store.get(user_id)
        if context.league_state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        state = context.league_state
        if (
            state_id != state.state_id
            or publication_generation_id != context.publication_generation_id
        ):
            # Atlas may remain visible while the mutable runtime advances. Never
            # answer that old request with evidence for this newer publication.
            return {
                "status": "superseded",
                "requested_state_id": state_id,
                "requested_publication_generation_id": publication_generation_id,
                "superseding_state_id": state.state_id,
                "superseding_publication_generation_id": context.publication_generation_id,
                "reason": "The League Atlas publication has advanced; promote Atlas before retrying.",
            }

        # Canonical Career Intrinsic is authoritative. A persisted presentation
        # snapshot is only last-good fallback while the exact-State production
        # artifact is preparing; it must never mask newly ready Career evidence.
        record = coordinator.current(context)
        if (
            record is not None
            and record.status == IntrinsicBuildStatus.COMPLETED
            and record.contract is not None
            and record.league_state_id == state.state_id
        ):
            rooms = build_dynasty_position_rooms(
                state,
                career_forward=record.contract,
                evidence_state_id=record.league_state_id,
            )
            return _dynasty_publication_payload(
                context,
                {
                    "status": "ready",
                    "capability": "career_intrinsic",
                    "league_state_id": state.state_id,
                    "input_fingerprint": record.intrinsic_input_fingerprint,
                    "model_version": rooms[0].model_version if rooms else None,
                    "rooms": [row.model_dump(mode="json") for row in rooms],
                    "career_position_depth": _career_position_depth_rows(
                        state, record.contract
                    ),
                },
            )

        persisted = None
        if presentation_payload_loader is not None:
            persisted = presentation_payload_loader(
                user_id,
                context,
                LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE,
            )
            if (
                persisted is not None
                and persisted.get("status") == "ready"
                and persisted.get("league_id") == state.league.league_id
                and persisted.get("league_state_id") == state.state_id
                and persisted.get("publication_generation_id")
                == context.publication_generation_id
            ):
                # The continuity loader validates league, team, promotion and
                # payload integrity. Dynasty must additionally be current-State
                # evidence: its consumer intentionally rejects last-good State.
                return _dynasty_publication_payload(context, persisted)

        # No canonical or verified last-good evidence is available. Request the
        # production Career lifecycle and report its real state; never fabricate
        # zero/empty Dynasty strength.
        if record is None:
            return _dynasty_publication_payload(context, {
                "status": "refresh_required",
                "capability": "career_intrinsic",
                "league_state_id": state.state_id,
                "reason": "No compatible Career publication is available; explicit intelligence preparation is required.",
            })
        if record.status in {IntrinsicBuildStatus.QUEUED, IntrinsicBuildStatus.RUNNING}:
            payload = _building_payload(record)
            payload["status"] = "preparing"
            return _dynasty_publication_payload(context, payload)
        if record.status == IntrinsicBuildStatus.FAILED or record.contract is None:
            return _dynasty_publication_payload(
                context,
                {
                    "status": "unavailable",
                    "capability": "career_intrinsic",
                    "league_state_id": state.state_id,
                    "reason": record.error or "Career Intrinsic evidence is unavailable",
                },
            )
        if record.league_state_id != state.state_id:
            return _dynasty_publication_payload(
                context,
                {
                    "status": "unavailable",
                    "capability": "career_intrinsic",
                    "league_state_id": state.state_id,
                    "reason": "Career Intrinsic evidence does not match the current league State",
                },
            )
        rooms = build_dynasty_position_rooms(
            state,
            career_forward=record.contract,
            evidence_state_id=record.league_state_id,
        )
        return _dynasty_publication_payload(
            context,
            {
                "status": "ready",
                "capability": "career_intrinsic",
                "league_state_id": state.state_id,
                "input_fingerprint": record.intrinsic_input_fingerprint,
                "model_version": rooms[0].model_version if rooms else None,
                "rooms": [row.model_dump(mode="json") for row in rooms],
                "career_position_depth": _career_position_depth_rows(
                    state, record.contract
                ),
            },
        )

    @app.get(FOUNDATION4_Y4_Y7_ENDPOINT)
    def y4_y7_shadow(user_id: str = Depends(require_beta_user)):
        context, record = _record(user_id)
        if record is None:
            raise HTTPException(status_code=503, detail="Prepare Career Intrinsic explicitly before requesting its component")
        if record.status in {IntrinsicBuildStatus.QUEUED, IntrinsicBuildStatus.RUNNING}:
            return JSONResponse(status_code=202, content=_building_payload(record))
        if record.status == IntrinsicBuildStatus.FAILED:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unavailable",
                    "shadow": True,
                    "reason": record.error or "Foundation 4 shadow build failed",
                    "current_intrinsic_replaced": False,
                },
            )
        component = loader.current_component(context)
        if component is None:
            raise HTTPException(
                status_code=503,
                detail="Foundation 4 Y4-Y7 shadow component is not available",
            )
        return component.model_dump(mode="json")


# Compatibility installer retained while callers/tests migrate from the accepted
# Foundation 4 shadow name. It installs the canonical production routes above.
install_foundation4_shadow_routes = install_career_intrinsic_routes

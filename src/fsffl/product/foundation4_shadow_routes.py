from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from fsffl.analytics.dynasty_position_room import (
    build_dynasty_position_rooms,
    build_three_year_position_rooms,
    build_three_year_intrinsic_player_values,
    three_year_source_reconciles_career_components,
)
from .foundation4_career_forward_runtime import CareerIntrinsicLoader
from .career_presentation import career_lens_for_publication, career_reference_ids_from_current
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
    state_hash = state.state_id
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
                "state_hash": state_hash,
            })

    state_players = [
        {"player_id": player.player_id, "position": str(player.position.value)}
        for player in state.players
    ]
    subjects = select_career_coverage(
        state_players=state_players,
        roster_rows=roster_rows,
        state_hash=state_hash,
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
        state_hash=state_hash,
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
    career_publication_validator=None,
    three_year_publication_validator=None,
    current_intrinsic_coordinator: ShapleyIntrinsicBackgroundCoordinator | None = None,
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
                "reason": "Career is not prepared for this publication. Refresh league intelligence to prepare it.",
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
        if (career_publication_validator is not None
                and not career_publication_validator(_context, record)):
            return JSONResponse(status_code=202, content={
                "status": "building", "build_status": "publication_pending",
                "capability": "career_intrinsic", "retry_after_ms": 3000,
                "league_state_id": _context.league_state.state_id,
                "publication_generation_id": _context.publication_generation_id,
                "reason": "Career is complete; its presentation publication is pending.",
            })
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
        from .dynamic_career_composition import DYNAMIC_CAREER_SOURCE_REFRESH_INTERVAL
        selected_as_of = loader.pin_build_context(_context).career_fingerprint_evaluation_as_of
        payload["source_selection_as_of"] = selected_as_of.isoformat()
        payload["source_refresh_due"] = datetime.now(UTC) - selected_as_of >= DYNAMIC_CAREER_SOURCE_REFRESH_INTERVAL
        # Age is presentation/readiness metadata. It never changes the artifact
        # key or silently starts a new provider capture on a browser read.
        payload["career_position_depth"] = _career_position_depth_rows(
            _context.league_state, record.contract
        )
        # The reference game is Current-owned; dynamic roster additions never
        # change its presentation ruler or participate as Market inputs.
        reference_ids = (career_reference_ids_from_current(current_intrinsic_coordinator.current(_context))
                         if current_intrinsic_coordinator is not None else None)
        summary, presentation_rows = career_lens_for_publication(
            record, served_state_id=record.league_state_id, reference_ids=reference_ids,
        )
        payload["career_presentation"] = summary
        for row in payload["estimates"]:
            row["career_intrinsic_index"] = presentation_rows.get(row["player_id"], {}).get("career_intrinsic_index")
            row["career_input_assumption"] = presentation_rows.get(row["player_id"], {}).get("career_input_assumption")
        payload["capability"] = "career_intrinsic"
        payload["value_label"] = "Career Intrinsic"
        if request.url.path == CAREER_INTRINSIC_ENDPOINT:
            # Canonical production consumers must not inherit the accepted
            # Foundation 4 contract's historical shadow lifecycle label.
            payload["status"] = "ready"
        return payload

    @app.get("/api/league/three-year-position-rooms")
    def three_year_position_rooms(
        state_id: str, publication_generation_id: str,
        user_id: str = Depends(require_beta_user),
    ):
        context = runtime_store.get(user_id)
        state = context.league_state
        if state is None:
            raise HTTPException(status_code=409, detail="No league is loaded")
        if state_id != state.state_id or publication_generation_id != context.publication_generation_id:
            return {"status": "superseded", "superseding_state_id": state.state_id,
                    "superseding_publication_generation_id": context.publication_generation_id}
        # Read the completed owner only. This GET never starts fitting or provider work.
        record = (current_intrinsic_coordinator.completed_for_state(context)
                  if current_intrinsic_coordinator is not None else None)
        if record is not None and record.league_state_id != state_id:
            record = None
        # This second lookup is also bounded and memory-only. It can supply only
        # retained Current Y1-Y3 Shapley components for roster players missing
        # from the stand-alone 3-Year cohort; it cannot restore or fit Career.
        career_record = (
            coordinator.completed_for_state(context)
            if coordinator is not None else None
        )
        if career_record is not None and career_record.league_state_id != state_id:
            career_record = None
        base = {"league_state_id": state_id,
                "publication_generation_id": publication_generation_id,
                "capability": "three_year_intrinsic"}
        intrinsic = record.contract if record is not None else None
        career_forward = career_record.contract if career_record is not None else None
        if (
            record is None
            or career_record is None
            or three_year_publication_validator is None
            or not three_year_publication_validator(context, record, career_record)
        ):
            return {**base, "status": "unavailable",
                    "reason": "3-Year and Career evidence are not bound to the active publication generation."}
        player_values = build_three_year_intrinsic_player_values(
            state,
            intrinsic=intrinsic,
            evidence_state_id=(record.league_state_id if record is not None else None),
            career_forward=career_forward,
            career_evidence_state_id=(
                career_record.league_state_id if career_record is not None else None
            ),
        )
        if not player_values:
            return {**base, "status": "unavailable",
                    "reason": "No completed 3-Year or matching Career Current Y1-Y3 evidence matches this State."}
        rooms = build_three_year_position_rooms(
            state, intrinsic=intrinsic,
            evidence_state_id=(record.league_state_id if record is not None else None),
            career_forward=career_forward,
            career_evidence_state_id=(
                career_record.league_state_id if career_record is not None else None
            ),
        )
        rows = [row.model_dump(mode="json") for row in rooms]
        players = [row.model_dump(mode="json") for row in player_values]
        state_players = {item.player_id: item for item in state.players}
        rostered = {
            (entry.player_id, state_players[entry.player_id].position)
            for team_state in state.team_states
            for entry in team_state.roster
            if entry.player_id in state_players
        }
        coverage = {}
        values_by_id = {row.player_id: row for row in player_values}
        for position in ("QB", "RB", "WR", "TE"):
            members = {player_id for player_id, actual in rostered if actual.value == position}
            covered = members & set(values_by_id)
            extended = sum(
                values_by_id[player_id].source == "career_current_y1_y3_discounted_extension"
                for player_id in covered
            )
            coverage[position] = {
                "rostered": len(members),
                "covered": len(covered),
                "extended_from_career_current_components": extended,
            }
        return {**base, "status": "ready",
                "input_fingerprint": (
                    record.intrinsic_input_fingerprint if record is not None
                    else career_record.intrinsic_input_fingerprint
                ),
                "source_input_fingerprints": {
                    "standalone_three_year": (
                        record.intrinsic_input_fingerprint if record is not None else None
                    ),
                    "career_current_components": (
                        career_record.intrinsic_input_fingerprint
                        if career_record is not None else None
                    ),
                },
                "model_version": rooms[0].model_version if rooms else None,
                "rooms": rows, "dynasty_rank_readiness": _dynasty_rank_readiness(rows),
                "coverage": coverage, "players": players}

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

        pending_record = coordinator.current(context)
        if (pending_record is not None
                and pending_record.status == IntrinsicBuildStatus.COMPLETED
                and pending_record.contract is not None
                and career_publication_validator is not None
                and not career_publication_validator(context, pending_record)):
            return _dynasty_publication_payload(context, {
                "status": "preparing", "build_status": "publication_pending",
                "league_state_id": state.state_id, "retry_after_ms": 3000,
                "reason": "Career is complete; its presentation publication is pending.",
            })

        # Canonical Career Intrinsic is authoritative. A persisted presentation
        # snapshot is only last-good fallback while the exact-State production
        # artifact is preparing; it must never mask newly ready Career evidence.
        record = pending_record
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
            current_record = (
                current_intrinsic_coordinator.completed_for_state(context)
                if current_intrinsic_coordinator is not None else None
            )
            current_intrinsic_input_fingerprint = None
            if (
                current_record is not None
                and current_record.league_state_id == state.state_id
                and three_year_source_reconciles_career_components(
                    state,
                    intrinsic=current_record.contract,
                    evidence_state_id=current_record.league_state_id,
                    career_forward=record.contract,
                    career_evidence_state_id=record.league_state_id,
                )
            ):
                current_intrinsic_input_fingerprint = (
                    current_record.intrinsic_input_fingerprint
                )
            return _dynasty_publication_payload(
                context,
                {
                    "status": "ready",
                    "capability": "career_intrinsic",
                    "league_state_id": state.state_id,
                    "input_fingerprint": record.intrinsic_input_fingerprint,
                    "current_intrinsic_input_fingerprint": current_intrinsic_input_fingerprint,
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
                "reason": "Career is not prepared for this publication. Refresh league intelligence to prepare it.",
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

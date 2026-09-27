from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import json
import logging

from fsffl.persistence.contracts import (
    ArtifactKey,
    PersistenceStore,
    ReusableArtifactRecord,
    canonical_fingerprint,
    utc_now,
)

from .runtime import UserRuntimeContext


_logger = logging.getLogger("fsffl.product.persistence")

PRESENTATION_SURFACE_ARTIFACT_KIND = "runtime_presentation_surface"
PRESENTATION_MANIFEST_ARTIFACT_KIND = "runtime_presentation_manifest"
PRESENTATION_SCOPE_KIND = "user_league_presentation"
PRESENTATION_MODEL_VERSION = "runtime-presentation-continuity-v1"

HOME_SURFACE = "home"
FRANCHISE_SURFACE = "franchise"
LEAGUE_ATLAS_SURFACE = "league_atlas"
LEAGUE_TEAM_VIEWS_SURFACE = "league_team_views"
MARKET_WORKSPACE_SURFACE = "market_workspace"
MARKET_VALUE_LENSES_ALL_SURFACE = "market_value_lenses_all"

REQUIRED_PRESENTATION_SURFACES = (
    HOME_SURFACE,
    FRANCHISE_SURFACE,
    LEAGUE_ATLAS_SURFACE,
    LEAGUE_TEAM_VIEWS_SURFACE,
    MARKET_WORKSPACE_SURFACE,
    MARKET_VALUE_LENSES_ALL_SURFACE,
)


SurfaceBuilder = Callable[[], Mapping[str, object]]


@dataclass(frozen=True)
class PresentationPromotionResult:
    league_id: str
    league_state_id: str
    as_of: datetime
    surfaces: tuple[str, ...]
    total_payload_bytes: int


def _scope_id(user_id: str, league_id: str) -> str:
    if not user_id.strip() or not league_id.strip():
        raise ValueError("presentation continuity scope requires user and league")
    return f"{user_id}:{league_id}"


def _surface_scope_id(user_id: str, league_id: str, surface: str) -> str:
    if not surface.strip():
        raise ValueError("presentation continuity surface cannot be blank")
    return f"{_scope_id(user_id, league_id)}:{surface}"


def _manifest_key(
    *,
    user_id: str,
    league_id: str,
    league_state_id: str,
) -> ArtifactKey:
    return ArtifactKey(
        artifact_kind=PRESENTATION_MANIFEST_ARTIFACT_KIND,
        scope_kind=PRESENTATION_SCOPE_KIND,
        scope_id=_scope_id(user_id, league_id),
        input_fingerprint=league_state_id,
        model_version=PRESENTATION_MODEL_VERSION,
    )


def _surface_key(
    *,
    user_id: str,
    league_id: str,
    league_state_id: str,
    surface: str,
) -> ArtifactKey:
    return ArtifactKey(
        artifact_kind=PRESENTATION_SURFACE_ARTIFACT_KIND,
        scope_kind=PRESENTATION_SCOPE_KIND,
        scope_id=_surface_scope_id(user_id, league_id, surface),
        input_fingerprint=league_state_id,
        model_version=PRESENTATION_MODEL_VERSION,
    )


def _json_round_trip(value: Mapping[str, object]) -> dict[str, object]:
    return json.loads(
        json.dumps(
            dict(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
    )


class PresentationContinuityStore:
    """Durable compact read-model continuity for primary product surfaces.

    This cache never owns State, Forecast, Simulation, Value, Decision, or Search
    authority. It stores only already-composed presentation payloads from a terminal
    governed runtime. Heavy model objects are never restored to serve stale presentation.

    Promotion is manifest-last. Individual surface writes from an interrupted promotion
    are unreachable because readers require an exact matching manifest first.
    """

    def __init__(self, persistence_store: PersistenceStore | None) -> None:
        self._persistence = persistence_store

    @property
    def enabled(self) -> bool:
        return self._persistence is not None

    def promote(
        self,
        *,
        user_id: str,
        runtime: UserRuntimeContext,
        builders: Sequence[tuple[str, SurfaceBuilder]],
    ) -> PresentationPromotionResult | None:
        if self._persistence is None or runtime.league_state is None:
            return None
        state = runtime.league_state
        if not builders:
            raise ValueError("presentation promotion requires at least one surface")
        surfaces = tuple(surface for surface, _ in builders)
        if len(set(surfaces)) != len(surfaces):
            raise ValueError("presentation promotion surfaces must be unique")

        now = utc_now()
        total_bytes = 0
        surface_hashes: list[tuple[str, str, int]] = []
        for surface, builder in builders:
            raw = builder()
            payload = _json_round_trip(raw)
            encoded = json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
            payload_hash = canonical_fingerprint(payload)
            size = len(encoded)
            total_bytes += size
            self._persistence.put_artifact(
                ReusableArtifactRecord(
                    key=_surface_key(
                        user_id=user_id,
                        league_id=state.league.league_id,
                        league_state_id=state.state_id,
                        surface=surface,
                    ),
                    payload={
                        "contract": PRESENTATION_MODEL_VERSION,
                        "surface": surface,
                        "league_id": state.league.league_id,
                        "league_state_id": state.state_id,
                        "as_of": state.as_of.isoformat(),
                        "selected_team_id": runtime.selected_team_id,
                        "payload_hash": payload_hash,
                        "payload_size_bytes": size,
                        "payload": payload,
                    },
                    computed_at=now,
                )
            )
            surface_hashes.append((surface, payload_hash, size))
            # Do not retain the serialized surface after persistence. Promotion is
            # intentionally sequential to cap transient memory.
            del payload, encoded

        self._persistence.put_artifact(
            ReusableArtifactRecord(
                key=_manifest_key(
                    user_id=user_id,
                    league_id=state.league.league_id,
                    league_state_id=state.state_id,
                ),
                payload={
                    "contract": PRESENTATION_MODEL_VERSION,
                    "league_id": state.league.league_id,
                    "league_state_id": state.state_id,
                    "as_of": state.as_of.isoformat(),
                    "selected_team_id": runtime.selected_team_id,
                    "surfaces": list(surfaces),
                    "surface_hashes": [
                        {
                            "surface": surface,
                            "payload_hash": payload_hash,
                            "payload_size_bytes": size,
                        }
                        for surface, payload_hash, size in surface_hashes
                    ],
                    "total_payload_bytes": total_bytes,
                },
                computed_at=now,
            )
        )
        _logger.info(
            "FSFFL presentation continuity promoted user=%s league=%s state=%s surfaces=%s bytes=%s",
            user_id,
            state.league.league_id,
            state.state_id,
            len(surfaces),
            total_bytes,
        )
        return PresentationPromotionResult(
            league_id=state.league.league_id,
            league_state_id=state.state_id,
            as_of=state.as_of,
            surfaces=surfaces,
            total_payload_bytes=total_bytes,
        )

    def has_snapshot(
        self,
        *,
        user_id: str,
        league_id: str,
        league_state_id: str,
        required_surfaces: Sequence[str] = REQUIRED_PRESENTATION_SURFACES,
    ) -> bool:
        if self._persistence is None:
            return False
        manifest = self._persistence.get_reusable_artifact(
            _manifest_key(
                user_id=user_id,
                league_id=league_id,
                league_state_id=league_state_id,
            )
        )
        if manifest is None:
            return False
        available = set(manifest.payload.get("surfaces") or ())
        return set(required_surfaces).issubset(available)

    def load_for_runtime(
        self,
        *,
        user_id: str,
        runtime: UserRuntimeContext,
        surface: str,
    ) -> dict[str, object] | None:
        """Load one stale last-good payload when exact-State presentation rebuilds."""

        if self._persistence is None or runtime.league_state is None:
            return None
        served = runtime.served_intelligence
        current = runtime.league_state
        if (
            served is None
            or served.league_id != current.league.league_id
            or served.league_state_id == current.state_id
        ):
            return None
        if not self.has_snapshot(
            user_id=user_id,
            league_id=served.league_id,
            league_state_id=served.league_state_id,
        ):
            return None

        record = self._persistence.get_reusable_artifact(
            _surface_key(
                user_id=user_id,
                league_id=served.league_id,
                league_state_id=served.league_state_id,
                surface=surface,
            )
        )
        if record is None:
            return None
        wrapper = dict(record.payload)
        if (
            wrapper.get("league_id") != served.league_id
            or wrapper.get("league_state_id") != served.league_state_id
            or wrapper.get("surface") != surface
        ):
            return None
        raw = wrapper.get("payload")
        if not isinstance(raw, Mapping):
            return None
        payload = _json_round_trip(raw)
        payload["intelligence_freshness"] = {
            "status": "stale_last_good",
            "stale": True,
            "target_state_id": current.state_id,
            "target_as_of": current.as_of.isoformat(),
            "served_state_id": served.league_state_id,
            "served_as_of": served.as_of.isoformat(),
            "message": (
                "Canonical State is current. This view remains available from the "
                "last-good governed presentation while exact-State intelligence rebuilds."
            ),
            "presentation_contract": PRESENTATION_MODEL_VERSION,
        }
        payload["presentation_continuity"] = {
            "mode": "stale_last_good",
            "target_league_state_id": current.state_id,
            "served_league_state_id": served.league_state_id,
            "served_as_of": served.as_of.isoformat(),
        }
        return payload

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from threading import RLock, local

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
PRESENTATION_MODEL_VERSION = "runtime-presentation-continuity-v2"
LEGACY_PRESENTATION_MODEL_VERSION = "runtime-presentation-continuity-v1"

HOME_SURFACE = "home"
FRANCHISE_SURFACE = "franchise"
LEAGUE_ATLAS_SURFACE = "league_atlas"
LEAGUE_TEAM_VIEWS_SURFACE = "league_team_views"
LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE = "league_dynasty_position_rooms"
MARKET_WORKSPACE_SURFACE = "market_workspace"
MARKET_VALUE_LENSES_ROSTERED_SURFACE = "market_value_lenses_rostered"
MARKET_VALUE_LENSES_ALL_SURFACE = "market_value_lenses_all"

REQUIRED_PRESENTATION_SURFACES = (
    HOME_SURFACE,
    FRANCHISE_SURFACE,
    LEAGUE_ATLAS_SURFACE,
    LEAGUE_TEAM_VIEWS_SURFACE,
    LEAGUE_DYNASTY_POSITION_ROOMS_SURFACE,
    MARKET_WORKSPACE_SURFACE,
    MARKET_VALUE_LENSES_ROSTERED_SURFACE,
    MARKET_VALUE_LENSES_ALL_SURFACE,
)


SurfaceBuilder = Callable[[], Mapping[str, object]]


@dataclass(frozen=True)
class PresentationPromotionResult:
    league_id: str
    league_state_id: str
    publication_generation_id: str
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
    model_version: str = PRESENTATION_MODEL_VERSION,
) -> ArtifactKey:
    return ArtifactKey(
        artifact_kind=PRESENTATION_MANIFEST_ARTIFACT_KIND,
        scope_kind=PRESENTATION_SCOPE_KIND,
        scope_id=_scope_id(user_id, league_id),
        input_fingerprint=league_state_id,
        model_version=model_version,
    )


def _surface_key(
    *,
    user_id: str,
    league_id: str,
    promotion_id: str,
    surface: str,
    model_version: str = PRESENTATION_MODEL_VERSION,
) -> ArtifactKey:
    return ArtifactKey(
        artifact_kind=PRESENTATION_SURFACE_ARTIFACT_KIND,
        scope_kind=PRESENTATION_SCOPE_KIND,
        scope_id=_surface_scope_id(user_id, league_id, surface),
        input_fingerprint=promotion_id,
        model_version=model_version,
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
        self._local = local()
        self._validation_lock = RLock()
        self._validated_snapshots: dict[
            tuple[str, str, str, str | None], str
        ] = {}

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
        promotion_id = canonical_fingerprint(
            state.state_id,
            now.isoformat(),
            surfaces,
        )
        total_bytes = 0
        surface_hashes: list[tuple[str, str, int]] = []
        self._local.promoting = True
        try:
            for surface, builder in builders:
                raw = builder()
                payload = _json_round_trip(raw)
                payload["publication_generation_id"] = promotion_id
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
                            promotion_id=promotion_id,
                            surface=surface,
                        ),
                        payload={
                            "contract": PRESENTATION_MODEL_VERSION,
                            "surface": surface,
                            "league_id": state.league.league_id,
                            "league_state_id": state.state_id,
                            "promotion_id": promotion_id,
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
                del payload, encoded
        finally:
            self._local.promoting = False

        manifest_payload = {
            "contract": PRESENTATION_MODEL_VERSION,
            "league_id": state.league.league_id,
            "league_state_id": state.state_id,
            "promotion_id": promotion_id,
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
        }
        self._persistence.put_artifact(
            ReusableArtifactRecord(
                key=_manifest_key(
                    user_id=user_id,
                    league_id=state.league.league_id,
                    league_state_id=state.state_id,
                ),
                payload=manifest_payload,
                computed_at=now,
            )
        )
        self._remember_validated_snapshot(
            user_id=user_id,
            league_id=state.league.league_id,
            league_state_id=state.state_id,
            selected_team_id=runtime.selected_team_id,
            manifest_payload=manifest_payload,
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
            publication_generation_id=promotion_id,
            as_of=state.as_of,
            surfaces=surfaces,
            total_payload_bytes=total_bytes,
        )

    def clear_user_validation_hints(self, user_id: str) -> int:
        """Drop process-local validation hints; durable presentation stays intact."""

        with self._validation_lock:
            stale = [item for item in self._validated_snapshots if item[0] == user_id]
            for item in stale:
                self._validated_snapshots.pop(item, None)
            return len(stale)

    @staticmethod
    def _snapshot_key(
        user_id: str,
        league_id: str,
        league_state_id: str,
        selected_team_id: str | None,
    ) -> tuple[str, str, str, str | None]:
        return user_id, league_id, league_state_id, selected_team_id

    def _remember_validated_snapshot(
        self,
        *,
        user_id: str,
        league_id: str,
        league_state_id: str,
        selected_team_id: str | None,
        manifest_payload: Mapping[str, object],
    ) -> None:
        key = self._snapshot_key(
            user_id,
            league_id,
            league_state_id,
            selected_team_id,
        )
        with self._validation_lock:
            self._validated_snapshots[key] = canonical_fingerprint(manifest_payload)

    def known_snapshot_available(
        self,
        *,
        user_id: str,
        league_id: str,
        league_state_id: str,
        selected_team_id: str | None = None,
    ) -> bool:
        """Fast read hint for a manifest validated or written in this process.

        A cold manifest still gets a strict all-surface integrity check. Once that
        check succeeds (or this process has just completed the manifest-last write),
        each read still hashes its requested surface against the known manifest but
        does not reread and rehash the other six payloads.
        """

        key = self._snapshot_key(
            user_id,
            league_id,
            league_state_id,
            selected_team_id,
        )
        with self._validation_lock:
            return key in self._validated_snapshots

    def has_snapshot(
        self,
        *,
        user_id: str,
        league_id: str,
        league_state_id: str,
        required_surfaces: Sequence[str] = REQUIRED_PRESENTATION_SURFACES,
        selected_team_id: str | None = None,
    ) -> bool:
        if self._persistence is None:
            return False
        validation_key = self._snapshot_key(
            user_id,
            league_id,
            league_state_id,
            selected_team_id,
        )
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
        if not set(required_surfaces).issubset(available):
            return False
        if (
            selected_team_id is not None
            and manifest.payload.get("selected_team_id") != selected_team_id
        ):
            return False
        promotion_id = str(manifest.payload.get("promotion_id") or "").strip()
        if not promotion_id:
            return False
        expected_hashes = {
            str(item.get("surface")): item
            for item in (manifest.payload.get("surface_hashes") or ())
            if isinstance(item, Mapping)
        }
        for surface in required_surfaces:
            record = self._persistence.get_reusable_artifact(
                _surface_key(
                    user_id=user_id,
                    league_id=league_id,
                    promotion_id=promotion_id,
                    surface=surface,
                )
            )
            if record is None:
                return False
            wrapper = record.payload
            expected = expected_hashes.get(surface)
            raw = wrapper.get("payload")
            if (
                wrapper.get("promotion_id") != promotion_id
                or wrapper.get("league_state_id") != league_state_id
                or wrapper.get("surface") != surface
                or (
                    selected_team_id is not None
                    and wrapper.get("selected_team_id") != selected_team_id
                )
                or expected is None
                or not isinstance(raw, Mapping)
                or wrapper.get("payload_hash") != expected.get("payload_hash")
                or int(wrapper.get("payload_size_bytes") or -1)
                != int(expected.get("payload_size_bytes") or -2)
                or canonical_fingerprint(_json_round_trip(raw))
                != wrapper.get("payload_hash")
            ):
                return False
        self._remember_validated_snapshot(
            user_id=user_id,
            league_id=league_id,
            league_state_id=league_state_id,
            selected_team_id=selected_team_id,
            manifest_payload=manifest.payload,
        )
        return True

    def load_for_runtime(
        self,
        *,
        user_id: str,
        runtime: UserRuntimeContext,
        surface: str,
    ) -> dict[str, object] | None:
        """Load a proven current publication, else the proven same-league last-good.

        A non-null runtime publication id is not sufficient presentation proof by
        itself. During restart/revalidation, durable runtime/core identity can become
        visible before the exact presentation manifest is available in this process.
        In that transition, ordinary reads must remain pinned to the prior proven
        served generation instead of falling through to incomplete live composition.
        """

        if (
            self._persistence is None
            or runtime.league_state is None
            or getattr(self._local, "promoting", False)
        ):
            return None

        current = runtime.league_state
        publication_id = str(
            getattr(runtime, "publication_generation_id", None) or ""
        ).strip()
        served = runtime.served_intelligence
        served_publication_id = str(
            getattr(served, "publication_generation_id", None) or ""
        ).strip()

        candidates: list[tuple[str, str, str, datetime, str]] = []
        if publication_id:
            candidates.append(
                (
                    "published",
                    current.league.league_id,
                    current.state_id,
                    current.as_of,
                    publication_id,
                )
            )
        if (
            served is not None
            and served.league_id == current.league.league_id
            and served.league_state_id != current.state_id
            and served_publication_id
        ):
            candidates.append(
                (
                    "stale_last_good",
                    served.league_id,
                    served.league_state_id,
                    served.as_of,
                    served_publication_id,
                )
            )
        if not candidates:
            return None

        def load_candidate(
            *,
            mode: str,
            served_league_id: str,
            served_state_id: str,
            served_as_of: datetime,
            expected_generation_id: str,
        ) -> dict[str, object] | None:
            manifest = self._persistence.get_reusable_artifact(
                _manifest_key(
                    user_id=user_id,
                    league_id=served_league_id,
                    league_state_id=served_state_id,
                )
            )
            if manifest is None:
                return None
            known_key = self._snapshot_key(
                user_id,
                served_league_id,
                served_state_id,
                runtime.selected_team_id,
            )
            with self._validation_lock:
                known_manifest_fingerprint = self._validated_snapshots.get(known_key)
            manifest_fingerprint = canonical_fingerprint(manifest.payload)
            if known_manifest_fingerprint != manifest_fingerprint:
                if not self.has_snapshot(
                    user_id=user_id,
                    league_id=served_league_id,
                    league_state_id=served_state_id,
                    selected_team_id=runtime.selected_team_id,
                ):
                    return None
                # Strict cold validation may have re-read a replacement manifest.
                manifest = self._persistence.get_reusable_artifact(
                    _manifest_key(
                        user_id=user_id,
                        league_id=served_league_id,
                        league_state_id=served_state_id,
                    )
                )
                if manifest is None:
                    return None

            promotion_id = str(manifest.payload.get("promotion_id") or "").strip()
            if (
                not promotion_id
                or promotion_id != expected_generation_id
                or manifest.payload.get("selected_team_id")
                != runtime.selected_team_id
            ):
                return None

            record = self._persistence.get_reusable_artifact(
                _surface_key(
                    user_id=user_id,
                    league_id=served_league_id,
                    promotion_id=promotion_id,
                    surface=surface,
                )
            )
            if record is None:
                return None
            wrapper = dict(record.payload)
            if (
                wrapper.get("league_id") != served_league_id
                or wrapper.get("league_state_id") != served_state_id
                or wrapper.get("promotion_id") != promotion_id
                or wrapper.get("surface") != surface
                or wrapper.get("selected_team_id") != runtime.selected_team_id
            ):
                return None
            raw = wrapper.get("payload")
            expected = next(
                (
                    item
                    for item in (manifest.payload.get("surface_hashes") or ())
                    if isinstance(item, Mapping) and item.get("surface") == surface
                ),
                None,
            )
            if not isinstance(raw, Mapping):
                return None
            if (
                expected is None
                or wrapper.get("payload_hash") != expected.get("payload_hash")
                or int(wrapper.get("payload_size_bytes") or -1)
                != int(expected.get("payload_size_bytes") or -2)
                or canonical_fingerprint(_json_round_trip(raw))
                != expected.get("payload_hash")
            ):
                return None

            payload = _json_round_trip(raw)
            payload["league_id"] = served_league_id
            payload["publication_generation_id"] = promotion_id
            if mode == "published":
                payload["intelligence_freshness"] = {
                    "status": "current",
                    "stale": False,
                    "target_state_id": current.state_id,
                    "target_league_id": current.league.league_id,
                    "target_as_of": current.as_of.isoformat(),
                    "served_state_id": served_state_id,
                    "served_league_id": served_league_id,
                    "served_as_of": served_as_of.isoformat(),
                    "publication_generation_id": promotion_id,
                    "presentation_contract": PRESENTATION_MODEL_VERSION,
                }
                payload["presentation_continuity"] = {
                    "mode": "published",
                    "target_league_id": current.league.league_id,
                    "served_league_id": served_league_id,
                    "target_league_state_id": current.state_id,
                    "served_league_state_id": served_state_id,
                    "served_as_of": served_as_of.isoformat(),
                    "promotion_id": promotion_id,
                    "publication_generation_id": promotion_id,
                }
                return payload

            payload["intelligence_freshness"] = {
                "status": "stale_last_good",
                "stale": True,
                "target_state_id": current.state_id,
                "target_league_id": current.league.league_id,
                "target_as_of": current.as_of.isoformat(),
                "served_state_id": served_state_id,
                "served_league_id": served_league_id,
                "served_as_of": served_as_of.isoformat(),
                "publication_generation_id": promotion_id,
                "message": (
                    "Canonical State is current. This view remains available from the "
                    "last-good governed presentation while exact-State intelligence rebuilds."
                ),
                "presentation_contract": PRESENTATION_MODEL_VERSION,
            }
            payload["presentation_continuity"] = {
                "mode": "stale_last_good",
                "target_league_id": current.league.league_id,
                "served_league_id": served_league_id,
                "target_league_state_id": current.state_id,
                "served_league_state_id": served_state_id,
                "served_as_of": served_as_of.isoformat(),
                "promotion_id": promotion_id,
                "publication_generation_id": promotion_id,
            }
            return payload

        # Prefer an exact proven current publication. If its manifest/surface cannot
        # be proven, keep every eligible surface on the same proven served generation.
        # Never use an invalid current presentation identity as permission to compose
        # derived fields from an incomplete replacement runtime.
        for (
            mode,
            served_league_id,
            served_state_id,
            served_as_of,
            expected_generation_id,
        ) in candidates:
            payload = load_candidate(
                mode=mode,
                served_league_id=served_league_id,
                served_state_id=served_state_id,
                served_as_of=served_as_of,
                expected_generation_id=expected_generation_id,
            )
            if payload is not None:
                return payload
        return None

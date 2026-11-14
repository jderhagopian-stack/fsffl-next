"""Research curve codec using the existing persistence owner; no connection lifecycle."""
from dataclasses import dataclass
from datetime import datetime

from fsffl.value.native_pick_curve_releases import CURVE_VERSION, FrozenNativePickCurve
from .contracts import ArtifactKey, PersistenceStore, ReusableArtifactRecord


@dataclass(frozen=True)
class NativePickCurveReference:
    economic_scope_key: str
    curve_id: str

    @property
    def key(self) -> ArtifactKey:
        return ArtifactKey('research_native_pick_curve', 'native_pick_economic_scope',
                           self.economic_scope_key, self.curve_id, CURVE_VERSION)


def curve_reference(curve: FrozenNativePickCurve) -> NativePickCurveReference:
    return NativePickCurveReference(curve.release.economic_scope_key, curve.curve_id)


def _decode(record: ReusableArtifactRecord, reference: NativePickCurveReference) -> FrozenNativePickCurve:
    curve = FrozenNativePickCurve.model_validate(record.payload)
    if record.key != reference.key or curve_reference(curve) != reference:
        raise ValueError('persisted curve does not match its exact reference')
    if record.computed_at != curve.release.released_at:
        raise ValueError('persisted curve release time does not match')
    return curve


def save_research_curve(store: PersistenceStore, curve: FrozenNativePickCurve) -> NativePickCurveReference:
    """Explicit producer operation. Content-addressed keys preserve older releases.

    The canonical publication owner must serialize release selection. This helper
    does not create or advance a mutable latest-release pointer.
    """
    reference = curve_reference(curve)
    existing = store.get_reusable_artifact(reference.key)
    if existing is not None:
        _decode(existing, reference)
        if not existing.reusable:
            raise ValueError('invalidated release requires an explicit new correction')
        return reference
    store.put_artifact(ReusableArtifactRecord(reference.key, curve.model_dump(mode='json'),
                                             curve.release.released_at))
    return reference


def load_research_curve(store: PersistenceStore, reference: NativePickCurveReference, *,
                        expected_economic_scope_key: str, as_of: datetime) -> FrozenNativePickCurve | None:
    """One exact read, never a rebuild or a latest lookup.

    The caller can retain the returned small frozen object for its governed
    publication lifetime. Invalidation is checked on restore; publication owners
    must retire warm references when a release is revoked.
    """
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError('curve read requires a timezone-aware cutoff')
    if reference.economic_scope_key != expected_economic_scope_key:
        raise ValueError('curve reference belongs to a different economic scope')
    record = store.get_reusable_artifact(reference.key)
    if record is None or not record.reusable:
        return None
    curve = _decode(record, reference)
    if curve.release.released_at > as_of:
        raise ValueError('curve release postdates the requested cutoff')
    return curve

"""Content-addressed annual release codec through the existing bounded store."""
from fsffl.value.native_pick_prior import NativePickPriorRelease, MODEL_VERSION
from .contracts import ArtifactKey, ReusableArtifactRecord
from fsffl.value.native_pick_prior import fingerprint


def release_key(scope_key: str, release_id: str) -> ArtifactKey:
    return ArtifactKey("native_pick_prior_release", "native_pick_economic_scope", scope_key, release_id, MODEL_VERSION)


def restore_native_pick_release(store, *, scope_key: str, release_id: str) -> NativePickPriorRelease | None:
    key = release_key(scope_key, release_id)
    record = store.get_reusable_artifact(key)
    if record is None or not record.reusable:
        return None
    result = NativePickPriorRelease.model_validate(record.payload)
    if (record.key != key or result.release_id != release_id or result.economic_scope_key != scope_key
        or record.computed_at != result.released_at):
        raise ValueError("annual pick release identity does not match its pinned reference")
    return result


def persist_native_pick_release(store, release: NativePickPriorRelease) -> None:
    # A model-version change cannot silently issue a second annual baseline in
    # the same economy. Explicit correction stages are separate future work.
    annual_scope = fingerprint({k:getattr(release,k) for k in (
        'evaluation_season','draft_season','team_count','rules_signature','scoring_signature','selection_policy')})
    annual_key = ArtifactKey('native_pick_prior_annual_baseline','native_pick_economic_scope',annual_scope,
                            'annual_baseline','native-pick-annual-release-lock-v1')
    reference = {'release_id':release.release_id,'scope_key':release.economic_scope_key}
    annual = store.put_immutable_artifact(ReusableArtifactRecord(annual_key,reference,release.released_at))
    if not annual.reusable or dict(annual.payload) != reference:
        raise ValueError('annual baseline is frozen; a change needs an explicit correction release')
    key = release_key(release.economic_scope_key, release.release_id)
    record = store.put_immutable_artifact(ReusableArtifactRecord(key, release.model_dump(mode='json'), release.released_at))
    if restore_native_pick_release_record(record, release) is None:
        raise ValueError("revoked annual release requires a new explicit correction")


def restore_native_pick_release_record(record, expected: NativePickPriorRelease):
    if not record.reusable:
        return None
    actual = NativePickPriorRelease.model_validate(record.payload)
    if (actual != expected or record.key != release_key(expected.economic_scope_key, expected.release_id)
        or record.computed_at != expected.released_at):
        raise ValueError("stored annual release differs from its immutable identity")
    return actual

from io import BytesIO
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from fsffl.product import foundation4_accepted_bundle as bundle
from fsffl.product import foundation4_dynamic_candidate_runtime as runtime


def test_restore_accepted_bundle_is_atomic_complete_and_shared(tmp_path, monkeypatch):
    calls = []
    def download(url, path, digest):
        calls.append(url)
        if path.suffix == '.zip':
            name = next(k for k, (asset, _) in bundle._ARCHIVES.items() if asset == path.name)
            with zipfile.ZipFile(path, 'w') as z:
                for value in bundle._PATHS.values():
                    if value.startswith(name + '/'):
                        z.writestr(value[len(name) + 1:], 'accepted')
        else:
            path.write_text('accepted')
    monkeypatch.setattr(bundle, '_download_verified', download)
    root = tmp_path / 'model'
    manifest = bundle.restore_accepted_bundle(root)
    values = json.loads(manifest.read_text())
    assert set(runtime._BUNDLE_KEYS) <= set(values)
    assert bundle._verified_cached_manifest(root)
    assert all(Path(values[key]).is_file() for key in runtime._BUNDLE_KEYS)
    assert len(calls) == 8
    assert bundle.restore_accepted_bundle(root) == manifest
    assert len(calls) == 8
    (root / 'dev.py').write_text('tampered')
    assert bundle.restore_accepted_bundle(root) == manifest
    assert len(calls) == 16
    assert (root / 'dev.py').read_text() == 'accepted'
    assert list(tmp_path.iterdir()) == [root]


def test_restore_failure_leaves_no_reusable_or_partial_bundle(tmp_path, monkeypatch):
    def fail(*args):
        raise OSError('exact accepted asset unavailable')
    monkeypatch.setattr(bundle, '_download_verified', fail)
    with pytest.raises(OSError, match='exact accepted asset unavailable'):
        bundle.restore_accepted_bundle(tmp_path / 'model')
    assert not list(tmp_path.iterdir())


def test_download_hash_verified_without_whole_response_copy(tmp_path, monkeypatch):
    content = b'accepted' * 400000
    monkeypatch.setattr(bundle, 'urlopen', lambda *a, **k: BytesIO(content))
    destination = tmp_path / 'accepted'
    bundle._download_verified('https://example.test/pinned', destination, hashlib.sha256(content).hexdigest())
    assert destination.read_bytes() == content
    with pytest.raises(ValueError, match='SHA256 mismatch'):
        bundle._download_verified('https://example.test/pinned', destination, 'incorrect')


def test_archive_member_cannot_escape_destination(tmp_path):
    archive = tmp_path / 'accepted.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('../unexpected.py', 'bad')
    with pytest.raises(ValueError, match='unsafe member'):
        bundle._extract(archive, tmp_path / 'model')
    assert not (tmp_path / 'unexpected.py').exists()


def test_opt_in_restore_uses_existing_materializer_owner_and_mount_wins(tmp_path, monkeypatch):
    for key in (runtime._MANIFEST_ENV, runtime._BUNDLE_ROOT_ENV):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('FSFFL_FOUNDATION4_RESTORE_ACCEPTED_BUNDLE', '1')
    manifest = tmp_path / runtime._BUNDLE_MANIFEST_NAME
    manifest.write_text('{"source": "accepted"}')
    calls = []
    monkeypatch.setattr(bundle, 'restore_accepted_bundle', lambda: calls.append(1) or manifest)
    assert runtime._accepted_materializer_manifest()[0] == {'source': 'accepted'}
    assert calls == [1]
    mounted = tmp_path / 'mounted'
    values = {
        'accepted_commit': bundle._COMMIT,
        'files': {},
        'sha256': {},
    }
    for key, relative in bundle._PATHS.items():
        path = mounted / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'accepted fixture {key}')
        resolved = path.resolve()
        values['files'][key] = str(resolved)
        values['sha256'][key] = bundle._file_sha256(resolved)
        values[key] = str(resolved)
    (mounted / runtime._BUNDLE_MANIFEST_NAME).write_text(json.dumps(values))
    monkeypatch.setenv(runtime._BUNDLE_ROOT_ENV, str(mounted))
    assert runtime._accepted_materializer_manifest()[0] == values
    assert calls == [1]

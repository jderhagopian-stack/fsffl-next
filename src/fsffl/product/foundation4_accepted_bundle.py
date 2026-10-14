"""Restore immutable accepted model inputs for the existing background scorer.

This is a process-shared model-version cache, never a player/provider acquisition
or a page-read lifecycle. Explicit deployment mounts remain authoritative.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from threading import RLock
from urllib.request import urlopen
import zipfile

_REPO = "https://github.com/jderhagopian-stack/fsffl-next"
_COMMIT = "be2541a496227b33c12c755f576843dc4ab5a0bb"
_RELEASE = f"{_REPO}/releases/download/career-405-accepted-research-evidence-20261007"
_ARCHIVES = {
    "term": ("10899387479.zip", "ea72f312148f01b8066419e8f12cb3a04a4dbbd99fd6e0b7dc975c65cc2446b5"),
    "panel": ("10912862252.zip", "6dd664b632f4897f286a99794e10df29be21bf8c6cae70e526ea807470fdcb0e"),
    "route": ("10916355135.zip", "63520ddb60a8ed12724fa21e8d276c4e3e7d5587162aade92ba7afaa3796ced2"),
    "board": ("11263913850.zip", "6a79e2d793403c128c1c34ee3ffb044aba67f873ec92b8c61a702d26c06c1b22"),
}
_PROGRAMS = {
    "dev.py": ("scripts/run_intrinsic_comprehensive_development.py", "85937f4e446aa7239a791d5e83c9d3364b38e58c09bd947e57f7c32c33bb3b41"),
    "route.py": ("scripts/run_intrinsic_cell_routing_validation.py", "f9dc1d2900894ac873403b9582d3c7d3b569115fe13e62c11c9453df9df2b975"),
    "reference-board.csv": ("artifacts/implementation/final_forecast_route_implementation_20260920/FINAL_CONNECTED_LEAGUE_BOARD_335.csv", "de6952237ba5a748a9c333b4b926af330bc933fe160c83c4c3555fd5dff74f9b"),
    "policy.json": ("artifacts/research/intrinsic_cell_routing_y4_y8_20260926/CELL_ROUTING_POLICY_FREEZE.json", "ca3013de813fdaf7299d8fa0b572a83cde5f74d020fd4d537708fd94d16d9476"),
}
_PATHS = {
    "development-module": "dev.py", "route-module": "route.py", "policy-freeze": "policy.json",
    "model-a-rows": "term/frozen/modela/multiyear-intrinsic-model-a/model_a_repair_point_in_time_rows.csv",
    "qb-results": "term/frozen/qb/qb_career_state_deployment_results.json",
    "raw-seasons": "panel/RAW_PLAYER_SEASONS_RICH.csv", "players": "panel/PLAYERS.csv",
    "residual-states": "term/frozen/modela/multiyear-intrinsic-model-a/player_specific_trajectory_residual_states.csv",
    "innovation-states": "term/frozen/modela/multiyear-intrinsic-model-a/within_player_trajectory_innovation_states.csv",
    "reference-board": "reference-board.csv",
    "current-route": "route/CURRENT_RESEARCH_ROUTE.csv",
    "cell-metrics": "board/f4/FOUNDATION4_FSFFL_ROLLING_POLICY_CELL_METRICS.csv",
}
_LOCK = RLock()
_MANIFEST = "foundation4_dynamic_materializer_manifest.json"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified_cached_manifest(root: Path) -> bool:
    manifest = root / _MANIFEST
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if payload.get("accepted_commit") != _COMMIT:
            return False
        expected = payload.get("sha256")
        files = payload.get("files")
        if not isinstance(expected, dict) or set(expected) != set(_PATHS):
            return False
        if not isinstance(files, dict) or set(files) != set(_PATHS):
            return False
        for key, relative in _PATHS.items():
            path = (root / relative).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                return False
            if files[key] != str(path) or _file_sha256(path) != expected[key]:
                return False
        return True
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def _download_verified(url: str, path: Path, digest: str) -> None:
    checksum = hashlib.sha256()
    with urlopen(url, timeout=120) as source, path.open("wb") as destination:
        while chunk := source.read(1024 * 1024):
            checksum.update(chunk)
            destination.write(chunk)
    if checksum.hexdigest() != digest:
        raise ValueError(f"accepted Foundation 4 input SHA256 mismatch: {path.name}")


def _extract(archive: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("accepted Foundation 4 archive has an unsafe member path")
        zipped.extractall(destination)


def restore_accepted_bundle(root: Path | None = None) -> Path:
    """Atomically restore the pinned accepted bundle once, bounded by model version."""
    root = root or Path(tempfile.gettempdir()) / f"fsffl-foundation4-{_COMMIT}"
    manifest = root / _MANIFEST
    with _LOCK:
        if manifest.is_file():
            if _verified_cached_manifest(root):
                return manifest
            shutil.rmtree(root, ignore_errors=True)
        root.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix="foundation4-restore-", dir=root.parent))
        try:
            for name, (asset, digest) in _ARCHIVES.items():
                archive = temporary / asset
                _download_verified(f"{_RELEASE}/{asset}", archive, digest)
                _extract(archive, temporary / name)
                archive.unlink()
            for name, (source, digest) in _PROGRAMS.items():
                _download_verified(
                    f"https://raw.githubusercontent.com/jderhagopian-stack/fsffl-next/{_COMMIT}/{source}",
                    temporary / name, digest,
                )
            absent = [key for key, value in _PATHS.items() if not (temporary / value).is_file()]
            if absent:
                raise ValueError("accepted Foundation 4 restored bundle missing files: " + ", ".join(absent))
            payload = {
                "accepted_commit": _COMMIT,
                "files": {key: str(root / value) for key, value in _PATHS.items()},
                "sha256": {
                    key: _file_sha256(temporary / value)
                    for key, value in _PATHS.items()
                },
            }
            # Preserve the adapter's established key-to-path interface.
            payload.update(payload["files"])
            (temporary / _MANIFEST).write_text(json.dumps(payload), encoding="utf-8")
            # A failed restore never leaves a manifest that can be reused.
            if root.exists():
                shutil.rmtree(root)
            os.replace(temporary, root)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    return manifest

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fsffl.product.static_assets import ContentFingerprintStaticFiles


def _fingerprint(content: bytes) -> str:
    return "sha256-" + hashlib.sha256(content).hexdigest()


def _client(static_dir: Path) -> TestClient:
    app = FastAPI()
    app.mount(
        "/static",
        ContentFingerprintStaticFiles(directory=static_dir),
        name="static",
    )
    return TestClient(app)


def test_stale_manual_key_redirects_to_content_fingerprint_and_keeps_other_query() -> None:
    with tempfile.TemporaryDirectory() as directory:
        static_dir = Path(directory)
        content = b"window.example = true;\n"
        (static_dir / "app.js").write_bytes(content)
        client = _client(static_dir)

        response = client.get("/static/app.js?pi=overlay1&v=manual-old", follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == f"/static/app.js?pi=overlay1&v={_fingerprint(content)}"
        assert response.headers["cache-control"] == "no-store"


def test_fingerprinted_url_is_stable_immutable_and_changes_with_content() -> None:
    with tempfile.TemporaryDirectory() as directory:
        static_dir = Path(directory)
        asset = static_dir / "app.css"
        first = b"body { color: red; }\n"
        second = b"body { color: blue; }\n"
        asset.write_bytes(first)
        client = _client(static_dir)

        first_url = f"/static/app.css?v={_fingerprint(first)}"
        first_response = client.get(first_url)
        assert first_response.status_code == 200
        assert first_response.content == first
        assert first_response.headers["cache-control"] == "public, max-age=31536000, immutable"
        asset.touch()
        unchanged_response = client.get(
            "/static/app.css?v=manual-old",
            follow_redirects=False,
        )
        assert unchanged_response.headers["location"] == first_url

        asset.write_bytes(second)
        stale_response = client.get(first_url, follow_redirects=False)
        assert stale_response.status_code == 307
        assert stale_response.headers["location"] == f"/static/app.css?v={_fingerprint(second)}"

        second_response = client.get(stale_response.headers["location"])
        assert second_response.status_code == 200
        assert second_response.content == second


def test_static_asset_fingerprint_cache_is_bounded() -> None:
    from fsffl.product.static_assets import _asset_fingerprint

    assert _asset_fingerprint.cache_info().maxsize == 512

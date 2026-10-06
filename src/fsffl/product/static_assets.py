"""Content-derived cache keys for the product's static assets."""

from __future__ import annotations

from functools import lru_cache
import hashlib
from pathlib import Path
from urllib.parse import urlencode

from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import QueryParams
from starlette.types import Scope


@lru_cache(maxsize=512)
def _asset_fingerprint(
    path: str,
    modified_ns: int,
    changed_ns: int,
    size: int,
) -> str:
    """Hash the actual bytes, retaining only a bounded number of file versions."""

    # The stat values key the cache and invalidate normal edits/replacements.
    del modified_ns, changed_ns, size
    return "sha256-" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ContentFingerprintStaticFiles(StaticFiles):
    """Redirect stale manual cache keys to a stable, content-derived URL."""

    async def get_response(self, path: str, scope: Scope):
        full_path, stat_result = self.lookup_path(path)
        if stat_result is None or not Path(path).suffix:
            return await super().get_response(path, scope)

        fingerprint = _asset_fingerprint(
            full_path,
            stat_result.st_mtime_ns,
            stat_result.st_ctime_ns,
            stat_result.st_size,
        )
        query = QueryParams(scope.get("query_string", b"").decode("latin-1"))
        if query.getlist("v") != [fingerprint]:
            pairs = [(key, value) for key, value in query.multi_items() if key != "v"]
            pairs.append(("v", fingerprint))
            location = scope["path"] + "?" + urlencode(pairs)
            return RedirectResponse(
                location,
                status_code=307,
                headers={"Cache-Control": "no-store"},
            )

        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

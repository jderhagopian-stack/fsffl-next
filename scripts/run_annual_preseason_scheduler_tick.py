from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    endpoint = os.getenv("FSFFL_ANNUAL_SNAPSHOT_ENDPOINT", "").strip()
    token = os.getenv("FSFFL_SCHEDULER_TOKEN", "").strip()
    if not endpoint:
        print(
            json.dumps(
                {
                    "attempted": False,
                    "outcome": "failed-with-reason",
                    "detail": "FSFFL_ANNUAL_SNAPSHOT_ENDPOINT is not configured",
                }
            ),
            flush=True,
        )
        return 2
    if not token:
        print(
            json.dumps(
                {
                    "attempted": False,
                    "outcome": "failed-with-reason",
                    "detail": "FSFFL_SCHEDULER_TOKEN is not configured",
                }
            ),
            flush=True,
        )
        return 2

    print(
        json.dumps(
            {
                "attempted": True,
                "outcome": "attempted",
                "endpoint": endpoint,
            }
        ),
        flush=True,
    )
    request = Request(
        endpoint,
        data=b"",
        method="POST",
        headers={
            "X-FSFFL-Scheduler-Token": token,
            "User-Agent": "fsffl-next-annual-preseason-scheduler/1",
        },
    )
    try:
        with urlopen(request, timeout=180) as response:  # nosec B310 - configured HTTPS endpoint
            body = response.read().decode("utf-8")
            print(body, flush=True)
            return 0
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(
            json.dumps(
                {
                    "attempted": True,
                    "outcome": "failed-with-reason",
                    "status_code": exc.code,
                    "detail": body,
                }
            ),
            flush=True,
        )
        return 1
    except (URLError, TimeoutError) as exc:
        print(
            json.dumps(
                {
                    "attempted": True,
                    "outcome": "failed-with-reason",
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            ),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

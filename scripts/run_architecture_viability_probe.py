#!/usr/bin/env python3
"""Research-only screening of Career composition process ownership.

This is NOT a full Career/3-Year refresh, an authenticated browser benchmark,
a cgroup isolation test, or proof of hosted viability. It uses the repository's
existing synthetic 335-player composer test with unchanged implementation.
Do not use this script for live source acquisition or production publication.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time


RESULT_PREFIX = "FSFFL_VIABILITY_RESULT="
SCENARIOS = ("shared", "isolated")


def _peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def _rss_bytes(pid: int) -> int | None:
    try:
        stat = Path(f"/proc/{pid}/statm").read_text(encoding="ascii").split()
        return int(stat[1]) * os.sysconf("SC_PAGE_SIZE")
    except (FileNotFoundError, ProcessLookupError, ValueError, OSError, IndexError):
        return None


def _composer() -> None:
    # Exact existing test fixture and composer path in both arms.
    from tests.test_career_forward_intrinsic import (
        test_career_composer_materializer_peak_rss_below_budget,
    )

    test_career_composer_materializer_peak_rss_below_budget()


def _web_import():
    # No persistence credentials, TestClient lifespan, State restore or requests
    # are needed for this initial app-resident proxy.
    from fsffl.product import persistent_webapp

    return persistent_webapp.app


def _health(app) -> int:
    from fastapi.testclient import TestClient

    return TestClient(app).get("/health").status_code


def _run_worker(crash: bool) -> dict:
    baseline = _peak_rss_bytes()
    start = time.perf_counter()
    if crash:
        # Intentional abnormal termination tests the PROCESS boundary only.
        # It does not establish retained artifact or job-ledger recovery.
        _ = bytearray(16 * 1024 * 1024)
        os._exit(47)
    _composer()
    return {
        "scenario": "worker",
        "initial_peak_rss_bytes": baseline,
        "peak_rss_bytes": _peak_rss_bytes(),
        "elapsed_seconds": round(time.perf_counter() - start, 4),
        "composer_fixture": "synthetic-335-cloned-rows",
    }


def _run_shared() -> dict:
    start = time.perf_counter()
    app = _web_import()
    web_baseline = _peak_rss_bytes()
    assert _health(app) == 200, "web proxy health failed before composer"
    _composer()
    health_after = _health(app)
    assert health_after == 200, "web proxy health failed after shared composer"
    return {
        "scenario": "shared",
        "web_import_peak_rss_bytes": web_baseline,
        "combined_process_peak_rss_bytes": _peak_rss_bytes(),
        "health_after_http": health_after,
        "elapsed_seconds": round(time.perf_counter() - start, 4),
        "composer_fixture": "synthetic-335-cloned-rows",
    }


def _spawn_worker(*, crash: bool = False) -> tuple[subprocess.Popen[str], float]:
    args = [sys.executable, str(Path(__file__).resolve()), "--internal",
            "crash" if crash else "worker"]
    launched = time.perf_counter()
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, cwd=Path(__file__).resolve().parents[1]), launched


def _run_isolated() -> dict:
    start = time.perf_counter()
    app = _web_import()
    web_baseline = _peak_rss_bytes()
    assert _health(app) == 200, "web proxy health failed before worker"
    worker, launched = _spawn_worker()
    worker_max_sample = 0
    web_max_sample = 0
    summed_max_sample = 0
    while worker.poll() is None:
        child = _rss_bytes(worker.pid) or 0
        parent = _rss_bytes(os.getpid()) or 0
        worker_max_sample = max(worker_max_sample, child)
        web_max_sample = max(web_max_sample, parent)
        # Sum of per-process RSS is NOT container/cgroup RSS: shared pages
        # can be double-counted. This is a conservative comparison proxy.
        summed_max_sample = max(summed_max_sample, parent + child)
        if time.perf_counter() - launched > 180:
            worker.kill()
            worker.communicate()
            raise TimeoutError("offline synthetic 335-player worker exceeded 180 seconds")
        time.sleep(0.02)
    output, _ = worker.communicate()
    if worker.returncode != 0:
        raise RuntimeError(f"worker exit {worker.returncode}: {output[-2500:]}")
    records = [json.loads(line[len(RESULT_PREFIX):])
               for line in output.splitlines() if line.startswith(RESULT_PREFIX)]
    if len(records) != 1:
        raise RuntimeError(f"worker JSON receipt missing: {output[-2500:]}")
    finished_worker = records[0]

    crashed, _ = _spawn_worker(crash=True)
    crashed.communicate(timeout=20)
    assert crashed.returncode == 47, "injected worker crash not observed"
    health_after_crash = _health(app)
    assert health_after_crash == 200, "web process did not survive worker crash"
    return {
        "scenario": "isolated",
        "web_import_peak_rss_bytes": web_baseline,
        "web_peak_sampled_rss_bytes": max(web_max_sample, _peak_rss_bytes()),
        "worker_peak_rss_bytes": finished_worker["peak_rss_bytes"],
        "worker_peak_sampled_rss_bytes": worker_max_sample,
        "max_sum_process_rss_proxy_bytes": summed_max_sample,
        "worker_elapsed_seconds": finished_worker["elapsed_seconds"],
        "injected_worker_exit_code": crashed.returncode,
        "health_after_crash_http": health_after_crash,
        "elapsed_seconds": round(time.perf_counter() - start, 4),
        "composer_fixture": "synthetic-335-cloned-rows",
    }


def _run_child(scenario: str) -> dict:
    start = time.perf_counter()
    args = [sys.executable, str(Path(__file__).resolve()), "--internal", scenario]
    try:
        completed = subprocess.run(
            args, capture_output=True, text=True, timeout=240, check=False,
            cwd=Path(__file__).resolve().parents[1],
        )
    except subprocess.TimeoutExpired:
        return {"scenario": scenario, "status": "timeout", "elapsed_seconds": 240}
    rows = [line for line in completed.stdout.splitlines()
            if line.startswith(RESULT_PREFIX)]
    receipt = json.loads(rows[-1][len(RESULT_PREFIX):]) if rows else {}
    receipt.update({
        "scenario": scenario,
        "status": "pass" if completed.returncode == 0 and rows else "fail",
        "process_exit_code": completed.returncode,
        "wall_seconds": round(time.perf_counter() - start, 4),
        "error_excerpt": completed.stderr[-1500:] if completed.returncode else "",
        "stdout_excerpt": completed.stdout[-1500:] if completed.returncode else "",
    })
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("architecture_viability_proxy.json"))
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--internal", choices=("shared", "isolated", "worker", "crash"))
    args = parser.parse_args()
    if args.internal:
        case = {
            "shared": _run_shared,
            "isolated": _run_isolated,
            "worker": lambda: _run_worker(False),
            "crash": lambda: _run_worker(True),
        }[args.internal]
        try:
            result = case()
        except Exception as exc:
            print(f"{RESULT_PREFIX}{json.dumps({'scenario': args.internal, 'status': 'fail', 'error': str(exc)})}")
            return 1
        print(RESULT_PREFIX + json.dumps(result, sort_keys=True))
        return 0
    if args.repeats not in (1, 2, 3):
        parser.error("--repeats must be between 1 and 3 to bound CI cost")
    results = [_run_child(scenario)
               for _ in range(args.repeats) for scenario in SCENARIOS]
    report = {
        "authority": "research_only",
        "full_state_acceptance": False,
        "hosted_acceptance": False,
        "can_decide_architecture": False,
        "input": "existing synthetic 335-cloned-row Career composer fixture",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "limitations": [
            "No preserved exact-State full Career/P0/Foundation4/shapley refresh",
            "No concurrent hosted web restore/navigation/provider acquisition",
            "Each scenario runs in a fresh Python process; isolated worker shares runner/container",
            "RSS sums double-count shared pages and are not cgroup peaks",
            "No publication, last-good, idempotent job, memory OOM or 100k scaling proof",
        ],
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(row["status"] == "pass" for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

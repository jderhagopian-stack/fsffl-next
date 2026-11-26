#!/usr/bin/env python3
"""Bounded current-code Career stage probes using public sanitized test fixtures.

No private saved State, network/provider credentials or production publication.
This measures accepted current-code tests separately, not the complete hosted
Career refresh or a decision-grade combined-vs-worker comparison.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import zipfile


# These exact tests are owned by the existing production test suite.
# Failure of any test remains a failure; no numerical authority is rewritten.
CASES = (
    ("frozen_335_numeric_parity",
     "tests/test_career_frozen_reference_parity.py::test_frozen_335_shapley_and_career_numeric_parity"),
    ("career_335_persistence",
     "tests/test_foundation4_career_forward_runtime.py::test_full_current_cohort_materializes_and_persists_both_shadow_artifacts"),
    ("restart_exact_restore",
     "tests/test_foundation4_career_forward_runtime.py::test_restart_restore_is_semantically_identical_and_skips_rebuild"),
    ("dynamic_roster_integration",
     "tests/test_private_beta_shapley_runtime.py::test_hosted_dynamic_career_bridge_defers_shapley_until_foundation4_complete"),
    ("last_good_failure_recovery",
     "tests/test_foundation4_career_forward_runtime.py::test_refresh_checkpoint_and_batch_failure_preserve_same_key_last_good"),
)


def _rss(pid: int) -> int | None:
    try:
        return int(Path(f"/proc/{pid}/statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE")
    except (OSError, ValueError, IndexError):
        return None


def _prepare_public_fixture(directory: Path) -> dict[str, str]:
    encoded = Path("tests/fixtures/career_coverage/frozen_335_numeric_reference.zip.b64")
    archive = directory / "frozen.zip"
    archive.write_bytes(base64.b64decode(encoded.read_bytes()))
    with zipfile.ZipFile(archive) as z:
        for member in z.infolist():
            target = (directory / member.filename).resolve()
            if not target.is_relative_to(directory.resolve()):
                raise ValueError("unsafe fixture archive member")
        z.extractall(directory)
    return {
        "CAREER_PR1_SEMANTIC_DIR": str(directory / "semantic"),
        "CAREER_FOUNDATION4_DIR": str(directory / "foundation4"),
    }


def _measure(case: str, test: str, env: dict[str, str], timeout: int):
    # Fresh OS process per case; sample direct child RSS at 20 ms,
    # record max child high-water where supported. No nested web or job.
    started = time.perf_counter()
    peak_sample = 0
    cmd = [sys.executable, "-m", "pytest", "-q", "-s", test]
    child = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, env=env)
    try:
        while child.poll() is None:
            peak_sample = max(peak_sample, _rss(child.pid) or 0)
            if time.perf_counter() - started > timeout:
                child.kill()
                raise TimeoutError(f"{case}: exceeded {timeout}s")
            time.sleep(.02)
        output = child.communicate()[0]
    except BaseException:
        child.kill()
        child.communicate()
        raise
    duration = time.perf_counter() - started
    return {
        "case": case, "test": test,
        "status": "pass" if child.returncode == 0 else "fail",
        "exit_code": child.returncode,
        "elapsed_seconds": round(duration, 3),
        "rss_peak_sample_bytes": peak_sample,
        "output_tail": output[-1200:] if child.returncode else "",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-per-test", type=int, default=140)
    args = parser.parse_args()
    if not 10 <= args.timeout_per_test <= 240:
        parser.error("timeout per test must be between 10 and 240 seconds")
    with tempfile.TemporaryDirectory(prefix="fsffl-viability-public-") as temp:
        environment = os.environ.copy()
        environment.update(_prepare_public_fixture(Path(temp)))
        # Explicitly clear credential-bearing fields and prevent inadvertent
        # source acquisition. The tests use injected in-memory sources.
        for key in ("FSFFL_DATABASE_URL", "FSFFL_BETA_PASSWORD",
                    "FSFFL_BETA_USERNAME", "FSFFL_SCHEDULER_TOKEN"):
            environment.pop(key, None)
        environment["FSFFL_BETA_AUTH"] = "0"
        results = []
        for case, test in CASES:
            result = _measure(case, test, environment, args.timeout_per_test)
            results.append(result)
            print(f"CURRENT_CODE_PROBE={json.dumps(result, sort_keys=True)}", flush=True)
            if result["status"] != "pass":
                break
    report = {
        "scope": "current-repository sanitized exact-test stage decomposition",
        "source_fixture": "existing public frozen-335 numerical fixture; synthetic in-memory State for other tests",
        "authority": "research_only",
        "full_saved_state_acceptance": False,
        "hosted_memory_acceptance": False,
        "private_data_used": False,
        "can_decide_architecture": False,
        "python": sys.version.split()[0],
        "results": results,
        "limitations": [
            "No full accepted real saved-State Career build; stages are independent",
            "No simultaneous web serving and heavy model execution",
            "Sampled child RSS may miss very brief peaks",
            "No provider traffic, cgroup isolation, production artifact writes or actual worker recovery",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if len(results) == len(CASES) and all(r["status"] == "pass" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

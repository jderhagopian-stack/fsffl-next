"""Behavioral regressions for production Trade Center evidence ownership."""
from pathlib import Path
import shutil
import subprocess

import pytest


def test_trade_evidence_lifecycle() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    script = Path(__file__).parent / "browser" / "trade_evidence_lifecycle.cjs"
    result = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr

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


def test_served_classic_scripts_parse() -> None:
    """The shell must not silently lose a module to a JavaScript syntax error."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    root = Path(__file__).resolve().parents[1] / "src/fsffl/product/static"
    script = r"""
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=process.argv[1],html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const names=[...html.matchAll(/<script src="\/static\/([^?"]+)/g)].map(m=>m[1]);
names.push('opportunities.js');
for(const name of names)new vm.Script(fs.readFileSync(path.join(root,name),'utf8'),{filename:name});
"""
    result = subprocess.run([node, "-e", script, str(root)], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr

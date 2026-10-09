"""Offline tests of the iPhone-launched Workflow entrypoint, no private data."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

class _Retry:
    def __init__(self, max_retries: int = 3, wait_duration_ms: int = 0):
        self.max_retries = max_retries
        self.wait_duration_ms = wait_duration_ms

class _Workflows:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.tasks = {}

    def task(self, **kwargs):
        def deco(fn):
            self.tasks[kwargs["name"]] = (fn, kwargs)
            return fn
        return deco

def _load_workflow(monkeypatch):
    fake = types.ModuleType("render")
    fake.Retry, fake.TaskContext, fake.Workflows = _Retry, object, _Workflows
    monkeypatch.setitem(sys.modules, "render", fake)
    path = HERE / "workflow_entry.py"
    spec = importlib.util.spec_from_file_location("storage_workflow_entry_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_registration_and_no_argument_credentials(monkeypatch):
    entry = _load_workflow(monkeypatch)
    assert set(entry.app.tasks) == {"preflight", "validate_real_artifacts"}
    for name, (task, settings) in entry.app.tasks.items():
        assert task.__code__.co_argcount == 1
        assert settings["retry"].max_retries == 0
        assert settings["retry"].wait_duration_ms == 0
        assert settings["plan"] == "flex"

def test_synthetic_preflight_no_secrets(monkeypatch):
    entry = _load_workflow(monkeypatch)
    assert entry.preflight(None)["status"] == "PASS"

def test_real_task_fail_closed_without_credentials(monkeypatch):
    entry = _load_workflow(monkeypatch)
    for name in ("FSFFL_DATABASE_URL", "FSFFL_TEST_S3_ACCESS_KEY_ID",
                 "FSFFL_TEST_S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(name, raising=False)
    try:
        entry.validate_real_artifacts(None)
    except RuntimeError as exc:
        assert "BLOCKED" in str(exc)
        assert "password" not in str(exc).lower()
    else:
        raise AssertionError("unconfigured validation must not run")

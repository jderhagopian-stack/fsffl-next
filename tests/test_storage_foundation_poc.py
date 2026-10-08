"""Focused isolation/identity/failure tests for the storage foundation POC.

No production dependencies, credentials, provider refresh or schema writes.
A private unmodified artifact export can optionally be passed by environment
variable; public fixtures intentionally contain no production-user data.
"""
from dataclasses import replace
from pathlib import Path
import json
import os
import sys
import tracemalloc
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
  "artifacts/implementation/storage_foundation_poc_20261008"))
from hybrid_adapter import ArtifactIdentity, HybridPrototype, IntegrityError, LocalObjectStore, Metadata


def ident(kind="current_forecast_evidence", tenant="test-user", fp="state-1"):
    return ArtifactIdentity(tenant, kind, "league_state", "state-1", fp,
                            "accepted-model-v1", "2026-10-08T15:00:00Z")


def sample(kind="current_forecast_evidence"):
    rows = [
      {"asset_id": f"public-fixture-{i}", "mean": 50.25+i*0.2,
       "weekly_points": [round(i+j*0.11, 3) for j in range(18)]}
      for i in range(400)
    ]
    if kind == "live_simulation_analytics":
        return {"model_version": "simulation-fixture-v1", "league_view":
                {"trial_count":50000, "rng":"numpy-pcg64-batched-gauss-v1"},
                "team_views":[{"team": f"fixture-{i}", "players": rows[i*25:i*25+25]}
                              for i in range(12)]}
    return {"model_version": "forecast-fixture-v1", "evidence_basis":"full-season",
            "successful_source_ids": ["source-a","source-b"], "raw_forecasts": rows}


@pytest.fixture
def repo(tmp_path):
    return HybridPrototype(LocalObjectStore(tmp_path/"objects"),
                           Metadata(tmp_path/"metadata.db"))


def test_forecast_simulation_roundtrip_and_size(repo):
    for kind in ("current_forecast_evidence", "live_simulation_analytics"):
        i = ident(kind)
        orig = sample(kind)
        metrics = repo.put(i, orig)
        assert metrics["stored_bytes"] < metrics["raw_bytes"]
        saved = repo.get(i)
        assert saved["payload"] == orig
        assert saved["identity"] == i
        assert saved["computed_at"] == i.computed_at


def test_immutable_first_writer_and_idempotent(repo):
    i = ident()
    p = sample()
    first = repo.put(i,p)
    assert first == repo.put(i,p)
    with pytest.raises(IntegrityError, match="first-writer"):
        repo.put(i, {**p, "evidence_basis":"changed"})
    assert repo.get(i)["payload"] == p


def test_missed_object_and_corruption_fail_closed(repo):
    i = ident()
    m = repo.put(i,sample())
    obj = repo.objects.path(i.tenant, m["sha256"])
    obj.write_bytes(b"not zlib")
    with pytest.raises(IntegrityError):
        repo.get(i)
    obj.unlink()
    with pytest.raises(IntegrityError):
        repo.get(i)


def test_tenant_isolation_and_version_fence(repo):
    a = ident(tenant="tenant-a")
    b = ident(tenant="tenant-b")
    p = sample()
    out_a = repo.put(a,p)
    out_b = repo.put(b,p)
    assert repo.objects.path(a.tenant,out_a["sha256"]) != repo.objects.path(
        b.tenant,out_b["sha256"])
    assert repo.get(a)["payload"] == repo.get(b)["payload"] == p
    assert repo.get(ident(tenant="tenant-c")) is None
    assert repo.get(replace(a, model_version="incompatible")) is None
    assert repo.get(replace(a, input_fingerprint="changed-State")) is None


def test_process_restart_and_legacy_coexistence(tmp_path):
    objects = LocalObjectStore(tmp_path/"objects")
    first = HybridPrototype(objects, Metadata(tmp_path/"meta.db"))
    key = ident(kind="live_simulation_analytics")
    src = sample("live_simulation_analytics")
    first.put(key,src)
    first.metadata.close()
    fallback_key = ident(fp="legacy-pg-artifact")
    def legacy(identity):
        if identity.key() == fallback_key.key():
            return {"identity":identity,"computed_at":identity.computed_at,
                    "payload":sample()}
        return None
    after = HybridPrototype(objects, Metadata(tmp_path/"meta.db"),legacy_read=legacy)
    assert after.get(key)["payload"] == src
    assert after.get(fallback_key,legacy_fallback=True)["payload"] == sample()
    assert after.get(fallback_key,legacy_fallback=False) is None


def test_object_failure_cannot_commit_metadata(repo,monkeypatch):
    i=ident()
    def die(*args):
        raise OSError("object storage unavailable")
    monkeypatch.setattr(repo.objects,"put_once",die)
    with pytest.raises(OSError):
        repo.put(i,sample())
    assert repo.metadata.get(i) is None


def test_bounded_read_memory(repo):
    i = ident()
    repo.put(i,sample())
    tracemalloc.start()
    try:
        p=repo.get(i)
        _, peak=tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert p["identity"] == i
    assert peak < 30*1024*1024


def test_real_artifact_copy_optional_local_only(repo):
    path=os.environ.get("FSFFL_NONPRODUCTION_ARTIFACT_JSON")
    if not path:
        pytest.skip("private real artifact copy intentionally not tracked in Git")
    with open(path,encoding="utf-8") as handle:
        obj=json.load(handle)
    key=obj["key"]
    assert key["artifact_kind"] in ("current_forecast_evidence",
                                  "live_simulation_analytics")
    i=ArtifactIdentity(obj["tenant"],key["artifact_kind"],key["scope_kind"],
        key["scope_id"],key["input_fingerprint"],key["model_version"],
        obj["computed_at"])
    assert repo.get(i) is None
    repo.put(i,obj["payload"])
    assert repo.get(i)["payload"] == obj["payload"]

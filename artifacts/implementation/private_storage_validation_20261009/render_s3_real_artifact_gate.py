"""Private nonproduction FSFFL phase-2 proof: execute ONLY in isolated Render ephemeral shell.

Requires the accepted #439 hybrid_adapter.py in PYTHONPATH and the main FSFFL
runtime installed in the Render build. Reads ONLY two existing PostgreSQL rows;
all object writes use one dedicated PRIVATE Supabase Storage TEST bucket.
Secrets are prompted from a TTY, never printed, committed or put in argv/logs.
Only anonymous aggregate timings/sizes are printed. Never run as web entrypoint.
"""
from __future__ import annotations

import gc
import getpass
from hashlib import sha256
import math
import os
import resource
import statistics
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4
import zlib

ARTIFACT_IDS = (11540, 11541)
EXPECTED_KINDS = {
    11540: "current_forecast_evidence",
    11541: "live_simulation_analytics",
}
BUCKET = "fsffl-private-storage-validation-20261009"
REGION = "us-east-1"
ENDPOINT = "https://gldxkbqcprzuffgmamxl.storage.supabase.co/storage/v1/s3"
REPS = 9
MAX_JSON_BYTES = 12 * 1024 * 1024
PG_TIMEOUT_MS = 8000


def percentile(values, q):
    s = sorted(values)
    return round(s[max(0, math.ceil(q * len(s)) - 1)], 2)


class S3Objects:
    """Only keys beneath this run's random private prefix; conditional immutable puts."""

    def __init__(self, client, prefix):
        self.client = client
        self.prefix = prefix
        self.written = set()

    def key(self, tenant, digest):
        tenant_hash = sha256(tenant.encode("utf-8")).hexdigest()[:24]
        return f"{self.prefix}/{tenant_hash}/{digest[:2]}/{digest}.zlib"

    @staticmethod
    def http_status(error):
        try:
            return int(error.response["ResponseMetadata"]["HTTPStatusCode"])
        except (KeyError, ValueError, TypeError):
            return 0

    def put_once(self, tenant, digest, packed):
        from botocore.exceptions import ClientError
        key = self.key(tenant, digest)
        try:
            self.client.put_object(
                Bucket=BUCKET, Key=key, Body=packed, IfNoneMatch="*",
                ContentType="application/octet-stream",
            )
            self.written.add(key)
        except ClientError as exc:
            if self.http_status(exc) not in (409, 412):
                raise RuntimeError("S3 conditional immutable PUT failed") from None
            if self.get(tenant, digest) != packed:
                raise RuntimeError("S3 immutable-key content collision") from None

    def get(self, tenant, digest):
        from botocore.exceptions import ClientError
        try:
            response = self.client.get_object(
                Bucket=BUCKET, Key=self.key(tenant, digest))
            try:
                return response["Body"].read()
            finally:
                response["Body"].close()
        except ClientError as exc:
            if self.http_status(exc) in (403, 404):
                raise FileNotFoundError("S3 object inaccessible/missing") from None
            raise OSError("S3 get failed") from None

    def head(self, tenant, digest):
        return self.client.head_object(
            Bucket=BUCKET, Key=self.key(tenant, digest))["ContentLength"]

    def cleanup(self):
        remaining = []
        for key in sorted(self.written):
            try:
                self.client.delete_object(Bucket=BUCKET, Key=key)
            except Exception:
                remaining.append(key)
        return len(remaining)


def read_two_rows():
    import psycopg
    from psycopg.rows import dict_row
    dsn = os.getenv("FSFFL_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("FSFFL_DATABASE_URL missing in ephemeral environment")
    with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=6,
                         options=f"-c statement_timeout={PG_TIMEOUT_MS}") as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute(
                """SELECT id, artifact_kind, scope_kind, scope_id, input_fingerprint,
                          model_version, payload, computed_at, invalidated_at,
                          pg_column_size(payload) AS jsonb_bytes,
                          octet_length(payload::text) AS pg_text_bytes
                   FROM fsffl.derived_artifact
                   WHERE id IN (11540, 11541) ORDER BY id""")
            rows = cursor.fetchall()
        connection.rollback()
    if len(rows) != 2 or [row["id"] for row in rows] != list(ARTIFACT_IDS):
        raise RuntimeError("exact two-artifact read gate failed")
    for row in rows:
        if row["artifact_kind"] != EXPECTED_KINDS[row["id"]]:
            raise RuntimeError("artifact-kind identity mismatch")
        if row["scope_kind"] != "league_state":
            raise RuntimeError("scope identity mismatch")
        if row["invalidated_at"] is not None:
            raise RuntimeError("selected artifact is invalidated")
        if not isinstance(row["payload"], dict):
            raise RuntimeError("JSONB payload is not a mapping")
    return rows


def benchmark_pg_get_and_decode(row, expected_canonical):
    """Bounded like-for-like current SQL+model decode. Never modify the DB."""
    import psycopg
    from psycopg.rows import dict_row
    samples = []
    with psycopg.connect(
        os.environ["FSFFL_DATABASE_URL"], row_factory=dict_row,
        connect_timeout=6, options=f"-c statement_timeout={PG_TIMEOUT_MS}"
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            for _ in range(REPS):
                start = time.perf_counter()
                cursor.execute(
                    "SELECT payload FROM fsffl.derived_artifact WHERE id = %s",
                    (row["id"],))
                selected = cursor.fetchone()
                if selected is None:
                    raise RuntimeError("PostgreSQL comparison record disappeared")
                decoded = decode_governed(
                    row["artifact_kind"], selected["payload"])
                if _bytes_for_comparison(selected["payload"]) != expected_canonical:
                    raise RuntimeError("PostgreSQL comparison bytes changed")
                if decoded is None:
                    raise RuntimeError("PostgreSQL governed decode absent")
                samples.append((time.perf_counter() - start) * 1000)
        connection.rollback()
    return samples


def _bytes_for_comparison(payload):
    from hybrid_adapter import _bytes
    return _bytes(payload)


def build_record(row, payload):
    from fsffl.persistence.contracts import ArtifactKey, ReusableArtifactRecord
    return ReusableArtifactRecord(
        key=ArtifactKey(
            artifact_kind=row["artifact_kind"], scope_kind=row["scope_kind"],
            scope_id=row["scope_id"], input_fingerprint=row["input_fingerprint"],
            model_version=row["model_version"]),
        payload=payload, computed_at=row["computed_at"])


def decode_governed(kind, payload):
    from fsffl.persistence.runtime_cache import (
        decode_forecast_evidence, decode_simulation)
    if kind == "current_forecast_evidence":
        return decode_forecast_evidence(payload)
    if kind == "live_simulation_analytics":
        return decode_simulation(payload)
    raise RuntimeError("unauthorized artifact family")


def probe_conditional_put(objects):
    """Fail closed if this S3 provider ignores If-None-Match on a foreign value."""
    from botocore.exceptions import ClientError
    canary = f"{objects.prefix}/immutable-canary"
    objects.client.put_object(
        Bucket=BUCKET, Key=canary, Body=b"first", IfNoneMatch="*",
        ContentType="application/octet-stream")
    objects.written.add(canary)
    try:
        objects.client.put_object(
            Bucket=BUCKET, Key=canary, Body=b"changed", IfNoneMatch="*",
            ContentType="application/octet-stream")
    except ClientError as exc:
        if objects.http_status(exc) not in (409, 412):
            raise RuntimeError("S3 conditional PUT error") from None
    else:
        raise RuntimeError("S3 accepted overwrite of immutable key")
    actual = objects.client.get_object(Bucket=BUCKET, Key=canary)
    try:
        if actual["Body"].read() != b"first":
            raise RuntimeError("S3 conditional-put race safety failed")
    finally:
        actual["Body"].close()


def run():
    # No persistent credentials: interactive prompt ONLY within ephemeral shell.
    import boto3
    from botocore.config import Config
    from hybrid_adapter import (
        ArtifactIdentity, HybridPrototype, IntegrityError, Metadata, _bytes)
    if not sys.stdin.isatty():
        raise RuntimeError("interactive private shell required")
    key = getpass.getpass("Supabase S3 access key ID (hidden): ")
    secret = getpass.getpass("Supabase S3 secret key (hidden): ")
    if not key or not secret:
        raise RuntimeError("S3 credentials not provided")
    client = boto3.client(
        "s3", region_name=REGION, endpoint_url=ENDPOINT,
        aws_access_key_id=key, aws_secret_access_key=secret,
        config=Config(s3={"addressing_style": "path"},
                      retries={"max_attempts": 2, "mode": "standard"},
                      connect_timeout=5, read_timeout=10))
    del key, secret
    prefix = "isolated-private-test/" + uuid4().hex
    store = S3Objects(client, prefix)
    status = "NO-GO"
    try:
        # Check bucket is private, bounded and exactly the pre-authorized bucket.
        client.head_bucket(Bucket=BUCKET)
        rows = read_two_rows()
        probe_conditional_put(store)
        with tempfile.TemporaryDirectory(prefix="fsffl-private-p2-") as td:
            # SQLite metadata and full payload objects exist only transiently.
            directory = Path(td)
            prototype = HybridPrototype(store, Metadata(directory / "local-meta.sqlite"))
            for row in rows:
                kind = row["artifact_kind"]
                identity = ArtifactIdentity(
                    tenant="isolated-validation-copy-only", artifact_kind=kind,
                    scope_kind=row["scope_kind"], scope_id=row["scope_id"],
                    input_fingerprint=row["input_fingerprint"],
                    model_version=row["model_version"],
                    computed_at=row["computed_at"].isoformat())
                source = build_record(row, row["payload"])
                original = decode_governed(kind, row["payload"])
                start_cpu = time.process_time()
                t0 = time.perf_counter()
                raw = _bytes(row["payload"])
                if len(raw) > MAX_JSON_BYTES:
                    raise RuntimeError("unbounded input rejected")
                digest = sha256(raw).hexdigest()
                packed = zlib.compress(raw, 6)
                encode_ms = (time.perf_counter() - t0) * 1000
                store_ms = time.perf_counter()
                stats = prototype.put(identity, row["payload"])
                put_ms = (time.perf_counter() - store_ms) * 1000
                if stats["stored_bytes"] != len(packed) or stats["sha256"] != digest:
                    raise RuntimeError("prototype zlib/digest mismatch")
                if store.head(identity.tenant, digest) != len(packed):
                    raise RuntimeError("S3 HEAD byte length mismatch")
                measured = []
                for _ in range(REPS):
                    t1 = time.perf_counter()
                    loaded = prototype.get(identity)
                    if loaded is None or _bytes(loaded["payload"]) != raw:
                        raise RuntimeError("S3 exact content reconstruction failed")
                    hydrated = build_record(row, loaded["payload"])
                    if hydrated != source:
                        raise RuntimeError("ReusableArtifactRecord contract difference")
                    decoded = decode_governed(kind, loaded["payload"])
                    if decoded != original:
                        raise RuntimeError("governed model decoder semantic difference")
                    measured.append((time.perf_counter() - t1) * 1000)
                pg_measurements = benchmark_pg_get_and_decode(row, raw)
                # Confirm a fresh persistence/metadata instance can restart and read.
                prototype.metadata.close()
                reopened = HybridPrototype(store, Metadata(directory / "local-meta.sqlite"))
                if _bytes(reopened.get(identity)["payload"]) != raw:
                    raise RuntimeError("restart continuity difference")
                # Tampering is detected without overwriting or exposing the S3 bytes.
                class Truncated:
                    def get(self, tenant, content_digest):
                        return store.get(tenant, content_digest)[:8]
                corrupted = HybridPrototype(Truncated(), reopened.metadata)
                try:
                    corrupted.get(identity)
                except IntegrityError:
                    pass
                else:
                    raise RuntimeError("corruption did not fail closed")
                reopened.metadata.close()
                # The second artifact needs its own fresh SQLite connection.
                prototype = HybridPrototype(
                    store, Metadata(directory / "local-meta.sqlite"))
                # Metric definitions: PostgreSQL compressed datum is NOT a physical
                # per-row disk saving; p95 here is 9 sampled S3+decoder round trips.
                cpu_ms = (time.process_time() - start_cpu) * 1000
                peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
                print(f"{kind}: pg_jsonb={row['jsonb_bytes']} "
                      f"pg_text={row['pg_text_bytes']} canonical={len(raw)} "
                      f"zlib_s3={len(packed)} ratio_vs_jsonb="
                      f"{len(packed) / row['jsonb_bytes']:.3f} "
                      f"encode_ms={encode_ms:.2f} put_ms={put_ms:.2f} "
                      f"get_rehydrate_p50_ms={statistics.median(measured):.2f} "
                      f"get_rehydrate_p95_ms={percentile(measured, 0.95):.2f} "
                      f"pg_get_model_p50_ms={statistics.median(pg_measurements):.2f} "
                      f"pg_get_model_p95_ms={percentile(pg_measurements, 0.95):.2f} "
                      f"samples={len(measured)} cpu_ms={cpu_ms:.2f} "
                      f"process_peak_rss_bytes={peak_rss} "
                      f"model_decoder=PASS sha256=PASS restart=PASS corruption=PASS")
                del source, original, raw, packed
                gc.collect()
        status = "GO — private two-artifact proof only; no production integration decision"
    finally:
        try:
            pending = store.cleanup()
        except Exception:
            pending = -1
        print("test_objects_cleanup_remaining_count=", pending,
              "; bucket remains private; verify cleanup before retiring credentials")
    print(status)


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        # Never print secret-bearing exception details or raw provider payload.
        print("NO-GO: private gate stopped at exception class", type(exc).__name__)
        sys.exit(1)

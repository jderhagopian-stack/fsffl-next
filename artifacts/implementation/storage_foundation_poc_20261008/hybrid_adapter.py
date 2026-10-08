"""Nonproduction FSFFL immutable-object storage POC.

Pure Python stdlib, no production configuration, DDL, provider or cloud calls.
Authoritative ArtifactIdentity arrives from the existing persistence caller.
SQLite and a local directory stand in for PostgreSQL metadata + object storage.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import os
import sqlite3
import zlib

CODEC = "fsffl-canonical-json-zlib-v1"


def _bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class ArtifactIdentity:
    tenant: str
    artifact_kind: str
    scope_kind: str
    scope_id: str
    input_fingerprint: str
    model_version: str
    computed_at: str

    def key(self):
        return (self.tenant, self.artifact_kind, self.scope_kind,
                self.scope_id, self.input_fingerprint, self.model_version)


class IntegrityError(RuntimeError):
    pass


class LocalObjectStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, tenant: str, digest: str) -> Path:
        return (self.root / sha256(tenant.encode()).hexdigest()[:24]
                / digest[:2] / (digest + ".zlib"))

    def put_once(self, tenant: str, digest: str, packed: bytes):
        path = self.path(tenant, digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != packed:
                raise IntegrityError("preexisting immutable object differs")
            return
        temp = path.with_name(path.name + ".new-" + str(os.getpid()))
        try:
            with temp.open("xb") as f:
                f.write(packed)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)

    def get(self, tenant: str, digest: str) -> bytes:
        return self.path(tenant, digest).read_bytes()


class Metadata:
    def __init__(self, db: Path):
        self.conn = sqlite3.connect(db)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS artifacts(
            tenant TEXT,kind TEXT,scope_kind TEXT,scope_id TEXT,fp TEXT,
            model TEXT,computed TEXT,codec TEXT,digest TEXT,raw_size INTEGER,
            packed_size INTEGER,
            PRIMARY KEY(tenant,kind,scope_kind,scope_id,fp,model))""")
        self.conn.commit()

    def put(self, identity: ArtifactIdentity, digest: str, n: int, packed_n: int):
        with self.conn:
            self.conn.execute(
                """INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(tenant,kind,scope_kind,scope_id,fp,model)
                DO NOTHING""",
                (*identity.key(), identity.computed_at, CODEC, digest, n, packed_n))
            prior = self.get(identity)
            if prior[2] != digest or prior[1] != CODEC:
                raise IntegrityError("first-writer metadata conflict")

    def get(self, identity: ArtifactIdentity):
        return self.conn.execute(
            """SELECT computed,codec,digest,raw_size,packed_size FROM artifacts
            WHERE tenant=? AND kind=? AND scope_kind=? AND scope_id=?
              AND fp=? AND model=?""", identity.key()).fetchone()

    def close(self):
        self.conn.close()


class HybridPrototype:
    """Never advances State, manifest, published-generation or last-good pointers."""

    def __init__(self, objects: LocalObjectStore, metadata: Metadata, legacy_read=None):
        self.objects = objects
        self.metadata = metadata
        self.legacy_read = legacy_read

    def put(self, identity: ArtifactIdentity, payload: dict):
        raw = _bytes(payload)
        digest = sha256(raw).hexdigest()
        packed = zlib.compress(raw, 6)
        # Durable immutable bytes FIRST; small authoritative metadata SECOND.
        self.objects.put_once(identity.tenant, digest, packed)
        self.metadata.put(identity, digest, len(raw), len(packed))
        return {"sha256": digest, "raw_bytes": len(raw),
                "stored_bytes": len(packed)}

    def get(self, identity: ArtifactIdentity, legacy_fallback=False):
        record = self.metadata.get(identity)
        if record is None:
            return self.legacy_read(identity) if legacy_fallback and self.legacy_read else None
        computed, codec, digest, expected, _ = record
        if codec != CODEC:
            raise IntegrityError("unsupported codec")
        try:
            packed = self.objects.get(identity.tenant, digest)
            decoder = zlib.decompressobj()
            raw = decoder.decompress(packed, expected + 1)
            if not decoder.eof or decoder.unconsumed_tail or len(raw) != expected:
                raise IntegrityError("compressed frame/size mismatch")
            if sha256(raw).hexdigest() != digest:
                raise IntegrityError("content hash mismatch")
            payload = json.loads(raw)
            if not isinstance(payload, dict) or _bytes(payload) != raw:
                raise IntegrityError("noncanonical payload")
        except (OSError, zlib.error, ValueError) as exc:
            if legacy_fallback and self.legacy_read:
                old = self.legacy_read(identity)
                if old is not None:
                    return old
            raise IntegrityError("missing/corrupt object") from exc
        return {"identity": identity, "computed_at": computed, "payload": payload}

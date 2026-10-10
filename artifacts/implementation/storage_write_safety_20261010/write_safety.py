"""Bounded, nonproduction prototype for immutable blob + DB publication.

The object-store port is deliberately tiny. Its Supabase implementation must
use the Standard Storage upload API with upsert=False; S3 PutObject is excluded.
SQLite stands in for the authoritative PostgreSQL metadata transaction. This
module is not wired into FSFFL persistence and makes no network calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from contextlib import contextmanager
from typing import Callable, Iterable, Protocol
import zlib

CODEC = "fsffl-canonical-json-zlib-v1"
MAX_RAW_BYTES = 16 * 1024 * 1024
MAX_OBJECT_BYTES = 8 * 1024 * 1024  # matches the existing private test bucket cap


def canonical_json(value: dict) -> bytes:
    if not isinstance(value, dict):
        raise TypeError("artifact payload must be an object")
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


class WriteSafetyError(RuntimeError):
    """Base class for fail-closed storage/publication errors."""


class AlreadyExists(WriteSafetyError):
    pass


class IntegrityError(WriteSafetyError):
    pass


class IdentityConflict(WriteSafetyError):
    pass


class PublicationConflict(WriteSafetyError):
    pass


@dataclass(frozen=True, order=True)
class ArtifactIdentity:
    tenant_id: str
    artifact_kind: str
    scope_kind: str
    scope_id: str
    state_id: str
    pit_state_id: str
    input_fingerprint: str
    model_version: str

    def fields(self) -> tuple[str, ...]:
        values = tuple(getattr(self, field) for field in self.__dataclass_fields__)
        if any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError("all artifact identity fields are required")
        return values

    def as_dict(self) -> dict[str, str]:
        return dict(zip(self.__dataclass_fields__, self.fields()))


@dataclass(frozen=True)
class ArtifactInput:
    identity: ArtifactIdentity
    payload: dict


@dataclass(frozen=True)
class PublicationCandidate:
    tenant_id: str
    surface: str
    generation_id: str
    state_id: str
    pit_state_id: str
    manifest_id: str
    artifacts: tuple[ArtifactInput, ...]

    def __post_init__(self):
        for value in (self.tenant_id, self.surface, self.generation_id,
                      self.state_id, self.pit_state_id, self.manifest_id):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("publication identity fields are required")
        if not self.artifacts:
            raise ValueError("a publication must contain at least one artifact")
        if len({a.identity for a in self.artifacts}) != len(self.artifacts):
            raise ValueError("duplicate artifact identity in publication")
        for artifact in self.artifacts:
            i = artifact.identity
            if (i.tenant_id, i.state_id, i.pit_state_id) != (
                    self.tenant_id, self.state_id, self.pit_state_id):
                raise ValueError("tenant, State, or PIT identity mismatch")


class CreateOnlyApi(Protocol):
    def upload(self, key: str, body: bytes, *, upsert: bool) -> None: ...
    def download(self, key: str) -> bytes: ...


class SupabaseStandardUploadStore:
    """Adapter around an injected Supabase Storage Standard Upload client.

    `upload` must call the bucket's documented Standard Upload endpoint with
    upsert=False and map Supabase's Asset Already Exists/KeyAlreadyExists
    response to AlreadyExists. Existing bytes are always read and verified.
    The adapter has no S3 fallback and never retries with upsert=True.
    """
    def __init__(self, api: CreateOnlyApi):
        self.api = api

    def put_if_absent(self, key: str, body: bytes, expected_sha256: str) -> bool:
        if sha256(body).hexdigest() != expected_sha256:
            raise IntegrityError("caller object hash mismatch")
        created = False
        try:
            self.api.upload(key, body, upsert=False)
            created = True
        except AlreadyExists:
            pass
        existing = self.api.download(key)
        if sha256(existing).hexdigest() != expected_sha256 or existing != body:
            raise IntegrityError("existing create-only object differs from expected bytes")
        return created

    def get(self, key: str) -> bytes:
        return self.api.download(key)


class AtomicDirectoryStore:
    """Local no-overwrite backend for deterministic offline concurrency tests."""
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("object path escaped store root")
        return path

    def put_if_absent(self, key: str, body: bytes, expected_sha256: str) -> bool:
        if sha256(body).hexdigest() != expected_sha256:
            raise IntegrityError("caller object hash mismatch")
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".stage-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                # Same-filesystem hard-link creation is atomic and fails if
                # target exists; os.replace() would violate immutability.
                os.link(temporary, path)
                return True
            except FileExistsError:
                return False
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()


@dataclass(frozen=True)
class PreparedObject:
    identity: ArtifactIdentity
    object_key: str
    raw_sha256: str
    object_sha256: str
    raw_size: int
    object_size: int
    computed_payload: dict


class MetadataDatabase:
    """SQLite transaction stand-in; production requires same constraints in PG."""
    def __init__(self, path: Path):
        self.path = str(path)
        with self.connection() as db:
            db.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS artifact_blob_registry (
                tenant_id TEXT NOT NULL,
                artifact_kind TEXT NOT NULL,
                scope_kind TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                state_id TEXT NOT NULL,
                pit_state_id TEXT NOT NULL,
                input_fingerprint TEXT NOT NULL,
                model_version TEXT NOT NULL,
                codec TEXT NOT NULL,
                raw_sha256 TEXT NOT NULL,
                object_sha256 TEXT NOT NULL,
                object_key TEXT NOT NULL,
                raw_size INTEGER NOT NULL,
                object_size INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, artifact_kind, scope_kind, scope_id,
                             state_id, pit_state_id, input_fingerprint, model_version)
            );
            CREATE TABLE IF NOT EXISTS publication_generation (
                tenant_id TEXT NOT NULL,
                surface TEXT NOT NULL,
                generation_id TEXT NOT NULL,
                state_id TEXT NOT NULL,
                pit_state_id TEXT NOT NULL,
                manifest_id TEXT NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                complete INTEGER NOT NULL CHECK (complete = 1),
                PRIMARY KEY (tenant_id, surface, generation_id)
            );
            CREATE TABLE IF NOT EXISTS publication_artifact_ref (
                tenant_id TEXT NOT NULL,
                surface TEXT NOT NULL,
                generation_id TEXT NOT NULL,
                artifact_kind TEXT NOT NULL,
                scope_kind TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                state_id TEXT NOT NULL,
                pit_state_id TEXT NOT NULL,
                input_fingerprint TEXT NOT NULL,
                model_version TEXT NOT NULL,
                raw_sha256 TEXT NOT NULL,
                PRIMARY KEY (tenant_id, surface, generation_id, artifact_kind,
                             scope_kind, scope_id, state_id, pit_state_id,
                             input_fingerprint, model_version),
                FOREIGN KEY (tenant_id, surface, generation_id)
                    REFERENCES publication_generation(tenant_id, surface, generation_id)
            );
            CREATE TABLE IF NOT EXISTS publication_pointer (
                tenant_id TEXT NOT NULL,
                surface TEXT NOT NULL,
                state_id TEXT NOT NULL,
                pit_state_id TEXT NOT NULL,
                manifest_id TEXT NOT NULL,
                current_generation_id TEXT NOT NULL,
                last_good_generation_id TEXT NOT NULL,
                PRIMARY KEY (tenant_id, surface)
            );
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    @contextmanager
    def connection(self):
        db = self.connect()
        try:
            yield db
        finally:
            if db.in_transaction:
                db.execute("ROLLBACK")
            db.close()


class ImmutablePublisher:
    """Stages immutable bytes; one DB transaction registers and publishes.

    Object upload may leave harmless unreferenced bytes on a later DB failure.
    No publication pointer is advanced until every object hash, registry row,
    complete manifest and caller's generation CAS all validate.
    """
    def __init__(self, objects, metadata: MetadataDatabase,
                 after_upload: Callable[[tuple[PreparedObject, ...]], None] | None = None,
                 before_pointer: Callable[[], None] | None = None):
        self.objects = objects
        self.metadata = metadata
        self.after_upload = after_upload
        self.before_pointer = before_pointer

    @staticmethod
    def _prepare(item: ArtifactInput) -> tuple[PreparedObject, bytes]:
        raw = canonical_json(item.payload)
        if len(raw) > MAX_RAW_BYTES:
            raise ValueError("artifact exceeds the bounded prototype size")
        packed = zlib.compress(raw, level=6)
        if len(packed) > MAX_OBJECT_BYTES:
            raise ValueError("compressed artifact exceeds the bounded object size")
        raw_hash = sha256(raw).hexdigest()
        object_hash = sha256(packed).hexdigest()
        tenant_path = sha256(item.identity.tenant_id.encode()).hexdigest()[:24]
        key = f"t/{tenant_path}/{CODEC}/{object_hash}.zlib"
        return PreparedObject(item.identity, key, raw_hash, object_hash,
                              len(raw), len(packed), item.payload), packed

    @staticmethod
    def _manifest_hash(candidate: PublicationCandidate,
                       prepared: Iterable[PreparedObject]) -> str:
        entries = [{"identity": p.identity.as_dict(),
                    "raw_sha256": p.raw_sha256,
                    "object_sha256": p.object_sha256,
                    "object_key": p.object_key}
                   for p in sorted(prepared, key=lambda v: v.identity)]
        body = {"tenant_id": candidate.tenant_id, "surface": candidate.surface,
                "generation_id": candidate.generation_id,
                "state_id": candidate.state_id,
                "pit_state_id": candidate.pit_state_id,
                "manifest_id": candidate.manifest_id, "artifacts": entries}
        return sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
                                allow_nan=False).encode()).hexdigest()

    @staticmethod
    def _identity_columns(identity: ArtifactIdentity):
        return identity.fields()

    def publish(self, candidate: PublicationCandidate,
                expected_current_generation: str | None,
                failpoint: str | None = None) -> str:
        prepared_and_bytes = [self._prepare(item) for item in candidate.artifacts]
        prepared = tuple(pair[0] for pair in prepared_and_bytes)
        for p, (_, packed) in zip(prepared, prepared_and_bytes):
            self.objects.put_if_absent(p.object_key, packed, p.object_sha256)
            stored = self.objects.get(p.object_key)
            if stored != packed or sha256(stored).hexdigest() != p.object_sha256:
                raise IntegrityError("object read-after-write verification failed")
        if self.after_upload:
            self.after_upload(prepared)
        if failpoint == "after_upload":
            raise OSError("injected failure after blob upload")

        current_is_verified = False
        if expected_current_generation is not None:
            try:
                self._read_generation(candidate.tenant_id, candidate.surface,
                                      expected_current_generation)
                current_is_verified = True
            except (IntegrityError, OSError, zlib.error, ValueError, json.JSONDecodeError):
                # Never replace a known-good fallback with an unverified
                # current generation. The pointer CAS below still fences it.
                current_is_verified = False

        manifest_hash = self._manifest_hash(candidate, prepared)
        with self.metadata.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                # Retry of this exact generation is idempotent; a same ID with
                # different manifest bytes is a hard collision, never replace.
                prior_pub = db.execute(
                    "SELECT manifest_sha256 FROM publication_generation "
                    "WHERE tenant_id=? AND surface=? AND generation_id=?",
                    (candidate.tenant_id, candidate.surface,
                     candidate.generation_id)).fetchone()
                if prior_pub:
                    if prior_pub["manifest_sha256"] != manifest_hash:
                        raise PublicationConflict("generation ID already names another manifest")
                    db.execute("COMMIT")
                    return "already_published"

                for p in prepared:
                    i = p.identity
                    cols = self._identity_columns(i)
                    db.execute("""INSERT INTO artifact_blob_registry
                        (tenant_id,artifact_kind,scope_kind,scope_id,state_id,pit_state_id,
                         input_fingerprint,model_version,codec,raw_sha256,object_sha256,
                         object_key,raw_size,object_size)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING""",
                        (*cols, CODEC, p.raw_sha256, p.object_sha256, p.object_key,
                         p.raw_size, p.object_size))
                    existing = db.execute("""SELECT raw_sha256,object_sha256,object_key,
                        codec,raw_size,object_size FROM artifact_blob_registry
                        WHERE tenant_id=? AND artifact_kind=? AND scope_kind=? AND scope_id=?
                          AND state_id=? AND pit_state_id=? AND input_fingerprint=?
                          AND model_version=?""", cols).fetchone()
                    expected = (p.raw_sha256, p.object_sha256, p.object_key,
                                CODEC, p.raw_size, p.object_size)
                    if tuple(existing) != expected:
                        raise IdentityConflict("immutable artifact identity already has different content")

                if failpoint == "after_registry":
                    raise OSError("injected failure before publication transaction commit")

                current = db.execute("""SELECT current_generation_id,last_good_generation_id
                    FROM publication_pointer WHERE tenant_id=? AND surface=?""",
                    (candidate.tenant_id, candidate.surface)).fetchone()
                observed = current["current_generation_id"] if current else None
                if observed != expected_current_generation:
                    raise PublicationConflict("publication pointer changed; compare-and-swap failed")

                db.execute("""INSERT INTO publication_generation
                    (tenant_id,surface,generation_id,state_id,pit_state_id,manifest_id,
                     manifest_sha256,complete) VALUES(?,?,?,?,?,?,?,1)""",
                    (candidate.tenant_id, candidate.surface, candidate.generation_id,
                     candidate.state_id, candidate.pit_state_id, candidate.manifest_id,
                     manifest_hash))
                for p in prepared:
                    i = p.identity
                    db.execute("""INSERT INTO publication_artifact_ref
                        (tenant_id,surface,generation_id,artifact_kind,scope_kind,scope_id,
                         state_id,pit_state_id,input_fingerprint,model_version,raw_sha256)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (candidate.tenant_id, candidate.surface, candidate.generation_id,
                         *i.fields()[1:], p.raw_sha256))
                if self.before_pointer:
                    self.before_pointer()
                if failpoint == "before_pointer":
                    raise OSError("injected failure before active pointer update")

                if current is None:
                    db.execute("""INSERT INTO publication_pointer
                        (tenant_id,surface,state_id,pit_state_id,manifest_id,
                         current_generation_id,last_good_generation_id)
                        VALUES(?,?,?,?,?,?,?)""",
                        (candidate.tenant_id, candidate.surface, candidate.state_id,
                         candidate.pit_state_id, candidate.manifest_id,
                         candidate.generation_id, candidate.generation_id))
                else:
                    last_good = (observed if current_is_verified
                                 else current["last_good_generation_id"])
                    changed = db.execute("""UPDATE publication_pointer SET
                        state_id=?,pit_state_id=?,manifest_id=?,
                        current_generation_id=?,last_good_generation_id=?
                        WHERE tenant_id=? AND surface=? AND current_generation_id=?""",
                        (candidate.state_id, candidate.pit_state_id, candidate.manifest_id,
                         candidate.generation_id, last_good, candidate.tenant_id,
                         candidate.surface, observed)).rowcount
                    if changed != 1:
                        raise PublicationConflict("publication compare-and-swap lost")
                db.execute("COMMIT")
                return "published"
            except BaseException:
                if db.in_transaction:
                    db.execute("ROLLBACK")
                raise

    def pointer(self, tenant_id: str, surface: str) -> dict | None:
        with self.metadata.connection() as db:
            row = db.execute("SELECT * FROM publication_pointer WHERE tenant_id=? AND surface=?",
                             (tenant_id, surface)).fetchone()
            return dict(row) if row else None

    def _read_generation(self, tenant_id: str, surface: str,
                         generation_id: str) -> dict:
        with self.metadata.connection() as db:
            pub = db.execute("""SELECT * FROM publication_generation WHERE
            tenant_id=? AND surface=? AND generation_id=? AND complete=1""",
                (tenant_id, surface, generation_id)).fetchone()
            if pub is None:
                raise IntegrityError("complete publication manifest missing")
            refs = db.execute("""SELECT a.*,r.codec,r.object_sha256,r.object_key,
                r.object_size,r.raw_size FROM publication_artifact_ref a
                JOIN artifact_blob_registry r USING(tenant_id,artifact_kind,scope_kind,
                    scope_id,state_id,pit_state_id,input_fingerprint,model_version)
                WHERE a.tenant_id=? AND a.surface=? AND a.generation_id=?""",
                (tenant_id, surface, generation_id)).fetchall()
        payloads = {}
        for row in refs:
            if row["state_id"] != pub["state_id"] or row["pit_state_id"] != pub["pit_state_id"]:
                raise IntegrityError("published artifact State/PIT fence mismatch")
            if row["codec"] != CODEC:
                raise IntegrityError("unsupported artifact codec")
            packed = self.objects.get(row["object_key"])
            if (len(packed) != row["object_size"] or
                    sha256(packed).hexdigest() != row["object_sha256"]):
                raise IntegrityError("stored object hash/size mismatch")
            decoder = zlib.decompressobj()
            raw = decoder.decompress(packed, min(row["raw_size"], MAX_RAW_BYTES) + 1)
            if (not decoder.eof or decoder.unconsumed_tail or decoder.unused_data or
                    len(raw) != row["raw_size"] or sha256(raw).hexdigest() != row["raw_sha256"]):
                raise IntegrityError("decompressed artifact hash/size mismatch")
            value = json.loads(raw)
            if canonical_json(value) != raw:
                raise IntegrityError("stored artifact is not canonical JSON")
            identity_fields = (row["tenant_id"], row["artifact_kind"],
                               row["scope_kind"], row["scope_id"], row["state_id"],
                               row["pit_state_id"], row["input_fingerprint"],
                               row["model_version"])
            payloads[identity_fields] = value
        if not refs:
            raise IntegrityError("publication has no artifact references")
        prepared = [PreparedObject(
            ArtifactIdentity(row["tenant_id"], row["artifact_kind"], row["scope_kind"],
                             row["scope_id"], row["state_id"], row["pit_state_id"],
                             row["input_fingerprint"], row["model_version"]),
            row["object_key"], row["raw_sha256"], row["object_sha256"],
            row["raw_size"], row["object_size"], payloads[(
                row["tenant_id"], row["artifact_kind"], row["scope_kind"],
                row["scope_id"], row["state_id"], row["pit_state_id"],
                row["input_fingerprint"], row["model_version"])])
            for row in refs]
        manifest_candidate = PublicationCandidate(
            tenant_id=tenant_id, surface=surface,
            generation_id=pub["generation_id"], state_id=pub["state_id"],
            pit_state_id=pub["pit_state_id"], manifest_id=pub["manifest_id"],
            artifacts=tuple(ArtifactInput(p.identity, p.computed_payload) for p in prepared))
        if self._manifest_hash(manifest_candidate, prepared) != pub["manifest_sha256"]:
            raise IntegrityError("published manifest digest mismatch")
        return {"generation_id": generation_id, "state_id": pub["state_id"],
                "pit_state_id": pub["pit_state_id"], "manifest_id": pub["manifest_id"],
                "manifest_sha256": pub["manifest_sha256"], "payloads": payloads}

    def read_current_or_last_good(self, tenant_id: str, surface: str) -> dict:
        pointer = self.pointer(tenant_id, surface)
        if pointer is None:
            raise KeyError("publication not found")
        try:
            current = self._read_generation(tenant_id, surface,
                                            pointer["current_generation_id"])
            current["served_as_last_good"] = False
            return current
        except (IntegrityError, OSError, zlib.error, ValueError, json.JSONDecodeError):
            if pointer["last_good_generation_id"] == pointer["current_generation_id"]:
                raise
            previous = self._read_generation(tenant_id, surface,
                                             pointer["last_good_generation_id"])
            previous["served_as_last_good"] = True
            return previous


def artifact_key(tenant_id: str, surface: str, kind: str, state_id: str,
                 pit_state_id: str, fingerprint: str, model: str) -> ArtifactIdentity:
    return ArtifactIdentity(tenant_id, kind, surface, surface, state_id,
                            pit_state_id, fingerprint, model)


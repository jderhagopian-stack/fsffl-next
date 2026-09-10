create table if not exists fsffl.historical_artifact (
    artifact_key text primary key,
    league_id text not null,
    transaction_id text not null,
    artifact_kind text not null,
    artifact_version text not null,
    as_of timestamptz,
    dependency_fingerprint text,
    identity_payload jsonb not null,
    report_payload jsonb not null,
    recorded_at timestamptz not null default now()
);
create index if not exists historical_artifact_league_transaction_idx
    on fsffl.historical_artifact (league_id, transaction_id, artifact_kind);
create index if not exists historical_artifact_refresh_idx
    on fsffl.historical_artifact (league_id, artifact_kind, as_of desc)
    where as_of is not null;

create table if not exists fsffl.historical_artifact_dependency (
    artifact_key text not null references fsffl.historical_artifact(artifact_key) on delete cascade,
    component text not null,
    version text not null,
    primary key (artifact_key, component)
);
create index if not exists historical_artifact_dependency_lookup_idx
    on fsffl.historical_artifact_dependency (component, version, artifact_key);

create table if not exists fsffl.historical_sync_checkpoint (
    league_id text not null,
    provider text not null,
    last_completed_at timestamptz not null,
    provider_cursor text,
    model_version text not null,
    updated_at timestamptz not null default now(),
    primary key (league_id, provider)
);

comment on table fsffl.historical_artifact is
    'Durable versioned historical Analytics artifacts. Storage preserves authoritative outputs and does not create grading, Decision, Value, or State truth.';
comment on table fsffl.historical_artifact_dependency is
    'Normalized dependency lineage for selective historical artifact invalidation without reacquiring immutable provider history.';
comment on table fsffl.historical_sync_checkpoint is
    'Latest successfully completed historical provider sync position. Failed or partial syncs must not advance this checkpoint.';

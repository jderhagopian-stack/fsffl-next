-- INACTIVE research migration; do not apply to production without gate #490.
-- Existing pooled PostgreSQL persistence connection remains the sole transport.
-- Records references only: never private model inputs, State payloads or forecasts.
create table if not exists fsffl.intelligence_worker_job (
    job_id text primary key,
    user_id text not null,
    league_id text not null,
    league_state_id text not null,
    publication_generation_id text not null,
    source_manifest_fingerprint text not null,
    model_version text not null,
    capability text not null check (capability in ('career_intrinsic')),
    status text not null default 'queued'
        check (status in ('queued', 'running', 'computed', 'failed')),
    attempts integer not null default 0 check (attempts >= 0),
    lease_token text,
    lease_expires_at timestamptz,
    result_artifact_kind text,
    result_artifact_model_version text,
    result_input_fingerprint text,
    failure_code text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint intelligence_worker_running_lease check (
        (status = 'running' and lease_token is not null and lease_expires_at is not null)
        or (status <> 'running' and lease_token is null and lease_expires_at is null)
    ),
    constraint intelligence_worker_computed_result check (
        status <> 'computed' or
        (result_artifact_kind is not null and result_artifact_model_version is not null
         and result_input_fingerprint is not null)
    )
);
-- Even two competing workers cannot run different-State tasks for one tenant.
create unique index if not exists intelligence_worker_one_running_per_user
    on fsffl.intelligence_worker_job (user_id) where status in ('queued', 'running');
create index if not exists intelligence_worker_runnable
    on fsffl.intelligence_worker_job (status, lease_expires_at, created_at);
alter table fsffl.intelligence_worker_job enable row level security;
comment on table fsffl.intelligence_worker_job is
    'INACTIVE: durable exact-State heavy-compute dispatch references; computed does not authorize publication. No browser access.';
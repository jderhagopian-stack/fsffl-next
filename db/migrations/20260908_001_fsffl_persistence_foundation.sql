create schema if not exists fsffl;

revoke all on schema fsffl from anon, authenticated;

create table fsffl.league_snapshot (
    provider text not null,
    league_id text not null,
    season integer not null,
    state_hash text not null,
    payload jsonb not null,
    source_updated_at timestamptz,
    recorded_at timestamptz not null default now(),
    primary key (provider, league_id, season)
);

create table fsffl.team_snapshot (
    provider text not null,
    league_id text not null,
    team_id text not null,
    state_hash text not null,
    payload jsonb not null,
    source_updated_at timestamptz,
    recorded_at timestamptz not null default now(),
    primary key (provider, league_id, team_id)
);

create table fsffl.sync_cursor (
    provider text not null,
    scope_kind text not null,
    scope_id text not null,
    cursor_payload jsonb not null default '{}'::jsonb,
    source_updated_at timestamptz,
    synced_at timestamptz not null default now(),
    primary key (provider, scope_kind, scope_id)
);

create table fsffl.state_change_event (
    id bigint generated always as identity primary key,
    provider text not null,
    league_id text not null,
    change_kind text not null,
    entity_kind text not null,
    entity_id text not null,
    before_hash text,
    after_hash text not null,
    payload jsonb not null default '{}'::jsonb,
    observed_at timestamptz not null default now()
);
create index state_change_event_league_time_idx
    on fsffl.state_change_event (provider, league_id, observed_at desc);
create index state_change_event_entity_idx
    on fsffl.state_change_event (entity_kind, entity_id, observed_at desc);

create table fsffl.derived_artifact (
    id bigint generated always as identity primary key,
    artifact_kind text not null,
    scope_kind text not null,
    scope_id text not null,
    input_fingerprint text not null,
    model_version text not null,
    payload jsonb not null,
    computed_at timestamptz not null default now(),
    invalidated_at timestamptz,
    invalidation_reason text,
    unique (artifact_kind, scope_kind, scope_id, input_fingerprint, model_version)
);
create index derived_artifact_lookup_idx
    on fsffl.derived_artifact (artifact_kind, scope_kind, scope_id, computed_at desc)
    where invalidated_at is null;

create table fsffl.invalidation_event (
    id bigint generated always as identity primary key,
    scope_kind text not null,
    scope_id text not null,
    cause_kind text not null,
    cause_ref text,
    input_fingerprint text,
    invalidated_artifact_kinds text[] not null default '{}',
    observed_at timestamptz not null default now()
);
create index invalidation_event_scope_time_idx
    on fsffl.invalidation_event (scope_kind, scope_id, observed_at desc);

create table fsffl.market_value_snapshot (
    id bigint generated always as identity primary key,
    asset_ref text not null,
    asset_kind text not null,
    scale_id text not null,
    market_context_id text not null,
    estimate_as_of timestamptz not null,
    recorded_at timestamptz not null default now(),
    value numeric not null,
    source_lineage jsonb not null default '{}'::jsonb,
    unique (asset_ref, asset_kind, scale_id, market_context_id, estimate_as_of)
);
create index market_value_snapshot_history_idx
    on fsffl.market_value_snapshot (
        asset_ref,
        asset_kind,
        scale_id,
        market_context_id,
        estimate_as_of desc
    );

comment on schema fsffl is
    'Private server-side persistence for FSFFL NEXT. Storage is not a model authority.';
comment on table fsffl.derived_artifact is
    'Reusable derived outputs keyed by exact upstream fingerprint and model version; invalidation prevents stale reuse.';
comment on table fsffl.market_value_snapshot is
    'Genuine retained market observations for historical movement; never synthesized from Cardinal Value.';

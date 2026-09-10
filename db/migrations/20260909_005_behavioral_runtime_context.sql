create table if not exists fsffl.behavior_runtime_context (
    user_id text primary key,
    league_state_id text not null,
    sleeper_league_external_id text not null,
    league_family_id text not null,
    current_owner_by_roster jsonb not null,
    updated_at timestamptz not null default now()
);

comment on table fsffl.behavior_runtime_context is
    'Durable product read-path context linking a beta user to already-built Behavioral observed evidence; contains no inferred preferences, acceptance probability, Decision Utility, or Value truth.';

create table fsffl.user_runtime_context (
    user_id text primary key,
    provider text not null,
    league_external_id text not null,
    league_id text not null,
    season integer not null,
    selected_team_id text,
    state_hash text not null,
    updated_at timestamptz not null default now()
);

alter table fsffl.user_runtime_context enable row level security;
revoke all on table fsffl.user_runtime_context from anon, authenticated;

comment on table fsffl.user_runtime_context is
    'Private server-side pointer to the last durable league/team context for a beta user; not model authority.';

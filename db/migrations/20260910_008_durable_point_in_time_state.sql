create table if not exists fsffl.state_snapshot_history (
    league_id text not null,
    state_hash text not null,
    season integer not null,
    as_of timestamptz not null,
    payload jsonb not null,
    recorded_at timestamptz not null default now(),
    primary key (league_id, state_hash)
);
create index if not exists state_snapshot_history_lookup_idx
    on fsffl.state_snapshot_history (league_id, as_of desc, recorded_at desc);

alter table fsffl.state_snapshot_history enable row level security;

comment on table fsffl.state_snapshot_history is
    'Durable canonical State snapshots for point-in-time retrieval. Persistence preserves State authority and performs no fantasy-football inference.';

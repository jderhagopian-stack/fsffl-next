create table if not exists fsffl.user_perceived_latency (
    id bigint generated always as identity primary key,
    user_id text not null,
    operation text not null,
    elapsed_ms double precision not null check (elapsed_ms >= 0),
    outcome text not null,
    detail text,
    observed_at timestamptz not null default now()
);
create index if not exists user_perceived_latency_operation_time_idx
    on fsffl.user_perceived_latency (operation, observed_at desc);
create index if not exists user_perceived_latency_user_time_idx
    on fsffl.user_perceived_latency (user_id, observed_at desc);

alter table fsffl.user_perceived_latency enable row level security;

comment on table fsffl.user_perceived_latency is
    'Durable private-beta performance evidence. Observability only; never a model or recommendation authority.';

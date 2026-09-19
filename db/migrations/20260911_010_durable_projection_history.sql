create table fsffl.projection_snapshot (
    id bigint generated always as identity primary key,
    provider text not null,
    season integer not null check (season >= 2000),
    horizon text not null check (horizon in ('week', 'rest_of_season', 'fantasy_regular_season', 'season', 'multi_year')),
    week integer check (week between 1 and 18),
    period_start timestamptz not null,
    period_end timestamptz not null,
    effective_at timestamptz not null,
    retrieved_at timestamptz not null,
    source_version text not null,
    usage_class text,
    content_fingerprint text not null,
    raw_payload jsonb,
    recorded_at timestamptz not null default now(),
    check (period_end > period_start),
    check (effective_at <= retrieved_at),
    check (
        (horizon = 'week' and week is not null)
        or (horizon <> 'week' and week is null)
    )
);

-- Duplicate polling of an unchanged provider publication is idempotent. A new
-- provider timestamp or changed normalized content remains a new point-in-time revision.
create unique index projection_snapshot_revision_key
    on fsffl.projection_snapshot (
        provider,
        season,
        horizon,
        coalesce(week, 0),
        period_start,
        period_end,
        effective_at,
        content_fingerprint,
        source_version
    );

create index projection_snapshot_current_idx
    on fsffl.projection_snapshot (
        season,
        horizon,
        coalesce(week, 0),
        provider,
        effective_at desc,
        id desc
    );

create index projection_snapshot_point_in_time_idx
    on fsffl.projection_snapshot (
        provider,
        season,
        horizon,
        coalesce(week, 0),
        effective_at desc
    );

create table fsffl.projection_observation (
    snapshot_id bigint not null references fsffl.projection_snapshot(id) on delete restrict,
    player_id text not null,
    external_id text not null,
    position text not null check (position in ('QB', 'RB', 'WR', 'TE', 'K', 'DST')),
    metric text not null,
    mean double precision not null,
    stddev double precision not null default 0 check (stddev >= 0),
    p10 double precision,
    p50 double precision,
    p90 double precision,
    primary key (snapshot_id, player_id, metric),
    check (
        (p10 is null or p50 is null or p10 <= p50)
        and (p50 is null or p90 is null or p50 <= p90)
        and (p10 is null or p90 is null or p10 <= p90)
    )
);

create index projection_observation_player_history_idx
    on fsffl.projection_observation (player_id, snapshot_id desc);
create index projection_observation_source_accuracy_idx
    on fsffl.projection_observation (position, metric, snapshot_id);

-- Fast current reads resolve the latest semantic revision per provider/horizon.
-- Forecast still decides how multiple independent providers become authoritative truth.
create view fsffl.projection_latest_snapshot as
select distinct on (provider, season, horizon, coalesce(week, 0))
    id,
    provider,
    season,
    horizon,
    week,
    period_start,
    period_end,
    effective_at,
    retrieved_at,
    source_version,
    usage_class,
    content_fingerprint,
    recorded_at
from fsffl.projection_snapshot
order by provider, season, horizon, coalesce(week, 0), effective_at desc, id desc;

alter table fsffl.projection_snapshot enable row level security;
alter table fsffl.projection_observation enable row level security;
revoke all on fsffl.projection_snapshot from anon, authenticated;
revoke all on fsffl.projection_observation from anon, authenticated;
revoke all on fsffl.projection_latest_snapshot from anon, authenticated;

comment on table fsffl.projection_snapshot is
    'Append-only point-in-time provider projection revisions. Storage is evidence, never Forecast calculation authority.';
comment on table fsffl.projection_observation is
    'Normalized metric observations attached to immutable provider revisions for horizon-aware current and historical Forecast reads.';

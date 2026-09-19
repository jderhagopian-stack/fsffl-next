create table if not exists fsffl.behavior_event (
    league_family_id text not null,
    event_id text not null,
    occurred_at timestamptz not null,
    payload jsonb not null,
    recorded_at timestamptz not null default now(),
    primary key (league_family_id, event_id)
);
create index if not exists behavior_event_family_time_idx
    on fsffl.behavior_event (league_family_id, occurred_at, event_id);

create table if not exists fsffl.behavior_profile (
    league_family_id text not null,
    owner_id text not null,
    as_of timestamptz not null,
    payload jsonb not null,
    updated_at timestamptz not null default now(),
    primary key (league_family_id, owner_id)
);

create table if not exists fsffl.behavior_season (
    league_family_id text not null,
    league_external_id text not null,
    season integer not null,
    complete boolean not null default false,
    updated_at timestamptz not null default now(),
    primary key (league_family_id, league_external_id)
);
create index if not exists behavior_season_complete_idx
    on fsffl.behavior_season (league_external_id)
    where complete;

comment on table fsffl.behavior_event is
    'Durable provider-derived owner action evidence. Behavioral inference remains authoritative in the Behavioral layer.';
comment on table fsffl.behavior_profile is
    'Reusable Behavioral profile output by league family and owner; not universal Market Value truth.';
comment on table fsffl.behavior_season is
    'Tracks immutable historical Sleeper seasons already scanned so history is not repeatedly reacquired.';

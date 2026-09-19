-- Defense-in-depth for the private persistence schema.
-- No anon/authenticated policies are intentionally created here.
-- Browser/client access remains denied; trusted backend/database roles
-- retain server-side access according to their PostgreSQL privileges.

alter table fsffl.league_snapshot enable row level security;
alter table fsffl.team_snapshot enable row level security;
alter table fsffl.sync_cursor enable row level security;
alter table fsffl.state_change_event enable row level security;
alter table fsffl.derived_artifact enable row level security;
alter table fsffl.invalidation_event enable row level security;
alter table fsffl.market_value_snapshot enable row level security;

-- Defense-in-depth for private FSFFL persistence tables added after the original
-- row-level-security migration. No anon/authenticated policies are intentionally
-- created: trusted backend/database roles retain server-side access according to
-- their PostgreSQL privileges, while browser/client roles remain denied.

alter table fsffl.user_runtime_context enable row level security;

alter table fsffl.behavior_event enable row level security;
alter table fsffl.behavior_profile enable row level security;
alter table fsffl.behavior_season enable row level security;
alter table fsffl.behavior_runtime_context enable row level security;

alter table fsffl.historical_artifact enable row level security;
alter table fsffl.historical_artifact_dependency enable row level security;
alter table fsffl.historical_sync_checkpoint enable row level security;

drop index if exists fsffl.projection_snapshot_revision_key;

-- Keep exact provider publications uniquely identifiable by their effective timestamp
-- and normalized content. Consecutive unchanged polls are suppressed by the persistence
-- adapter after comparing against the latest retained semantic revision. Retaining
-- effective_at here allows a legitimate A -> B -> A provider reversion to be stored as
-- a new point-in-time revision and avoids migration failures from pre-existing rows.
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

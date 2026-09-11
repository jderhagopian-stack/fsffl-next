drop index if exists fsffl.projection_snapshot_revision_key;

-- Retrieval/effective timestamps alone do not create a meaningful projection revision.
-- A revision is new when its normalized source content or semantic forecast identity changes.
create unique index projection_snapshot_revision_key
    on fsffl.projection_snapshot (
        provider,
        season,
        horizon,
        coalesce(week, 0),
        period_start,
        period_end,
        content_fingerprint,
        source_version
    );

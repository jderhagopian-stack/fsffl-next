# Historical Trade Persistence and Incremental Refresh

## Goal

Historical league facts should survive sign-outs and application restarts. A user with years of league history should not repeatedly download and reconstruct the same completed trades.

This design separates immutable historical facts from versioned point-in-time analysis and refreshable hindsight analysis.

## Authority boundary

Persistence does not create model truth. It stores artifacts already produced by authoritative NEXT layers together with identity, version, as-of time, and dependency lineage.

The architecture remains:

Data -> Point-in-Time State -> Forecast -> Value -> Decision -> Analytics/API -> Presentation

Storage is cross-cutting infrastructure, not a replacement authority layer.

## Artifact lifecycle

### Immutable historical facts

Examples:
- completed provider transaction
- reconstructed transaction package
- validated point-in-time league-state snapshot
- original evidence/provenance records

These should be written once under a stable identity. A correction creates a new version; it must not silently overwrite a prior artifact under the same identity.

### Versioned point-in-time analysis

The question "Was this a good decision based on what was knowable then?" is evaluated against immutable historical evidence but can be rerun when an authoritative NEXT model improves.

Therefore the analysis is cached by transaction plus model/dependency fingerprint. A Decision or Historical Pick Coordinate upgrade creates a new derived version without re-fetching the underlying historical facts.

### Refreshable hindsight analysis

Retrospective analysis can legitimately change as:
- players produce additional seasons
- injuries/development become known
- draft picks resolve into players
- later trades extend asset lineage
- franchise outcomes accumulate

These artifacts require an explicit `as_of` and should be refreshed incrementally.

## Incremental sign-in/sync flow

1. Load persisted league identity and latest successful provider sync checkpoint.
2. Request only provider data newer than the checkpoint when the provider supports a cursor/window.
3. Normalize and append genuinely new transactions.
4. Reconstruct point-in-time state/evidence only for new or explicitly corrected historical records.
5. Extend lineage from newly observed transactions/drafts.
6. Refresh only hindsight artifacts whose `as_of` is stale or whose dependencies changed.
7. Reuse all unchanged historical facts and point-in-time artifacts.
8. Advance the checkpoint only after the sync batch completes successfully.

A failed or partial sync must not advance the checkpoint.

## Dependency-aware invalidation

Derived artifacts record a dependency fingerprint. When a governed model changes, an invalidation request names:
- league
- dependency component
- old version
- new version
- optional affected transaction ids

Examples:

- Historical Pick Coordinate `v3 -> v4`: invalidate derived analyses for trades containing affected picks; preserve transaction facts and league-state snapshots.
- Decision model `v5 -> v6`: rerun point-in-time decision analysis/reports, but do not re-download Sleeper history.
- Retrospective production normalization update: refresh hindsight/outcome artifacts only.

The initial in-memory implementation uses version presence in the fingerprint as a simple reference implementation. Production persistence should store normalized dependency records/indexes so invalidation is queryable and efficient at scale.

## Production storage recommendation

The contract is database-neutral. A commercial deployment can map it to relational tables plus object/JSON payload storage, for example:

- `league_sync_checkpoint`
- `historical_transaction_fact`
- `historical_state_snapshot`
- `historical_forecast_artifact`
- `historical_value_artifact`
- `historical_decision_artifact`
- `historical_lineage_event`
- `historical_retrospective_artifact`
- `historical_trade_report`
- `artifact_dependency`

Recommended keys include league, transaction/state id, artifact kind, artifact/model version, evidence `as_of`, and dependency fingerprint.

Large immutable payloads may be content-addressed. Database rows can store metadata, lineage, indexes, and payload location/hash.

## Product behavior

The intended user experience is:

**open league -> immediately read persisted league/history -> sync only new provider events -> refresh stale derived artifacts**

not:

**open league -> redownload and recompute the entire historical league**

This same persistent historical foundation can support Historical Trade Grader, GM Report Card, best/worst trade views, league analytics, and future portfolio/owner-history products without duplicating reconstruction work.

## Current scope

This work defines the persistence/invalidation contracts and reference in-memory behavior. It intentionally does not select PostgreSQL, Redis, object storage, or a hosting vendor yet. Production infrastructure can implement the protocols without changing the Historical Trade Grader domain model.

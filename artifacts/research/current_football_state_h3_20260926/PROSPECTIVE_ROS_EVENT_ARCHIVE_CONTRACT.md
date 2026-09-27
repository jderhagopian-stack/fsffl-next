# Prospective Governed ROS / Event Snapshot Archive Contract

Date: 2026-09-27  
Status: **IMPLEMENTED FOR RESEARCH RETENTION / NOT FORECAST AUTHORITY**

## Purpose

Create the missing point-in-time evidence series needed to study how current provider ROS expectations and current football-state evidence evolve after real events.

This archive preserves evidence. It does not create Forecast truth.

## Security / storage boundary

The GitHub repository is public, so provider projection rows are **not** retained in GitHub artifacts or committed files.

Private durable storage:
- `fsffl.projection_snapshot`;
- `fsffl.projection_observation`;
- `fsffl.current_football_state_capture`;
- `fsffl.football_event_snapshot`.

All four tables have RLS enabled and no user-facing RLS policy. The two new tables explicitly revoke `anon` / `authenticated` privileges.

The archive writer is a server-side Supabase Edge Function. GitHub Actions authenticates to it with a short-lived GitHub OIDC token bound to:
- repository `jderhagopian-stack/fsffl-next`;
- repository ID `1357146400`;
- `refs/heads/main`;
- workflow `.github/workflows/prospective-ros-event-capture.yml`;
- fixed audience `fsffl-supabase-ros-archive`.

No Supabase secret or database credential is stored in GitHub.

## Capture cadence

The main-branch workflow runs:
- daily at 23:20 UTC;
- on manual dispatch;
- once on changes to the capture script/workflow after they reach `main`.

Pull requests execute acquisition/payload construction only. They cannot ingest.

## Provider snapshot evidence

Current research sources:
- CBS rest-of-season;
- Razzball rest-of-season.

Each capture preserves:
- provider;
- acquisition/retrieval timestamp;
- provider effective timestamp;
- season/week;
- source version;
- usage class / rights classification;
- content fingerprint;
- mapping/provenance manifest;
- normalized provider stat observations;
- exact frozen-standard points only where all required scoring coordinates exist.

Raw provider HTML is **not** retained.

The archive does not promote provider rights. Existing `SOURCE_RIGHTS_LEDGER.md` classifications remain authoritative.

## Event-state evidence

Current NFL state is reconstructed from governed nflverse evidence using the frozen event-reconstruction oracle.

For mapped current players, the archive preserves:
- acquisition/observed time;
- season/week;
- canonical event labels;
- roster/status/participation counters available in the governed event state;
- deterministic state fingerprint;
- current-player identity link and historical GSIS provenance.

Event rows are evidence/provenance only.

## Snapshot semantics

Every capture has a unique `capture_key` derived from acquisition time plus a canonical payload hash.

Rows are append-only from the Research workflow's perspective.

The projection archive may contain consecutive identical provider content fingerprints. This is intentional: unchanged provider state at two different observed times remains valid point-in-time evidence.

## Research uses

Permitted future studies include:
- provider revision before/after injury or roster events;
- whether provider ROS already internalizes availability/role changes;
- lag between event evidence and provider revisions;
- incremental value of event state beyond provider ROS;
- calibration of fallback availability behavior when provider authority is absent.

## Prohibited interpretations

The archive must not be treated as:
- provider deployment authorization;
- historical evidence before the actual acquisition timestamp;
- a reason to backdate ROS views;
- a direct injury multiplier;
- a direct Intrinsic adjustment;
- acceptance probability or Team Utility evidence.

## Double-counting rule

If a future governed ROS Forecast owns H1:
- ROS is the integrated H1 expectation;
- do not multiply it by a separate injury availability factor;
- archived event state is explanatory/provenance and future research input.

If ROS authority is unavailable:
- a separately approved availability fallback may eventually consume the accepted injury-availability component;
- conditional healthy production remains independently governed.

## Implementation

Private schema migration:
`add_private_current_football_state_research_archive`.

Edge Function:
`fsffl-research-snapshot-ingest`.

Main-branch capture files:
- `scripts/capture_prospective_ros_event_snapshot.py`;
- `.github/workflows/prospective-ros-event-capture.yml`.

No production H3 or Intrinsic code path consumes these rows.

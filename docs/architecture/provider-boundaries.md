# Provider and Data Boundaries

FSFFL NEXT must not confuse an external provider with the domain model it feeds.

## Provider role

A provider adapter may:

- authenticate or retrieve provider data;
- map provider-specific identifiers to canonical identities;
- normalize payloads into canonical records;
- attach provenance, timestamps, quality and licensing metadata;
- expose capability limitations.

A provider adapter may not:

- define valuation logic;
- define team utility;
- embed presentation decisions;
- silently reinterpret unknown data;
- become the authoritative source merely because it is convenient.

## Canonical boundary

All downstream engines consume canonical FSFFL records rather than raw Sleeper, projection-vendor, market-vendor, or other provider payloads.

This allows providers to be replaced without redesigning valuation, simulation, trade, opportunity, analytics, or UI layers.

## Source provenance

Each material imported datum should be able to identify:

- provider;
- provider record/source identifier when safe;
- effective timestamp;
- retrieval/ingestion timestamp;
- normalization version;
- licensing/redistribution constraints where relevant;
- quality/confidence metadata when applicable.

## Multi-provider conflicts

When providers disagree, conflict resolution belongs in an explicit reconciliation or forecasting layer. Raw ingestion must preserve the disagreement rather than silently overwrite it.

## Private and public data

The public repository may contain provider interfaces, schemas, synthetic fixtures, and openly redistributable sample data.

It should not contain secrets, credentials, personal information, private league dumps, or third-party datasets whose licenses prohibit redistribution.

These constraints do not limit model capability; runtime data remains external to source code.

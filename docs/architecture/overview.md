# FSFFL NEXT Architecture Overview

## Intelligence lifecycle efficiency direction (2026-10-09)

Storage destination follows **evidence dependency and lifecycle economics**, not vice versa. Management no longer assumes PostgreSQL-to-object bulk migration is optimal; hybrid is one nonproduction candidate. Governed Data → State → Forecast → Simulation/Value → Current/Dynasty → one publication owner → consumer remains unchanged. First classify global/provider-horizon evidence, season/versioned raw snapshot, immutable model/rules-scoped computation, league-State/team-specific outputs, exact published generation, last-good, PIT and replay. Preserve historical versions and license/tenant isolation. Profile acquisition requests, shared-cache rights, independent Current freshness, numerical output version, serialization, full-payload reads and browser response sizes before evaluating (A) optimized PostgreSQL, (B) optimized hybrid, (C) selective compact hybrid. No second lifecycle controller, no same-State publication skipping, no provider/model/refresh change. Source rights include commercial licensing for Sleeper/Razzball/CBS. All concrete decisions remain in [Supabase capacity workstream](../operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md); neither PR #439 nor an object provider is production authorized.

## Storage architecture direction and production gate (2026-10-08)

The existing PostgreSQL `PersistenceStore` owns all active and accepted runtime persistence, including bounded pooled connections (Tranche A) and idempotent batched Market first-writer writes (Tranche B). Tranche C whole-publication skipping was closed. A hybrid design—authoritative PostgreSQL metadata/PIT/publication and immutable compressed large object payloads through the same adapter—is a **nonproduction architectural candidate only**.

The isolated Foundation prototype remains draft [PR #439](https://github.com/jderhagopian-stack/fsffl-next/pull/439), unmerged and not deployed. In Phase 2, complete real Forecast and Simulation records were identifiable read-only through the connected Supabase tool but could not be transferred safely into the private Python zlib/Pydantic runner. A local genuine S3-compatible service was unavailable. Therefore exact full-real codec/model decoding, transport p95/RSS, storage-byte economics and complete failure-mode reliability have **NOT been validated**; production integration/migration must not commence. Resume this gate only within a private test environment capable of securely reading complete real artifacts and running their governed decoders against a genuine isolated object backend. Never commit raw production user payloads to the public repo. See the canonical [Supabase workstream](../operations/workstreams/SUPABASE_CAPACITY_AND_SCALABILITY.md) for the current blocked status.

## Purpose

FSFFL NEXT is organized around one-directional authority:

`Data -> Point-in-Time State -> Forecast -> Value -> Decision -> Search/Optimization -> Analytics/API -> Presentation`

Each layer owns a distinct class of truth. Downstream layers consume upstream outputs; they do not recreate the same concept independently.

## Core layers

### Data
Raw and normalized facts from providers. No valuation or recommendation logic.

### Point-in-Time State
Canonical, timestamped reconstruction of league, team, player, pick, rules, roster, transaction, injury, and known-environment state.

### Forecast
Probabilistic future outcomes: player production, availability, development, aging, pick outcomes, and uncertainty.

### Value
Transforms forecast distributions and market information into asset and franchise value representations. Market price, intrinsic value, team-specific value, and likely transaction price remain distinct concepts.

### Decision
Evaluates state changes for one or more teams. Owns bilateral franchise utility and strategic consequences.

### Search / Optimization
Generates and searches candidate actions. It may ask the Decision layer to score possibilities but cannot invent its own value logic.

### Analytics / API
Read-only derived views and stable structured contracts for reports, terminal, web, mobile, and other clients.

### Presentation
Human-facing explanation and interaction. Presentation may filter, sort, and explain authoritative outputs but may not silently alter model conclusions.

## Foundational properties

- Point-in-time reproducibility is mandatory.
- Model, evidence, parameter, and provider versions are explicit.
- Expensive deterministic or stochastic intermediates are cacheable.
- Historical evaluation must prevent future-information leakage.
- League rules are configuration, not hard-coded assumptions.
- Sleeper is an adapter, not the domain model.
- Legacy FSFFL is evidence and a research corpus, not an authority source.

## NEXT-0 exit condition

No substantial valuation implementation should begin until domain objects, authority boundaries, state semantics, evidence lifecycle, versioning, and validation contracts are documented and internally consistent.

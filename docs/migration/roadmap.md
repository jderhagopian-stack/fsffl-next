# FSFFL NEXT Implementation Roadmap

This roadmap orders development so later modules depend on stable upstream contracts rather than rebuilding shared concepts.

## NEXT-0 — Architecture & Foundation

Define and review:

- project charter;
- directional architecture and authority boundaries;
- canonical domain model;
- point-in-time state semantics;
- provider/data boundaries;
- evidence and parameter lifecycle;
- model versioning and reproducibility;
- validation framework;
- performance/caching principles;
- legacy concept inventory.

**Exit gate:** the architecture is coherent enough to implement without unresolved duplicated authority or a requirement for legacy parity.

## NEXT-1 — Canonical State & Data Foundation

Implement executable canonical schemas and state materialization.

Primary deliverables:

- `League`, `LeagueRules`, `LeagueState`;
- `Team`, `TeamState`;
- `Player`, `PlayerState`;
- `DraftPick` / future-pick ownership;
- `Asset` and transaction primitives;
- provider adapter interfaces;
- snapshot/provenance metadata;
- serialization and validation;
- synthetic fixtures;
- deterministic state identity;
- first Sleeper adapter behind the canonical boundary;
- historical reconstruction hooks.

**Exit gate:** the same canonical state can support live and historical execution without downstream code depending on Sleeper payloads.

## NEXT-2 — Forecast Engine

Build first-class probabilistic forecasting.

Deliverables include source adapters, point-in-time projection snapshots, ensemble framework, player-age/development treatment, position/horizon-specific evaluation, uncertainty distributions, and calibration/backtesting.

**Exit gate:** forecasts can be evaluated historically and consumed without knowledge of source-specific payloads.

## NEXT-3 — Asset & Franchise Valuation

Re-derive valuation from first principles.

Separate and type:

- market price;
- intrinsic dynasty value;
- team-specific value;
- pick value;
- replacement/scarcity effects;
- uncertainty and liquidity/risk treatment.

**Exit gate:** player and pick valuation pass empirical/sanity validation and expose provenance/version metadata.

## NEXT-4 — Team Utility & Simulation

Build roster optimization, competitive-state estimation, simulation, and long-horizon franchise utility while keeping owner strategic posture distinct from calculated competitive state.

**Exit gate:** a transaction-free baseline and controlled roster changes produce coherent, reproducible team outcomes.

## NEXT-5 — Trade Decision Engine

Implement:

`Candidate Structure -> Bilateral Evaluation -> Price Discovery -> Behavioral Plausibility -> Decision`

Include originator/counterparty perspectives and uncertainty-aware negotiation frontiers.

**Exit gate:** known absurd historical failure modes are rejected for the correct reasons and useful transactions survive.

## NEXT-6 — Opportunity Engine

Search trades, waivers, draft moves, and other actionable improvements using authoritative upstream services.

**Exit gate:** search is efficient, realistic, and cannot invent its own valuation/utility authority.

## NEXT-7 — Analytics & API

Expose stable structured outputs for reports and user interfaces.

Include league intelligence, team-centric comparisons, FSFFL-vs-market analysis, heat maps, trade-partner intelligence, and explanation contracts.

**Exit gate:** a client can obtain all material analysis without embedding model logic.

## NEXT-8 — Interactive Product Layer

Build polished web/app experiences on top of the API boundary: roster dashboards, trade builders, scenario controls, opportunity feeds, draft tools, reports, and future mobile clients.

## Cross-cutting workstreams

These run throughout rather than waiting for a single phase:

- historical reconstruction;
- calibration datasets;
- evidence provenance;
- licensing/data-source review;
- performance profiling;
- challenger/production governance;
- synthetic and regression test suites;
- legacy failure-case harvesting.

## Development rule

Do not mechanically port an old module because the roadmap reaches a similarly named phase. Re-derive the responsibility and only retain legacy concepts that earn their place under the charter.

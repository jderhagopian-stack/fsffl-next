# Workstream — Forecast Research: K/DST Empirical Evidence & Source Gates

## State
**ACTIVE — MANAGEMENT AUTHORIZED**

Authorized: 2026-09-25

## Objective
Determine whether the remaining empirical/source gates blocking governed K/DST Forecast authority can be cleared with legitimate evidence, without reopening the completed K/DST architecture and without implementing or promoting production Forecast/model changes.

## Authoritative starting state
- The K/DST architecture directive is complete. Its durable handoff is `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`.
- Forecast implementation PR #215 completed the evidence-independent contracts/scoring work and non-promoting calibration harness.
- Implementation is correctly stopped at `BLOCKED — EMPIRICAL/SOURCE EVIDENCE GATE`.
- The controlling implementation checkpoint is `artifacts/implementation/forecast_k_dst_contracts_20260924/EVIDENCE_GATE_CHECK_20260925.md`.
- Existing Forecast authority, two-independent-source governance, fail-closed scoring semantics, and no-backdating rules remain binding.

## Authorized research questions

### 1. Historical independent K/DST projection evidence
Aggressively investigate materially distinct legitimate sources for a genuinely independent second historical point-in-time raw K and D/ST projection corpus suitable for empirical calibration.

Required proof:
- actual content date and forecast horizon, not a year-looking URL alone;
- provider/source identity and independence;
- raw component coverage sufficient for the calibration coordinate;
- durable provenance such as retained snapshot, archive capture, repository commit, provider export, or governed artifact;
- no current content relabeled as historical PIT evidence.

### 2. Production-source feasibility and rights
Separate:
- technical availability;
- ingestion/storage/derived-output permission;
- private-beta use;
- eventual commercial use.

Record terms, licensing/API evidence, and any case requiring direct provider permission. Do not infer commercial permission from public accessibility.

### 3. Sleeper scoring truth
Resolve remaining K/DST scoring semantics from authoritative Sleeper documentation and reproducible historical scoring examples. Produce exact truth fixtures where evidence permits. Leave unresolved attribution semantics explicit rather than guessing.

### 4. 2026 evidence recovery
Exhaustively search the repository, governed artifacts, retained source payloads, historical sources, provider exports, snapshots, and other legitimate evidence paths for authentic 2026 preseason K/DST raw projections.

Any recovered evidence must preserve source, point-in-time timestamp/content date, retrieval lineage, raw rows/components, and content identity. If no qualifying evidence exists, state that explicitly.

### 5. Gate decomposition
Determine gate status separately for:
- current-forward K/DST Forecast;
- empirical uncertainty calibration;
- preseason-baseline comparison;
- downstream Value/Simulation authority;
- private-beta operation;
- eventual commercial production.

Do not make these one monolithic gate where the governed architecture permits truthful partial capability, and do not weaken an authority rule to create partial capability.

## Required closeout
For each individual gate, persist:
- evidence found;
- provenance;
- authority implication;
- `CLEARED`, `PARTIALLY CLEARED`, or `STILL BLOCKED`;
- exactly what remains missing;
- next legitimate path to resolution;
- external Management action where public research cannot resolve the dependency;
- what durable evidence would constitute resolution.

## Prohibitions
- no production Forecast/model implementation or promotion;
- no fabricated projections;
- no one-source evidence presented as independent calibration;
- no mutable current page relabeled as PIT evidence;
- no guessed D/ST semantics;
- no weakening the two-source or uncertainty authority requirements;
- no synthetic 2026 preseason evidence;
- no repeated searching of an exhausted path without new evidence.

## Prior directive
The 2026-09-24 K/DST + new-league bootstrap architecture directive remains **DIRECTIVE COMPLETE — RESEARCH**. Its conclusions and implementation contract are not reopened by this directive.

## Operating behavior
Follow `../OPERATING_PROTOCOL.md`. Exhaust materially distinct authorized research paths. Before ending apply: **Is there another authorized research action I can perform now that could materially resolve one of these gates?** If yes, perform it.

Valid terminal states:
- `DIRECTIVE COMPLETE — RESEARCH`
- `BLOCKED — [specific external dependency]`
- `MANAGEMENT GATE — [specific decision required]`

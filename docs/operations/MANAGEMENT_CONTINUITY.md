# FSFFL NEXT — Management Continuity

Updated: 2026-10-07  
Authority: canonical durable record of Management direction, sequencing, deferred work, and roadmap changes across Management chats.

This document answers **where Management is going and why**.  
For **what is happening right now**, read [CURRENT_OPERATIONS.md](CURRENT_OPERATIONS.md).  
For exact tranche implementation evidence, read the linked workstream checkpoint.  
For the broad long-range capability plan, read [PRODUCT_ROADMAP.md](PRODUCT_ROADMAP.md) and [../FSFFL_NEXT_PRODUCT_PRIORITIES.md](../FSFFL_NEXT_PRODUCT_PRIORITIES.md).

## Management handoff rule

A new Management chat must, before issuing new scope:

1. read `AGENTS.md`;
2. read `docs/operations/CURRENT_OPERATIONS.md`;
3. read this `MANAGEMENT_CONTINUITY.md`;
4. read `docs/operations/PRODUCT_ROADMAP.md`;
5. read `docs/FSFFL_NEXT_PRODUCT_PRIORITIES.md`;
6. read the currently active workstream checkpoint(s);
7. verify current GitHub main / open PR / Render deployment state rather than assuming the documents are perfectly current.

Do not recreate priority order from chat memory alone.

## 2026-10-07 Management reconciliation

The larger FSFFL NEXT roadmap has **not** been replaced by the recent corrective program.

The project spent the recent period closing prerequisite reliability, architecture, Simulation, Intrinsic, League Atlas, Current Position & Depth, and managed-team product consolidation work. Those corrections are enabling work. They are not the new long-term roadmap.

Management intent remains to return to forward product development once the bounded immediate gates below are closed.

### Program position now

- **P0 Architecture Recovery:** architecturally complete. Preserve the simplified published-reader / lifecycle model. Do not resume endpoint-specific plumbing repair unless new evidence proves a surviving architectural invariant is violated.
- **Simulation 2.0:** core program accepted. Preserve 50,000-run authority, replay identity, week-by-week current-season semantics, governed postseason, common-world counterfactuals, team-of-origin ordering, and accepted Multiverse foundations unless a separately approved directive changes them.
- **Foundation 4 / Career Intrinsic:** career-forward model foundation is live. The remaining material gap is **coverage/completeness**, tracked in Issue #405 and the Career Coverage checkpoint.
- **League Atlas / Current Position & Depth:** physically accepted. Current follows the lineup; Dynasty follows the assets. Do not create another Current positional authority.
- **Home → Franchise Overview:** PR #418 is merged/deployed and physically accepted by Management on authenticated iPhone/Safari. Franchise is now the managed-team landing experience. Standalone Home is retired as a product surface.
- **Navigation / product hierarchy:** PR #421 is merged, deployed and physically accepted on authenticated iPhone/Safari. Primary navigation is now `Franchise | League | Explore | Trade | More`. The former Home item is removed; this tranche is closed.
- **Franchise visual-polish note:** Management preferred the original Home treatment where the “What Matters Most” card was red. This is a non-blocking presentation preference for a future Franchise polish pass, not a reason to reopen navigation or change Franchise semantics.
- **Dynamic Career Intrinsic invariant:** Career Intrinsic is current point-in-time intelligence, not a hard annual player-value table. The accepted model family/policy may be frozen and versioned, but player inputs and resulting Career values must respond to materially changing governed football evidence during the season and must rematerialize for each new season. Prior values should remain preserved as historical point-in-time snapshots. Selective invalidation/recomputation should follow dependency fingerprints; this does not authorize request-time model fitting or unnecessary whole-platform refreshes.
- **Career refresh scalability invariant:** freshness must be evidence-driven and coalesced, not page-driven or timer-driven by default. Cheap provider/change detection decides whether Career dependencies changed; unchanged fingerprints reuse last-good artifacts. Expensive fitted model authority should be reused across in-season evidence updates when its historical-training/model fingerprint is unchanged. Changed/new player evidence should be materialized in batch, and any league-wide economics/ranks that mathematically depend on the full cohort should recompute once for the resulting publication generation, not once per player/event. Broad waiver coverage should prewarm with the publication; unusual long-tail subjects remain on demand. A season rollover or promoted model/training-data change may legitimately trigger a full rematerialization.
- **Multi-league scale invariant:** design Career/Forecast refresh for thousands to tens of thousands of leagues, not for the current beta league. One league changing must not imply one historical model fit, provider ingest, or full player-universe rebuild unique to that league when the underlying evidence/authority is shared. Every expensive stage must declare its true dependency scope and cache/reuse at the widest mathematically safe level: provider/global evidence → model/training authority → scoring/rules signature → lineup/team-count signature → exact league State → team/user context. Identical semantic fingerprints should share computation/artifacts across leagues while tenant/private State remains isolated. Per-league work is reserved for facts/economics that genuinely depend on that league.
- **Global scale/resource invariant:** the same dependency-scope discipline applies to every FSFFL NEXT capability, not only Career Intrinsic. Commercial-scale architecture is required now; commercial-scale brute-force load is not. The private beta's limited CPU/RAM budget must be protected. Scale validation should use real measured stage costs, bounded synthetic/reuse tests and projected 1,000/10,000-league envelopes unless a larger execution is both necessary and explicitly resource-safe.
- **Deferred Python-runtime modernization:** do not broaden Career #405 to a Python upgrade. Python 3.11 remains a historical reproducibility fixture for the accepted Foundation 4 replay; the platform may later validate a newer production/materialization runtime (3.12 is already within the repository's declared supported range) through explicit dependency/provider compatibility, parity, performance and memory testing. Revisit only as a separate modernization tranche after the current Career/product priorities, and do not infer that historical 3.11 replay requires permanent production pinning.

## Immediate approved development sequence

### 1. Navigation / product hierarchy tranche — COMPLETE

Target primary product hierarchy:

`Franchise | League | Explore | Trade | More`

Management direction:
- remove the obsolete/inert Home primary-nav item;
- **Franchise** remains the managed-team landing/product surface;
- **League** remains the competitive landscape / League Atlas surface;
- rename **Market** to **Explore** for discovery/opportunity work;
- surface **Trade Center** in primary navigation as **Trade**;
- **More** holds secondary destinations rather than forcing every surface into the primary row.

This is a bounded information-architecture/product-navigation tranche. It does **not** authorize changes to Forecast, Value, Decision, Search economics, Simulation semantics, Current/Dynasty authority, lifecycle/publication plumbing, or Career Intrinsic.

Authenticated iPhone/Safari physical acceptance completed on 2026-10-07.

### 2. Career Coverage #405 — ACTIVE

**PR1 COMPLETE (2026-10-07 ET):** accepted after exact source/route/policy/identity/terminal provenance plus bounded downstream semantic sensitivity. Stable head `223241edcccf44af6e1c236cbab84751820c6ddf` passed Stable full suite `37723655257` attempt 2 (**2,231 passed / 1 warning**) and merged as `9141c12f3d69e8fa012b4e4db664f96e54f94aec`. The original strict numerical replay comparator remains red and visible; no back-fit epsilon or memory-limit relaxation was adopted. The first stable-suite attempt had one GitHub-runner absolute-RSS failure on the identical head; unchanged retry passed, so no product/runtime corrective was introduced. No Render deploy required. **PR2 is now the active authorized tranche:** subject resolver + dynamic evidence/materialization + complete rostered coverage under the recorded season-rollover, multi-league reuse, resource-bounded and no-retuning contracts.

The preserved 25-player roster gap is evidence of a broader production-universe boundary, not evidence that the accepted Y4–Y7 methodology was lost.

Management correction:
- the accepted Y4–Y7 authority is a deterministic **fit-on-materialization pipeline**;
- exact research code is durably preserved at commit `be2541a496227b33c12c755f576843dc4ab5a0bb`;
- accepted workflow `37096263982` restores that exact development/route code plus governed historical inputs and frozen route policy, then calls the preserved fitting path to produce the season board;
- no standalone serialized Y4–Y7 scorer was required by the accepted design, so Implementation must not reverse-engineer or “rediscover” one.

Approved production populations:
- **Reference cohort:** the frozen 335-player accepted calibration/parity cohort.
- **League accounting population:** every rostered QB/RB/WR/TE in the exact League State.
- **League decision universe:** the accounting population plus a broad, precomputed fantasy-relevant waiver/free-agent cohort so users can see Career information *before* making a waiver claim.
- **Extended universe:** unusual/deep candidates scored/materialized on demand through the same accepted pipeline when they become relevant.

The broad waiver cohort must be governed by football/eligibility evidence rather than an arbitrary top-N list. Market/Search/waiver signals may identify which players belong in the decision universe, but Market value/rank/percentile must not become a Career Intrinsic model feature.

Implementation authority:
- preserve remaining accepted historical artifacts/provenance before retention expiry;
- reuse the exact accepted Y4–Y7 code, historical evidence, frozen feature/model/route policy, seeds/settings and normalization;
- first reproduce the frozen 335 reference outputs within governed tolerance as a parity check;
- do **not** use the 25 missing rostered players or waiver candidates for model/route selection or tuning;
- do **not** reopen model-family research or change Career economics/#370;
- after parity, generalize only the subject/evidence/materialization boundary for rostered + waiver decision-universe + long-tail candidates.

The existing runtime is explicitly 2026-season scoped and carries frozen Y4–Y7/terminal assets. That is now recognized as an implementation limitation relative to the broader charter, not the intended end-state. #405 must not entrench that limitation: the reusable coverage/materialization design must be evidence-updating and season-rollover capable. Exact scheduling can remain bounded and selective, but materially changed governed football evidence must be able to invalidate/rematerialize the affected Career outputs under the same accepted model authority.

Checkpoint: [Career Coverage Extension](workstreams/CAREER_COVERAGE_EXTENSION.md).

### 3. Resume the broader product roadmap deliberately

After the two bounded items above, do **not** default into another indefinite corrective loop.

The next major program should be selected from the reconciled roadmap according to dependency and leverage, with primary emphasis on:

1. **Core product usefulness / actionability**
   - one coherent product hierarchy;
   - high-quality Explore/opportunity discovery;
   - strong Trade decision experience;
   - plain-English governed consequences and drill-through evidence;
   - repeated-session usefulness and latency.

2. **Historical intelligence foundation**
   - canonical point-in-time historical State reconstruction;
   - durable transaction/player/pick lineage;
   - player franchise history;
   - pick conversion history;
   - dated Forecast/Simulation snapshot archive and replay provenance.

3. **Decision uncertainty + Owner Intelligence**
   - simulation-sensitivity / sign-stability where useful;
   - context-normalized behavioral evidence;
   - owner tendencies as directional/descriptive intelligence;
   - no fabricated acceptance probabilities and no contamination of universal Value.

4. **Productize the league's memory**
   - Record Book;
   - franchise timelines;
   - trade/pick genealogy;
   - historical trade review;
   - generalized forward/historical What-If;
   - Multiverse / alternative futures;
   - rivalries, season stories and shareable league artifacts.

5. **Publications / analyst surfaces**
   - Preseason Preview, weekly reports, Trade Deadline / Playoff / Draft publications;
   - Year in Review / Almanac;
   - Analytics / investigation surfaces;
   - presentation remains downstream of governed truth.

6. **Commercialization / scale / league agnosticism**
   - unusual scoring/roster validation;
   - provider resilience;
   - multi-league support;
   - privacy/deletion controls;
   - observability and capacity;
   - public-scale architecture review before broad launch.

## Long-term intent that remains active

Do not lose or silently retire:
- historical PIT truth and hindsight isolation;
- origin-aware draft-pick economics;
- Broad Market / Intrinsic / League Market / Team Utility separation;
- Owner Intelligence;
- generalized What-If / Alternate History;
- Mock Draft / future behavior and needs-aware draft intelligence;
- Record Book, league history, lore and franchise identity;
- asset/pick lineage and player franchise history;
- Multiverse / alternative-futures product;
- polished FSFFL publications;
- horizon-specific/value-over-time Intrinsic presentation;
- league-agnostic scoring/provider expansion;
- evidence warehouse / proprietary calibration flywheel subject to governance;
- commercialization/public-scale hardening before broad launch.

## Frozen authority boundaries

Preserve:
`Data → Point-in-Time State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation`

Management-specific guardrails:
- recent bug-fix work does not automatically become roadmap priority;
- Presentation may organize/visualize/explain governed truth but may not create model truth;
- Explore/Search discovers; Trade/Decision evaluates;
- Simulation evaluates stochastic competitive outcomes and shortlisted scenarios; it is not broad discovery;
- Current follows configured lineup slots; Dynasty follows Career-forward assets;
- Current / 3-Year Intrinsic and Career Intrinsic remain distinct visible concepts;
- no hidden composite/master score merely to simplify the UI;
- no fabricated acceptance probability;
- no return to redundant per-surface publication/lifecycle negotiation.

## Documentation responsibilities

- `CURRENT_OPERATIONS.md`: live status / blockers / exact merge-deploy position.
- `MANAGEMENT_CONTINUITY.md`: Management direction, changed sequencing, deferred work, and next approved development path.
- `PRODUCT_ROADMAP.md`: broad long-range capability roadmap and reconciled program location.
- `FSFFL_NEXT_PRODUCT_PRIORITIES.md`: product-phase framing, user jobs, exit gates.
- workstream checkpoints: exact tranche contract, implementation evidence and acceptance.
- Charter / North Star: durable principles; change only when Management changes the principle itself.

## Handoff state

As of this reconciliation, the clean handoff is:

**Franchise Overview accepted → navigation/product hierarchy accepted → Career Coverage #405 active decision gate → resume broader roadmap from the reconciled position.**

The next Management chat should verify live repository/runtime state first, but should not invent a different sequence merely because older roadmap sections contain stale historical “NEXT” language.

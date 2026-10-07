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
- **Known navigation debt after #418:** the old Home bottom-nav item is still visible but inert. This was explicitly outside #418 scope and is the first item of the next navigation/product-hierarchy tranche; it is not a reason to reopen Franchise Overview semantics.

## Immediate approved development sequence

### 1. Navigation / product hierarchy tranche

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

Physical iPhone/Safari acceptance remains required.

### 2. Career Coverage #405

Resume the already-approved coverage/completeness problem after navigation closes.

Current preserved finding: the exact audited State contained **25 distinct missing rostered QB/RB/WR/TE assets** from the accepted Career artifact.

First required Management question:
- can the accepted Career scorer/inference function be reconstructed exactly from retained evidence so missing assets can be scored under the already-accepted model?

Boundary:
- no model fitting/retraining merely to fill coverage;
- no PR2 or new-model promotion until Management explicitly decides that exact scorer reconstruction is impossible or insufficient and authorizes the next evidence/model step;
- preserve #370 Dynasty formula and current Career economics.

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

**Franchise Overview accepted → navigation/product hierarchy next → Career Coverage #405 → resume broader roadmap from the reconciled position.**

The next Management chat should verify live repository/runtime state first, but should not invent a different sequence merely because older roadmap sections contain stale historical “NEXT” language.

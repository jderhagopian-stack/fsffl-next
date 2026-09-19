# Historical Trade Grader — audit, architecture, and implementation status

## Scope

This workstream rebuilds historical trade grading without changing production market value, team utility, trade-decision authority, or UI behavior. It is intentionally additive and read-only.

The product distinguishes three questions:

1. **Point-in-time decision grade** — was the decision good using only information reasonably knowable then?
2. **Final outcome grade** — knowing what happened later, how did the acquired assets and team results turn out?
3. **What changed after the trade?** — explanatory bridge, not a third grade.

A favorable original decision and a favorable realized outcome are deliberately independent.

## Existing NEXT infrastructure audit

### Reusable now

- `fsffl.state.history`
  - point-in-time snapshot-store protocol
  - deterministic `latest_at_or_before` semantics
  - suitable contract for cached historical league/team reconstruction
- `fsffl.state.models`
  - league rules, lineups, teams, players, ages/status provenance, rosters, picks, pick ownership, transactions
- `fsffl.forecast.history`
  - provider-neutral point-in-time forecast observations
  - prevents a later forecast from being substituted into an earlier query
- `fsffl.value.pick`
  - uncertainty-aware pick-value mixture primitive
  - does not invent draft-slot probabilities or class-strength coefficients
- `fsffl.value.market`, `market_context`, `transaction`, and calibration modules
  - point-in-time market/value and transaction-price primitives with model/version provenance
- `fsffl.value.transaction_evidence`
  - clean historical transaction evidence import for one-for-one player trades
  - intentionally refuses to decompose multi-asset packages into fake standalone prices
- `fsffl.trade_decision`
  - authoritative bilateral before/after consequence binding
  - directional decision shape, feasibility, materiality, economics, acceptance, strategy
- `fsffl.team_utility`
  - lineup, resilience, competitive state, simulation, asset-portfolio and scenario-delta authority
- `fsffl.analytics`
  - read-only downstream product/API layer and cache-oriented service patterns
- Architecture and governance docs already establish point-in-time state, provider boundaries, caching, evidence/parameter governance, validation, and strict authority separation.

### Important existing limits

- `StateSnapshotStore` is currently a protocol plus in-memory reference implementation; durable historical snapshot persistence is deferred.
- Historical forecast storage is likewise in-memory/reference-level even though the no-future-leakage semantics are correct.
- Pick valuation has the right uncertainty primitive, but NEXT does not yet contain the full Historical Pick Coordinate research pipeline that estimates historical slot distributions/class strength for every relevant FSFFL pick.
- Transaction evidence currently imports only clean one-for-one player trades. Multi-asset, pick-inclusive, and FAAB-inclusive historical trade normalization is not yet implemented in NEXT.
- Trade Decision currently describes bilateral decision shape and consequences but does **not** emit a governed scalar historical decision-quality score. Therefore the Historical Trade Grader must not invent one in Analytics.
- No asset-lineage domain contract previously existed.
- No retrospective outcome normalization policy previously existed.

## Gap analysis versus the requested grader

| Capability | Status | Remaining work |
| --- | --- | --- |
| Point-in-time state cutoff | Foundation exists | Historical materializer + durable snapshots |
| Historical projections | Foundation exists | Populate/retain historical source observations by trade date |
| Historical player market value | Partial | Backfill usable point-in-time market panels with rights/provenance |
| Historical pick value | Primitive exists | Complete Historical Pick Coordinate evidence pipeline |
| Bilateral trade consequences | Exists | Re-run against reconstructed historical state |
| Package/consolidation economics | Existing NEXT transaction/economic modules | Historical package evidence needs richer import/benchmark coverage |
| Behavioral Intelligence | Not required for v1 | Add only if historically reconstructible; negotiation context only |
| Point-in-time letter grade | Contract implemented | Decision authority must emit governed score/policy or approve a governed translation policy |
| Retrospective components | Contract implemented | Build empirical normalization for asset value, production, franchise outcomes |
| Asset lineage | Contract implemented | Build lineage events from historical transactions/drafts; preserve ambiguous bundles |
| Human-readable report object | Implemented | Product rendering later; no UI added here |
| Caching/precompute | Architecture-ready | Persist reconstructed state, forecast/value artifacts, lineage, and completed reports |

## New implementation

`src/fsffl/analytics/historical_trade.py` adds a read-only, governed report contract.

### Fail-closed point-in-time grading

`PointInTimeDecisionEvidence` contains the evidence that a historical Decision-layer reconstruction may expose to Analytics: value exchanged, utility, lineup/replacement/pick/package consequences, uncertainty, disposition, evidence completeness, and the authoritative decision model version.

Crucially, Analytics does **not** calculate `decision_quality_score`. If Decision has not emitted a governed score, the result is:

> NOT GRADED — Decision has not emitted a governed historical decision-quality score

If required historical evidence is missing, it returns:

> NOT GRADED — insufficient point-in-time evidence: ...

This prevents false precision and future-information leakage.

### Governed grade policy

`GovernedGradePolicy` translates a 0–100 authoritative score into a letter grade. It has:

- explicit bands
- policy id
- model version
- provenance
- no default thresholds

The Historical Trade Grader therefore cannot silently create letter-grade cutoffs.

### Retrospective outcome grade

`RetrospectiveOutcomeComponents` supports three separately measurable dimensions:

- asset-value outcome
- production outcome
- franchise/team outcome

`RetrospectiveOutcomePolicy` can combine them into a summary score, but:

- weights have no defaults
- weights must sum to one
- every positively weighted component must be available
- missing components cause `NOT_GRADED`; weight is never silently redistributed

This lets research later determine whether all three dimensions deserve authority and what evidence/weights are defensible.

### Asset lineage

`AssetLineageEvent` and `trace_asset_lineage()` support:

- direct player-to-asset chains
- pick-to-selected-player conversion
- multi-asset descendants only when explicit attribution weights are available
- terminal retained assets
- cycle rejection
- ambiguity reporting when multiple competing causal paths exist

The grader never marks a later-traded asset merely “gone,” but it also does not invent causal credit inside ambiguous bundles.

### Report/API contract

`HistoricalTradeReport` is UI-ready and includes:

- transaction id/date
- teams and assets exchanged
- originator if known
- point-in-time grade and evidence
- final-outcome grade and components
- asset lineage
- what changed after the trade
- lessons
- report model version

The contract is read-only. Presentation can render it but should not calculate model truth.

## Recommended orchestration

The eventual production historical-grading job should run in this order:

1. Load the completed historical transaction and trade timestamp.
2. Resolve or materialize the latest league state at/before the transaction.
3. Resolve only forecast observations available at/before that timestamp.
4. Resolve point-in-time player market/value estimates and Historical Pick Coordinate estimates.
5. Build the original bilateral proposal from the historical transaction.
6. Run authoritative Team Utility and Trade Decision before/after scenarios on the reconstructed state.
7. Ask Decision for the governed historical decision-quality output. If unavailable, retain the evidence and return `NOT_GRADED` rather than approximating it in Analytics.
8. Separately collect later realized player production, value evolution, pick conversion, lineage, and causally defensible team outcomes.
9. Normalize retrospective components under an evidence-backed research policy.
10. Translate scores to letters under the governed grade policy.
11. Persist the completed report and its dependency/model versions for fast product reads.

## Performance design

A commercial implementation should key persisted artifacts by `(league_id, as_of, model_version/dependency fingerprint)` rather than reconstructing everything when a report opens.

Recommended reusable artifacts:

- historical `LeagueState` snapshots
- historical normalized forecast observations
- point-in-time value estimates
- Historical Pick Coordinate estimates
- historical bilateral decision evidence
- asset-lineage traces
- completed `HistoricalTradeReport`

When new later outcomes arrive, retrospective components/lineage can be incrementally refreshed without changing the immutable point-in-time decision evidence.

## 2022 startup and FAAB governance

The Historical Pick Coordinate research layer must explicitly exclude the 2022 FSFFL startup from normal rookie-pick calibration. That event was an auction-style startup where nominal picks functioned as nomination slots, so treating those slots as ordinary rookie draft capital would contaminate historical pick-value evidence.

FAAB should remain economically de minimis by default in historical trade evidence unless the transaction itself supplies a defensible exception (for example, a roster-bubble player moved for FAAB instead of being cut). Any special treatment must be provenance-bearing and governed; the grader should not assign a universal FAAB premium from anecdote.

## Calibration and sanity cases

The current implementation unit-tests the architecture rather than tuning grades to remembered trade opinions:

- complete evidence + authoritative score can be translated to a letter only through an explicit governed policy
- missing historical evidence fails closed
- absence of a Decision-owned quality score fails closed
- retrospective grades require every positively weighted component
- pick → selected player lineage is preserved
- invalid multi-asset attribution is rejected
- competing lineage paths are reported ambiguous rather than arbitrarily resolved

The next calibration dataset should include real FSFFL examples across player/player, player/pick, pick/player, one-for-many, contender, rebuild, aging-veteran/young-asset, good-decision/bad-outcome, and bad-decision/good-outcome cases. Those examples should validate discrimination and hindsight-bias resistance; they should not dictate the answer.

## Plain-English example report

### Trade Summary

**Date:** August 15, 2025  
**Team A received:** Player X, 2027 1st  
**Team B received:** Player Y  
**Originator:** Team A, if reconstructible from transaction provenance

### At-the-Time Grade

**NOT GRADED — insufficient point-in-time evidence**

The roster and league settings are reconstructed, and historical market value is available, but the historical projection set for Player X is incomplete. NEXT therefore does not pretend it knows what a fully informed decision model would have said on August 15, 2025.

### Why That Was the Grade

What we can say safely is that Team A acquired more long-term asset value and a future first-round pick, while Team B consolidated into the stronger immediate starter. The exact lineup and competitive-window effect remains incomplete because one required historical forecast input is missing.

### Final Outcome Grade

**A — high confidence** *(illustrative only; requires an approved retrospective policy)*

Player X subsequently broke out, the 2027 first became Player Z, and both assets retained substantial value. Player Y declined sooner than expected.

### What Actually Happened

The acquired 2027 first was used on Player Z, so the pick is not treated as “gone.” Player X remained on Team A. No later bundled transaction requires ambiguous attribution.

### What Changed After the Trade

The original decision could not be graded confidently with the surviving point-in-time evidence. The retrospective outcome is much clearer because Player X exceeded the range of expectations and the acquired pick converted into a valuable player.

### Lessons

- Do not confuse a great realized outcome with proof that the original decision was obviously correct.
- Preserve the value created by pick conversion and later asset lineage.
- Missing historical evidence should reduce certainty, not invite hindsight.

## Remaining research blockers

The two most important evidence projects are:

1. **Historical Pick Coordinate completion** — point-in-time pick distributions/class strength with uncertainty and provenance.
2. **Historical Decision Quality calibration** — decide whether Decision should expose a scalar quality score and, if so, estimate/validate it without double counting value, lineup, competitive state, package structure, and uncertainty.

Retrospective component normalization is the next tier: define defensible asset-value, production, and franchise-outcome measures, then empirically determine whether a single combined final grade adds signal or simply hides useful distinctions.

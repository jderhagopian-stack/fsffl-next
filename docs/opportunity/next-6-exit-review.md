# NEXT-6 Exit Review

This is the governing closeout matrix for NEXT-6 Opportunity Search & Optimization.

## Promotion states

- **AUTHORITATIVE** — validated enough for default NEXT search behavior.
- **AUTHORITATIVE_CONDITIONAL** — authoritative when explicit governed upstream/policy inputs are supplied.
- **PROVISIONAL_GOVERNED** — real behavior with incomplete calibration; explicit and future-updatable.
- **ABSENT_BY_DESIGN** — intentionally not fabricated without evidence.
- **OUT_OF_SCOPE** — belongs downstream.

## Current classification

| Component | Status | Basis | NEXT-7 may consume? |
| --- | --- | --- | --- |
| Candidate lifecycle / discovery state | AUTHORITATIVE | Immutable typed lifecycle with deterministic identity/versioning | Yes |
| Action-authority separation | AUTHORITATIVE | Diagnostic, market-test, actionable, none remain distinct | Yes |
| Unknown acceptance handling | AUTHORITATIVE | `NOT_ESTIMATED` never becomes automatic action authority | Yes |
| Focal NEXT-5 disposition gate | AUTHORITATIVE | Realistic/acceptable deal cannot become actionable if focal NEXT-5 disposition does not SUPPORT | Yes |
| Counterparty domination guard | AUTHORITATIVE | Complete uniform counterparty loss remains diagnostic | Yes |
| Legal trade inventories | AUTHORITATIVE | Canonical owned players/picks/FAAB only | Yes |
| Bounded package generation | AUTHORITATIVE | Explicit package-size/type/FAAB bounds; canonical deduplication | Yes |
| Bilateral package pair generation | AUTHORITATIVE | Deterministic cross-product with explicit truncation/coverage | Yes |
| Adjacent negotiation frontier geometry | AUTHORITATIVE | Add/remove one owned asset; bounds and FAAB alternatives preserved | Yes |
| Frontier traversal | AUTHORITATIVE | Bounded BFS continues through bad/theoretical early offers rather than stopping early | Yes |
| Frontier completeness on bounded fixtures | AUTHORITATIVE_VALIDATION | Small exhaustive fixture proves full reachable package-pair recovery when depth/budget permit | Yes |
| Multi-objective Pareto ordering | AUTHORITATIVE | Explicit named objectives; no hidden master opportunity score | Yes |
| Action/evidence categorical tiering | AUTHORITATIVE | Orders promotion/readiness separately from substantive objectives | Yes |
| Asset-shopping structural universe | AUTHORITATIVE | Owned focal asset -> legal counterparties/return packages; no inferred demand | Yes |
| Waiver/free-agent structural universe | AUTHORITATIVE | Free-agent add pool; actual active-roster fullness; taxi/IR not silently cut | Yes |
| Waiver add/drop canonical scenario | AUTHORITATIVE | Immutable state scenario; new player enters bench for NEXT-4 optimization | Yes |
| Waiver material assessment | AUTHORITATIVE_CONDITIONAL | Reuses explicit governed materiality policies; no hidden thresholds | Yes, with policy |
| Waiver action authority | AUTHORITATIVE_CONDITIONAL | Requires complete competitive + economic material evidence and SUPPORT disposition | Yes, with policy |
| Production search depth/evaluation budgets | PROVISIONAL_GOVERNED | Explicit bounded compute controls; not yet empirically performance-tuned | Yes, but expose policy/version |
| Value-based pruning | ABSENT_BY_DESIGN | No unsafe heuristic pruning promoted before recall validation | No hidden use |
| Scalar opportunity score | ABSENT_BY_DESIGN | Pareto/multi-objective architecture preferred; no arbitrary weights | No |
| Acceptance probability | UPSTREAM ABSENT_BY_DESIGN | NEXT-5 remains `NOT_ESTIMATED` until calibrated evidence exists | Preserve unknown |
| Production materiality thresholds | UPSTREAM ABSENT_BY_DESIGN | Explicit policies exist; production calibration still pending | No silent defaults |
| Reports/charts/presentation | OUT_OF_SCOPE | NEXT-7/8 | Yes downstream only |

## Key safety properties

- Search cannot create or modify player/pick values.
- Search cannot rewrite NEXT-4 utility or simulation outcomes.
- Search cannot fabricate acceptance odds.
- Search cannot promote counterparty-dominated or incomplete candidates as actionable.
- A candidate that NEXT-5 says the focal team should decline/review cannot become actionable merely because acceptance appears likely.
- Missing materiality policy prevents unsupported action authority.
- Bounded pair generation reports truncation instead of pretending partial search was exhaustive.
- Frontier search does not terminate simply because early offers are poor or theoretical.
- Pareto ordering preserves mixed short-term/long-term tradeoffs instead of hiding them in a scalar.
- Shopping search does not infer demand merely from structural counterparty availability.
- Waiver search uses actual active roster capacity and does not silently treat taxi/IR as ordinary cuts.
- NEXT-6 has an automated import boundary preventing Analytics/Presentation authority leakage.

## Controlled validation coverage

Current tests cover:

- candidate lifecycle and action-authority invariants;
- legal owned-asset trade inventories;
- package canonicalization and bounded generation;
- bounded FAAB alternatives;
- deterministic bilateral package-pair generation;
- explicit package-cross-product truncation reporting;
- frontier add/remove adjacency and ownership checks;
- frontier continuation after a diagnostic/bad seed;
- evaluation-budget enforcement and reproducibility;
- full recovery of the complete 3 x 3 bounded package-pair universe in a small fixture;
- Pareto preservation of mixed tradeoffs and removal of strictly dominated opportunities;
- NEXT-5 unknown-acceptance and counterparty-domination translation;
- focal NEXT-5 disposition promotion guard;
- structural asset-shopping counterparties/packages;
- waiver active-roster vs taxi behavior;
- immutable add/drop scenarios;
- explicit-policy waiver material support/review/insufficient states;
- future-evidence and economic-scale rejection;
- authority/import-boundary protection.

## Remaining empirical / runtime work

### 1. Search-budget profiling

`max_depth`, `max_evaluations`, package-size bounds, and pair-generation caps are explicit compute policies, not model-value coefficients. They should be profiled on realistic league workloads for latency and recall before a product default is locked.

Until then:

- bounds remain explicit/versioned;
- truncation/exhaustion state remains visible;
- no partial search may be represented as exhaustive.

### 2. Safe staged pruning

NEXT-6 currently prefers correctness over aggressive value-based pruning. Future cheap pruning may use complete, scale-compatible authoritative evidence only after pruning-recall tests prove known good opportunities are not systematically removed.

### 3. Acceptance and historical league behavior

NEXT-6 is ready to consume NEXT-5 acceptance evidence, including future global -> league -> owner historical behavior adjustments, but no calibrated acceptance model is currently populated. Unknown acceptance remains unknown.

### 4. Live integrated beta

No live league output has been observed in this chat runtime. The deferred integrated beta should eventually exercise:

**Provider -> State -> Forecast -> Value -> Team Utility -> Trade Decision -> Opportunity Search -> Analytics/API**

A real league is diagnostic/adversarial validation, not universal calibration truth. Generalizable defects should become regression tests.

## Exit recommendation

NEXT-6's clean-sheet search architecture is suitable for closeout once the final exact-head CI and changed-file scope review are clean.

The phase should **not** be held open merely to invent:

- acceptance probabilities;
- production materiality thresholds;
- scalar opportunity-ranking weights;
- hidden value/pruning premiums;
- product-specific latency defaults.

Those should remain explicit calibration/profiling tasks.

NEXT-7 Analytics & API may consume NEXT-6 outputs read-only and present:

- opportunity candidates;
- action-authority tiers;
- evidence completeness and reasons;
- Pareto/frontier membership;
- search coverage/truncation/exhaustion;
- trade/waiver structured consequences;
- acceptance status and historical evidence when available.

NEXT-7 must not repair, rescore, or reinterpret NEXT-6 opportunities in presentation code.

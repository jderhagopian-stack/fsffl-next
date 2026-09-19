# Forecast Bounded Final Fit + Current-Player Credibility Gate — fitting boundary

Date: 2026-09-18  
Authority: research/materialization only  
Final classification: **C — REPRODUCIBILITY / FITTING BOUNDARY**

## 1. Pre-fit gate result

The required pre-fit recovery manifest was persisted **before any B2a or R2 model execution** at commit:

`4c90abd1f43c92b493ef72dd0517c2f46417be81`

The pre-fit gate fails. No final-current-cutoff fit is authorized under the directive because the frozen historical evidence does not uniquely specify the deployment fit.

## 2. What is fully frozen

The final route itself is reproducible and unchanged:

- B2a is the default.
- QB experience 0–3: B2a at Y2/Y3.
- QB experience 4–8: R2 at Y2/Y3.
- QB experience 9+: R2 at Y2, B2a at Y3.
- RB/WR/TE: B2a at Y2/Y3.

The governed 335-player Y1 coordinate is durable at SHA-256
`c668b74b9010809904c14366d992137f7b038b299d6d3f031b07eea0d63c0b3f`.

The approved replacement identity/history coordinate is also durable:
- 335 rows;
- coordinate SHA-256 `95fd6565a908b044ca234898cc801749abb2b6aa62a84c2d3c917445d369cda1`;
- 300 accepted historical identities and 35 explicit unmatched identities;
- 199 players with two genuine prior seasons.

Historical prediction evidence is intact:
- B2 prediction rows: 16,689, SHA-256 `9eda45f36786c0c73a190566b9eb14d199a604427112c890488f2d5a2cdaacb6`.
- Ordered-state recombination rows: 41,344, SHA-256 `dbd1b1b5fd7fe7c6c43c2e6bda417db192c852f136ac704a7a5abb48fae2288b`.
- Candidate-B ancestor prediction rows: 22,252, SHA-256 `4298b40667906fca5a88ad823313e57c0c5971b5eef9c6b38f55f5f5155bd3f5`.

## 3. B2a: what is known and what is missing

Durable evidence establishes B2a as:

> a five-bin monotone nonlinear within-position production-percentile correction in log-point space, partially pooled by position/horizon using n/(n+50) shrinkage toward the global bin effect.

That is enough to identify the historical candidate but not enough to execute one exact new fit.

The durable record does **not** uniquely specify:
- the exact five-bin boundary construction / edge values and tie handling;
- the exact monotonicity-enforcement procedure;
- the exact Candidate-B estimator/design that the correction replaces or augments;
- the complete target/residual and back-transform/floor implementation;
- a durable executable B2a final-fit implementation or parameter object.

Choosing those details now would be reconstruction by judgment, not mechanical deployment.

## 4. R2: what is known and what is missing

Durable evidence establishes the conceptual R2 architecture:

- frozen A2/routed persistence;
- frozen D / integrated-I1 ordered future-state probabilities;
- player-specific positive-state conditional production;
- R2 = R1 plus frozen two-prior-season consistency evidence;
- no named-player terms and no future information;
- cold-start remains separate.

The two-prior consistency component is itself reproducibly specified: training-only normalization, explicit coverage, neutral zero continuous values when uncovered, and no-intercept BayesianRidge on residual-z with global mean/gap/coverage plus position deviations.

But the **R1 state-conditional learner that R2 extends is not durably specified at deployment precision**. Missing:
- exact estimator/formula;
- exact design matrix/basis;
- fixed regularization hyperparameters;
- exact partial-pooling/shrinkage hierarchy;
- minimum-support and fallback rules;
- exact state-conditional target transform/back-transform.

The prior recombination Stage-0 audit records an `ARCHITECTURE_SPECIFICATION.json` with SHA-256
`197acd61b3420c6664e171c00a24e7d2a19b91ee1fcf8e2ec91ab6e307dee9cc`,
but those bytes are not present in the live repository or FSFFL NEXT Library surfaces available to this task.

The 41,344 historical prediction rows prove what R2 predicted in historical folds; they do not uniquely identify the fitted estimator needed for a new current-cutoff fit.

## 5. Current-cutoff ambiguity

The historical studies fit inside chronological cutoffs. The durable multi-year component documents
`source_season + horizon <= evaluation_source_season` for its eligible transitions.

However, there is no durable B2a/R2 deployment rule that uniquely answers which final completed-source endpoint must be used for the 2026 board. Choosing between horizon-specific latest-available source seasons and a common completed-source endpoint would be a new training-window/cutoff decision.

The directive expressly forbids making that choice here.

## 6. Why historical-output reverse engineering is not allowed

It may be technically possible to infer a B2a binning convention or search for an R2 regression that approximately reproduces the historical prediction rows. That would violate this task.

The authorization is for **one exact mechanical final fit of an already-frozen recipe**, not for identifying a recipe by solving backward from its outputs. Multiple implementations could match historical rows closely while extrapolating differently on the current board.

No such reverse engineering, parameter search, or fit-selection exercise was performed.

## 7. Branch integrity recovery

At task start the research ref was `9d45d8968f9a90bc5c830e82e5f22369c958fc34`, but that commit's tree contained only seven entries because the preceding binary-PDF persistence step had accidentally created a tree from scratch.

The repository history still contained the intact parent tree. It was restored without changing any model/research content:
- intact research tree before the binary artifact issue: `37c40b87df242e94d05caf0e894c66a999ae249c`;
- repair commit: `7b962a6406c0132e6991d33ebad7b1cff9e9c494`;
- the two intended prior gate binary/manifest artifacts were overlaid;
- an unrelated concurrent collapse-provenance commit `19f6c6983cf673b833c35684ff2c8090ba3eff8b` was preserved.

This repair is repository-state hygiene only; it does not alter Forecast methodology or results.

## 8. Consequence for the credibility gate

Because the fitted B2a/R2 package cannot be created legally:
- no fitted package exists;
- no reload verification can be performed;
- no exact final-route Y2/Y3 board can be produced;
- no apples-to-apples Y1/Y2/Y3 credibility judgment is permitted;
- no named current-player inspection is performed.

A 335-player CSV/XLSX is therefore intentionally **not** generated. Filling it from the older sentinel or from an approximated fit would violate the directive.

## 9. Outcome

**C — REPRODUCIBILITY / FITTING BOUNDARY.**

Smallest missing dependency:

> The exact durable deployment-grade B2a and R1/R2 fitting specifications — especially the B2a basis/monotonic construction, the R1 state-conditional learner and pooling/regularization rules, and the mechanically governed final training cutoff. The previously recorded R2 architecture-specification bytes would materially narrow this boundary if recovered.

## 10. Execution accounting

- B2a fits: **0**
- R2 fits: **0**
- deterministic verification reruns: **0**
- candidate comparisons: **0**
- hyperparameter searches: **0**
- coefficient tuning iterations: **0**
- current-player tuning actions: **0**
- holdout selection runs: **0**
- 335-player final-route board materializations: **0**
- current-player credibility judgments: **0**
- production/downstream changes: **0**

No main, PR #147, production authority, Intrinsic/Shapley, Constitution, C=0.25, lineup, or discounting change.

**STOP FOR MANAGEMENT REVIEW.**

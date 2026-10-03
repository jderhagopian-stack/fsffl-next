# 2026-10-02 — Foundation 4 Holistic Career-Forward Governance Slice

## Status

**FOUNDATION 4 ACTIVE — RESEARCH / GOVERNANCE**

PR #346 is accepted only as the governed Y4-Y7 long-horizon component. Current Intrinsic Y1-Y3 remains separate production authority. This slice resolves only the two remaining Foundation-4 evidence gaps: Y8+ terminal/tail economics and aggregation into one career-forward raw coordinate.

## Frozen economic coordinate

The holistic candidate raw quantity is:

```
CAREER_FORWARD_RAW =
  phi_Y1 + phi_Y2 + phi_Y3
  + phi_Y4 + phi_Y5 + phi_Y6 + phi_Y7
  + TAIL_Y8_PLUS
```

where every `phi_Yh` is the league-aware annual Shapley marginal lineup contribution in fantasy-point units, and `TAIL_Y8_PLUS` is the expected cumulative annual Shapley contribution from literal Y8 through career end.

This is dimensional aggregation of the same economic unit, not a preference weighting. No discount rate, horizon weight, youth/age multiplier, survival coefficient, terminal multiplier, Market input, team utility, owner signal or display index enters the formula.

Current Intrinsic is unchanged and remains the separate governed Y1-Y3 lens with its existing production discount semantics. Foundation 4 reuses the underlying annual Y1-Y3 raw Shapley coordinates, not Current Intrinsic's display index and not its discounted scalar.

The accepted #346 Y4-Y7 component remains unchanged. Foundation 4 consumes its annual authority coordinates directly; it never adds/averages the #346 0-10000 ruler.

## Frozen terminal research target

Tail calibration target:

```
TAIL_Y8_PLUS_REALIZED =
  sum(realized annual league-capacity Shapley contribution, Y8 ... career end)
```

No perpetuity, carried-Y8 value, geometric terminal multiplier or arbitrary end year is permitted.

Historical target computation uses the same lineup-capacity Shapley game as governed Intrinsic, with 2,048 permutations and deterministic seeds. Because Shapley economics depend on league lineup capacity, a fitted terminal artifact is authoritative only for the exact lineup-capacity signature used by the study. A nonmatching league fails closed until separately calibrated.

## PIT features and candidates

Only point-in-time football facts available at the base season may enter:
- position;
- age;
- NFL experience;
- current-season fantasy production;
- prior-season fantasy production;
- explicit prior-production-missing indicator.

No current-player names, Market/dynasty values, owner behavior, team competitive state, contract multiplier, manual age curve or workload penalty is allowed.

Frozen candidate set:
1. `zero_tail` — guardrail comparator only;
2. `direct_ridge` — regularized direct `log1p(TAIL_Y8_PLUS)` regression;
3. `two_part_state` — logistic probability of positive Y8+ tail × regularized conditional positive-tail magnitude.

The two learnable families are deliberately retained together when both pass. The study must not choose one because named-player shadows look better.

## Chronology / censoring

- Historical source: retained governed `PLAYER_SEASONS.csv` from workflow artifact `10899387479`, digest `sha256:ea72f312148f01b8066419e8f12cb3a04a4dbbd99fd6e0b7dc975c65cc2446b5`.
- Model-selection origins: base seasons through 2010.
- Untouched final holdout origin: base season 2011. Candidate/gate rules are frozen before this holdout is inspected.
- Rows whose careers remain observably right-censored near the evidence boundary are excluded from scored target rows and reported separately; exclusion is never converted to zero tail.
- No current 2026 player is inspected until the historical disposition is frozen.

This is retrospective completed-career calibration, not a claim that terminal labels were available in historical real time. That limitation is part of model-authority uncertainty and is why this slice may promote only a coarse/set-valued terminal coordinate, not an exact career-value oracle.

## Frozen promotion gates

A learnable family is supported only if, on the pre-holdout rolling/model-selection evidence:
- aggregate RMSE is lower than `zero_tail`;
- aggregate rank correlation is positive;
- no governed position has RMSE worse than 1.15x the zero-tail comparator;
- predictions are finite and non-negative.

The untouched 2011 holdout is confirmation/evidence only after the supported set is frozen. It must report aggregate and position metrics, right-censoring, empirical 80/90 absolute-residual coverage, and model-envelope coverage. No post-hoc candidate pruning is allowed from the holdout.

## Uncertainty semantics

Terminal model-authority uncertainty:
- supported-model prediction low/high envelope;
- midpoint is reference only;
- authority remains `coarse_set_valued` unless independent evidence later supports exact cardinal authority.

Ordinary outcome uncertainty:
- model/position empirical absolute-residual 80/90 bands from model-selection evidence;
- preserved separately from model-family spread.

No cumulative career standard deviation is authorized. Cross-horizon covariance among Y1-Y7 and the terminal tail remains unvalidated.

## Holistic aggregation uncertainty

If the tail gate passes, the holistic raw model-authority envelope is the arithmetic sum of compatible annual authority coordinates:
- governed Y1-Y3 annual raw Shapley values;
- #346 Y4-Y7 annual low/high authority;
- terminal Y8+ low/high authority.

This sum is not a probabilistic confidence interval. Horizon-specific ordinary uncertainty remains separately exposed; no independence assumption or variance summation is permitted.

## Next action if governed

If the historical gate passes, continue directly to:
1. freeze fitted terminal evidence/coefficients and lineup-capacity signature;
2. implement pure terminal Value consumer and holistic aggregator;
3. materialize the current governed cohort in shadow using existing Y1-Y3 and #346 Y4-Y7 authorities;
4. persist holistic output separately from Current Intrinsic and from the #346 component;
5. expose a separate shadow API;
6. run resource/performance and semantic-fingerprint validation;
7. perform bounded review and targeted acceptance.

If the research gate fails, stop only at the failed evidence boundary. Do not guess a terminal value.

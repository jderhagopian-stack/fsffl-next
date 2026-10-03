# Foundation 4 Career-Tail Research Closeout

Date: 2026-10-02

Status: **GOVERNED FOR BOUNDED SHADOW IMPLEMENTATION**

Frozen directive:
`docs/operations/directives/20261002_FOUNDATION4_CAREER_TAIL_GOVERNANCE.md`

Corrected exact research workflow:
- run: `37086000162`
- head: `ae03df724bb2b8ff16a48b9798dcf21b8bc9c3b9`
- artifact: `11260487964`
- artifact name: `foundation4-career-tail-research`
- digest: `sha256:505ba72e71ddcb868c1673386f2a516d64e1a087fe2d8d9807572cb24cd99aa6`

Historical source:
- retained governed term-structure artifact `10899387479`
- source digest: `sha256:ea72f312148f01b8066419e8f12cb3a04a4dbbd99fd6e0b7dc975c65cc2446b5`
- player-season evidence through 2025.

## Review corrections incorporated

The final evidence corrects both exact-head review findings:
- rolling and final-holdout validation are grouped by `player_id`; no evaluated player's overlapping career rows enter that split's training set;
- log-target models use training-only Duan smearing so terminal predictions target **expected original-scale cumulative Y8+ Shapley mass**, not the log-scale median/geometric coordinate.

The early two-part folds use only the mathematical identifiability minimum (both classes plus at least one positive magnitude row). No hidden sample-size promotion gate is introduced; model adequacy is decided only by the frozen out-of-sample promotion gates.

## Frozen tail target

The terminal target is direct cumulative **Y8+ career Shapley mass**:

`sum(realized annual league-capacity Shapley contribution from literal Y8 through career end)`.

It is not a perpetuity, a carried-Y8 value, an age multiplier, a survival multiplier, or a terminal-value multiple.

Annual target Shapley used the governed lineup-capacity economy, 2,048 permutations and seed family `20260915 + season`.

The calibrated artifact is authoritative only for lineup-capacity signature:
`fe6d07a77a7f11cd61e1af476e9d6b3fe89b7e59c6aecdeab5eb61c991b21349`

That signature corresponds to QB 1 / RB 2 / WR 3 / TE 1 / FLEX 1 / SUPERFLEX 1. A nonmatching lineup-capacity signature must fail closed until separately calibrated.

## Candidate disposition

Rolling/model-selection evidence: **2,752** scored rows with **zero train/test player overlap**.

Both frozen learnable families still pass:
- `direct_ridge`: RMSE **147.454**, MAE **27.625**, Spearman **0.117**.
- `two_part_state`: RMSE **146.037**, MAE **27.366**, Spearman **0.302**.
- zero-tail comparator RMSE: **148.401**.
- neither supported family breaches the frozen 1.15x position-catastrophe RMSE guardrail.

The governed terminal authority remains **coarse set-valued** across both supported model families. No winner is selected from current-player or final-holdout aesthetics.

## Untouched 2011 final holdout

- total candidate rows: **567**
- right-censored rows excluded, not zeroed: **8**
- scored rows: **559**
- direct ridge: RMSE **85.719**, MAE **18.360**, Spearman **0.192**
- two-part state: RMSE **80.041**, MAE **18.497**, Spearman **0.316**
- central supported-model envelope coverage: **2.7%**
- combined empirical outer-80 coverage: **61.2%**
- combined empirical outer-90 coverage: **93.0%**

Model-family spread is model-authority uncertainty, not an outcome interval. Position/model empirical absolute-residual bands remain separately governed ordinary outcome uncertainty.

## Aggregation governance

The compatible primitive is annual raw league-capacity Shapley marginal fantasy points:

`CAREER_FORWARD_RAW = phi_Y1 + phi_Y2 + phi_Y3 + phi_Y4 + phi_Y5 + phi_Y6 + phi_Y7 + TAIL_Y8_PLUS`

No discount or horizon weighting is applied. Current Intrinsic remains the separate discounted Y1-Y3 product lens; holistic career-forward Value consumes its **underlying annual raw** Y1-Y3 Shapley coordinates, not its scalar/display index. The #346 Y4-Y7 component remains unchanged; holistic Value consumes its annual raw authority coordinates, not the component display ruler.

## Uncertainty governance

Holistic model-authority low/high may be formed by arithmetic addition of governed Y1-Y3 annual raw Shapley coordinates, accepted #346 Y4-Y7 annual authority low/high, and terminal Y8+ supported-model low/high. This is a model-authority envelope, not a probabilistic confidence interval.

Ordinary uncertainty remains horizon-specific. No cumulative career standard deviation or cross-horizon covariance is authorized.

## Management disposition

The research boundary is resolved strongly enough for the next **shadow implementation** slice.

Proceed with:
1. frozen terminal coefficients/scalers/Duan factors/residual bands from artifact `11260487964`;
2. pure terminal Value consumer;
3. holistic raw aggregator over compatible annual Shapley coordinates;
4. current-cohort shadow materialization;
5. separate persistence/API from Current Intrinsic;
6. resource validation and bounded review.

Do not promote user-facing Long-Term Intrinsic until live-cohort coverage, semantic validation, persistence/API, resource acceptance and Management promotion are complete.

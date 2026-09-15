# FSFFL NEXT - Intrinsic Constitution / Frozen Shapley Test Plan

Research-only. Frozen before any new constitutional test output is inspected.

## Frozen candidate and governance

Keep unchanged: the PR #139 league-wide assignment game W; Shapley coalition semantics; 2048 fixed permutations for league-scale research cases; state-conditioned central production treatment; generic residual SD exclusion; 0.85 discount for isolation; B4 holding effects = zero; roster-neutrality; and all market / owner / transaction exclusions. Do not rescale, add an intercept, add a low-end floor or penalty, insert replacement surplus, change coalition weights, introduce another attribution axiom, change the old target, or fit to named players.

## Common synthetic design

Synthetic tests use input-defined production bands, not Shapley outputs or the old historical target. The base structural pool contains deliberately scarce elite production, ordinary starter production, replacement-useful but genuinely deployable production, weak fringe production, and zero production. The same frozen assignment game allocates legally deployable production. Monte Carlo tests use fixed seeds and 2048 permutations unless the game is small enough for exact Shapley.

For controlled career-right tests, current and future production/state paths are supplied as governed Forecast inputs. Value does not infer or reconstruct Forecast. Generic residual SD is varied only when means and state/path probabilities are held fixed.

## Constitutional mapping

### Principle 1 - Useful production has positive value
Interpretation: a genuinely useful replacement-level right must retain positive contribution even when substitutes exist; replacement is descriptive, not the score's zero point.
Synthetic test: compare elite, starter, replacement-useful, fringe, and zero rights in the same supply environment. Pass if replacement-useful Shapley > 0, zero right = 0, and weak fringe is lower than replacement-useful. Fail if replacement-useful becomes zero solely because it is substitutable.
Historical diagnostic: realized Shapley distribution among predeclared positive-production structural bands; useful non-elite rows should remain positive and bounded.
Failure ownership: Shapley/W if the structural game makes useful rights zero; Forecast is not implicated in realized tests.

### Principle 2 - Scarcity increases value
Interpretation: holding raw production fixed, lower substitutability must increase attribution without a manual position multiplier.
Synthetic tests: 1QB vs Superflex for the same QB; shallow vs deep WR/RB starts; FLEX off/on for the same eligible player; abundant vs reduced same-position alternative supply. Pass if the same right receives more Shapley when structurally scarcer in each applicable perturbation. Fail on systematic non-response or reversal.
Failure ownership: Shapley/W.

### Principle 3 - Elite separation matters disproportionately
Interpretation: scarce elite production should receive stronger structural significance than ordinary useful production; global convexity is not required.
Synthetic test: compare equal raw point increments applied in an ordinary-useful band and a scarce-elite band while holding the surrounding pool fixed. Also report elite/starter and elite/replacement-useful value ratios and shares. Pass if elite separation exceeds the corresponding linear raw-point separation in at least the scarcity-controlled elite fixture and remains structurally explainable. Fail if Shapley collapses to raw-point linearity or cannot distinguish scarce elite production.
Historical diagnostic: realized Shapley share and distribution of predeclared top production decile vs ordinary positive bands.
Failure ownership: Shapley/W.

### Principle 4 - Zero means no meaningful competitive right
Interpretation: zero belongs to no credible present/future useful production, not below-replacement status.
Synthetic tests: (a) zero current + zero future; (b) negligible current + negligible future; (c) useful current; (d) zero current + credible future governed production. Pass if (a)=0, (b) near 0 and below useful rights, (c)>0, and (d)>0. Fail if a future-useful right is zero or a no-use right receives material value.
Failure ownership: Shapley if attribution causes it; Forecast if future inputs themselves are wrong.

### Principle 5 - Future rights count
Interpretation: future value may enter through governed anticipated production and governed state/path probabilities; career-state labels are not the sole channel.
Synthetic tests: (a) hold state probabilities fixed and raise Y2/Y3 anticipated production; (b) hold anticipated central production fixed and improve state probabilities; (c) improve both. Pass if each legitimate improvement increases long-term Shapley, with the combined case at least as high as either isolated improvement. Fail if anticipated means cannot add value unless state labels change, or if Value independently reconstructs Forecast.
Failure ownership: Shapley integration if frozen inputs fail to transmit; Forecast remains a separate question about input accuracy.

### Principle 6 - Generic uncertainty does not count as upside
Interpretation: widening generic residual Forecast variance with governed means and states fixed must not manufacture option value.
Synthetic test: identical anticipated means/state probabilities with narrow vs wide generic residual SD. Pass if Shapley difference is numerically zero / immaterial under the frozen path. Fail on material positive uplift.
Failure ownership: Shapley integration.

### Principle 7 - League format changes scarcity endogenously
Interpretation: 1QB/SF, starter depth, FLEX, TE-premium normalized scoring, and eligibility change Intrinsic through W rather than manual multipliers.
Synthetic tests: format perturbations above plus TE normalized production and an eligibility toggle in an otherwise fixed game. Pass if all applicable directions are endogenous and no position multiplier is present. Fail if format rules do not propagate or a manual multiplier is required.
Failure ownership: W/Shapley.

### Principle 8 - Actual roster fit does not enter Intrinsic
Interpretation: franchise roster composition, lineup bottlenecks, team needs, strategy and owner identity are downstream.
Static dependency audit + invariant test: inspect candidate code path and run identical league-wide player supply with arbitrary franchise labels/context omitted/changed. Pass if coordinate is unchanged and candidate has no dependency on actual rosters/team utility/owner identity. Fail on any such dependency.
Failure ownership: architecture/leakage.

### Principle 9 - Roster-space opportunity cost does not reduce Intrinsic
Interpretation: B4 keeps bench/taxi/IR scarcity and hold/cut opportunity cost downstream.
Static dependency + synthetic invariant: same player/supply/scoring/starter structure with bench/taxi/IR capacity metadata changed only. Pass if Shapley is identical and no hold/cut term enters. Fail if universal Intrinsic changes solely from roster-space pressure.
Failure ownership: architecture/leakage.

### Principle 10 - Market willingness to pay does not define Intrinsic
Interpretation: Broad Market, League Market, trades, acceptance behavior and owner tendencies are absent from definition/fitting/calibration.
Static dependency audit. Pass if no market/trade/owner inputs enter W, Shapley, candidate selection or calibration. Fail on any such dependency.
Failure ownership: architecture/leakage.

## Cardinality audit

Report without using the old target as a ruler:
1. elite / ordinary starter / replacement-useful / fringe value levels, ratios and shares of total W;
2. bottom and middle positive production shares;
3. sensitivity to adding redundant supply at fixed test-player production;
4. sensitivity to league size and starter depth;
5. whether ordinary useful production stays positive but bounded;
6. whether elite contribution remains meaningfully scarce;
7. whether efficiency identity holds.

The cardinality audit is a constitutional coherence test, not a fitted calibration target. No scalar, intercept or tier coefficient may be adopted.

## Realized historical constitutional diagnostics

Use realized historical Shapley already computed under the frozen W where possible. Define descriptive production cohorts from realized input production, not Shapley results: zero/no-use, positive bottom quartile (replacement-useful descriptive low band), middle 50% ordinary useful, top quartile premium/elite, and top decile elite. Report distributions, position, near-zero fraction, relationship to production scarcity, and whether useful non-elite production remains positive/bounded. Developmental diagnostics use predeclared young/low-current-production definitions already frozen in prior research. The old marginal-surplus target is comparison-only: rank agreement, cardinal disagreement and semantic compression may be shown but never determine pass/fail.

## Track A conclusion rules

A1. SHAPLEY SATISFIES THE INTRINSIC CONSTITUTION AS A PROMISING CARDINAL CHALLENGER only if all ten principles pass, no leakage appears, cardinal allocations remain structurally coherent under perturbations, and no material unresolved cardinal pathology is demonstrated. This is research-only and does not authorize promotion.

A2. SHAPLEY RANKING/STRUCTURE IS SOUND BUT CARDINAL ATTRIBUTION IS NOT YET DEFENSIBLE if constitutional directionality/ordering is coherent but absolute allocation across tiers is unjustified or materially ambiguous.

A3. SHAPLEY FAILS THE INTRINSIC CONSTITUTION if a frozen test demonstrates systematic overvaluation of no-use/weak rights, zeroing of useful replacement-level contribution, failure of scarcity/elite separation/future-right transmission, or prohibited leakage.

A4. INSUFFICIENT EVIDENCE if the Constitution cannot be adjudicated without an unavailable independent competitive validation object and the internal invariants do not settle the question.

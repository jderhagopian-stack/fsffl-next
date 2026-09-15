# FSFFL NEXT - Forecast Low-End Career Calibration Protocol

Research-only. Frozen before any new low-end challenger output is inspected. This track calibrates Forecast to realized football/fantasy outcomes only. It must not use Shapley, Primitive A, the old Intrinsic target, market prices, owner behavior, transactions, or desired current-player ordering to fit/select a correction.

## Baseline mechanism audit to preserve

Governed multi-year Forecast separates conditional production persistence from survival/continuation. Career-state probabilities are Forecast-owned. Candidate explanatory inputs may include position, age, experience, prior production, prior usage, rookie status, production/usage bands and role/opportunity evidence where strict point-in-time history exists. Missing evidence must fail closed rather than be backfilled by Value.

## Predeclared cohort design

All cohort thresholds are estimated using training history only within each chronological fold where a threshold is needed.

1. Low-end source: bottom quartile of positive current-season production within position in training history; the corresponding training threshold is applied to the holdout season.
2. True developmental: low-end source, young at source (QB <=25; RB/WR/TE <=23), and later reaches at least the predeclared 'usable' future production state within the evaluated horizon.
3. Disappears: source player has no future panel row or zero realized future production at the evaluated horizon.
4. Depth-only: future row exists but remains in the training-derived depth state and never reaches usable-or-better within evaluated horizon.
5. Young low-production: low-end source and young by the age definition above.
6. Older fringe veteran: low-end source and aging (QB >31; RB/WR/TE >27).
7. Position groups: QB, RB, WR, TE.
8. Strong/weak role-opportunity evidence: use only if a governed historical PIT usage/opportunity field has adequate coverage before the holdout. If unavailable, report the stratification unavailable; do not synthesize a proxy after seeing outcomes.

State boundaries are estimated chronologically from training-only positive production, using the already-governed state construction. A missing future row is an observed transition to `out` whenever the horizon outcome is chronologically observable; it is not silently dropped.

## Baseline calibration metrics

For horizons H1 and H2 where strict PIT outcomes are observable, report:
- future production MAE and mean bias;
- multiclass career-state Brier score and log loss;
- survival / `out` Brier and reliability;
- predicted vs realized probability of reaching usable-or-better, starter-or-better, and premium-or-better;
- upward / stable / downward transition calibration;
- low-end anticipated-production calibration;
- false-positive developmental rate: predicted probability usable-or-better >=0.50 but realized state remains below usable / disappears;
- false-negative breakout rate: predicted probability usable-or-better <0.50 but realized state reaches usable-or-better;
- results by low-end, true-developmental, disappear, depth-only, age, position and chronological fold.

No named-player diagnostics are used to select or tune the challenger.

## Predeclared defect hypothesis

The first mechanism to test is censoring-induced false persistence in historical career-state transition estimation. In the frozen state-transition harness, transitions with no `(player_id, season+h)` row are skipped. Because disappearance is a legitimate realized `out` outcome, conditioning transition counts on future-row presence can understate `out` probability and redistribute probability mass to persistent/upward states, particularly for low-end sources.

This is a hypothesis to test, not an assumed conclusion. The audit must quantify missing-future-row frequency and compare baseline predicted out/survival/state probabilities with realized outcomes before any correction is judged.

## Smallest bounded challenger

If the audit confirms the censoring mechanism, test exactly one correction:
- when a source row is chronologically eligible for horizon h and no future row exists, record the destination state as `out` instead of skipping that transition;
- when the row exists, preserve the existing state assignment;
- preserve all state definitions, age bands, smoothing, fallback hierarchy, Forecast inputs and Value logic;
- do not add youth bonuses, market priors, Value feedback, named-player exceptions or generic fringe penalties.

No broader Forecast redesign is authorized in this track.

## Challenger acceptance guardrails

A bounded correction is 'promising' only if all material guardrails hold under strict chronological PIT validation:
1. low-end multiclass state Brier improves by at least 10% relative OR low-end survival/out Brier improves by at least 15% relative;
2. overall multiclass state Brier degrades by no more than 2% relative;
3. true-developmental usable-or-better recall degrades by no more than 3 percentage points;
4. no position's low-end state Brier degrades by more than 5% relative;
5. at least two-thirds of scored chronological folds are non-worse on low-end state Brier;
6. breakout false-negative rate does not worsen materially (>3 percentage points) while false-positive developmental rate should improve or remain non-worse.

These are predeclared research guardrails to prevent a post-result rescue. They are not production promotion thresholds.

## Downstream Value diagnostic

Only after a correction is frozen and judged on Forecast evidence may its corrected career-state probabilities / anticipated path be passed through the frozen Shapley coordinate as a diagnostic. This diagnostic may quantify whether the known false low-end future uplift falls, but it may not be used to fit, select or retune the Forecast correction.

## Track B conclusion rules

B1. IDENTIFIED FORECAST DEFECT + PROMISING BOUNDED CORRECTION only if the censoring or another specifically audited upstream defect is demonstrated and the smallest correction satisfies the guardrails without erasing legitimate developmental upside.

B2. FORECAST DEFECT CONFIRMED BUT NO CURRENT CORRECTION IS PROMOTABLE if the source of optimism is demonstrated but the bounded correction violates material guardrails or damages legitimate development prediction.

B3. CURRENT LOW-END ERROR IS MOSTLY EVIDENCE LIMITATION / IRREDUCIBLE UNCERTAINTY only if strict PIT evidence cannot distinguish likely breakout from disappearance well enough to support a governed correction.

B4. INSUFFICIENT EVIDENCE TO IDENTIFY THE FORECAST DEFECT if the audit cannot identify a specific causal calibration defect. Do not manufacture a correction.

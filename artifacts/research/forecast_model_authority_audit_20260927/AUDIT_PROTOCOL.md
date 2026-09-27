# Symmetric Forecast Model Authority Audit Protocol

Date: 2026-09-27  
State: **FROZEN BEFORE NEW AUDIT SCORING / RESEARCH ONLY**

## Authority

This audit implements the canonical 2026-09-27 Research correction: **no Forecast model receives scientific privilege because it is incumbent, later, selected, deployed, or operationally cheaper to keep.**

Production Forecast, production H3, Intrinsic, provider authority, and deployed runtime are unchanged.

## Questions

1. What serious Forecast candidates are durably recoverable without post-result tuning?
2. Which can be compared on the same point-in-time rows and target semantics?
3. On those common coordinates, which candidates are best-supported, tied, or genuinely uncomparable by horizon / position / career stage?
4. Does the historical candidate universe span enough substantively different model families to support Forecast authority?
5. If not, what **bounded, predeclared** new-family challenge is justified?
6. Does the prior joint-vs-separate injury result change when scientific authority is interpreted symmetrically rather than with a replacement tax?

## Symmetric scientific rule

For any common comparison:
- use the same evaluation rows and realized target;
- score every candidate with the same metric definition;
- report pairwise differences with chronology/player-cluster uncertainty where support permits;
- retain absolute safety / leakage / calibration gates;
- do **not** require a challenger to beat another candidate by an arbitrary switching margin;
- do **not** convert an uncertain difference into incumbent authority;
- if evidence is practically indistinguishable, record a tie;
- complexity / operational cost may break a genuine scientific tie only after predictive evidence is classified, and may not rewrite that classification.

No candidate is called “control” in the authority decision. Historical names such as B0 or P0 remain provenance labels only.

## Stage 1 — candidate reconstruction ledger

Inventory every serious durable/recoverable Forecast representation, including:
- empirical / baseline controls;
- persistence-first B1 / M2;
- integrated I1;
- integrated I2;
- Phase-3/4 baseline, A1, A2, B, C, D and serious frozen combinations / routing;
- routed B2a / R1 / R2 / H2 where exact evidence is recoverable;
- redeveloped D0 / D1 and the frozen position × career routing;
- M1a continuous conditional-production representation;
- the frozen prior-two consistency extension;
- serious later cell-specific conditional-production challengers that reached durable chronological validation;
- injury availability / return-timing severity, separate learned models, and the joint shared-latent architecture as a separate current-season availability coordinate.

For each candidate persist:
- target semantics;
- horizons;
- PIT feature families;
- model family / decomposition;
- fixed or historically selected hyperparameters;
- original training / validation chronology;
- durable row-level evidence available;
- exact common-replay feasibility;
- known target-semantic mismatch;
- whether the candidate is whole-Forecast, component-only, or cell-specific.

## Common evaluation coordinates

A single fake “universal” target is prohibited when historical studies used materially different target semantics.

Use three explicit coordinates:

### F — factual-state coordinate
Where factual roster/attachment evidence is recoverable, evaluate six-state / persistence probabilities against the integrated factual-state contract. Candidates with compatible six-state probabilities may be rescored on the same factual rows even if their original study used a weaker absence-as-out label, provided no refit or target-dependent transformation occurs.

### P — production-row coordinate
For common source-season / player / position / literal horizon rows, evaluate:
- realized target fantasy points, with no target production row represented as zero;
- the source-cutoff state boundaries used by the candidate generation only when converting target points to state for probability scoring;
- expected points, bias, RMSE, MAE, rank;
- CRPS / distributional quality when a candidate exposes a coherent predictive distribution.

This coordinate is the primary bridge between integrated / Phase-3/4 / D0-D1 generations because expected fantasy points have a common realized quantity even when attachment semantics differ.

### A — injury-availability coordinate
Use the already-governed 4,793 injury episodes and the exact prior OOT predictions. Do not refit or tune the separate or joint injury systems during reinterpretation.

## Exact replay / join rules

- Join candidates only on explicit durable keys: source season, player ID, position, horizon (or injury episode ID for A).
- Never infer player identity from row order.
- Metadata-only replay changes are allowed solely to export keys or already-computed probability vectors that existed in memory in the frozen code path.
- Every such replay must reproduce the prior aggregate evidence within frozen numerical tolerances before entering the authority audit.
- If exact prediction recovery is not possible, classify the candidate as **recoverable summary only / not head-to-head comparable** rather than substituting a neighboring model.

## Metrics

Where applicable and supported:
- expected-points MAE, RMSE, bias, Pearson/Spearman;
- persistence Brier / log loss / calibration gap;
- six-state Brier / log loss;
- useful / starter / premium threshold Brier;
- CRPS or equivalent proper distribution score;
- conditional-active production MAE / bias;
- top-10% / top-5% source magnitude performance;
- lower-tail / collapse / role-loss stress;
- position;
- age / career stage;
- literal horizon;
- source-era / origin stability;
- coverage / fallback path;
- empirical uncertainty for pairwise differences.

Metrics unavailable by model construction remain explicitly unavailable rather than imputed.

## Practical-materiality classification

For pairwise metric differences:
- **supported difference**: direction is stable across chronology and the clustered interval excludes zero, or a predeclared absolute calibration/safety violation is materially different;
- **directional but uncertain**: point estimate has a direction but uncertainty includes zero or chronology is thin;
- **practical tie**: central differences are small across the principal target and no candidate shows a material safety/calibration advantage;
- **tradeoff**: different candidates lead on different primary dimensions without a dominant safety-calibrated representation;
- **uncomparable**: exact common rows / target semantics / predictive outputs are not recoverable.

No “challenger must improve by X%” rule is used.

## Stage 3 breadth sufficiency rubric — frozen before audit result

The historical family set is considered sufficient only if, on a common PIT coordinate, it contains defensible whole-Forecast candidates spanning all of:
1. at least one decomposed generalized-linear / state model;
2. at least one substantively nonlinear learner capable of learning interactions without hand-authored hinges;
3. at least one smooth nonlinear / trajectory representation for continuous magnitude or age effects;
4. a coherent survival / persistence representation;
5. a predictive distribution or state-mixture representation that can be scored with a proper distributional rule.

A family counts only if it has chronology-preserving OOT evidence on the common coordinate; a diagnostic or one-cell experiment does not fill the whole-Forecast family slot.

In addition, even if nominal family coverage exists, a bounded new-family challenge is required if a replicated material residual structure remains unresolved (for example stable nonlinear magnitude compression) and no prior whole-Forecast candidate can represent it.

This breadth rule is architectural, not based on which named candidate wins.

## Bounded new-family slate if required

If Stage 3 says prior breadth is insufficient, test exactly these two additional whole-Forecast families on the production-row coordinate. No other family may be added in this audit.

### N1 — nonlinear tree state + conditional magnitude
- direct six-state HistGradientBoostingClassifier;
- state-conditioned HistGradientBoostingRegressor for positive-state magnitude;
- fixed PIT feature set from the governed redeveloped panel;
- fixed hyperparameters before scoring: learning_rate 0.05, max_iter 180, max_leaf_nodes 15, min_samples_leaf 30, l2_regularization 3.0, random_state 20260927;
- no hyperparameter search.

### N2 — smooth spline two-part state + conditional magnitude
- logistic persistence plus conditional ordered-state logistic heads;
- continuous age / experience / log production / source percentile / prior-production / prior-two terms transformed by fixed cubic splines;
- conditional positive-state Ridge production using the same fixed spline basis plus future-state indicator;
- fixed spline knots = 5, degree = 3; logistic C = 0.25; Ridge alpha = 10.0;
- no hyperparameter search.

Both use only source-time information and the same frozen common evaluation rows. Any unsupported feature is represented with an explicit coverage flag / neutral value rather than future imputation.

## New-family chronology

For literal horizon h and outer source season T:
- training target must satisfy source_season + h <= T - 1;
- no future origin enters preprocessing, splines, category mapping, fitting, calibration, or uncertainty;
- score Y2 origins 2014-2023 and Y3 origins 2014-2022 where the governed common panel supports them;
- assess origin stability and position/career-stage safety;
- no current-player board or 2026 outcomes may select/tune the family.

Because many historical years have already been inspected in prior studies, this is **rolling comparative validation**, not a pristine untouched final holdout. Any genuinely future confirmation remains future work.

## Injury reinterpretation

Use exact existing OOT rows. Compare severity/status, separate HistGB, and joint architecture symmetrically on:
- endpoint return Brier;
- integrated return-time Brier;
- log loss;
- calibration;
- holdout and position stability;
- remaining-season availability;
- expected active weeks / downstream H1 availability quantity derivable without healthy-production assumptions;
- clustered/bootstrap uncertainty of pairwise differences.

The old frozen joint direct-comparison gate remains part of historical provenance but is not a scientific authority rule in this audit.

## Stage 4 downstream Intrinsic sandbox

Only after the best-supported / tied Forecast set is frozen. Research-only:
- expected trajectory changes;
- rank/value deltas;
- age/career-state curves;
- uncertainty propagation;
- material reversals.

It cannot tune Forecast and cannot alter production Intrinsic.

## Terminal outputs

Persist:
1. candidate authority ledger;
2. symmetric comparison matrix;
3. pairwise uncertainty / practical-materiality analysis;
4. explicit horizon × position best-supported / tied / uncomparable map;
5. injury symmetric reinterpretation;
6. breadth-sufficiency determination and, if required, bounded new-family results;
7. Research-only downstream sandbox only after the Forecast set is frozen;
8. reproducibility / provenance;
9. terminal state under OPERATING_PROTOCOL.md.

Production Forecast / H3 / Intrinsic remain unchanged unless Management separately authorizes a later implementation phase.

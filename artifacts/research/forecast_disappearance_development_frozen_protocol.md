# FSFFL NEXT — Forecast disappearance vs development frozen challenger protocol

Research only. Frozen before any C2/C3 chronological challenger result is generated or inspected.

## Phase 0 controls
- C0 BASELINE: frozen transition estimator that skips missing future rows.
- C1 HARD missing=OUT: every chronologically observable missing target row is OUT. Failed control only; never promotable.

## Eligible evidence after Phase 1 audit
Strict-PIT seasonal source coverage is 100% from 1999–2025 for fantasy production, games, pass attempts, carries, targets and receptions for QB/RB/WR/TE. No starts, snaps, snap share, routes or route participation are available in this source. Draft round/pick coverage is only about 46–56% by fantasy position and is excluded from challengers. Age/experience/position/current production state remain governed inputs. No market/roster/owner/Value inputs.

## Missing-row semantics
An eligible missing target row is evidence of no modeled fantasy-relevant production row at that horizon, not proof of permanent career death. Target-row present with explicit zero is distinct. A missing target followed by later historical return is an evaluation diagnostic only; later return never enters predictor features. Targets beyond available history are censored and excluded.

## C2 — soft disappearance / censoring-aware challenger
For each fold and horizon h=1,2, estimate the probability M of an eligible target row being missing from strictly prior evidence. Jeffreys smoothing Beta(0.5,0.5) is fixed. Use the first supported cell with n>=30 in this fixed hierarchy:
1. position + frozen age band + current governed production state + horizon;
2. position + current governed production state + horizon;
3. position + horizon.

Let B(s) be the frozen C0 state distribution conditional on present-row evidence. Construct pre-QB-override state probabilities as:
- P(out) = M + (1-M) * B(out)
- P(s) = (1-M) * B(s) for every non-out state.
Then apply the existing frozen QB meaningful-state override unchanged where it already applies. C2 does not alter anticipated-production means.

## C3 — role/opportunity-aware soft disappearance challenger
Use the same construction as C2, adding one direct PIT role band to the disappearance model only.

Frozen role metric by source season:
- QB: pass attempts / games;
- RB: (carries + targets) / games;
- WR: targets / games;
- TE: targets / games.
Games<=0 maps to zero opportunity. Within each source season and position, role band is WEAK below the contemporaneous median and ESTABLISHED at/above the median. This is a direct usage band, not a market or roster proxy.

Use the first supported cell with n>=30 in this fixed hierarchy:
1. position + frozen age band + current state + role band + horizon;
2. position + current state + role band + horizon;
3. C2 hierarchy in its frozen order.
Jeffreys Beta(0.5,0.5) smoothing is fixed. The same C0 conditional present-row state mix and frozen QB override are retained. C3 does not alter anticipated-production means.

## Frozen cohorts
- LOW-END: source production >0 and <= the position-specific 25th percentile estimated from seasons strictly before the fold cutoff, matching the prior study concept.
- TRUE-DEVELOPMENTAL: LOW-END + frozen YOUNG age band + realized target state usable-or-better. Evaluation label only.
- DISAPPEAR: target state out/missing for that horizon.
- DEPTH-ONLY: realized target state depth.
- YOUNG-LOW / PRIME-LOW / OLDER-FRINGE: LOW-END crossed with the frozen age-band rule.
- Position: QB/RB/WR/TE.
- Role: WEAK/ESTABLISHED using the frozen direct opportunity definition above; evaluated only for C3 diagnostics.
- TEMPORARY-ABSENCE-RETURN: target row missing but a later production row exists. Outcome diagnostic only; never a predictor.

## Frozen probability/diagnostic rules
- Useful states: usable/starter/premium/elite.
- Starter-or-better: starter/premium/elite.
- Premium-or-better: premium/elite.
- Developmental classification threshold for FP/FN and recall: predicted useful probability >=0.50.
- No stochastic fitting is used; random seed is N/A.
- Baseline production means remain frozen and are evaluated but not modified.

## Frozen promotion guardrails
A new challenger is promotable from research only if ALL apply:
A. LOW-END CALIBRATION: >=10% relative improvement in low-end multiclass State Brier OR >=15% relative improvement in low-end survival Brier vs C0.
B. TRUE-DEVELOPMENTAL PRESERVATION: recall drop vs C0 <=3 percentage points.
C. BREAKOUT FN CONTROL: low-end false-negative breakout rate increase vs C0 <=3 percentage points.
D. FALSE-POSITIVE IMPROVEMENT: low-end false-positive developmental rate decreases by >=10% relative vs C0.
E. POSITION SAFETY: no position-specific low-end State Brier worsens by >5% relative vs C0.
F. TEMPORAL CONSISTENCY: at least 2/3 of scored chronological folds are non-worse on low-end State Brier and no fold worsens by >20% relative.
G. OVERALL FORECAST SAFETY: overall multiclass State Brier worsens by <=2% relative vs C0.
H. LEAKAGE: zero Value, Shapley, market, transaction, owner, roster-fit, named-player or future-label predictor leakage.

## Frozen selection rule
C1 is never eligible. Prefer the simplest challenger satisfying every guardrail: C2 if C2 passes; otherwise C3 if C3 passes. Do not choose by the best single aggregate score. If neither passes, do not retune.

## Chronological validation
Preserve the prior fold/evaluation construction. Training evidence must satisfy target season < fold cutoff; evaluation uses h=1/h=2 realized outcomes. Report aggregate, position, age, role, temporary-return, and fold-level metrics: state Brier/log loss, survival Brier/out calibration, useful/starter/premium Briers, developmental recall, FP/FN, production MAE/bias, and reliability tables where support permits.

## Production-mean rule
C2/C3 do not alter anticipated-production means. Quantify production MAE/bias by horizon and low-end subgroup after state recalibration. If a separate mean defect remains, document it and stop before redesigning means.

## Downstream Value rule
Only an independently selected F1 Forecast challenger may be passed through frozen 2048-Shapley for a diagnostic. Shapley may never select or tune the Forecast challenger.
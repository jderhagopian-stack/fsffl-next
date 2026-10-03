# Player-Specific Multi-Season Trajectory Residual Research — PR #131

**Status:** research-only, non-authoritative. Production Forecast and Value behavior are unchanged. The accepted recursive uncertainty carry-forward remains research-only. Model B was not fitted. PR #131 remains a draft research branch.

## Question

The preceding Forecast studies showed that broad cohort state can improve multi-year path shape but cannot identify which individual players should retain more or less newly learned information. This cycle tested the narrower hypothesis that a player's own multi-season Forecast residual history contains point-in-time predictive information about deeper-horizon persistence.

The governing question was:

> Does a player's resolved history of outperforming or underperforming the Forecast help distinguish which individual players should preserve more of newly learned information in Years 2-3?

The primary gate was player-specific persistence, not aggregate path correlation or downstream Model A performance.

## Player-specific state

For every historical preseason fold, the research reconstructs resolved one-step Forecast residuals using only evidence that would have been available at that time:

`one-step residual = realized production - point-in-time Forecast for that season`

A single-season residual cannot activate player-specific state. A player must have at least **2 resolved prior residual seasons**.

For an eligible player, the model estimates the player's mean historical residual and shrinks it toward football cohorts using an empirical-Bayes reliability weight. Reliability rises when the player has more historical observations and when the player's residual history is more stable relative to the cross-player signal in the cohort. Sparse or volatile histories are shrunk more strongly.

The fallback hierarchy is:

1. position × career stage × production tier;
2. position × career stage;
3. position;
4. global.

A cohort prior may act independently only with at least **20 players** and **100 resolved residuals**. The Year-2/Year-3 translation from the shrunken player residual into a horizon adjustment uses only prior resolved applications, with a minimum **100 observations** before a narrower cell acts independently.

No market value, trade value, Team Utility, owner behavior, roster need, downstream Value output, QB bonus, elite-player override, or universal persistence multiplier is used.

## Chronology and provenance

Every player residual is resolved before the preseason cutoff in which it is used. Every cohort prior, empirical-Bayes variance estimate, and horizon translation coefficient is fitted from evidence resolved before that fold. There is no through-2025 back-application, current-holdout tuning, or future leakage.

The historical player universe and career-transition reconstruction rules are unchanged from the preceding PR #131 research. The run continued to use 14,876 career-transition rows spanning 1999-2024, with supported preseason research folds determined by the same prehistory and full-horizon rules.

## Frozen direct gate

The acceptance rule was declared before the empirical result was read. Relative to the current Forecast baseline, the challenger had to:

- improve legacy player-specific persistence Pearson correlation by at least **+0.05**;
- reduce legacy persistence MAE;
- improve stable-denominator persistence rank correlation by at least **+0.05**;
- not reduce far-horizon revision correlation;
- not reduce path-slope correlation;
- not worsen path-slope MAE;
- keep near-horizon revision correlation within 0.01;
- keep cumulative MAE within 1%;
- keep Year-2 and Year-3 MAE within 1%; and
- preserve aging-RB persistence, slope, and cumulative error within a 2% guardrail.

The stable-denominator persistence diagnostic requires both the modeled near revision and subsequently needed near revision to have absolute magnitude of at least 10 points. This avoids allowing unstable division by near-zero movements to determine the research conclusion, while the legacy all-finite metric remains reported for continuity.

## Primary persistence result — FAIL

The challenger did **not** improve the target it was designed to repair.

| Persistence target | Baseline | Player residual | Result |
|---|---:|---:|---|
| Legacy Pearson correlation | ~0.000 | ~0.000 | no improvement |
| Legacy persistence MAE | 109.005 | 110.856 | worse |
| Stable-denominator Pearson | 0.029 | 0.028 | slightly worse |
| Stable-denominator Spearman | 0.107 | 0.107 | no improvement |
| Stable-denominator MAE | 0.926 | 1.001 | worse |

The stable persistence quantiles also failed to show stronger high-versus-low discrimination. Under the baseline, the mean subsequently needed persistence rises from **0.523** in the lowest modeled quartile to **0.736** in the highest, a gap of **0.213**. Under the player-residual challenger, the corresponding needed means are **0.567** and **0.774**, a gap of **0.207**. The model therefore did not become better at sorting players into genuinely high- versus low-persistence trajectories.

This is the decisive result. Multi-season average player residual is not the missing player-specific persistence state.

## Other direct Forecast results

The failed persistence result is not equivalent to saying the player history is useless. The same state improves several **level-accuracy** targets:

| Metric | Baseline | Player residual | Change |
|---|---:|---:|---:|
| Far revision correlation | 0.396 | 0.417 | better |
| Path-slope correlation | 0.135 | 0.172 | better |
| Path-slope MAE | 33.064 | 33.219 | slightly worse |
| Cumulative common-path MAE | 67.398 | 66.066 | better |
| Year-1 MAE | 33.774 | 33.774 | unchanged by design |
| Year-2 MAE | 36.979 | 36.014 | better |
| Year-3 MAE | 35.557 | 34.773 | better |
| Near / far nominal-80% coverage | 75.6% / 67.7% | 75.6% / 68.5% | modest far improvement |

Survival Brier score is unchanged at **0.18162** because this challenger changes the mean trajectory only and does not alter Forecast survival mechanics.

This creates an important distinction: **persistent player-level Forecast bias appears useful for correcting multi-year production levels, but it does not identify how a new Forecast revision should persist across horizons.**

## Evidence-length diagnostics

Longer histories did not solve the persistence problem.

- **2-3 residual seasons:** cumulative MAE improves from 66.54 to 65.80, but stable persistence MAE worsens from 0.912 to 0.959.
- **4-5 residual seasons:** cumulative MAE improves from 64.69 to 63.50, but persistence MAE worsens from 0.798 to 0.889.
- **6+ residual seasons:** cumulative MAE improves materially from 78.02 to 73.36, while persistence Pearson falls from 0.069 to 0.009 and persistence MAE worsens from 0.886 to 1.104.

Therefore the failure is not simply insufficient player-history length. More historical residual observations strengthen the evidence that a player's average level bias is useful, but they do not make that bias a reliable persistence-ranking signal.

## Stable signal versus volatility

Diagnostic residual-state groupings reinforce the same distinction.

### Stable negative residuals

This is the most interesting narrow pocket. For only about 130 path observations, stable-denominator persistence Pearson improves from **0.593 to 0.704** and persistence MAE improves from **0.265 to 0.257**. Cumulative MAE also improves from **24.26 to 22.41**.

This suggests that repeated negative Forecast residuals may contain some genuine player-specific information. But the sample is too narrow, and rank correlation does not improve consistently enough, to justify a special decline rule or promotion.

### Stable positive residuals

The much larger stable-positive group behaves very differently. Cumulative MAE improves from **103.35 to 97.47**, but persistence MAE worsens materially from **1.015 to 1.344**. Persistence correlation remains near zero.

Repeated positive Forecast misses therefore look useful as a level correction without establishing that future revisions should persist more strongly.

### One-year spikes and collapses

A one-year spike shows a modest Pearson persistence improvement from roughly **-0.039 to 0.085** and a small MAE improvement from **1.083 to 1.056**, but rank correlation does not improve. One-year collapses show slightly worse persistence calibration despite somewhat better cumulative level accuracy. These pockets do not support an automatic breakout/collapse persistence rule.

### Volatile histories

Volatile mixed histories improve cumulative level accuracy slightly but do not improve persistence discrimination. The empirical shrinkage therefore correctly prevents volatility from automatically being interpreted as persistent signal, but volatility alone is not the missing discriminator.

## Position and career-stage stability

The level correction is broad but persistence degradation is also broad.

- **QB:** far revision correlation 0.385 → 0.420; cumulative MAE 142.98 → 136.19; persistence MAE worsens materially.
- **RB:** cumulative MAE 61.01 → 60.76, but slope MAE and persistence MAE worsen.
- **WR:** far revision correlation 0.376 → 0.409 and cumulative MAE 61.04 → 60.28, but slope MAE and persistence MAE worsen.
- **TE:** small improvements in far correlation, slope MAE, and cumulative error, but persistence MAE worsens.

Prime-career players are the one broad career-stage group where legacy persistence MAE modestly improves, but the aggregate and robust rank gates still fail. Veteran level accuracy improves substantially while veteran persistence remains unstable.

## Elite-QB test

The elite-QB result is useful but not sufficient:

| Elite-QB target | Baseline | Player residual |
|---|---:|---:|
| Near revision correlation | 0.458 | 0.481 |
| Far revision correlation | 0.279 | 0.356 |
| Slope correlation | 0.102 | 0.195 |
| Slope MAE | 96.553 | 91.671 |
| Cumulative MAE | 197.632 | 184.622 |
| Persistence correlation | 0.002 | -0.011 |
| Persistence MAE | 2.315 | 2.661 |
| Far nominal-80% coverage | 59.8% | 65.0% |

Thus the player's multi-season residual history materially improves elite-QB **level and path-shape accuracy**, but makes the explicit persistence target worse. There is still no basis for a QB premium or manual elite persistence override.

With the separately accepted research-only uncertainty carry-forward, elite-QB far-horizon nominal-80% coverage reaches **80.9%**. That variance result remains independent of this failed mean-path persistence challenger.

## Young breakout WR test

For young breakout WRs:

- far revision correlation declines from **0.344 to 0.307**;
- slope correlation improves from **0.044 to 0.064**;
- slope MAE is essentially flat/slightly better, **41.893 to 41.838**;
- cumulative MAE improves slightly, **76.142 to 75.830**;
- persistence correlation becomes less negative, **-0.192 to -0.108**, but remains poor;
- persistence MAE is effectively flat/slightly worse, **2.024 to 2.031**.

The model therefore does not reliably separate sustained young-WR development from noisy breakout behavior. It should not be used to amplify young breakouts.

## Young-TE test

Young TEs are nearly neutral on level/path correlation, with a small cumulative MAE improvement (**42.789 to 42.509**) but materially worse persistence MAE (**5.522 to 6.520**). There is no evidence for a special young-TE persistence treatment.

## Aging-RB guardrail

Aging RBs expose why this challenger must be rejected despite some aggregate level gains:

- far revision correlation improves **0.368 to 0.391**;
- slope correlation improves **0.219 to 0.243**;
- slope MAE worsens modestly **23.567 to 23.713**;
- cumulative MAE improves **46.805 to 46.541**;
- persistence correlation remains approximately zero;
- persistence MAE worsens materially **3.346 to 4.485**.

The frozen aging-RB persistence guardrail therefore fails. The research may not improve elite-QB or general level forecasts by breaking an already reasonably calibrated aging-RB persistence behavior.

## Uncertainty remains a separate accepted research finding

The player-residual mean challenger with baseline uncertainty moves far-horizon coverage only from 67.7% to 68.5%. Combining it with the independently validated recursive uncertainty carry-forward raises far coverage to **83.0%**.

Subgroup far coverage under player-residual mean + repaired uncertainty is approximately:

- elite QB: **80.9%**;
- young breakout WR: **80.6%**;
- young TE: **80.1%**;
- aging RB: **89.0%**.

This confirms the prior uncertainty result. It does **not** rescue the failed mean-path persistence challenger, and the uncertainty repair remains research-only.

## Model A retest

**Not run.**

The player-specific residual challenger failed the direct Forecast persistence gate and the aging-RB guardrail. Under the predeclared research contract, downstream Model A performance cannot be used to rescue a failed Forecast challenger.

The canonical Model A state therefore remains unchanged:

- context-valid replacement: `marginal_lineup_opportunity`;
- Model A MAE: 20.307 vs affine 26.968;
- relative improvement: ~24.7%;
- SF/1QB scarcity: PASS;
- uncertainty: PASS;
- market independence: PASS;
- elite-QB longevity: FAIL;
- expected appreciation/decline: FAIL;
- economic usefulness: 4/6;
- production promotion gate: NOT CLEARED.

## Accepted / rejected findings

### Accepted as research evidence

1. Multi-season player-specific Forecast residual history contains useful information about a player's future **production level** beyond the current recursive cohort mean.
2. Empirical-Bayes shrinkage is a defensible transparent way to prevent sparse/noisy player histories from acting as unsupported overrides.
3. The effect is visible in better Year-2, Year-3, cumulative, and elite-QB level error.
4. The previously accepted recursive uncertainty carry-forward remains independently supported.

### Rejected as a Forecast mean-path challenger

Using the player's historical **average residual level** as the personal trajectory state does not improve individual revision-persistence ranking. It worsens persistence MAE overall and for key guardrail groups. This formulation is therefore rejected and is not eligible for production or Model A retesting.

## Narrowest remaining Forecast cause

The research has now separated two different player-specific phenomena:

- **persistent level residual:** a player can repeatedly score above/below what the cohort Forecast expects; this is useful for level correction;
- **persistence of new information:** whether a *change* in that player's Forecast should carry into deeper horizons; average residual level does not predict this well.

The narrowest remaining Forecast-owned hypothesis is therefore **within-player trajectory innovation dynamics**, not another level adjustment.

The next justified study would test whether the *change in* a player's residual state is persistent: residual slope/acceleration, repeated same-sign residual innovations, volatility-adjusted changes, and autocorrelation of residual innovations after first removing any stable player-level bias. That study should ask whether a player's recent Forecast innovations—not the player's average historical miss—predict which revisions persist into Years 2-3.

This remains a Forecast question. Forecast therefore still has a material unresolved player-state defect, and the residual is **not yet cleanly assignable to Value**.

## Model B and production recommendation

**Model B remains blocked.** No nonlinear Value challenger should be fitted while direct player-specific Forecast persistence remains unresolved.

**Production recommendation: no change.** Do not promote this mean challenger, do not promote the recursive uncertainty repair in this cycle, do not alter production Forecast or Value, and do not merge PR #131 automatically.

## Reproducibility

Successful research workflow: `34724290153`  
Artifact: `10307760543`  
Artifact SHA256: `3748c331105a163fc3a2ba9b4fc8439811e623a27e4258b06368eeba31f2779c`  
Repository test suite: **1,153 passed, 2 warnings**.

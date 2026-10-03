# Within-Player Trajectory Innovation Dynamics — PR #131

**Status:** research-only, non-authoritative. Production Forecast and Value behavior are unchanged. The recursive uncertainty carry-forward repair remains research-only. Model B was not fitted. PR #131 remains draft and unmerged.

## Executive conclusion

This cycle did **not** find a reproducible player-specific innovation signal strong enough to justify additional mean-path Forecast complexity.

After removing stable player-level residual bias, transparent within-player innovation features slightly improved several path-shape and level metrics, but they did not improve the central target: identifying which individual Forecast revisions should persist more or less into deeper horizons.

The predeclared direct Forecast gate therefore **failed**, Model A was **not rerun**, and no production behavior changed.

The accumulated PR #131 Forecast evidence now supports a different conclusion than the one that motivated the earlier persistence work: the remaining individual persistence variation is not presently identifiable as a stable point-estimate signal from the governed historical evidence. It should primarily be represented as **Forecast uncertainty**, not chased with another adjacent persistence multiplier or increasingly narrow state rule.

This does **not** mean Forecast is perfect. It means the unresolved error is now sufficiently characterized and bounded that it should no longer automatically block a separate Value-residual investigation. A future production review may separately consider the validated stable player-level residual correction and the validated recursive uncertainty carry-forward repair; neither is promoted by this report.

## Research question

The test was:

> After removing a player's stable tendency to run above or below the cohort Forecast, do changes in that player's residual state predict how much of a newly learned Forecast revision should persist into Years 2-3?

This intentionally separates two concepts:

1. **Stable player-level residual:** a player repeatedly produces above or below cohort expectation.
2. **Within-player innovation:** the player's residual has recently changed relative to his own prior baseline.

The prior player-residual study found real evidence for the first concept as a production-level correction, but not as a persistence-ranking signal. This cycle tested the second concept directly.

## Point-in-time innovation-state definition

For historical preseason fold `T`, only residual outcomes fully resolved before that cutoff are available.

A resolved one-step residual is:

`realized next-season production - point-in-time cohort Forecast for that season`

A player requires at least **3 resolved residual seasons** before an innovation state can act:

- earlier resolved residuals establish the player's stable personal residual baseline;
- the latest resolved residual is compared with that prior baseline;
- the difference is the latest residual innovation.

This prevents stable level bias from masquerading as momentum and prevents one historical residual from defining a player-specific dynamic state.

The following transparent PIT-safe features were measured:

- latest residual innovation;
- innovation relative to the player's historical residual volatility;
- innovation slope;
- innovation acceleration/deceleration;
- innovation autocorrelation;
- consecutive same-sign innovations;
- positive/negative reversals;
- positive/negative shocks;
- positive/negative one-off innovations;
- repeated positive/negative sequences;
- player innovation volatility relative to broader residual variance.

No market value, trade value, Team Utility, owner behavior, roster need, Value output, manual archetype label, injury history, QB premium, or elite-player override entered the fit.

## Predeclared evidence and acceptance rules

The following rules were fixed before final holdout results were read:

- minimum player residual history: **3 resolved seasons**;
- stable persistence denominator move floor: **10 fantasy points**;
- large volatility-adjusted innovation threshold: **1.0 player-history SD**;
- independent narrow hierarchy cell floor: **100 resolved persistence observations**;
- material persistence-correlation/rank improvement: **+0.05**;
- Year-2, Year-3, cumulative, and other adjacent level/path tolerance where applicable: **1%**;
- aging-RB guardrail tolerance: **2%**.

The persistence correction hierarchy was:

`global -> position -> position × career stage -> position × career stage × innovation state -> position × career stage × production tier × innovation state × volatility`

Narrow cells could act independently only when the sample floor was satisfied and empirical between-cell variance supported nonzero reliability. Otherwise they shrank toward the appropriate parent.

For fold `T`, fitted persistence evidence was restricted to historical path pairs whose far outcome was already resolved before the fold cutoff. There is no through-2025 back-application, current-holdout tuning, or future leakage.

## Primary persistence result

The innovation challenger failed the primary target.

| Persistence metric | Current Forecast | Innovation dynamics | Result |
|---|---:|---:|---|
| Legacy Pearson | -0.000 | 0.000 | No material gain |
| Legacy MAE | 109.005 | 109.558 | Worse |
| Stable-denominator Pearson | 0.029 | 0.024 | Worse |
| Stable-denominator Spearman | 0.107 | 0.116 | +0.009; below +0.05 gate |
| Stable-denominator MAE | 0.926 | 0.951 | Worse |
| High-minus-low needed-persistence gap | 0.213 | 0.187 | Worse discrimination |

Modeled persistence quartiles also remained poorly calibrated. Under the innovation challenger, mean needed persistence by modeled quartile was approximately **0.526 / 0.733 / 0.803 / 0.714**. The highest modeled-persistence quartile did not have the highest realized needed persistence. That is incompatible with a reliable player-specific ranking mechanism.

The direct innovation gate therefore **FAILS**.

## Feature-level signal test

The raw PIT innovation features themselves show essentially no stable linear or rank signal for the needed persistence correction across 2,078 eligible resolved applications:

| Feature | Pearson | Spearman |
|---|---:|---:|
| Latest innovation | -0.007 | 0.009 |
| Volatility-adjusted innovation | 0.007 | 0.015 |
| Innovation slope | -0.011 | 0.013 |
| Innovation acceleration | -0.006 | 0.018 |
| Innovation autocorrelation | 0.001 | -0.010 |
| Signed same-sign count | -0.004 | 0.021 |
| Volatility ratio | 0.014 | 0.005 |

This is important because it reduces the likelihood that the failed hierarchical correction merely chose the wrong transformation. The underlying transparent candidate signals are themselves weak for individual persistence.

## Direct Forecast comparison

Innovation dynamics do contain some useful path information, but not enough to justify the persistence mean adjustment.

| Variant | Far revision corr | Slope corr | Slope MAE | Cumulative MAE | Year-2 MAE | Year-3 MAE | Far raw 80% coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current Forecast | 0.396 | 0.135 | 33.064 | 67.398 | 36.979 | 35.557 | 67.7% |
| Hierarchical trajectory state | 0.545 | 0.437 | 32.886 | 67.721 | 37.167 | 37.990 | 67.4% |
| Player average residual | 0.417 | 0.172 | 33.219 | **66.066** | **36.014** | **34.773** | 68.5% |
| Innovation dynamics | 0.406 | 0.150 | **32.834** | 67.278 | 36.853 | 35.557 | 67.7% |
| Stable level + innovation | **0.421** | **0.182** | 33.080 | 66.098 | **36.006** | 34.773 | 68.1% |
| Innovation + repaired uncertainty | 0.406 | 0.150 | 32.834 | 67.278 | 36.853 | 35.557 | **83.3%** |

The pattern across challengers is now consistent:

- cohort/hierarchical state can improve broad path shape substantially but not individual persistence discrimination;
- stable player-level residual history improves deeper **level accuracy**;
- innovation dynamics modestly improve path shape but do not identify player-specific persistence;
- combining stable level and innovation provides only a small additional path-shape gain and does not establish independent persistence value;
- recursive uncertainty carry-forward repairs deeper-horizon coverage without changing means.

Therefore stable player-level bias and innovation should **not** be combined into an authoritative mean model merely because their aggregate path metrics are complementary.

## History length, volatility, and repeated innovations

More player history does not reveal a strong hidden persistence signal.

Stable-denominator persistence Pearson by innovation-history band under the challenger was approximately:

- 3-4 residual seasons: **-0.023**;
- 5-6: **-0.002**;
- 7+: **0.069**.

Longer history improves some path-shape diagnostics but does not produce a robust player-level persistence estimator.

Volatility also behaves more like an uncertainty descriptor than a reliable mean-persistence predictor. Low-volatility histories have better persistence MAE (**0.865**) than high-volatility histories (**0.981**), but neither group has useful Pearson discrimination (approximately **-0.022** and **0.025**, respectively). This supports carrying uncertainty rather than imposing a stronger deterministic persistence correction.

Repeated same-sign innovations show some descriptive separation:

- 0-1 same-sign run: Pearson **0.019**, Spearman **0.101**, MAE **0.971**;
- 2-run: Pearson **0.063**, Spearman **0.203**, MAE **0.779**;
- 3+ run: Pearson **0.088**, Spearman **0.218**, MAE **1.015**.

The lack of monotonic MAE improvement, particularly the deterioration for 3+ runs, prevents a defensible rule such as “more consecutive innovations should always receive more persistence.”

The strongest descriptive pocket was repeated negative innovation: stable-denominator Pearson **0.084**, Spearman **0.274**, MAE **0.752**. That is useful research evidence but is not strong or broad enough to justify a special decline rule, especially given the predeclared no-post-hoc-special-case guardrail.

## Key football subgroups

### Elite QBs

Innovation dynamics improve several elite-QB path metrics:

- far revision correlation: **0.279 -> 0.291**;
- slope correlation: **0.102 -> 0.142**;
- slope MAE: **96.553 -> 94.165**;
- cumulative MAE: **197.632 -> 195.029**.

But the central persistence behavior worsens:

- persistence correlation: **0.002 -> -0.008**;
- persistence MAE: **2.315 -> 2.536**.

The stable player-level residual correction remains much more useful for elite-QB **level/path accuracy** than innovation persistence. The combined level+innovation diagnostic further improves slope/cumulative level metrics but still does not establish reliable individual persistence. There is therefore no evidence-based QB persistence bonus or elite override.

### Young breakout WRs

Innovation dynamics make only small changes:

- far correlation: **0.344 -> 0.353**;
- slope MAE: **41.893 -> 41.775**;
- cumulative MAE: **76.142 -> 75.803**;
- persistence correlation remains about **-0.19**;
- persistence MAE is essentially unchanged around **2.02**.

The model still cannot reliably distinguish sustained development from a one-year/noisy breakout through innovation persistence alone.

### Young TEs

Results are effectively flat:

- far correlation: **0.467 -> 0.465**;
- slope MAE: **20.614 -> 20.576**;
- cumulative MAE: **42.789 -> 42.746**;
- persistence correlation remains approximately **-0.028**;
- persistence MAE remains approximately **5.52**.

No durable dynamic-persistence signal is established.

### Aging RB guardrail

The aging-RB guardrail fails:

- far correlation: **0.368 -> 0.371**;
- slope correlation: **0.219 -> 0.235**;
- slope MAE: **23.567 -> 23.527**;
- cumulative MAE: **46.804 -> 46.977**;
- persistence correlation: **-0.003 -> -0.005**;
- persistence MAE: **3.346 -> 3.445**, roughly a **3.0%** deterioration, exceeding the predeclared 2% guardrail;
- far-horizon directional accuracy is unchanged at about **57.6%**.

That independently prevents acceptance even apart from the failed overall persistence gate.

## Stable level bias remains a separate finding

This cycle does not invalidate the prior player-level residual result.

The stable player-level residual challenger still materially improves deeper level accuracy relative to the current Forecast:

- Year-2 MAE: **36.979 -> 36.014**;
- Year-3 MAE: **35.557 -> 34.773**;
- cumulative MAE: **67.398 -> 66.066**.

Its value is therefore best characterized as a **player-level production correction**, not as evidence that the newest Forecast revision should persist more strongly.

The combined stable-level + innovation diagnostic produces:

- far correlation **0.421**;
- slope correlation **0.182**;
- cumulative MAE **66.098**;
- Year-2 MAE **36.006**;
- Year-3 MAE **34.773**.

That is only a small incremental path-shape change over the level correction alone, while persistence metrics remain poor. The two components are therefore **not approved as a combined authoritative mean architecture** by this research cycle.

## Uncertainty remains separate and better supported

The recursive variance carry-forward repair remains the cleanest deeper-horizon Forecast finding in the entire persistence sequence.

With the innovation mean unchanged, far-horizon nominal-80% coverage moves from **67.7% to 83.3%** when the already validated research-only recursive uncertainty repair is applied.

This does not make the failed innovation mean challenger acceptable. It does, however, show that much of the unresolved deeper-horizon player-specific variation can be represented honestly as uncertainty rather than converted into unsupported point-estimate persistence.

The uncertainty repair remains research-only and is **not promoted here**.

## Evidence-ceiling decision

### Have we found a reproducible player-specific persistence signal strong enough to justify further mean-path complexity?

**No.**

Across the sequence of transparent PIT-safe tests, the research has now evaluated:

- universal update shrink/gain;
- recursive state/percentile persistence;
- hierarchical position/career-stage/tier state;
- multi-season player-average residual state;
- within-player innovation magnitude, slope, acceleration, autocorrelation, volatility, reversals, and repeated directional sequences.

Several of these mechanisms improve group-level path shape or deeper production levels. None materially recovers individual persistence discrimination under the frozen gate. The raw innovation features themselves also have near-zero association with the needed correction.

Opening another adjacent persistence-model family would therefore risk post-hoc complexity without a demonstrated empirical signal. Under the governed evidence currently available, the practical evidence ceiling for a stronger **player-specific persistence mean adjustment** has likely been reached.

### Is the remaining Forecast defect primarily mean bias or uncertainty?

The evidence now separates the answer:

- **Stable player-level mean bias is real enough to merit separate future production review.** It improves Year-2, Year-3, cumulative, and important elite-QB level/path metrics.
- **Individual revision persistence remains weakly identifiable.** Multiple structurally different point-estimate challengers fail to rank which players should retain more or less new information.
- **Deeper uncertainty propagation is materially underrepresented by the current production recursion.** The research-only variance carry-forward repair directly fixes coverage without changing means.

Accordingly, the unresolved persistence component should now be treated primarily as **bounded Forecast uncertainty**, not as a known missing deterministic mean rule.

## Is Forecast now good enough to stop blocking Value research?

**Yes for continued research isolation; no production promotion is implied.**

Forecast is not perfect, but the remaining limitation is now understood well enough to avoid teaching Value to compensate for it:

1. current Forecast revisions have demonstrable one-season and cumulative information value;
2. a stable player-level residual correction has independently demonstrated deeper level value;
3. repeated attempts to recover individual revision persistence have not found a reproducible mean signal;
4. the deeper-horizon uncertainty defect has a separate mathematically grounded repair that restores credible coverage in research;
5. therefore a downstream residual that remains after conditioning on Forecast level and uncertainty can now be studied as a potential **Value-owned economic residual**, rather than presumed Forecast error.

This conclusion only unblocks a **research question**. It does not authorize the player-level residual correction, uncertainty repair, or any Model B behavior in production.

## Model A retest

**Not run.**

The innovation challenger failed the direct Forecast gate, so downstream Model A results were not permitted to rescue it.

The canonical Model A state therefore remains unchanged:

- materially better MAE than affine;
- context-valid scarcity passes;
- market independence passes;
- uncertainty calibration passes;
- economic usefulness remains **4/6**;
- elite-QB longevity remains a failing economic check;
- expected appreciation/decline remains a failing economic check;
- production-promotion gate remains uncleared.

## Model B status and narrowest justified next hypothesis

Model B remains **unfitted and blocked from implementation in this cycle**.

However, Forecast no longer needs to be treated as an unlimited upstream explanation for every remaining Model A residual. The narrowest justified next Value-owned hypothesis for review is:

> **A bounded, monotone nonlinear transformation of Forecast-owned multi-year replacement-adjusted surplus may better represent intrinsic franchise economics in the elite tail than the current affine surplus mapping.**

The specific question is whether the marginal intrinsic franchise value of very large, durable surplus is non-affine after Forecast-owned production level, survival, uncertainty, league scarcity, and replacement opportunity have already been accounted for.

Any future Model B study should therefore:

- leave Forecast outputs untouched;
- use the same context-valid `marginal_lineup_opportunity` replacement construction;
- nest the existing linear/identity transformation as the control;
- use a bounded, monotone, interpretable nonlinear form rather than an opaque score;
- estimate only from chronologically valid intrinsic/economic evidence, not market value;
- explicitly test whether the residual is concentrated in the elite tail and stable across folds;
- require incremental improvement in the two remaining economic checks without degrading Model A's existing four passes;
- preserve market independence and anti-double-counting rules.

That is a hypothesis for review only. **Do not fit it on the basis of this report alone.**

## Production recommendation

No production change is recommended or authorized by this cycle.

Keep production Forecast and Value unchanged. Preserve separately for future review:

1. the stable player-level residual correction as a potential Forecast mean-level enhancement;
2. recursive uncertainty carry-forward as a potential Forecast uncertainty repair;
3. the conclusion that further player-specific persistence mean complexity is not justified by the current governed evidence.

PR #131 should remain draft, research-only, non-authoritative, and unmerged.

## Reproducibility

Successful research workflow:

- run: `34726574978`
- artifact: `10307958400`
- artifact SHA-256: `284789a34013a79c5c78c94931732a73593de2946e7898ea557082bef7ce7f7d`
- historical transition panel: **14,876 rows**, seasons 1999-2024, QB/RB/WR/TE
- repository tests: **1,153 passed, 2 warnings**

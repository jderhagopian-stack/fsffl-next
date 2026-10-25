# Multi-Year Intrinsic — Value-Owned Economic Residual Identification Results

**PR:** #131  
**Status:** research-only, non-authoritative, unmerged  
**Production Forecast changed:** no  
**Production Value changed:** no  
**Production Decision/Search/API/presentation changed:** no  
**Model B fitted:** no

## Executive conclusion

**Outcome B — suggestive nonlinear structure, but evidence is insufficient to identify it as Value-owned.**

Transparent Model A leaves a strong-looking negative residual at the extreme replacement-adjusted-surplus tail: relative to middle-ranked surplus observations, the highest-surplus players tend to realize less three-year replacement-adjusted surplus than Model A predicts. This is the opposite of the previously plausible “elite convexity” or superstar-bonus hypothesis. If anything, the raw residual shape suggests compression/concavity at the extreme tail.

However, the predeclared Value-owned residual gate **fails** because the effect is not sufficiently robust to influential observations. Bounding only the most extreme 1% of residuals reduces the elite-minus-middle gap from **-19.467 to -9.795**, retaining about **50.3%** of the original magnitude, below the predeclared **60%** influence-robustness requirement.

Seven of the eight other/remaining falsification checks pass: the raw tail gap is material, chronologically stable, present across all four positions, persists in 1QB, becomes larger rather than disappearing under the research-only stable player-level Forecast correction, and remains directionally present after the research-only recursive uncertainty repair is represented. That makes the pattern genuinely interesting, but the influential-observation failure prevents us from calling it a reproducible Value-owned economic effect.

Therefore:

- **no Model B challenger was fitted;**
- **Model A remains the preferred simple intrinsic architecture at this research stage;**
- the elite-tail pattern is recorded as unresolved evidence, not promoted as a Value rule;
- the result does **not** justify an elite-QB bonus, superstar multiplier, convex curve, or any other hand-selected nonlinear adjustment;
- no additional adjacent nonlinear family should be opened automatically.

The correct management interpretation is that the remaining residual is **unresolved rather than proven Value-owned or proven absent**.

## Exact research context

At the start of this cycle:

- `main` was `f38e2f029a0d9563986635012336434a3f9beb63`;
- draft PR #131 was open, unmerged, and research-only;
- the only newer open parallel work was roadmap/documentation work with no overlap with this research implementation.

The study continued the existing PR #131 historical reconstruction and governance contract. No production authority was changed.

## Why Forecast persistence research stopped

The preceding PR #131 studies progressively separated three issues:

1. **Forecast revisions contain useful information.** New information generally improves future football forecasts.
2. **Stable player-level Forecast bias contains level information.** Some players repeatedly score above or below the broad cohort Forecast, and a chronologically estimated/shrunk player residual improves Year-2, Year-3, cumulative, and elite-QB production-level accuracy.
3. **Individual revision persistence is weakly identifiable.** Universal gain/shrinkage, cohort trajectory state, player-average residual state, and within-player residual innovation dynamics all failed to identify which individual player's newest Forecast change should persist more strongly into Years 2-3.

The within-player innovation study therefore established a practical evidence ceiling for another deterministic persistence mean rule. Remaining player-specific persistence variation is better represented primarily through Forecast uncertainty rather than another point-estimate mechanism.

That cleared the way for the present question: after holding that Forecast boundary conceptually fixed, does Model A leave a separate residual that belongs to intrinsic economics?

## Model A control

The study did not redefine Model A.

For each year:

`surplus_y = max(0, player Forecast_y - replacement Forecast_y)`

The three benchmark research weights remain:

- Year 1: **1.00**
- Year 2: **0.85**
- Year 3: **0.70**

The replacement definition remains:

`marginal_lineup_opportunity`

These weights remain benchmark parameters, not identified time-preference truth. Replacement-policy research was not reopened.

The canonical previously established Model A benchmark remains approximately:

- Model A MAE: **20.307**;
- affine-control MAE: **26.968**;
- relative MAE improvement: **24.7%**;
- Superflex/1QB structural scarcity: **PASS**;
- uncertainty calibration: **PASS** under the existing research calibration contract;
- market independence: **PASS**;
- economic-usefulness checks: **4/6**;
- elite-QB longevity: **FAIL**;
- expected appreciation/decline: **FAIL**;
- production-promotion gate: **NOT CLEARED**.

The direct residual-identification reconstruction contains 9,975 matched observations and has a Model A MAE of **20.514**. This is an analysis-universe reconstruction for residual diagnostics, not a replacement for the canonical 20.307 benchmark result.

## Residual definition and point-in-time chronology

For each historical player/fold, the core diagnostic residual is:

`realized 3-year replacement-adjusted surplus - Model A predicted 3-year replacement-adjusted surplus`

Positive residual means Model A understated realized replacement-adjusted surplus. Negative residual means Model A overstated it.

All Forecast inputs, replacement contexts, player histories, and sensitivity estimates use only information available before the corresponding historical cutoff. No through-2025 parameter is back-applied to earlier folds, no current holdout result is used for fitting, and no future target is allowed to enter its own historical estimate.

Market value, trade calculators, startup ADP, Team Utility, roster need, contender state, owner preference, and Behavioral Intelligence are not fitting targets.

## Predeclared residual test

Before the final holdout result was read, the study defined the elite tail as observations at or above the **90th percentile (top 10%)** of Model A replacement-adjusted surplus within position and historical fold. The reference middle is the **40th through 80th percentile**.

The Value-owned residual gate required all of the following:

- absolute elite-minus-middle residual gap of at least **0.10 realized-surplus SD**;
- chronological fold-level t-like magnitude of at least **2.0**;
- same-sign fold stability of at least **65%** over at least 8 folds;
- the 1%-winsorized gap to retain at least **60%** of the raw gap with the same sign;
- the stable player-level Forecast-bias sensitivity to retain at least **60%** of the raw gap with the same sign;
- the 1QB sensitivity to retain at least **50%** of the normalized effect with the same sign;
- at least **3 positions** to show the same residual direction;
- the repaired-uncertainty standardized residual to remain materially present in the same direction.

This gate was deliberately defined before the empirical result. A failure means the study cannot label the residual Value-owned and cannot fit the conditional Model B challenger.

## Canonical residual result

Across **9,975** player/fold observations:

- residual-vs-surplus Pearson: **-0.294**;
- residual-vs-surplus Spearman: **-0.220**;
- residual-vs-within-position surplus-rank Spearman: **-0.149**;
- mean residual/bias: **+7.255**;
- direct residual-universe MAE: **20.514**.

The negative rank relationship means that as predicted replacement-adjusted surplus gets larger, Model A's residual tends to become less positive and eventually negative. This is not evidence for giving elite assets an extra positive premium. It points in the opposite direction.

### Elite tail versus middle

- elite tail N: **999**;
- middle-reference N: **3,987**;
- elite mean residual: **-8.060**;
- middle mean residual: **+11.407**;
- elite-minus-middle gap: **-19.467**;
- normalized gap: **-0.315 realized-surplus SD**.

Chronologically:

- fold-level t-like statistic: **-3.969**;
- same-sign fold stability: **88.9%**.

So the raw residual is both large and chronologically persistent enough to deserve falsification. It is not merely an aggregate cross-sectional artifact.

## Influential-observation falsification — decisive failure

The predeclared influence test winsorized the most extreme 1% of residuals without changing the tail definition.

After that treatment:

- elite-minus-middle gap: **-9.795**;
- normalized gap: **-0.159**;
- magnitude retained versus the raw gap: **~50.3%**.

The sign remains negative and the residual is still non-trivial, but the predeclared rule required at least **60%** magnitude retention.

**Influence robustness: FAIL.**

This is the decisive result. The apparent nonlinear tail relationship depends too materially on extreme historical observations to justify introducing a new intrinsic-value curve.

The study intentionally did not relax the threshold, switch to a different trimming rule, redefine the tail, or search additional slices after seeing this result.

## Position behavior

The raw elite-minus-middle gap points in the same negative direction for all four positions:

| Position | Tail gap | Normalized gap |
|---|---:|---:|
| QB | -107.180 | -0.994 |
| RB | -11.031 | -0.174 |
| TE | -7.009 | -0.269 |
| WR | -2.687 | -0.061 |

This passes the predeclared direction-stability requirement, but it also illustrates why influence robustness matters: QB carries by far the largest raw magnitude. A Value rule must not become a disguised QB penalty or bonus merely because a few historically extreme QB observations dominate the tail.

No QB-specific adjustment was introduced.

## Forecast stable-level-bias sensitivity

The previously validated research finding that player-specific historical Forecast residuals can improve future **production-level** accuracy was used only as a falsification sensitivity.

Under that research-only mean correction:

- tail gap: **-33.129**;
- normalized gap: **-0.537**;
- fold-level t-like statistic: **-6.225**;
- fold sign stability: **100%**;
- all four positions remain same-sign.

The apparent tail residual therefore does **not** disappear when this known Forecast-level issue is represented. In fact it becomes larger.

That means the raw tail pattern cannot simply be dismissed as the previously identified stable player-level mean bias. But because influence robustness still fails, this sensitivity does not prove the residual is Value-owned.

The stable-level correction remains research-only and is not promoted by this study.

## Forecast uncertainty sensitivity

The research-only recursive variance carry-forward was also applied only as a confidence/uncertainty sensitivity. It changes uncertainty, not the mean.

Under that variance representation:

- the standardized elite-minus-middle residual gap remains negative at **-1.269**;
- nominal-80% coverage in this residual-study universe is **90.7%**.

The residual direction therefore remains after scaling by the repaired Forecast uncertainty. However, 90.7% is slightly above the former 70%-90% calibration envelope in this particular residual universe. This is not a new uncertainty-promotion result and should not be interpreted as such. The independently validated Forecast uncertainty work remains the relevant authority for that question.

Improved or widened uncertainty was not allowed to rescue or condemn a mean Value challenger.

## League-format sensitivity

In the 1QB sensitivity:

- tail gap: **-18.331**;
- normalized gap: **-0.376**;
- fold-level t-like statistic: **-4.159**;
- fold sign stability: **83.3%**;
- all four positions remain same-sign.

The raw pattern therefore is not merely a Superflex QB-scarcity artifact.

`marginal_lineup_opportunity` continues to own structural format scarcity. No second scarcity premium was layered into Value.

## Other residual-shape diagnostics

The canonical residual has modest negative rank relationships with several quantities that covary with elite surplus:

- surplus concentration Spearman: **-0.231**;
- Year-3/terminal surplus share Spearman: **-0.216**;
- Forecast-uncertainty ratio Spearman: **-0.216**;
- source survival probability Spearman: approximately **-0.001**.

The essentially zero survival relationship is useful: there is no evidence here for adding a second survival adjustment to Value. Survival is already embedded in future Forecast means and must not be multiplied through surplus again.

The concentration, terminal-share, and uncertainty relationships are not treated as independent Value channels. They overlap strongly with the same high-surplus observations and were diagnostics only.

## Career-stage diagnostics

Canonical residual MAE / mean bias by career stage:

| Career stage | N | MAE | Mean residual |
|---|---:|---:|---:|
| Rookie / Year 2 | 3,228 | 19.757 | +11.037 |
| Young | 2,636 | 19.925 | +7.386 |
| Prime | 2,859 | 19.114 | +5.487 |
| Veteran | 1,252 | 26.902 | +1.268 |

These are diagnostic only. No age/career-stage Value multiplier was fitted.

## Double-counting and confounding checks

The study explicitly preserved the following boundaries:

1. **Forecast mean error:** stable player-level Forecast bias was tested separately and not silently moved into Value.
2. **Forecast uncertainty:** recursive variance carry-forward was represented separately and did not alter the Value mean.
3. **Survival:** no additional survival multiplier was applied; survival is already embedded in future Forecast means.
4. **Replacement context:** `marginal_lineup_opportunity` remained fixed; replacement-policy research was not reopened.
5. **Positional scarcity:** Superflex/1QB differences continue to arise through governed lineup opportunity/replacement mechanics.
6. **Second scarcity premium:** none was added.
7. **Market imitation:** KeepTradeCut, FantasyCalc, DynastyProcess, startup ADP, external rankings/calculators, Broad Market Value and League Market Value were not intrinsic fitting targets.
8. **Team Utility:** roster need and team fit were excluded.
9. **Competitive posture:** contender/rebuilder preference was excluded.
10. **Owner behavior:** league willingness-to-pay and Behavioral Intelligence were excluded.

The study therefore did not create a hidden path for downstream preferences or market behavior to masquerade as intrinsic economics.

## Residual gate result

| Predeclared check | Result |
|---|---|
| Material tail gap | PASS |
| Chronological t-like magnitude | PASS |
| Chronological sign stability | PASS |
| Influence robustness | **FAIL** |
| Stable-level Forecast sensitivity | PASS |
| 1QB format sensitivity | PASS |
| Position stability | PASS |
| Repaired-uncertainty sensitivity | PASS |

The all-check gate therefore **fails**.

Under the management taxonomy, this is **Outcome B: VALUE RESIDUAL EXISTS, BUT EVIDENCE IS INSUFFICIENT** in the sense that there is suggestive nonlinear residual structure worth recording, but it is too sensitive to influential observations to identify as a reproducible Value-owned phenomenon.

This wording is deliberately more precise than saying the raw pattern is absent. It is also deliberately weaker than saying a Value residual has been established.

## Model B decision

**Model B was not fitted.**

The conditional challenger had been predeclared as a single monotonic piecewise-linear elite-tail hinge, fitted chronologically only if every residual-identification check passed. Because influence robustness failed, fitting that challenger would violate the study contract and would risk turning influential historical observations into a structural intrinsic-value rule.

There are therefore no Model A-versus-Model B performance statistics from this cycle. That is a governed stopping outcome, not missing work.

The direction of the raw residual is nevertheless informative for future interpretation: it argues **against** an untested elite convexity or superstar premium. If this issue is ever revisited with materially better historical evidence, the unresolved shape to falsify would be elite-tail compression/concavity, not an assumed bonus.

## Existing economic validation remains unchanged

Because no Value challenger qualified for fitting, the established Model A economic validation remains the relevant state:

- aging RB: **PASS** (~68.3% directional check in the canonical research);
- elite-QB longevity: **FAIL**, rank-signal correlation approximately **0.1948**;
- developing WR: **PASS**, correlation approximately **0.5133**;
- developing TE: **PASS**, correlation approximately **0.3981**;
- Superflex/1QB scarcity shift: **PASS**;
- expected appreciation/decline: **FAIL**, approximately **44.6% direction / -0.269 correlation**;
- economic checks: **4/6**;
- market independence: **PASS**.

The two failing showcase checks were not used to justify complexity, and no new model was allowed to “fix” them after the residual gate failed.

## What this means for Model A

This study does not prove Model A is production-ready. It does establish that the current evidence does **not** justify replacing its transparent linear surplus architecture with a nonlinear Value model.

Model A therefore remains the preferred **simple research architecture**, with its limitations explicitly known:

- Forecast has a separately demonstrated stable player-level level signal that has not been promoted;
- Forecast has a separately validated recursive uncertainty repair that has not been promoted;
- individual deeper-horizon persistence is weakly identifiable and should primarily remain uncertainty;
- Value shows a suggestive elite-tail compression pattern, but the pattern is too influence-sensitive to earn a nonlinear rule.

This is materially different from asking Value to repair an unknown Forecast defect. The boundaries are now much better understood even though the full production-promotion gate remains uncleared.

## Evidence-ceiling / stopping decision

Do **not** automatically open another nonlinear Value family.

The requested residual-identification question has been answered: there is suggestive negative elite-tail structure, but the governed evidence is insufficient to call it Value-owned or to justify Model B.

The appropriate next step is a **management review**, not another model search.

A useful management decision would be whether PR #131 has now produced enough research to move into a separate production-readiness review of the simplest defensible components—Model A itself, the stable player-level Forecast level correction, and the recursive Forecast uncertainty carry-forward—each under its own authority and promotion standard. That review should decide whether those components are mature enough for controlled implementation or whether PR #131 should simply close as research evidence.

No such promotion decision is made here.

## Production recommendation

**NO PRODUCTION PROMOTION.**

- Keep PR #131 draft, research-only, non-authoritative, and unmerged.
- Do not fit or promote Model B from this evidence.
- Do not add an elite/QB/superstar multiplier.
- Do not modify production Forecast or Value behavior.
- Do not promote the stable player-level correction or recursive uncertainty repair in this cycle.
- Do not begin another adjacent nonlinear family without management review.

## Reproducibility

The initial clean empirical run of the residual-identification implementation was GitHub Actions run **34727497605** on research head `51b02de8a35de3a4a290935826e63e72de795487`.

That run produced:

- artifact: `pr131-model-a-intrinsic-forecast-audit`;
- artifact ID: **10308650756**;
- artifact SHA-256: `da739fa7a95285b83d7844899a9fd13c5946740e4a38a11c0d3781c8aaec5bb4`;
- full repository tests: **1,153 passed, 2 warnings**.

Machine-readable evidence includes:

- `value_residual_identification_results.json`;
- `value_residual_identification_rows.csv`;
- `value_residual_fold_diagnostics.csv`;
- generated research report `value_residual_identification_report.md`.

No Model B row/parameter artifact is expected because the predeclared residual gate failed before challenger fitting.

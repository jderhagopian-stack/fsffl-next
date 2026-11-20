# Current Competitive Strength — Research v0.1
**20 November 2026 · FSFFL NEXT · research-only / no production promotion**

## Governing product definition

The Power Ranking answers: **Which fantasy franchise would we trust to beat randomly selected league opponents, under standardized competitive conditions, if they played now?**

It is neither a reward for historical wins nor an approximation of playoff odds, three-year Intrinsic, Career value, or this week's bye-aware matchup probability. Editorial narratives can cite actual records, all-play results, momentum, trades, injuries and unexpected overperformance. Those are supporting evidence, **not separately awarded power-ranking points**.

## New model (independent of the V2 weighted Power Index in draft PR #579)

Research code: `src/fsffl/analytics/competitive_power_research.py`; focused tests: `tests/test_competitive_power_research.py`. No import into production service, routing, forecast authority or simulation. No new worker, schema or costs.

1. The prior is the **current roster's standardized weekly point projection** plus modeled game-to-game variance. A separate correction-prior variance represents uncertainty that the roster forecast misses a persistent scoring tendency. The prior variance is a *research hyperparameter*, not the calibrated uncertainty currently produced by Forecast.
2. For a historical completed fantasy week, compare actual points with a **forecast computed before that week's first NFL kickoff**. Subtract that week's league-median actual-minus-projected residual. This prevents a shared league-wide systematic projection bias from becoming a phantom advantage for every team.
3. Update the team-specific residual using a normal-prior/normal-likelihood precision update. Each historical week contributes **one** observation per franchise (not 11 artificial all-play observations). Expected-score noise, elapsed time, and continuity of model-optimized starter identities reduce its weight. The largest residuals are clipped at 2.5 standard deviations.
4. Convert posterior expected weekly team scoring and predictive uncertainty into a pairwise normal win probability against each other league franchise. The average of those N−1 comparisons is a **neutral all-play strength estimate**, not the chance of winning the next scheduled matchup. Sort deterministically.

**No fixed percentages for record, momentum, or past scoring.** Actual scoring matters by updating beliefs about today's roster; recent evidence carries more weight insofar as it concerns current personnel.

## Preliminary Week 11 exercise — NOT publication-authoritative

**Source:** existing saved FSFFL NEXT November 17 State (Sleeper league 1312071960615731200) and live_simulation_analytics artifact #13894, dated Nov 17 21:18 UTC. Current roster's neutral-weekly projection is provisionally approximated by the mean of artifact Week 15–17 forecasts (those weeks have no scheduled byes). It is **not proven** to be a properly standardized or healthy starting lineup; it remains subject to forecast and lineup model limitations.

**Historical pregame model artifacts:** Week 5 #11231; Week 6 #11541; Week 7 #12590; Week 8 #12836; Week 10 #13504. All computed before the relevant week; actual scores from the saved Nov 17 league State. Other weeks lack a suitable archived matched pregame forecast. Old model vintages can differ in calibration. Continuity is estimated from overlap of historical/current **optimized** starting-player IDs, NOT verified historical submitted Sleeper lineups. Five-week evidence is sparse and older forecast snapshots can be stale.

Example provisional parameters: systematic-correction prior SD **12 points**, recent-evidence half-life **4 fantasy weeks**, observation-noise floor **20 points**, clip **2.5 SD**, normal approximation and independent conditional scores. These numbers were picked for an intelligible research test, **not backtested or validated**.

| Rank | Sleeper owner account | Neutral win rate | Roster prior pts | Evidence correction pts |
|---:|---|---:|---:|---:|
| 1 | Drigs24 | 64.9% | 138.4 | −5.0 |
| 2 | MochaSmev | 64.7% | 127.2 | +5.0 |
| 3 | PVos | 63.5% | 127.7 | +3.5 |
| 4 | jimmygoodjob | 61.7% | 129.3 | −0.3 |
| 5 | nuckyniners | 59.3% | 127.6 | −1.4 |
| 6 | Anthonyder | 57.7% | 123.4 | +0.8 |
| 7 | CoachKoko | 53.7% | 110.5 | +9.0 |
| 8 | jder52 | 45.3% | 110.4 | +0.5 |
| 9 | Ballard22 | 45.2% | 109.7 | +1.1 |
| 10 | jaco057 | 32.3% | 97.2 | +0.3 |
| 11 | ddersimon | 30.6% | 98.5 | −3.0 |
| 12 | chuckthegoat77 | 21.1% | 87.1 | −1.2 |

The first two teams differ by **only 0.2 percentage points** in the neutral win estimate; this is not a statistically established difference. Nothing above should silently overwrite the V1 or V2 editorial reports.

**Sensitivity (changing only the assumed prior SD on systematic projection error):**

| Prior correction SD | Top three teams in research replay |
|---:|---|
| 6 pts | Drigs24, jimmygoodjob, MochaSmev |
| 8 pts | Drigs24, MochaSmev, PVos |
| 12 pts | Drigs24, MochaSmev, PVos |
| 18 pts | MochaSmev, PVos, Drigs24 |
| 24 pts | MochaSmev, PVos, CoachKoko |

**Result: No validated winner yet.** This is precisely the dependency we need to calibrate from more independent historical evidence before granting numerical authority to a published Power Ranking.

### Diagnosis uncovered in archived model evidence

Across the five reconstructed fantasy weeks, actual scores exceeded corresponding pregame model scoring averages by **4.5 to 15.3 fantasy points per team per week** across the league. This is evidence of an overall model-versus-observation discrepancy in these saved vintages, not necessarily permanent underprediction by today's model. Preseason/season forecasting validation is a prerequisite. Centering historical residuals identifies *relative* persistent departures while not solving absolute league scoring calibration.

A prominent tension is **Anthonyder**: it leads the league's Week 1–10 actual points per game, yet the Nov 17 no-bye proxy estimates only 123.4 before correction, versus 138.4 for Drigs24. That difference requires player-level analysis (injury status, trades, provider projections, availability, source coverage) before publishing a definitive power ranking. A new estimator cannot repair incorrect roster projections through weighting.

## Non-negotiable gates before promotion

1. **Point-in-time authority.** Source adapter must resolve real team membership and the timestamp and roster of every historical observation, first NFL kickoff, exact pregame projection lineage and actual scores; reject future leakage or ambiguous identity. Current code performs local temporal and completeness validation but does *not* fetch/attest upstream NFL kickoff schedule.
2. **Genuinely comparable roster prior.** Build an explicit standardized bye-neutral forecast *from current player and roster evidence*, not the late-season Week 15–17 shortcut; preserve realistic injuries and unknown availability as separate source facts. Do not silently assume every player is healthy.
3. **Empirically estimate prior correction variance, recency decay, historical residual scale, dependence and outlier policy** across multiple seasons and leagues; do not tune these against the test period.
4. **Historical roster continuity.** Replace optimized-lineup intersection proxy with attested historical roster and actual player starts where possible; explicitly downgrade missing evidence rather than faking zeroes.
5. **Competition metrics.** Walk-forward compare against current roster prior alone, season all-play, actual record, PR #579, and the research update. Evaluate future scored-point residuals, matchup picks, rank correlations, probabilistic calibration/Brier and uncertainty. Account for schedule-dependent missingness and historical model-version changes.
6. **Snapshot and report contract.** Archive immutable input hashes/model versions, interpreted owner/team display names, posterior strength, evidence coverage and explanations. Never feed this editorial power rating back into Forecast, Intrinsic, Simulation or Trade Center.
7. **Provider reality.** Submitted Sleeper Week 11 starters and live points must come from their authoritative weekly matchup endpoint, not from the modeled/rostered lineup. Tie results are W–L–T, not losses.
8. **Publish authority.** Set publication_ready=false until independent source-parity, multi-league backtests, expert review and report/editorial methodology approval. An on-demand cached artifact is sufficient initially; no new paid service is needed.

## Recommended handoff

Review and keep this as a separate, unmerged **research PR**. Next implement the frozen, read-only evidence adapter with receipts, followed by historical replay and a calibration comparison. Keep the weekly publication prototype and its humor, but do not claim the provisional scores above are validated predictive outputs.

Earlier research: draft PR #579, the 45/25/20/10 versus 40/35/15/10 five-week walk-forward comparison (both 22/30 matchup winner predictions; insufficient discrimination). The change here is **the estimand and measurement logic**, not another arbitrary weight vector.

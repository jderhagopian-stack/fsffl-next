# FSFFL NEXT — Competitive Strength Forecast Readiness Audit
**2026-11-20 · Research-only · No production writes, reruns, or new workers**

## Decision

**Do not calibrate a published current-strength ranking using the existing five-week backtest.**

That retrospective exercise crosses a **hard forecast regime change**, and the current 2026 State does not provide enough exact player-week participation evidence for a reliable current-strength publication.

This PR contributes only an isolated evidence/eligibility audit and focused synthetic tests. It must **not** cause automatically injured players to score zero or modify the season simulation. It is adjacent to power-ranking research PR #580; neither is promoted.

## Verified evidence (read-only Supabase queries, FSFFL league 1312071960615731200)

**Artifact lineage:**

| Data vintage | Artifact IDs | Model regime | Baseline lineup horizon |
|---|---|---|---|
| Historical test Weeks 5/6/7/8/10 | 11231 / 11541 / 12590 / 12836 / 13504 | next18-live-simulation-analytics-v18 | `season` |
| Latest stored Week 11 view, Nov 17 21:18 UTC | 13894 | next18-live-simulation-analytics-v19:native-participation-ros | `rest_of_season` |

- The persisted archive contains **83 v18 simulation artifacts** (Oct 2–Nov 11) and **9 v19 artifacts** (first Nov 13, through Nov 17). The nine v19 artifacts are not nine independent completed weeks; they are repeated snapshots around Week 11.
- In v18, season forecast means were decomposed over a structural 17 games. In v19, the native ROS forecast is distributed across the *remaining eligible game count*, with NFL bye-aware optimizations. A retrospective model can examine old artifacts but cannot pretend that this tests the new v19 forecast family.
- Across Weeks 5, 6, 7, 8, 10 the older model's league-wide projected score averages were 103.85 / 90.01 / 102.56 / 102.35 / 99.83. Actual averages were 115.41 / 101.59 / 110.80 / 106.88 / 115.14. Observed discrepancies: +11.56 / +11.58 / +8.24 / +4.53 / +15.31 points. This is a **v18-era diagnostic**, not evidence that v19 retains the same bias.
- The latest v19 artifact's Week 11 mean is 106.75 points per team; its mean across bye-free Weeks 15–17 is 115.57. This disparity is not evidence of an error: Week 11 has six NFL teams on bye, including Cleveland, Green Bay, New England and the Los Angeles Rams.

**Source State availability coverage (Nov 17 league snapshot):**
- 255 rostered players across 12 teams; 67 have canonical `injured` status.
- 37 of those injured-status players are in roster slots other than `IR`/`TAXI`, so a simple fantasy-roster-slot exclusion cannot resolve the problem.
- **0** canonical `player_week_availability` rows.
- Of the model's 108 optimally assigned baseline starting slots (9 per team), **16 have canonical `injured` status**. They include Puka Nacua and Travis Kelce on Anthonyder's model-optimized baseline lineup. Injured status alone is ambiguous and may include short-term ailments; DO NOT remove all 16 or assign zeros.

The source code at `src/fsffl/team_utility/scoring.py` currently excludes *verified bye weeks* and exact `WeeklyAvailabilityStatus.UNAVAILABLE` rows when building weekly lineups; `src/fsffl/team_utility/lineup.py` also excludes fantasy `IR`/`TAXI` slots. The absence of exact weekly rows is not interpreted as unavailable. This is scientifically appropriate as a data boundary but produces a meaningful **unknown-availability exposure**.

**Anthonyder root-cause investigation:**
- Weeks 1–10 historical team scoring average: **137.35**. Nov 17 modeled bye-free forward scoring proxy: **123.38**; Nov 17 actual Week 11 projection: **90.50**.
- Actual fantasy roster at snapshot: Jalen Hurts and Jaxson Dart on fantasy IR; Drake Maye flagged injured and in QB slot. Projected ROS: Hurts **0**, Dart **0**, Maye **37.1** (single-source ROS fallback). The current optimizer instead assigns Deshaun Watson at QB, with ROS projected **119.7**. **Do not describe this as an optimizer bug:** the forecast inputs and IR restrictions cause it.
- The Nov 17 optimized baseline lineup also chooses Puka Nacua (ROS **69.4**, canonical injured) and Travis Kelce (ROS **74.3**, canonical injured); neither is currently on fantasy IR. The team also has A.J. Brown injured with a remaining ROS forecast.
- Historic optimized lineup Weeks 5–10 included Drake Maye, Matthew Stafford, Sam LaPorta, and Puka Nacua; Nov 17 optimized baseline does not include Maye or LaPorta, and now includes Watson/Kelce. These are **model-optimized** rosters, not a substitute for actual Sleeper submitted weekly starters.
- Independent first-party NFL reports corroborate serious injuries: Eagles IR for Jalen Hurts, Patriots Maye ankle injury, Rams IR for Puka Nacua. The point is not that every listed injured player is definitely out indefinitely; it's that the model needs *exact week-specific availability/return-time evidence* to make participation-aware scoring credible.
  - Eagles: https://www.philadelphiaeagles.com/news/eagles-place-jalen-hurts-on-injured-reserve-sign-jaydon-blue-to-the-active-roster-2026-nfl-week-6-panthers
  - NFL Maye: https://www.nfl.com/news/patriots-drake-maye-ankle-injury-lions
  - Rams Nacua: https://www.therams.com/news/mcvay-rams-placed-puka-nacua-on-ir-because-they-needed-the-roster-spot-week-10-2026-cardinals
  - NFL 2026 byes: https://www.nfl.com/news/2026-nfl-schedule-release-every-team-bye-week

**Conclusion about the team:** The gap between 137.35 actual prior scoring and 123.38 current forecast is partly explained by roster/participation deterioration and forecast regime differences. It is **not** an empirically isolated 14-point projection error. Unverified future availability may simultaneously be *inflating* the current projection for certain injured players.

## Implementation on this PR

- `src/fsffl/analytics/forecast_strength_readiness.py` provides a pure, research-only compatibility/participation audit.
- Historical forecast receipts must be computed **before first NFL kickoff**, finalized before the target as-of date, and declare model regime and horizon.
- Cross-regime receipts are reported as **incompatible**, never silently included in current calibration residual averages.
- Baseline optimized starters flagged injured/inactive/PUP/suspended are labeled **unverified** when no exact weekly participation fact exists. Explicit available/unavailable facts remain distinct; a baseline optimized starter marked unavailable requires the week-specific reoptimizer rather than being treated as an actual starter.
- Unknown participation is **not** interpreted as a zero or a forecasted absence. Publication remains false until separate research promotion.
- Focused synthetic tests cover pregame cutoff, duplicate evidence, model version mismatch, missing/injured starter facts, definite unavailability, and no-fabricated-zero behavior.

## Recommended next engineering work (priority order)

1. **Source-level injury/participation bridge.** Preserve source-declared exact injury/IR/list-status evidence with acquisition timestamps. Convert only objectively supported week-specific unavailable/available facts to `PlayerWeekAvailability`; ambiguous questionable/injured statuses stay unknown, with probabilistic absence modeled separately in Forecast. Add tests for NFL IR minimum eligibility and return dates **only if the source proves the interval**. Do not infer an automatic 4-week absence from all injury statuses.
2. **Direct weekly forecasting evidence.** The current source states ROS totals are divided across remaining eligible games (the product runtime explicitly warns this bridge is provisional). Improve validated weekly player forecasts and uncertainty rather than masking issues through a Power Index. Preserve fully sourced player-game projections and availability.
3. **Historical version-parity.** Capture native v19 pregame player-week/team-week forecasts and associated published actuals and lineup membership on upcoming weeks, append to immutable archive, and replay only comparable evidence. Archived v18 data may still support *methodological* research within v18 but is not forward-calibration proof for v19.
4. **Explicit current roster strength.** Use a governed standardized neutral condition that separates true expected participant availability from upcoming scheduled byes. Injuries must not disappear under a label such as "no-bye team strength".
5. **Model verification.** Check mean absolute scoring error, directional bias, absolute rank skill, predictive intervals and actual fantasy matchup probabilities against naive alternatives. Calibrate by season, position and league scoring settings; maintain honest no-evidence states for sparse leagues.
6. **Report publication gate.** Allow the editorial report format and descriptive observations, but mark unvalidated power ratings provisional and never inject editorial ratings into Simulation, Intrinsic or Trade Center.

This is the **next highest-value engineering boundary** for truthful power rankings *and* live matchup intelligence. It does not require another paid worker; all steps are research/validation using the existing provider and artifact lifecycle.

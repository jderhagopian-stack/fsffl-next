# FSFFL NEXT — Weekly Power Rankings v2 research handoff

**Date:** November 20, 2026  
**Status:** RESEARCH ONLY / no application integration / no model promotion  
**Test league:** Sleeper 1312071960615731200 (FSFFL 2026)  
**Development priority:** Retain as Reports & History research; do not divert Trade Center work.

## Decision

The Week 11 research prototype is a meaningful methodological improvement but NOT an empirically established predictive improvement. Do **not** replace any production simulation, team scoring, or report-ranking authority with this model yet.

The same five archived weeks gave **22 correct matchup winner picks out of 30** for both the prior 45/25/20/10 ranking formula and this 40/35/15/10 proposal. Actual season-to-date all-play standing alone also achieved 22/30, as did raw record (with ties handled as half wins). Predicting winners from the standardized bye-free model alone got 20/30. These samples are far too small and internally dependent to optimize weights or claim significance.

The code added on this branch is an isolated, deterministic, league-agnostic research implementation with focused unit tests. No route, database schema, live simulation, or product output is modified.

## Why this version exists

The original editorial ranking combined (1) a forward-looking model measure derived from averaging multiple weeks, (2) season all-play, (3) last-three all-play, and (4) record. That:

1. Double-counts the last three weeks of observed performance.
2. Depresses a hypothetical neutral team's underlying talent rating with future bye-week absences.
3. Compares each team to a synthetic league-average opponent rather than its actual peer group.
4. Treats point differences in an uncalibrated Power Index as overly meaningful.
5. Does not distinguish editorial power strength from a **specific** week's scheduled-matchup win probability.

This research alternative explicitly separates those concepts.

## Proposed scoring components (not yet calibrated)

- **40% current roster model strength:** expected all-play win fraction against each other franchise using standardized future no-bye weekly mean and standard deviation; pairwise probabilities derive from the independent normal difference. Inputs are prepared upstream and must preserve realistic availability.
- **35% observed season performance:** completed season-to-date all-play fraction, every weekly opponent counted, ties half.
- **15% momentum change:** 0.5 + 0.5 × (all-play performance in recent three completed games − earlier completed weeks). A flat team has neutral momentum, even when its recent raw performance is excellent. The 0.5 coefficient is an explicit small-sample shrinkage assumption, not a fitted parameter.
- **10% scheduled record:** wins plus half ties divided by completed scheduled matchups.

The research module is in src/fsffl/analytics/weekly_power_rankings.py. It uses frozen typed evidence, validates weights and input fractions, rejects duplicate IDs, sorts ties deterministically, and is entirely detached from the deployed report or forecast runtime. It deliberately cannot determine whether its upstream data is a legitimate point-in-time snapshot: the orchestration and evidence authority must guarantee that.

## Week 11 comparison from frozen November 17 evidence

| V2 rank | Owner handle | V2 score | Published V1 rank |
| ---: | --- | ---: | ---: |
| 1 | Anthonyder | 65.72 | 2 |
| 2 | Drigs24 | 65.58 | 1 |
| 3 | nuckyniners | 62.13 | 3 |
| 4 | MochaSmev | 60.58 | 4 |
| 5 | PVos | 60.28 | 5 |
| 6 | jimmygoodjob | 59.07 | 6 |
| 7 | CoachKoko | 52.18 | 7 |
| 8 | jder52 | 49.26 | 8 |
| 9 | Ballard22 | 41.59 | 9 |
| 10 | ddersimon | 32.14 | 10 |
| 11 | chuckthegoat77 | 27.60 | 11 |
| 12 | jaco057 | 23.89 | 12 |

V2 input for this exercise: average model-derived weekly scoring distributions for NFL weeks 15–17, which showed no scheduled bye suppression in the November 17 saved panel. This is a **research proxy**, not a proven clean 100%-available standardized weekly forecast. For example Drigs24's Week 11 mean is 104.9 because of byes, versus 138.4 in the later no-bye weeks. Anthonyder's analogous figures are 90.5 and 123.4. Official Week 11 matchup predictions must use the actual Week 11 panel, NOT these no-bye numbers.

The top-two 0.14-point gap is not meaningful statistical separation; report them as a shared contender tier rather than as distinct established probabilities.

## Point-in-time replay and audit trail

The replay used pre-Thursday archived FSFFL NEXT model artifacts, with current league snapshot's completed scores for outcomes:

| Predicted NFL/fantasy week | Model artifact ID | Artifact computed UTC | Source as-of UTC |
| --- | ---: | --- | --- |
| 5 | 11231 | Oct 8 16:24 | Oct 7 11:23 |
| 6 | 11541 | Oct 13 16:54 | Oct 8 16:20 |
| 7 | 12590 | Oct 21 12:06 | Oct 21 03:28 |
| 8 | 12836 | Oct 28 10:29 | Oct 28 10:26 |
| 10 | 13504 | Nov 11 03:06 | Nov 11 02:58 |
| Week 11 editorial input | 13894 | Nov 17 21:18 | Nov 17 21:08 |

Weeks 1–4 and 9 lacked a suitable pregame weekly-scoring panel in the archive. Week 6's last usable forecast was several days old; the replay does not retroactively refresh it. This is **five scoring weeks / six league matchups each / one league**: a diagnostic sample only. Source-matchup data is the November 17 fsffl.league_snapshot payload. For each test week, all all-play and record features are built from **earlier completed weeks only**. No future score enters the predicted week. All analyses are descriptive.

| Method | Correct matchups | Mean within-week Spearman rank correlation to actual points |
| --- | ---: | ---: |
| Season all-play alone | 22/30 | 0.406 |
| Record alone | 22/30 | 0.404 |
| Prior editorial 45/25/20/10 | 22/30 | 0.380 |
| Research v2 40/35/15/10 | 22/30 | 0.369 |
| Candidate 45/35/10/10 | 22/30 | 0.397 |
| No-bye model alone | 20/30 | 0.344 |
| Last-three all-play alone | 20/30 | 0.259 |

**Do not infer** from these numbers that record is globally more predictive than model strength. The historical sample, data vintages and forecast model maturity cannot support that claim.

**Confirmed Week 2 tie (user corroborated, November 20, 2026):** The stored Sleeper matchup result for Week 2 is Anthonyder 107.62, MochaSmev 107.62. The league owner confirms there was a real tie this season. This is **not erroneous source data**; the prior editorial report incorrectly displayed conventional W–L records (8–2 / 5–5) instead of preserving the tie. Results calculated from the saved Week 1–10 matchup points are Anthonyder **8–1–1** and MochaSmev **5–4–1**, with a tie counted as half a win for ranking/all-play rates. The Sleeper account handle Anthonyder has not yet been independently reconciled to the reported fantasy-franchise name “Blitzers”; verify owner/franchise display names and provider standings before production publication.

## Requirements before promotion

1. **Frozen evidence boundary:** weekly reports and research rankings must store snapshot timestamp, league scoring/rules hash, roster hash, model version and input data lineage. Historical replay must fail closed if a forecast was generated after the target week's kickoff or no eligible snapshot exists.
2. **True standardized team strength:** compute the team-level full-availability baseline from current player-week forecasts with governed explicit absence handling. Do not simply take future weeks 15–17 forever.
3. **Roster changes:** use each week's exact roster, not the November 17 roster retroactively. The forecast artifact associated with each test week is a partial historical proxy, not complete source-state provenance.
4. **More evidence:** archived model/league states from several seasons and leagues; time-ordered out-of-sample evaluation; compare all-play, actual record, model and ensembles. Evaluate matchup accuracy and weekly scoring rank correlation; if generating calibrated matchup probabilities, use Brier score, log loss and reliability diagrams.
5. **Uncertainty:** do not label 0.14-index-point differences definitive. Add tiers and possibly rank stability using bootstrap across weeks and parameter sensitivity.
6. **Correct live inputs:** actual Sleeper fantasy team names, submitted starters, completed player scores, lineup locks and game status must drive matchup intelligence. A roster-slot label or optimized lineup is not proof of a submitted starter (Woody Marks correction).
7. **Boundary with simulations:** power ranking outputs are ordinal editorial measurements, NEVER injected into the 50,000-trial competitive season simulation or normalized into fake actual matchup win odds.
8. **Publication service:** Rankings → narrative evidence cards → matchup intelligence → prediction accountability → archived weekly edition. Make the design league-agnostic and keep report generation separated from analytics and forecast authority.
9. **Cost:** no separate always-on paid worker is a prerequisite. First implement as an on-demand cached artifact derived from existing frozen evidence; benchmark before introducing independent scaling.

## Next recommended change

Keep this PR as a reviewable research artifact. A follow-on implementation should add a read-only, versioned evidence builder and real historical fixtures. Do not route production page reads to this function until the data contract and out-of-sample evaluation gates are complete.

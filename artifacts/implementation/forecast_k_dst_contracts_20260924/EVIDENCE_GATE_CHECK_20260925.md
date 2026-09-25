# FSFFL NEXT — K/DST Empirical Evidence Gate Check

Date: 2026-09-25  
Workstream: Forecast / Product Implementation  
Merged implementation: PR #215  
Canonical implementation merge SHA: `407c1bf85e5dc75f92b9906719f82bcd11d97c31`

## Purpose

Apply the post-merge operating-protocol test to the remaining Stage 2/3 evidence dependencies rather than treating the merged PR itself as completion.

This check does **not** promote any provider or model authority. It records what evidence was and was not recoverable from the presently available retained/public sources.

## Historical projection recovery check

### Razzball

A dated Razzball article from 2024 explicitly states that free preseason projections were available for both K and DEF(Team):

- https://football.razzball.com/2024fantasyfootballprojections/

That article is dated August 14, 2024, but its K and DEF projection links now resolve to mutable projection endpoints such as:

- https://football.razzball.com/projections-pk-restofseason/
- https://football.razzball.com/projections-teamdefense-restofseason/

The linked content is currently updated/current-season content rather than an immutable retained 2024 raw projection corpus. Therefore the dated article proves that 2024 projections existed, but it does **not** supply the point-in-time raw rows required for governed calibration.

Conclusion: **not a qualifying historical independent PIT source #2**.

### CBS Sports

CBS exposes URLs containing historical year segments, including K/DST pages under `/2024/`. Publicly reachable projection-style routes can render current/week projection content despite the historical-looking path. This reproduces the Research warning that path year alone is not content-year authority.

Examples inspected:

- https://www.cbssports.com/fantasy/football/stats/K/2024/9/projections/ppr/
- https://new.cbssports.com/fantasy/football/stats/K/2024/restofseason/projections/nonppr/
- https://www.cbssports.com/fantasy/football/stats/DST/2024/14/projections/ppr/

Conclusion: **historical-looking CBS paths are not sufficient PIT provenance and cannot be used as calibration evidence without a retained dated corpus/content proof**.

## Source-rights check

### Razzball
Current terms state that projections/calculations are property of Razzball LLC; personal non-commercial use is permitted and other use requires permission.

- https://razzball.com/termsandconditions/

Result: production/commercial promotion remains **rights-gated** absent written permission/license.

### CBS Sports
Current fantasy terms grant personal, non-transferable, non-commercial use and prohibit commercial reuse/redistribution of CBS Sports Content.

- https://www.cbssports.com/info/about/tos/ffs

Result: production/commercial projection ingestion remains **rights-gated** absent an appropriate license.

### Sleeper
Sleeper's API documentation states the API is free for non-commercial purposes and directs commercial users to contact Sleeper regarding licensing.

- https://docs.sleeper.com/

Result: commercial product use remains **licensing-gated**.

## Sleeper scoring-semantics check

Official Sleeper documentation materially clarifies two parts of D/ST realized scoring:

1. Points allowed includes opponent offensive scoring, including field goals, PATs/2-point conversions, and touchdowns including special-teams return TDs; opposing defensive touchdowns are not charged as points allowed, while resulting extra points/2-point conversions are still charged.
   - https://support.sleeper.com/en/articles/4126495-how-are-points-allowed-calculated

2. Special Teams Defense and Special Teams Player are distinct scoring subjects; team `def_st_*` and individual `st_*` coordinates must not be collapsed.
   - https://support.sleeper.com/en/articles/3278982-special-teams-scoring-options
   - https://support.sleeper.com/en/articles/3998131-what-scoring-options-are-available

These documents support the implemented subject separation and narrow some realized-score ambiguity. They do **not** by themselves replace exact weekly scored truth fixtures for all obscure D/ST attribution/bucket cases required before promotion.

## Gate determination

No presently recovered source clears the missing historical independent-source requirement for empirical K/DST calibration. In addition, candidate production sources remain rights/licensing gated.

Therefore:

- do not fit/promote K/DST uncertainty from FFToday alone;
- do not treat mutable Razzball/CBS pages as historical PIT evidence;
- do not implement a production K/DST adapter against non-commercial content as if rights were resolved;
- do not synthesize 2026 K/DST preseason evidence;
- do not advance downstream K/DST Value/Simulation/Decision/Search authority.

## Resume conditions

The Forecast/Product implementation workstream can resume production-authority work when at least one applicable gate is cleared with durable evidence, for example:

- a second genuinely independent dated historical K/DST raw projection corpus with provenance suitable for calibration;
- explicit production/commercial source permission or licensed provider access satisfying the content-health contract;
- exact Sleeper weekly truth fixtures sufficient to validate remaining D/ST scoring attribution;
- qualifying retained two-source 2026 preseason K/DST raw evidence.

Until then the correct terminal state is:

**BLOCKED — FORECAST / PRODUCT IMPLEMENTATION — EMPIRICAL/SOURCE EVIDENCE GATE**

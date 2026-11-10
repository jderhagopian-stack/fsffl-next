# Sparse production with no projection

A missing ROS row is expected for many developmental and depth players. The
Forecast participation owner now supports a general, scoring-independent
fallback instead of adding player names to an exception list.

Version 1 applies from November 10, 2026 at 13:12:49 UTC. Version 2 applies
from 15:41:53 UTC on that date, with the coarse-injury admission described below.
The policy requires all of the following:

- At least four completed regular-season weeks, with remaining weeks to play.
- A successfully acquired, nonempty full stats response for every completed
  week, with matching season/week and no future capture timestamps.
- At least one successfully acquired current ROS projection source.
- No raw ROS projection rows for the player. Even a partial provider row vetoes
  this fallback; accepted single-source/fumbles completion retains precedence.
- A signed NFL team and known active, inactive, or practice-squad status.
  Version 2 also admits injured/PUP statuses under the same usage and source
  conditions: a coarse injury flag is not a quantitative projection and does not
  veto a transparent low-confidence assumption. Version 1's injury/PUP veto
  remains in earlier replay cutoffs. Suspended, retired and unknown statuses do
  not qualify automatically. Existing official absence, unsigned and IR policies
  remain intact; raw injury status is never rewritten as healthy/inactive.
- No more than five combined passing attempts, rushing attempts and targets
  (or receptions if greater than reported targets), no more than 50 combined
  passing/rushing/receiving yards, and zero offensive touchdowns to date.
  Absolute weekly quantities prevent negative corrections hiding participation.

These are conservative operational thresholds directed by the product policy,
not an empirically fitted prediction of season-long inactivity. Missing player
rows in successful weekly cohorts can support the **assumption** of no additional
production; they are not relabeled as observed zero stat rows. Empty/failed feeds,
insufficient weeks, or an overall ROS outage cannot establish eligibility.
Assumption receipt time is at least the applicable policy admission time; original
stat acquisition timestamps are retained in its evidence identity.

Both season comparison and live Intrinsic Year-1 preparation consume the same
helper. They retain earned actuals and label the remainder as low confidence:
“Little or no production and no projection: actuals only; no additional
production assumed.” This is not an official season-ending absence or a
provider projection. It expires naturally when new evidence or a projection
arrives on a subsequent governed refresh. No manual player admission is needed.

The existing P0/Y2/Y3, Career survival/tail and Shapley calculations remain
unchanged. Supplying the newly admitted Year-1 input can affect their outputs
through their existing dependencies; future contribution is not forced to zero.
Historical source/capture fences, preseason snapshots, scoring and named older
policies are preserved. The policy enters Career dependency identity; comparison
uses version 5 so old saved output is not reused as current-policy output.

The helper retains only bounded per-player counters, seen weeks and capture
metadata from acquisitions already owned by the refresh. It adds no provider
calls, raw-cohort copies, worker, queue, persistence table or request-time fitting.
Repeated comparison reads of a week do not double count its actuals. Receipts
carry exact State/player/week/stat-summary identity and policy provenance.

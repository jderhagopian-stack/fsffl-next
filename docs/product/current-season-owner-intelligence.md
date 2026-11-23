# Current-season owner intelligence

Owner Intelligence leads with this season's completed head-to-head record, current
pick holdings, available draft selections, recent completed moves and short factual
takeaways. The archived franchise résumé remains historical, rather than standing
in for today's team. Record coverage gaps show unavailable; head-to-head results
are not advertised as official standings for formats with additional median wins.

The existing Sleeper history scan retains completion receipts from the transaction
responses it already fetches. Created, completed, source-observed and State cutoff
clocks remain distinct. Only completed actions by the cutoff enter the current
section. Missing completion receipts are retained as a coverage count. Counts are
per franchise participant, not league-wide distinct transaction counts. The existing
profile JSON contains at most 12 recent actions and 64 trade examples per owner.
There are no new tables, source requests, services, caches or economic formulas.

Canonical State owns current results, roster membership and pick inventory. The
read-only API assembles these inexpensive facts without fetching sources or running
models. Draft selections use the admitted résumé where available. Activity can be
updated explicitly through the existing behavioral coordinator and heavy-work gate;
this does not refresh Forecast, Value or Simulation. Older saved profiles remain
readable before their first activity update.

Current completed exchanges supplement the existing shared precedent reader used
by Opportunities, Trade Center and counteroffer search. Only supported pick/player
flow is matched; today's position labels are not historical position proof. An
example must have been observed by the proposal cutoff. Repeated scans retain the
first observation only for an identical receipt, through the existing atomic profile
refresh. Newly observed actions wait for a later State before influencing that
reader. These weaker exchange facts never acquire a reconstructed roster, at-time
record, competitive state or owner intent. Qualified archived contextual cases keep
priority and their original event/prefix admission checks.

Factual pick flow and recent additions still rostered explain how the franchise
changed. They do not establish a willingness to sell, positional surplus, a stable
preference, an acceptance probability or a different valuation. Current bilateral
economics and explicit user direction remain authoritative.

Acceptance: completed-vs-pending/future source actions; separate source clocks;
current and foreign league fencing; canonical record/pick reading; persistence and
first-observation restore; shared consumer use without invented context; no work on
GET; an explicit activity update through the existing job; compact mobile owner
switching and expansion. Real hosted/physical-iPhone acceptance is recorded
separately from fixture browser verification.

# Manual refresh during automatic repair

An automatic reconciliation can repair intelligence for the currently saved
State without loading a new State. A manual Refresh Intelligence request must
also synchronize State. Previously, the same-user coalescer returned an active
automatic job without retaining that stronger request. A week rollover could
therefore leave the saved cutoff unchanged while reporting completion.

The existing reconciliation owner now retains one small synchronized intent
per active user/job. A manual request before execution upgrades the first pass.
A request during a non-sync pass causes one State-sync pass in the same worker
after the first pass returns. Once a sync pass is underway, repeated requests
join it without scheduling additional passes. This is at most two passes and
adds no executor, thread, queue, polling loop, or new lifecycle controller.

Both coalescing checks preserve the manual intent. Ownership is revalidated
before a follow-up pass; existing generation checks still fence publication and
cleanup. Closed intent cannot acknowledge work it will no longer perform: the
brief terminal handoff returns the existing busy-style HTTP 503 with a one-second
Retry-After, allowing a fresh request after completion. Intent entries are removed
by their owning worker, including failure/interruption, without deleting a
replacement owner's intent.

State normalization, exact completed-week checks, first-party fumbles completion,
Forecast reuse, scoring, Intrinsic economics, historical artifacts and publication
rules are unchanged. Fresh State follows the existing canonical loader and its
resource coordinator. Full-season evidence may still reuse when its existing
semantic dependency checks permit it; week-dependent supplements retain their
existing invalidation rules. No production artifact is patched manually.

Regression tests exercise the real POST route with an automatic repair held in
flight, repeated manual taps, a single fresh-State load, matching final State /
Simulation / Value, queued intent, lifecycle interruption, and terminal handoff.
The full-suite job budget is 20 minutes so its unchanged tests and exact-head
checks can finish installation/cleanup: a prior 15-minute run passed every
assertion and both head checks but was cancelled during cleanup. Test contents,
check names, permissions and branch-protection settings are unchanged.

# Beta runtime stability v1

This correction keeps the private beta responsive across deploys and repeated mobile session recovery without changing model authority.

- Canonical league State is checkpointed asynchronously as soon as it is usable.
- Forecast, Simulation and Value checkpoints follow on the same serialized persistence worker so an older partial snapshot cannot overwrite newer evidence.
- Hosted connect reuses already-restored matching league State instead of reacquiring Sleeper data.
- Browser connect/session recovery shares a single in-flight league import and polling loop.
- Existing server coordinator deduplication remains authoritative for queued/running same-league jobs.

This is runtime orchestration only. Forecast, Value, Decision, Search, Simulation and Behavioral model truth are unchanged.

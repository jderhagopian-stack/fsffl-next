# Current Intrinsic readiness reads

Readiness polling must report already-published completion facts. It must not
resolve Forecast compatibility or restore a large Current Intrinsic contract.
Previously the hosted callback called the coordinator's `current()` method,
which pins inputs, resolves a compatibility fingerprint and may restore a
weakly released contract. Serialization of compatibility work did not prevent
these transient allocations from occurring on foreground status requests.

The existing bounded coordinator record now captures a small immutable summary
when a real contract is built or restored: availability/reason, Forecast model
identity, coverage counts, estimate count and target years. It retains no
estimates, Forecast rows, raw inputs or model graph. Releasing the contract keeps
this metadata under the same record eviction/invalidation policy.

Hosted readiness uses `readiness_record_for_state`: an in-memory lookup for the
exact user, league and State. Missing or ambiguous source attempts fail closed;
queued/running/failed states retain their existing meaning. The existing
readiness classifier consumes the full contract or its producer-recorded summary
with identical classification rules. It never substitutes another State's result.

This is not a new source-freshness cache or lifecycle controller. Producers still
pin inputs, validate dependency fingerprints and use staged restoration. Explicit
model readers retain their existing contract semantics. Presentation publication
checks, source rules, numerical models and historical snapshots are unchanged.

Regressions exercise fresh build and durable restore, garbage collection of the
released full contract, concurrent completion reads, a minimal HTTP status harness,
full/partial/unavailable equivalence, scope isolation, ambiguity and invalidation.
Static boundary checks now explicitly reject `current()` in the hosted readiness
callback; absence of a direct `restore_compatible()` call was insufficient proof.

This fix removes a confirmed source of request-time allocation. It does not by
itself explain all retained memory after a refresh or establish that every other
foreground/model-reader path is free of costly work. Those require separate
measurement against the same deployed process.

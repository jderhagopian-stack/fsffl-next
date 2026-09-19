# Performance and Caching Principles

FSFFL NEXT should be designed for high analytical fidelity without unnecessary recomputation.

## Principle: compute by responsibility

Each expensive engine should expose reusable outputs with explicit identities and dependencies. Downstream components should consume those outputs rather than re-running upstream work implicitly.

Examples:

- a player forecast distribution should be reusable across multiple trade candidates when its inputs have not changed;
- a team baseline simulation should be reusable across nearby transaction scenarios;
- market snapshots should be cached by provider, effective time, and normalization version;
- historical state materialization should be cacheable by state identity.

## Cache correctness before cache hit rate

A cached artifact must be invalidated when any material dependency changes. Cache keys should ultimately include the relevant input identities, model versions, parameter/evidence versions, and configuration.

Never reuse a cached result merely because the entity name or league ID matches.

## Incremental computation

Prefer delta/incremental evaluation when mathematically valid.

For example, trade analysis may reuse a baseline team simulation and evaluate the effect of changed assets rather than reconstructing unrelated state for every package.

Incremental methods must be validated against full recomputation to ensure approximation error is bounded and understood.

## Simulation

Large Monte Carlo runs remain appropriate when they materially improve decision quality. The target sample size should be chosen by convergence/error criteria rather than habit alone. Approximately 50,000 simulations is a useful high-fidelity default for important analyses when computationally feasible, but adaptive stopping or reuse may be superior.

## Parallelism

Independent work should be parallelizable at clear boundaries such as:

- provider ingestion;
- player forecast generation;
- candidate transaction evaluation;
- league-wide team analyses;
- historical backtest partitions.

Parallel execution must not compromise deterministic reproducibility where required.

## Performance observability

Material engines should eventually report runtime, cache usage, simulation count, and relevant approximation metadata. Performance regressions should be testable.

## Commercial scaling

Architecture should support moving expensive computation behind asynchronous workers or scalable services later, but NEXT should not introduce distributed-system complexity until justified by real workload.

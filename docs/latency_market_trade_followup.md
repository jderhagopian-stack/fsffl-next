# Market / Trade latency follow-up

Measured on the hosted private beta after PR #125:

- Cold Market workspace: ~15.9s.
- Exact Market workspace cache hit: ~0.24s request wall time; server cache lookup effectively 0s.
- Trade Center browser: ~0.03-0.07s.
- Trade Center analyze: ~12.9s.
- Fresh changed-roster Simulation: ~85.1s.
- Previously observed exact Simulation cache hit: ~1.3-1.4s.
- Previously observed counter frontier: ~315.8s for the current bounded 24-analysis search.

This slice does not reduce simulation fidelity. It removes avoidable Search rebuilds when Market Focus changes by caching the exact full structural candidate catalog. A subsequent performance slice should profile the fresh 50,000-run Simulation kernel and the repeated full-analysis frontier path separately.

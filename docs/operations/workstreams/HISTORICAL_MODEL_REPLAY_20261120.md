# Historical Model Replay — 2026 pre-kickoff recovery (research checkpoint)

Date: 2026-11-20  
Repository: jderhagopian-stack/fsffl-next  
Research branch: research/historical-model-replay-20261120  
Verified base main: 2eaa9fb6526fad607ee12b59e8319743f8fda61e

## Scope and result

Management requested a working Historical Model Replay prototype for the 2026 FSFFL Preseason Almanac. An audit of the existing FSFFL NEXT production database found that the original pre-kickoff modeling results **already exist**. Therefore the first prototype recovers, checks and presents those historical-vintage outputs; it must not silently substitute a new current-model rerun.

Exact pre-kickoff cutoff: **2026-09-10T00:20:00Z**, corresponding to 8:20 p.m. EDT on September 9 (NFL New England at Seattle opener; NFL official 2026 schedule release).

Read-only source identities in project gldxkbqcprzuffgmamxl:

- fsffl.derived_artifact id **65**: live_simulation_analytics, computed **2026-09-09T23:26:17.146824Z**, state as_of **2026-09-09T23:23:55.051114Z**.
- Source scope e58dbab603fdc12f88a18754518d19cad133610916f68980e2dd0768327c7089.
- Source input fingerprint e212bb80bfbfc69ab0fa3a9b0bc9297362256f5c1d953f9a119cee423984ed9a.
- Saved Analytics version next8-live-simulation-analytics-v6:position-strength.
- Simulation model version next4-live-regular-season-v4:empirical-weekly-volatility. Original seed **20260905**, **50,000** trials.
- Current forecast evidence artifact id **63** matches the same saved State and predates kickoff.

## Verified read-only evidence

Queried the existing authoritative rows without any production changes:

1. 12 simulation outcome identities; all have 50,000-trial results.
2. Original simulation probability totals: expected wins **84**, playoff berth probability mass **6**, championship probability mass **1**, first-place mass **1**.
3. All **432** archived player-forecast entries from **216** distinct forecasted players were checked for their as_of/effective_at/retrieved_at timestamps. There were **zero post-cutoff timestamps**; max source effective **2026-09-09T19:40:02Z**, max source retrieved **2026-09-09T23:23:39.444746Z**.
4. Original archived team views contained **237** rostered player ownership pairs and **108** future-pick ownership pairs. Both sets matched the first retained canonical State at **2026-09-10T12:44:36.198236Z** exactly: **0 player mismatches, 0 pick mismatches**.
5. This next-day State is strictly **retrospective ownership corroboration**, not evidence that later football state or forecasts were already known at kickoff. Nothing from that State was used to rewrite the original simulation numbers.
6. The earliest and final pre-kickoff simulation vintages (September 8 and September 9) are both retained. Their estimates are consistent but not identical, demonstrating genuine time-indexed model updates.

## Original source warnings (not normalized away)

- The original weekly means were provisionally equalized across active NFL games, with historically calibrated volatility but not yet direct weekly means.
- Nine rostered active players used the governed conservative position-floor forecast.
- Certain bye weeks had unfilled legal lineup slots; affected weeks score zero for that slot.
- Competitive state was a provisional relative league classification.
- NEXT-3 dynasty Value was **not enriched** in the original simulation; don't label modern 3-Year/Career Intrinsic as historical output.
- An archived zero championship outcome is zero sampled wins in 50,000 trials, **not** proof a team had an impossible chance.

## Prototype implementation and safeguards

A portable read-only research validator and 11 synthetic tests were executed locally and all passed. It accepts an exported archived Analytics row and optional later canonical State payload, checks cutoff/provenance, league/roster/pick identity, original model probabilities, and optional aggregate invariants. Output declares **original_historical_simulation_recovered_not_rerun**, not a modern re-execution.

Original source data are private tenant artifacts and **must not be committed** to this public repository. The full raw production payload was not exported to the local prototype environment; separate real-source SQL checks above were performed against the database. The 11 tests validate the portable adapter on synthetic data, not an end-to-end real-payload decode. That integration is an explicit remaining gate.

The report-specific 2026 PDF and source figures were generated externally for Management review, including actual 2026 championship odds, position strength, and future pick holdings. Neither the PDF nor proprietary raw inputs become a runtime or modeling authority.

## Next acceptance gates

1. Bring the validator into the existing governed persistence/Analytics read path, using the existing tenant auth, bounded DB transport, source licensing and versioned artifact publication. No independent DB client or new worker.
2. Run a private, exact-payload real source decoder against artifact 65 with an authorized/secure fixture. Verify 12 franchise labels against stable historical owner and roster identities (do not guess from current names).
3. Prove artifact selection uses exact cutoff, source provenance and version identity, and rejects post-cutoff sources even when a later model offers better results.
4. Store a small, versioned report manifest and let presentation consume it. Avoid repeated multi-MB raw payload reads; query compact existing subfields.
5. **Separately** research a modern-model reconstruction on the reconstructed 2026 State with date-appropriate Forecast inputs; do not silently reclassify the archived original as such.
6. Later compare frozen preseason forecast outcomes with actual results for backtesting without leaking those results into the original publication.

## Promotion and runtime limits

Research only. No live-site change, no new model, no production data write, no service tier adjustment, no deployment, no new persistence adapter. Normal exact-head CI / Stable and review gates remain necessary before any executable code could be merged or activated.

# FSFFL NEXT — Current-Only FUMBLES_LOST Supplement Implementation Handoff

Updated: 2026-09-26 UTC

## Terminal state
**BLOCKED — FORECAST / PRODUCT IMPLEMENTATION — EXTERNAL PROVIDER RIGHTS / LIVE CREDENTIALS**

The evidence-independent implementation is complete. Production FUMBLES_LOST authority is intentionally not promoted.

## Governing Research
The current implementation is aligned to:
- `artifacts/research/fumbles_lost_current_only_certification_20260926/CERTIFICATION_LEDGER.md`
- `artifacts/research/fumbles_lost_current_only_certification_20260926/NORMALIZATION_UNCERTAINTY_CONTRACT.md`
- `artifacts/research/fumbles_lost_current_only_certification_20260926/IMPLEMENTATION_HANDOFF.md`

Research's shortest technical pair is JerryGM Projections API + LineupExperts Premium In-Season Projections. Those are candidates only. Their external rights/live-access/independence gates remain red.

## Merged implementation
### PR #253
`Forecast: add bounded current FUMBLES_LOST supplement contracts`

- accepted head: `f72690ba56ca08c388a1ea18a7cc768aff4493cb`
- merge: `407050092186b72386f4b264cf675837ebeaa606`
- CI: **1,647 passed**
- PR164 focused corrective regression: success
- Live Forecast corrective trace: success
- Corrective live provider numerical trace: success

This established the separate source/evidence artifact, target-period normalization seam, mixed-vintage lineage concept, selective invalidation plan, and non-regression coverage without registering a production source.

### PR #255
`Forecast: reconcile FUMBLES_LOST supplement with certified Research contract`

- accepted head: `6380dcb68fbdcc8281a3cf87761cca34d691f276`
- merge: `91ee2acef8e8dc8e1f2371d237c9c765f2061ae1`
- CI: **1,651 passed**
- PR164 focused corrective regression: success
- Live Forecast corrective trace: success
- Corrective live provider numerical trace: success

PR #254 was closed unmerged as a stale pre-rebase head after concurrent Research/operations commits landed.

## Implemented contract

### Source evidence
The supplement contract is provider-neutral and 2026/current-only.

Each source record preserves:
- provider and independence-group identity;
- source id/version/locator;
- exact acquisition and effective timestamps;
- source evidence period;
- content SHA-256;
- stage-appropriate private-beta eligibility;
- explicit source-health result;
- explicit exact-lost-fumble semantics;
- canonical player id, position and NFL team;
- raw ROS lost-fumble total;
- provider games represented;
- canonical remaining NFL games at capture.

A source row is rejected when the provider games represented do not equal the canonical remaining-game state. No completed-game actual/projected fumble value is subtracted heuristically.

### Target normalization
The source evidence remains `REST_OF_SEASON`.

The current scorer target remains a separate 17-game season-equivalent current pace:

`source_rate = ROS lost fumbles / canonical remaining games at capture`

`season_equivalent_current = 17 * source_rate`

The existing ordinary offense Forecast is not rebased and is not mutated.

### Material-coordinate authority
The future certified builder requires:
- exactly two accepted sources;
- two distinct independence groups;
- private-beta eligibility;
- source-health pass;
- exact FUMBLES_LOST semantics;
- full two-source coverage for every required player in the governed target universe;
- matching canonical player/team identity.

Missing/absent evidence never becomes zero.

### Uncertainty
The accepted current-coordinate contract is:

`provider_disagreement_std = abs(x_A - x_B) / 2`

`empirical_coordinate_floor = 1.13855744535 lost fumbles`

`supplement_stddev_events = max(provider_disagreement_std, empirical_coordinate_floor)`

Equal source values therefore still retain non-zero uncertainty. The floor is coordinate-specific retained empirical evidence; it does not reclassify the source providers or replace broader season-fantasy-point uncertainty.

### Authority-valid-from / historical boundary
`authority_valid_from = max(source_A.captured_at, source_B.captured_at)`

Hard exclusions:
- `preseason_eligible = false`;
- `annual_preseason_snapshot_eligible = false`;
- `historical_pit_before_authority_valid_from = false`;
- `backfill_allowed = false`.

The supplement is unavailable to any evaluation cutoff before `authority_valid_from`.

### Separate current scoring input
The scorer accepts supplemental observations separately from the immutable ordinary raw Forecast.

It does **not** rewrite the baseline observation's:
- source;
- model version;
- as-of;
- provenance.

When current league scoring actually consumes the supplement, the resulting scored Forecast:
- uses the maximum current evidence as-of/retrieved/effective timestamps;
- carries explicit `supplemental_mixed_vintage_current` lineage;
- preserves both base and supplement lineage in scored provenance.

If the league does not score `fum_lost`, ordinary scoring output is regression-identical.

### Persistence
Staged source evidence uses:
- `current_supplemental_coordinate_evidence`

A future certified target-shape coordinate uses:
- `current_supplemental_forecast_coordinate`

Both are distinct from:
- canonical current Forecast artifact identity;
- annual/preseason snapshot identity;
- league-scoped preseason baseline identity.

### Freshness and reuse
A persisted certified coordinate is reusable only while:
- season remains 2026;
- player/team identity still matches;
- external rights remain eligible;
- source health remains green;
- canonical remaining-game state has not advanced beyond the evidence cutoff.

If any affected team's remaining-game state advances, the supplement becomes stale and must be reacquired. No roll-forward heuristic is authorized.

### Selective invalidation
A new/stale certified FUMBLES_LOST authority state affects only leagues that score `fum_lost`.

Affected current artifacts:
- current Forecast;
- Forecast-dependent Simulation;
- Forecast-derived team intelligence.

Explicitly preserved:
- immutable annual/preseason evidence;
- league-scoped preseason baseline;
- independently governed current Value.

Leagues that do not score `fum_lost` are not invalidated.

## Production authority deliberately unchanged
No implementation in PR #253 or PR #255:
- registers JerryGM;
- registers LineupExperts;
- registers SportsDataIO or another fallback;
- acquires a paid/authenticated provider payload;
- claims written provider usage rights;
- claims LineupExperts independence;
- promotes a production FUMBLES_LOST coordinate;
- changes the ordinary retained offense Forecast;
- changes preseason/PIT history;
- restores current FSFFL Simulation by fabrication.

Because the new code has no production source adapter/registration, deployment would not activate the supplement and is not an authority step.

## Exact external dependencies
Implementation cannot legitimately continue to production acquisition/promotion until Research/source governance receives:

### JerryGM
- authenticated API access for the current full QB/RB/WR/TE pool;
- written permission for the narrow two-source derived-supplement use.

### LineupExperts Premium
- paid ROS API access;
- FSFFL private-beta registration/permission for minimal persistence and derived use;
- written confirmation that Premium NFL projection output is LineupExperts-generated and independent of JerryGM.

### Governed live capture
After rights/access clear, one live acquisition must validate:
- exact request identity without secrets;
- captured/generated/effective times;
- source versions/content identity;
- row counts and canonical match/duplicate/unmatched counts;
- exact two-source per-player coverage;
- provider remaining games versus canonical schedule;
- zero versus missing semantics;
- normalized current pace and disagreement distributions;
- final `authority_valid_from`.

Only then may Implementation add source adapters/runtime acquisition, persist the certified coordinate, selectively invalidate/rebuild affected current Forecast/Simulation, and run production FSFFL acceptance.

## Operating-protocol terminal
There is no additional authorized implementation action that can create valid provider rights, paid credentials, live full-pool coverage, or independence confirmation.

**BLOCKED — FORECAST / PRODUCT IMPLEMENTATION — EXTERNAL PROVIDER RIGHTS / LIVE CREDENTIALS**

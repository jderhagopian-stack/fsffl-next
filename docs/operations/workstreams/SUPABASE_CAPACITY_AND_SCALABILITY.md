# Supabase Capacity & Scalability Recovery

## 2026-10-08 — Tranche C dependency-authority DESIGN GATE CLOSED / NO-GO on whole-publication guard

**Management decision input:** The immediately preceding C conditional implementation STOP was ACCEPTED. A narrowly bounded dependency-authority investigation was authorized; **no C skip/coalescing implementation or deployment** authorized. Started from canonical GitHub main `371d48642212f8e6d0e3df0629cfe662251235a9`; live Render remains B merge `3f079ca6df48fbae3e6adb83fa3df877dc05f1b1` / deploy `dep-db3ruiqjnfac738ibiag`.

**Decision: NO-GO / ABANDON the proposed pre-builder whole-publication C no-op as currently conceived.** Existing cheap immutable metadata is not a COMPLETE authoritative freshness fence for every surface. The benefit under proven-safe conditions is **zero certified redundant publications / zero realizable C savings**; building a complete source-watermark service to create the missing signals would be a separate architectural/product-policy project, not narrow C work.

**Exact Current inputs traced (production code, not guessed):**
1. Governed ROS projections: `persistent_webapp._current_position_depth_provider` calls `build_governed_current_position_depth` → `build_governed_in_season_outlook` → `build_in_season_forecasts`. Runtime fetches current Razzball and CBS rest-of-season projection snapshots from providers, normalizes/equal-weight ensembles, scores under canonical league rules, applies explicit FUMBLES_LOST and preseason remaining-prior gap policies. `projection_snapshot` retains metadata (`provider, season, horizon, week, period_start/end, source_version, usage_class, effective_at, retrieved_at, content_fingerprint`), but `save_revision` is invoked **after live provider acquisition and normalization**. The last persisted provider fingerprint is not proof that another provider revision is not available.
2. Completed actuals / calendar: `SleeperWeeklyStatsSource.fetch_nfl_state` selects completed week using season/week/display_week/leg; `load_completed_actuals` calls live `fetch_week` for each finalized week, transforms raw stats into league-scored fantasy points. `SleeperWeeklyStatsSource.source_version` names the adapter, not a cheaply persisted content revision of each weekly-stat response; corrected provider stats can alter Current under fixed State and fixed ROS keys. Captured_at/effective week and `evaluation_as_of` can also advance without canonical State changing.
3. Preseason prior: `load_preseason_season_forecasts` reuses governed immutable `preseason_forecast_baseline` / annual preseason artifact (currently one retained immutable league preseason baseline); its `input_fingerprint` and model/version are cheap candidates, but they cover this one family, not current ROS or completed actuals.
4. Scoring and lineup: canonical State carries league scoring/roster rules; `CURRENT_POSITION_DEPTH_MODEL_VERSION` and in-season ensemble/scoring/fumbles/prior model versions, lineup slot config and `optimize_team_lineup` algorithm/policy determine the output. These are mostly static or State-scoped, not freshness substitutes.
5. Team and publication: selected `user_id`/`league_id`/`selected_team_id`, State, exact publication generation, full eight-surface manifest metadata, hash/size, invalidation and durable exact snapshot availability must survive. `known_snapshot_available` is only a process-local hint; `has_snapshot` metadata validates presence, not content hash on read. Readers verify actual payload hashes when consumed. Manifest-last plus published pointer and last-good require separate governance.
6. Intrinsic/Dynasty: coordinator `IntrinsicBuildRecord` includes State, forecast coordinate, intrinsic input fingerprint, status (queued/running/completed/failed), contract availability, timestamps/error and source contract. Late completion can alter Dynasty and both Value Lens surfaces. Recorded `started_at`/`updated_at` changed across the three completed-status publications, so timestamp-only equivalence remains consumer-policy dependent. `market_workspace` wraps process-local cached payload with a fresh `workspace_cache_elapsed_ms`; this is operational timing, not model evidence, yet changes the exact served contract.

**Known 3-publication proof at the same State/selected team/core F/S/V identity** (UTC 14:50, 15:40, 16:08):
- Latest retained ROS projection versions recorded before each publication: CBS content fingerprint prefixes `4a503eff...` → `c5336fb0...` → `7f75b9eb...`; Razzball `d60714af...` → `f1664840...` → `f1664840...`. They change exactly along the two publication transitions. This timestamp-ordered proximity is strong supporting evidence, **not** a direct per-request source-trace guaranteeing which row was consumed.
- Actual saved `league_team_views.current_position_depth`: transition 1 changed 9 player `season_outlook_points`, 24 slot `strength_index` and 24 league averages plus 4 slot expected-point values; transition 2 changed 2 further player outlook points. Other surface changes previously classified (Market intrinsic execution timestamps; workspace elapsed-time). A read-only SQL regression assertion confirms **2/2** consecutive transitions have identical State/team but changed Current player values; State/core-only guard would produce false-positive skip opportunities.
- Deterministic dependency-decision counterexample harness (8 checks PASS, no runtime production code): rejects both observed changed ROS-version transitions; rejects synthetic completed-stat revision with identical ROS/core, managed-team switch, intrinsic completion status change, missing certified manifest, and missing actuals revision metadata; permits an entirely equal synthetic complete signature *only assuming all required fields exist and are up-to-date*. This verifies fail-closed requirements; **it does not establish actual cheap metadata availability** or live full-product equivalence. Test artifact is a local design analysis, not a merged production test.
- Immutable projection history contains 2026 ROS CBS 28 snapshots/28 distinct fingerprints and Razzball 21 snapshots/20 distinct fingerprints. These are useful post-acquisition/audit versions, not pre-acquisition provider watermarks. No provider refresh was initiated during this gate.

**Economic/scale judgment:** Earlier 169 published records → 40 equal core groups (129 extra generation IDs) and the 17-generation example are *candidate* repetitions, NOT 129 or 16 safe skips. Three example 8-surface publications each ~3.08MB encoded/~541KB JSONB datum. Eliminating two would be a theoretical upper reduction of 16 surface writes, ~6.16MB encoded/~1.083MB JSONB payload datum, but those two contain material Current differences, so **realizable certified saving = 0**. Building cheap up-to-date revision authority for provider weekly stats, independent ROS snapshots, intrinsic lifecycle and consumer-visible metadata would incur new persisted versions/fetch policy and process/race complexity, contrary to C's no-second-controller/no-refresh-change scope. No blanket C ROI extrapolation is defensible.
- Supabase physical database **590,605,459 bytes** (read-only check), ~53.7MB above a 512MiB numerical comparison, with `runtime_presentation_surface` **2,509 rows / 154,089,092 bytes** of JSONB payload datum (not whole-table disk or safely reclaimable). Additional last-good rows are independently protected. C does not reclaim historical disk even if a future guard reduced new writes.

**One recommended next gate, not authorized here:** close/refrain from C publication skipping and seek **separate Management authorization for a read-only, non-destructive presentation-generation reachability and storage-bytes audit**. Prove which older `runtime_presentation_surface` payloads are reachable via exact manifest, published pointer, served last-good, restore, Dynasty copied source metadata, and historical PIT/replay before even proposing generation-specific compaction/retention. The result would be a capacity decision for the largest payload family without premature deletion. This is evidence-only: **do not implement D/E/F, migrate, compact or delete anything without a fresh directive**. D (payload-read reduction) may help egress but by itself does not fix the physical-size overage. Issue #436, Career #405 PR2, model, refresh policy and paid tier remain outside scope.

**Terminal:** DIRECTIVE COMPLETE — C DEPENDENCY-AUTHORITY DESIGN GATE; Management recommendation **NO-GO on C whole-publication skip**, preserve A+B. No new deployment, no provider refresh, no destructive action, zero C savings.


## 2026-10-08 — Tranche C CONDITIONAL IMPLEMENTATION STOP / DEPENDENCY-INTEGRITY GATE (NO BYPASS CODE)

**Management authority:** A and B ACCEPTED; C narrow implementation conditionally authorized *only after* complete pre-publication semantic dependency proof. Investigated current main initially `7db94b52474d08022dac9d5f1db9c0caa528ef20`, deployed runtime remains `3f079ca6df48fbae3e6adb83fa3df877dc05f1b1` / Render `dep-db3ruiqjnfac738ibiag`. **Disposition: BLOCKED — C skip cannot be safely enabled** because the core State/Forecast/Simulation/Value/selected-team tuple does not fully determine presentation outputs. No code change, skip, PR merge, full Refresh Intelligence run, production deploy, migration, paid tier or data removal.

**Definitive 3-generation investigation** (one identical State prefix `d62d1fa57f39540e`, same managed team, same Forecast/Simulation/Value fingerprints, 8 surfaces generated at 14:50:15, 15:40:47, 16:08:00 UTC): JSONB key-by-key read-only comparisons reveal:
- `franchise`, `home`, `league_atlas`, `league_dynasty_position_rooms`: ONLY top-level `publication_generation_id` differs. This comparison does not grant permission to skip the whole publication.
- `league_team_views`: `current_position_depth.forecast_as_of` differs across both transitions; `players[].season_outlook_points` changed for **9 players** in first interval and **2** in second; `strengths[].league_average_expected_points` and `strengths[].strength_index` changed in **24** entries each in first interval, `strengths[].expected_points` changed in **4** entries. These are material numerical differences, not only timestamp/generation noise.
- `market_value_lenses_all` and `market_value_lenses_rostered`: `intrinsic_execution.started_at` / `updated_at` vary; `intrinsic_execution.status` stayed `completed` in all three. Treat as potentially meaningful lifecycle freshness until an explicit policy defines equivalence; never hide pending/late completion.
- `market_workspace`: `execution.workspace_cache_elapsed_ms` varies, an operational-time field. It may be excluded from semantic evidence *only after* consumer contract acceptance; it still changes the published payload.
- Fundamental gap rooted in accepted Current authority: `_current_position_depth_provider` in `src/fsffl/product/persistent_webapp.py` explicitly states **ROS and completed-week evidence can advance while LeagueState remains unchanged** and must not be State-cached. It calls `load_preseason_season_forecasts` and `build_governed_current_position_depth` with a history writer; `current_position_depth.py` calls `build_governed_in_season_outlook`, recomputes season forecasts and jointly optimized lineups. No existing cheap, persisted *complete* authoritative freshness identity for these external inputs was demonstrated ahead of builder invocation. The core Forecast hash cannot certify these Current numbers. Pre-existing metadata also does not prove that background Dynasty/intrinsic execution freshness is unchanged.
- Measured materialization opportunity (NOT realizable under this gate): three 8-surface publications summed ~9.244 MB logically encoded JSON, ~1.624 MB `pg_column_size(payload)` JSONB datum storage; a hypothetical two-generation elimination would affect 16 surface writes / ~6.16 MB encoded, **but both generations contain meaningful differing Current evidence**, so **0 safe-to-skip publications / 0 measured SQL and storage savings** from Tranche C here. Do not report those upper bounds as achieved benefits.

**Draft documentation PR #438 reconciliation:** PR `#438` head `1baac7a3879d7229fc42dc049ad28bf35ede67ff` based on stale pre-C main `361ae91b4a9ef5d129c5c23e03c1d3c2297e604f` proposed corrective *read-only* Tranche B Market SQL counts. Verified actual `pg_stat_statements` query shapes: 300-VALUES 3 calls/300 inserted, 235-VALUES 2 calls/0 inserted, 239-VALUES 1 call/239 inserted; legacy 1-VALUES 329,447 calls. Relative to pre-refresh 1x300+1x235 (both zero inserts), the later explicit refresh used **2x300 + 1x235 + 1x239 = 1,074 attempted observations in 4 SQL statements** and **539 inserted**; market row count **169,923**, **539** stamped 16:25:47.737449 UTC. The previous 1,070 / zero-retained claim in historical handoff was incorrect and is superseded. Correct facts incorporated here *additively* without replacing newer canonical C forensic findings. #438 must not be merged as-is against newer documentation.
- PR #438's docs-only stable full suite failed **1 test** (`test_browser_manual_refresh_joins_auto_refresh_and_reaches_usable_core_layers`): 2,247 passed, 1 failed, 1 warning; current RSS `537,247,744` B exceeded `536,870,900` B gate by **376,844 B**, with 169.43s run. Focused `CI / test` passed. No product/algorithm changes existed in this documentation PR, so the failure cannot be attributed to a new C skip or code diff; it is still a real failing resource gate and **must not be waived or labeled a proven flake**. Separate CI/runtime memory method diagnosis is appropriate when authorized; do not rerun full suite or weaken gates in C investigation. Production heavy-refresh peak `440,963,072` B remains above `429,496,720` B internal budget.
- Tranche C dependency prerequisite before any reauthorization: produce **cheap authoritative source-version coordinates** for preseason forecast rows, ROS/completed-week observations and Current projection source policy/lineup model, plus exact Dynasty/intrinsic execution status/contract and Market workspace operational metadata semantics, without hashing bulky payloads foreground. Confirm completeness with targeted changed-Current/same-core evidence tests, late Dynasty completion, team switch and manifest-last crash/fencing tests. If all dependency coordinates are complete and certified existing manifest/surfaces remain accessible, consider bounded no-op guard *inside existing owner* with ambiguous cases falling through; otherwise full original publication path. Do not conflate no-op guard with permission to suppress State history, PIT Market first writer, last-good or publication fences.
- **Terminal status:** MANAGEMENT GATE — C dependency completeness NOT PROVEN; C implementation safety condition failed. A+B accepted and retained. Tranches D-F, Career #405 PR2, issue #436, paid tier, deletion/retention, migrations, model and refresh policy remain separate. DB allocated `590,605,459` B (last C evidence check) above Free quota; zero physical storage reclaimed.



## 2026-10-08 - Tranche C EVIDENCE GATE COMPLETED (Management decision required; NO BYPASS CODE)

**Authority/status:** Management ACCEPTED A+B, authorizes Tranche C *measurement/classification only*. Exact investigated GitHub main `361ae91b4a9ef5d129c5c23e03c1d3c2297e604f`; Render still live Tranche B commit `3f079ca6df48fbae3e6adb83fa3df877dc05f1b1`, deployment `dep-db3ruiqjnfac738ibiag`. No changes to production, SQL, model, refresh policy, retention, billing, or Career #405 PR2. This entry is documentation only.

**Core distinction: unchanged published evidence versus truly changed evidence under fixed State.**
- The production user's retained `runtime_published_intelligence_generation` manifests contain **169 generation records but only 40 distinct (State, selected-team, Forecast fingerprint, Simulation fingerprint, Value fingerprint) groups**. That leaves **129 extra generation IDs** sharing an earlier core-evidence coordinate, across 29 repeated groups. They are *candidate repetitions*, not 129 proven safe no-ops: presentation status/Dynasty/team/last-good semantics must be checked independently. Across the whole database, 311 generation records / 153 such groups, 37 repeated, 158 excess IDs.
- One exact recent State (fingerprint prefix `d62d1fa57f39540e`) and selected team contains **17** successive distinct published-generation IDs using **one** unchanged Forecast/Simulation/Value fingerprint triple over 2026-10-07 11:30 through 2026-10-08 16:24 UTC. Recent presentation snapshots for the same State at **14:50, 15:40, 16:08 UTC** each wrote eight surfaces, with logical encoded payload sizes **3,081,506 / 3,081,483 / 3,081,485 bytes**, and JSONB datum sizes **541,442 / 541,467 / 541,461 bytes**. The three complete groups total ~9.244MB logical JSON and ~1.624MB JSONB datum storage. Removing only the top-level generation field, **4 of 8 surface families had identical normalized payloads** across all three; four still differed and cannot be declared unchanged without mapping nested publication/semantic dependencies.
- `PresentationContinuityStore.promote` at `src/fsffl/product/presentation_continuity.py` derives fresh `promotion_id = canonical_fingerprint(State, now.isoformat(), surfaces)`; it then builds/JSON-roundtrips every surface and persists generation-specific wrappers before upserting a State-keyed manifest. A new timestamp produces new generation identity even if core evidence and much presentation content are identical. The State-keyed manifest itself is updated; prior generation-specific surfaces persist. Never treat their historic reachability as disposable without explicit separate evidence.
- **Changed evidence under the same State is real**: two historic exact State scopes (prefixes `614ac5b71f1deee` on Sep 28 and `4c1ca1d0642a1c9` on Sep 30) each have *two distinct* Forecast, Simulation, and Value artifact fingerprints. Underlying semantic drift versus timestamp/provenance changes was not determined, so both must remain authoritative candidate versions. The Oct 8 16:24-16:25 refresh then crossed from old State prefix `d62d...` to new State prefix `e431...`, with distinct Forecast/Simulation/Value fingerprints: unequivocally NOT a same-State no-op.
- For production artifacts, Forecast has **397 rows / 395 distinct State scopes**, Simulation **295 / 293**, and Value **357 / 355**. Avoid a blanket assumption that core artifact proliferation is mainly many same-State variants; most stored core artifacts are bound to different State coordinates.

**Write amplification and performance (different measurement types):**
- `pg_stat_statements` cumulative `derived_artifact` UPSERT query shape **11,559 executions** (stats reset Sep 8). `pg_stat_user_tables` cumulative derived tuples **5,977 inserts and 5,583 updates**, live retained **5,645**. League snapshots show 1,463 updates against two inserted rows; team snapshots show 17,545 updates against 24 inserts (database-wide since stats reset Aug 25). These demonstrate repeated writes to keys but not that every UPSERT/update was semantically unnecessary or attributable to one specific refresh; updates can carry required State/team or timestamp information. Old/new same-key full payload re-encoding is not instrumented directly.
- Immutable PIT State history: **445 rows, 445 distinct State hashes, zero additional (league,State) versions**; do not suppress it. Market first-writer PIT persistence and published-generation manifest-before-pointer/last-good ordering remain mandatory.
- Latest explicitly requested hosted refresh trace around Oct 8 16:20-16:26 UTC: raw replay history discovery **114.897s**, Simulation kernel/aggregation **21.398s**, persistent artifact encode/write phases **2.149s, 1.986s and 2.911s**, last listed atomic manifest/pointer phases **0.728s and 0.727s** (one intermediate working checkpoint showed 0.000s). Max logged process RSS **440,963,072 bytes**, above internal work budget **429,496,720** but below Render hard limit **536,870,900**. These phases include genuinely new evidence/State and are not all avoidable C work.
- Stored JSONB datum size by top logical families: presentation surfaces **2,509 records / 154,089,092 B**; Forecast **397 / 63,057,386 B**; Simulation **295 / 27,491,129 B**; supplemental forecast coordinate **294 / 25,732,613 B**; Value **357 / 19,298,066 B**. `pg_column_size(payload)` is NOT network bytes/WAL or whole-table physical allocation. Latest measured DB allocation **590,605,459 B**, still over Supabase Free 0.5GB quota. No reclaim attempted.

**Cause classification (confidence):**
1. HIGH: presentation generation ID is always time-derived, forcing new surface keys, encoding and writes without a pre-promotion identical-dependency short circuit.
2. HIGH: `persist_runtime_snapshot` writes State/team and all present Forecast/Simulation/Value/last-good/manifest on published terminal checkpoint; `put_artifact` is unconditional `INSERT ... ON CONFLICT DO UPDATE`, including same-key updates. The per-user executor coalesces *queued* same-State checkpoints but not already-running checkpoints or later equal contexts; write attempts can recur.
3. HIGH: truly changed State and same-State fingerprint variants exist; they **must not** be suppressed by State-only rules.
4. UNRESOLVED: how many same-core-evidence presentation differences are meaningful nested readiness/Dynasty updates versus only generated IDs; number of duplicate full-payload encodes per user-journey and exact WAL/billed egress saved cannot be deduced from aggregate statistics.

**Bounded C implementation proposal - NOT authorized in this gate:**
- Within the **existing single publication owner**, before calling expensive presentation builders or generating a *new* promotion ID, compare latest already-governed publication metadata for exact (State, selected-team, Forecast fingerprint + version, Simulation fingerprint + RNG/contract version, Value fingerprint + version, and relevant presentation/Dynasty completion/contract dependencies). If all predicates are proved identical **and** manifest/surface integrity is confirmed, reuse the certified existing generation without changing user publication fence or refetching bulky payloads. Do not introduce a new lifecycle controller or foreground hash. Absence/ambiguity => execute original path.
- Assess same-key derived artifact UPSERT suppression only as a second narrow option AFTER data-authority and `computed_at` timestamp semantics are proven safe. Never short-circuit historical State writes, necessary last-good recovery, managed-team identity, new evidence under unchanged State, publication manifest-first/pointer-last atomic fences, required replay lineage, first-writer Market records, or Dynasty late completion.
- Focused proof suite before any future promotion: no-op same-semantic republish, same State *different* Forecast/Value/simulation/Dynasty, team switch, startup restart, last-good missing/invalid, manifest crash windows, stale request, partial failure, PIT history continuity, no-silent-heavy-refresh; one stable-head full-suite gate only if separately authorized. Collect per-attempt source dependencies, actual writer/encode count, JSON bytes, SQL attempts, p95 latency, peak RSS and absent/superseded status with comparable hosted workload. Upper observed same-State footprint of *two* additional 8-surface groups = 16 materialized surfaces and ~6.16MB logical JSON; not a promised saving because not all differences are classified.
- Decision: **Management Gate / evidence complete; request separate authorization for narrow C implementation**, conditional on proving presentation dependency completeness without heavy foreground hashing. Do not begin C bypass, D-F, Career PR2 or storage cleanup automatically.


## 2026-10-08 — Management ACCEPTS Tranche B; authorizes Tranche C evidence gate only

**Management disposition:** ACCEPT Tranche B. PR #434 stable-tested head `48d78375cce957dca5faee71a8c39108c3e006a2` passed the one stable full suite `37805666770` (**2,248 passed / 1 warning**), squash-merged as `3f079ca6df48fbae3e6adb83fa3df877dc05f1b1`, and is live on Render `dep-db3ruiqjnfac738ibiag`. The accepted set-oriented writer preserves the original five-part conflict key, first-writer lineage, PIT history, publication ordering and tenant/model authority.

**Live end-to-end confirmation:** Management intentionally invoked one normal Refresh Intelligence action from authenticated iPhone/Safari. The refresh completed through Forecast, Simulation, Value, Intrinsic reconciliation and `publication_complete` at ~16:25:55 UTC. PostgreSQL cumulative statement evidence after that journey showed the Tranche B multirow INSERT shapes executed as **2x 300-row + 2x 235-row statements = 1,070 market observations attempted in 4 SQL statements**, while `ON CONFLICT DO NOTHING` retained **0 new rows** because the exact market identities already existed. The legacy one-row INSERT shape did not need to execute once per observation. This is real hosted-path evidence and reinforces the previously measured ~99.6% SQL-attempt reduction without changing retained market history.

**Standing Tranche B regression boundary:** future Market persistence must not silently return to one SQL INSERT per market observation under comparable publication work. Preserve bounded deterministic chunking, exact idempotent conflict semantics and first-writer lineage. A material regression in statements-per-observation, transaction/RSS behavior, or bypass of the batch PersistenceStore boundary reopens this narrow gate before promotion.

**Physical side finding, separate from B:** during the same refresh, Player Intelligence briefly returned HTTP 500 because `IntrinsicBuildSuperseded` escaped the route while execution State ownership advanced. History remained 200, the refresh itself completed, and the same Player Intelligence surface worked after publication. GitHub issue **#436** tracks the required graceful supersession handling. Do not conflate this lifecycle/UI defect with Tranche B persistence correctness.

**Resource note:** the explicit full refresh reached observed process peak RSS **440,963,072 bytes**, above the internal heavy-work budget **429,496,720** but below the Render hard limit **536,870,900**. This does not invalidate B's narrow persistence semantics, but it remains a current capacity signal and must not be erased from later scale claims.

**Next authorized work — Tranche C evidence gate only.** Do not implement skip/coalescing behavior yet. First measure and classify redundant materialization under current A+B production behavior: counts of same-State/same-evidence republish attempts, exact semantic fingerprints/invalidation coordinates, changed-evidence-with-same-State cases, artifact encode/UPSERT attempts, publication chronology, and affected bytes/RSS/latency. Use existing hashes/metadata where possible; do not add a second lifecycle controller or heavy foreground hashing. Return to Management with evidence and a bounded C implementation proposal. **Tranches D-F, deletion/retention, paid Supabase, migrations, refresh-policy changes, and Career #405 PR2 remain paused.**

**Capacity remains unresolved:** PostgreSQL physical allocation remains above the Free 0.5GB quota (latest B closeout ~586.4MB before the explicit refresh). A and B reduce ongoing waste; they do not physically reclaim historical bytes. No cleanup or reclaim action is authorized here.




## 2026-10-08 — Tranche B live acceptance closeout; Management review

**Worker recommendation: ACCEPT Tranche B only**, pending explicit Management promotion. Tranche A previously ACCEPTED by Management. Stable-tested PR #434 head `48d78375cce957dca5faee71a8c39108c3e006a2`, full-suite run `37805666770` **2,248 passed / 1 warning / 87.03s**, exact-head verified. Squash merge **`3f079ca6df48fbae3e6adb83fa3df877dc05f1b1`**, Render deployment **`dep-db3ruiqjnfac738ibiag`** LIVE on Free service `srv-dae6k7vqj5pc73af7bt0`.

**Bounded batching / preserved contract.** `src/fsffl/persistence/postgres.py` adds `append_market_value_snapshots` using up to **300 deterministic ordered VALUES** rows per transaction, original exact five-part conflict key, `ON CONFLICT DO NOTHING`, and earliest input lineage on within-chunk collisions. Individual append remains; `src/fsffl/persistence/session.py` routes published Market observations through batch when supported and retains individual-writer fallback. No PIT, provenance, as_of, recorded_at, value, scale/context, tenant, first-writer or atomic publication semantic changes. No schema, migration, provider refresh experiment or model modifications.

**Automated and backend gates.** Focused tests on exact head and full suite passed. Deterministic 540-record fixture: 540 original SQL statements versus 2 batch statements; exact row, value, timestamp, context, lineage equivalence and rerun idempotence; duplicate conflicts inside/between chunks, partial second-chunk failure with first committed chunk preserved, 1,201-input deterministic chunk bound and Python memory <20MiB. Independent isolated real PostgreSQL two-conflict VALUES rollback probe passed with original first-writer retained during subtransaction, and **0 residual probe rows** afterwards. Not a Render-credential write test by itself.

**Actual hosted post-deploy evidence.** Natural startup/restore with actual pooled Render credentials produced two new `pg_stat_statements` market INSERT SQL shapes: **300 and 235 VALUES records; 1 execution each** (`224.12ms` + `127.64ms` server execution), **0 new rows** due idempotent first-writer conflicts. Legacy one-row statement count **unchanged at 329,447 calls**. This proves actual hosted B path; measured SQL attempt savings against legacy writer's 535 calls: **535 -> 2 (-99.626%)** for this workload. Market table **169,384 retained rows**, PIT States **444**, latest recorded market observation unchanged; no history or accepted lineage removed or overwritten.

**Matched startup restore:** Tranche A 14:49 UTC vs B 16:07 UTC, identical 25 persistence reads in same order and **22,318,183** logged serialized bytes. Restore 7,987.60 -> 8,114.12ms (small variance); persistence-read p50 344.51 -> 297.18ms, p95 1,200.87 -> 1,107.31ms. Combined derived-artifact write phase 11.920 -> 1.867 seconds (cannot assign the full duration difference solely to batching). Forecast/Simulation/Value complete, product readiness full; no inspected B app warnings/errors. B peak process RSS **346,505,216** bytes versus A **335,355,904** (+11.15MB), below budget **429,496,720** and hard limit **536,870,900**. Aggregate Supavisor 3-minute startup window A auth 5/term 2/log events 10/message chars 453; B auth 2/term 1/events 4/message chars 179. This is project-wide, not app-only connections or billed log bytes. Pool checkout/wait/error counters were not available in Render logs; no numerical claim is made for them, or for database SQL p95 under broad traffic.

**Critical capacity limitation:** allocated PostgreSQL physical bytes `584,715,411` pre-B and `586,435,731` after normal B startup; still above 0.5GB Free quota. Tranche B corrects prospective market SQL amplification, not existing physical storage. No cleanup, migration, new model, refresh policy, paid Supabase, Career #405 PR2, or **Tranches C-F** is authorized by this closeout. Management must separately approve any next tranche or capacity reclamation. Live runtime remains B merge SHA, regardless of subsequent docs-only commits.


## 2026-10-08 — Management ACCEPTS Tranche A; authorizes B ONLY (active draft)

**Authorization.** Management explicitly ACCEPTED Tranche A pooled transport and closed Gate 2 on its naturally occurring hosted publication evidence. Accepted live identity: PR #433 tested `8d3c17cdf0f9f81cc4360f3c85f76845c151cbe8` (2,240 tests), merge `1c5b5325791cddaf49d35d372270a9aba0586afb`, Render deploy `dep-db3qq4vlk1mc73cj3910`. Batching alone is now the P0 execution priority. **Tranches C-F and Career #405 PR2 remain paused.** No paid tier, deletion, migration, refresh policy, provider experiment, or model/analytics work.

**Tranche B implementation:** `work/supabase-tranche-b-market-batching-20261008`, draft [PR #434](https://github.com/jderhagopian-stack/fsffl-next/pull/434), based on main `29d2395c213829ed9fbcbf648d552c96089f0c05`. Only three runtime files are affected: (1) immutable `MarketValueSnapshotRecord` and batch PersistenceStore protocol; (2) `PostgresPersistenceStore.append_market_value_snapshots` performs deterministic <=300-row multirow VALUES, parameterized, each bounded chunk in one transaction, exact original five-column `ON CONFLICT DO NOTHING` and preserves earliest lineage for duplicate keys; (3) `persist_runtime_snapshot()` routes published market estimates through batch when supported, falling back to the individual method for legacy/custom stores. Same per-estimate mean/time/scale/market_context/evidence sources, unchanged publication order. No schema or market history rewrite. Existing individual append remains unchanged. No retry after SQL execution or implicit batch rebuild.

**Validation plan:** focused 540-row simulation of SQL rows comparing legacy 540 separate statements with two <=300-row multirow statements, first-writer conflict within and across chunks, rerun idempotence, partial-failure first-chunk durable/second-chunk rolled back, full value/timestamp/lineage equality, deterministic SQL, 1,201-row bounded memory, and actual caller publish_context/legacy-fallback tests. These prove mocked DB SQL semantics, not yet live backend performance. One stable-head full suite only after focused CI and final draft candidate. No deployment before exact-head gate. Hosted acceptance must not trigger provider refresh or broad publication; rely on natural live market writes where available, additionally bounded rollback-only database checks if safe/needed. If actual pooled batch cannot be verified without forbidden heavy work, return an explicit Management gate rather than claim success.

**Before B (read-only snapshot Oct 8 15:57 UTC):** Supabase allocated `584,715,411` bytes (~558 MiB), `169,384` retained market_value_snapshot rows, `5,617` derived_artifact rows, `444` State history records. Cumulative historical simple `INSERT market_value_snapshot` shape: `329,447` calls; `169,385` rows affected (cumulative statistics may exceed retained counts); mean SQL execution 0.939 ms, total 309.4 sec. Hypothesis at ~540 estimates/valuation: legacy 540 SQL statements -> 2 batch SQL statements (99.63% reduction in SQL statements), BEFORE accounting for pool/transaction overhead; only measured in fixture until verified live. Cumulative counters do not directly reveal current rate. **Physical ~585 MB storage remains over Free Plan quota; B does not reclaim it.** No retention/compaction is authorized.

**Status:** DRAFT IMPLEMENTATION / focused CI; production still **Tranche A**, no B deploy or data changes; no C-F approval.


## 2026-10-08 — Tranche A live hosted-write acceptance reconciliation (Management review; B-F NOT AUTHORIZED)

**Recommendation: ACCEPT Tranche A transport / close Gate 2 natural-write proof.** No manual operator telemetry POST is necessary. Live host identity: PR #433 tested head `8d3c17cdf0f9f81cc4360f3c85f76845c151cbe8` (stable suite `37781664575`: 2,240 passed, 1 warning); squash merge **`1c5b5325791cddaf49d35d372270a9aba0586afb`**, Render deploy **`dep-db3qq4vlk1mc73cj3910`** live on service `srv-dae6k7vqj5pc73af7bt0`, Free one instance / one Uvicorn worker. Protected DB transport independently confirmed by Management: Supavisor shared session pooler on port 5432; no secret disclosed. Pooled mode is default absent explicit legacy override; no environment change in deployment. The opening pool itself did not emit a counted checkout metric in available logs.

**Gate 2 substitute proof (stronger than a telemetry-response-only assertion):** same hosted Render startup/restore `restore_id=325ad471-a88a-4cc3-86b9-574dc882e69a` logged phase `persistence.derived_artifact_encode_and_write` (finished 14:51:49.022 UTC) and `persistence.atomic_manifest_and_pointer` (finished 14:51:49.641 UTC), while independent Supabase reads identify saved artifacts dated 14:50:09-14:51:49 UTC: 8 `runtime_presentation_surface`, 1 presentation manifest, current Forecast/Simulation/Market evidence, published generation, last-good user and league bundles, player-future continuity. Normal live workload supplied writes; no probe was injected. `FSFFL_TRANCHE_A_GATE2_20261008_PR433_8D3C17_C7A91F3E` has **0** matching telemetry rows, so no delete or clean-up action is required. No artificial refresh/analytics change initiated by the acceptance investigation. Market snapshot rows 169,384; PIT State rows 444 in the observed aftermath. Projection observation count increased from 91,563 to 96,837 in natural runtime activity, NOT attributable to the probe (there was none).

**Matched 10-minute Supavisor startup-centered windows:** previous release 2026-10-07 23:58-2026-10-08 00:08 UTC versus deployed Tranche A 2026-10-08 14:49-14:59 UTC: auth **468 -> 5 (-98.93%)**, terminations **451 -> 4 (-99.11%)**, total Supavisor log events **1,078 -> 14 (-98.70%)**, event-message characters **47,761 -> 830 (-98.26%)**. Supavisor events are across project clients, not explicitly app-only connections or billed log bytes; matched startup restores increase confidence but do not establish perfect workload controls. Do not extrapolate this to all dayparts or traffic.

**Matched persisted restore workload:** both startup restores performed **25 reads in the same artifact order**, each totaling **22,318,183 logged serialized payload bytes** (not actual wire transfer bytes). Legacy `restore_id=a509f688-23f6-4c0e-a9b5-b66e71a3de8a`: ready in **8,699.28 ms**, read p50 **354.37 ms**, read p95 **1,207.12 ms**, process peak RSS **343,904,256 bytes**. Pooled: ready in **7,987.60 ms**, read p50 **344.51 ms**, read p95 **1,200.87 ms**, process peak RSS **335,355,904 bytes**, `rss=328,314,880` at full startup readiness; underlying hard limit **536,870,900 bytes**. The new host also logged `forecast=True simulation=True value=True complete=True` and product readiness `full`. Zero app warning/error logs in selected post-deploy 14:49-15:25 UTC window; Supabase inspected connection-error terms absent.

**Bounded acceptance and limitations:** This is real live startup saved-context restore and persistence-read evidence, not a newly issued authenticated browser GET; browser saved-session physical view was NOT independently exercised in this checkpoint. User-visible startup behavior and measured p95 are not broad load guarantees. Internally instrumented app-created connection counts, ConnectionPool opens/checkouts/waits/timeouts and transaction retries are **not exported** on this tested head; only bounds (min=0,max=3,wait=5s,max idle=75s,lifetime=720s), absence of observed pool-timeout/errors, and Supavisor aggregate event counts are available. No pre/post **database SQL execution p95** was captured; p95 values above are app-side persistence-read timings. The unchanged ~22.32 MB restore payload means Tranche A does not address Tranches D/E. Supabase physical database size remained above Free quota (~582,864,019 bytes at the observed inspection). Never claim the 70-95% target as an app-created connection counter; only the observed project-wide auth reduction is measured.

**Management gate disposition:** Recommend **ACCEPT** Tranche A as a bounded transport correction that has exercised actual hosted writes and matched restore reads, with a measured >98% reduction in startup-window Supavisor auth/log churn and no observed memory or persistence regression. Before extending this improvement to sustained traffic or marking physical saved-session acceptance, obtain a single no-refresh authenticated Safari saved-session confirmation and/or future counters where proportionate; these are residual observability/physical-acceptance notes, not grounds to repeat artificial Gate 2 POST. **Tranche B is NOT AUTOMATICALLY AUTHORIZED**. Management may separately evaluate row-wise idempotent market-write batching next using the Gate B design, while preserving PIT/lineage. No new code/deploy, billing upgrade, retention cleanup, migration, refresh policy, Career #405 PR2, or B-F work performed in this reconciliation.

**Standing regression boundary after Tranche A acceptance:** bounded connection reuse is now the accepted hosted persistence transport contract. Future persistence, publication, restore, or background work must not reintroduce one-connection-per-operation behavior or silently bypass the pooled adapter. Preserve the focused pool regressions in CI. For future changes that can affect this boundary, compare matched-workload connection/authentication/termination/log behavior, pool waits/timeouts where observable, affected persistence latency, errors/retries, and peak RSS against the latest accepted baseline. If connection churn materially regresses under comparable work, reopen this narrow resource gate before promotion. The legacy transport flag remains an emergency rollback path, not an alternate normal operating mode.

**Observability follow-up:** current acceptance does not export app-only pool opens/checkouts/waits/timeouts. Add low-volume aggregate counters only when proportionate to an authorized tranche; do not create high-volume per-operation logging merely to observe the pool.



## 2026-10-08 — Tranche A draft implementation checkpoint / pre-stable-head gate

- **Main baseline:** `55f9ce5da494466a107f4664f06385935c7b2ff7`; branch `work/supabase-tranche-a-pooled-connections-20261008`; draft PR **#433**. Latest implementation/documentation branch head before this checkpoint: `2f2157a9659fdb6272ce79c9ab26b4c2b9cc2dc3`; the new checkpoint commit becomes the exact next head.
- **Scope changed in draft:** `src/fsffl/persistence/postgres.py` only alters `_connect()` transport and adds `close()`; all existing SQL and `with self._connect()` transaction sites are unmodified. `pyproject.toml` adds `psycopg-pool>=3.2,<4` to hosted extras, `src/fsffl/product/persistent_webapp.py` closes the global runtime adapter on FastAPI shutdown, `.github/workflows/ci.yml` includes new Tranche A focused regressions; `tests/test_postgres_connection_pool.py` covers lazy bounded initialization, concurrent reads/writes/tenant parameters, rollback isolation, checkout timeout, stale-check preflight, shutdown/restart, and legacy-equivalent telemetry statement/parameters.
- **Pool settings:** min_size=0, max_size=3, wait=5s, max_waiting=12, idle=75s, max lifetime=720s, reconnect_timeout=5s, 1 background maintenance worker. `check=ConnectionPool.check_connection` tests stale connections before a caller executes its SQL. No replay of attempted writes. Disabled prepared statements maintain compatibility with session or transaction Supavisor mode. `FSFFL_PERSISTENCE_CONNECTION_MODE=legacy` retains prior direct-connect semantics (requires restart/redeploy to change).
- **Focus validation:** Draft PR `CI / test` **passed** run `37780997029` on earlier head `1c5b5d603d88f467cc53769780c2cb125d9853f6`. The branch then added a concurrent real-adapter read/write isolation test and operating checkpoints; latest-head focused run must pass before marking ready. Full suite intentionally **not run** on draft. No production work/deploy.
- **Deployment/observability gate:** Render has one Free instance / single Uvicorn process (no worker flag), underlying PostgreSQL max_connections=60 and current observed active=6. Recent Supavisor logs show postgres session-mode pool, but Render credential URL has not been directly inspected. Render connector has **no selected workspace**; a workspace selection from Management is required to access hosted log/metrics and safely complete a Render-credential rollback-only telemetry acceptance. Do not make an inferred host-credential acceptance claim, deploy without a viable acceptance path, or perform a discretionary refresh.
- **Acceptance requirement:** one stable full-suite run at final ready PR head; exact diff/identity review; hosted rollback-only telemetry insert+no residue, comparable Supavisor auth/termination/log bytes, app-connection attempts, p95 persistence/restore and peak RSS; stop if unsafe or benefit does not materialize. If the testing route is inaccessible, preserve the draft PR and return to Management for workspace/acceptance resolution.
- **Not authorized:** Tranches B-F, Career #405 PR2, billing, migrations, historical deletion, new refresh, provider retrieval, analytical/model updates, or lifecycle rewrite.

## 2026-10-08 — Tranche A implementation start (Management-authorized, NOT DEPLOYED)

- **Management scope:** bounded PostgreSQL connection ownership/reuse ONLY. Supabase stays Free; B-F and Career #405 PR2 remain paused. No SQL, migrations, retention, refresh, value, model, or lifecycle changes.
- **Starting main:** `55f9ce5da494466a107f4664f06385935c7b2ff7`. **Branch:** `work/supabase-tranche-a-pooled-connections-20261008`. Draft PR/testing/deployment status: not yet started.
- **Live before:** Render `srv-dae6k7vqj5pc73af7bt0` on `dep-db3dp1d9fdbs73dbo7eg` / `b43fa8690fb6fe3dc4c28e9b203c51fd5a860480`, one free instance; Uvicorn start command has no `--workers` (one worker per instance). PostgreSQL `max_connections=60`, three reserved and six observed active at the read-only check. Historical and recent Supavisor logs show `mode: :session` for role `postgres`, but the exact encrypted `FSFFL_DATABASE_URL` transport endpoint from Render has not been directly inspected; verify at hosted acceptance, don't claim it is proven by log strings alone.
- **Verified transport mechanism:** `src/fsffl/persistence/postgres.py` currently calls `psycopg.connect` for every individual `with self._connect()` SQL operation. Existing `psycopg_pool.ConnectionPool.connection()` API commits on success, rolls back on exception and returns the connection; connection health-check can discard stale connections before caller SQL.
- **Proposed bounded parameters:** lazy per-adapter/process pool, min_size=0, max_size=3, timeout=5s, max_idle=75s, max_lifetime=720s; explicit shutdown; session/transaction-compatible disabled prepared statements; legacy mode escape `FSFFL_PERSISTENCE_CONNECTION_MODE=legacy`.
- **Pre-deploy gates:** focused concurrency/isolation/rollback/timeouts/disconnect/shutdown tests, stable-head full-suite on ready PR, exact dependency and pooler mode compatibility, RSS and connection headroom; deploy only after stable candidate acceptance. Hosted rollback-only telemetry test and measured comparable windows must pass before marking tranche accepted. If credentials/observability inaccessible or risk elevated, stop and report to Management without claiming production acceptance.
- **Frozen:** every existing SQL statement, publication/pointer ordering and tenancy, PIT lineage, replay, last-good, model authority, and explicit no-silent-heavy-refresh saved-session policy. Baselines: Gate A forensic and Minimal Write-Capability PDFs; Gate B design (15 pages).


Updated: 2026-10-08  
Status: **P0 OPERATIONAL PRIORITY — GATE A AUTHORIZED; PRODUCTION REMEDIATION NOT YET AUTHORIZED EXCEPT SEPARATE NARROW EMERGENCY BRIDGE**

## Management objective

Restore safe operation, identify the mechanism behind the late-September Supabase resource inflection, and redesign persistence/egress behavior so FSFFL NEXT can scale to thousands or tens of thousands of leagues without multiplying shared work by raw league count.

A temporary paid Supabase tier may be used only as a **short-lived access/headroom bridge** if required to regain normal operation. It is not evidence that the present architecture is acceptable and must not replace root-cause correction, retention design, or scale validation.

## Current incident evidence

- Supabase Free Plan database allowance: 0.5 GB per project.
- Observed FSFFL NEXT database size: **568.16 MB**, with Supabase reporting the project over quota and Management observing the project locked/read-only.
- Billing-cycle log ingestion: **1.12 GB** against 1 GB included.
- Egress was low through most of September, began rising materially around 2026-09-23..25, and showed a clear step-change around **2026-09-26/27**, followed by repeated daily volumes around roughly 0.5–2 GB.
- Log ingestion shows a similar late-September step-change, strengthening the hypothesis of increased runtime/persistence/read/write/connection activity rather than storage retention alone.
- Prior read-only inspection found approximately:
  - `derived_artifact`: 376 MB, including roughly 369 MB TOAST;
  - `market_value_snapshot`: 114 MB;
  - `state_snapshot_history`: 24 MB;
  - `projection_observation`: 19 MB.
  The two largest relations total roughly 490 MB. This is **not** permission to delete them.

## Immediate sequencing

This workstream temporarily supersedes Career Coverage #405 PR2 as the active operational priority. PR1 is complete and preserved. PR2 remains authorized in principle but **paused from implementation/promotion** until the Supabase Gate A audit/design determines that its dynamic materialization plan will not amplify the current database/egress failure mode.

Do not launch new persistence-heavy features, broad rematerialization, retention cleanup, migrations, destructive SQL, or scale simulations while the incident is unclassified.

## Phase 0 — incident containment

Objective: regain and preserve enough operational headroom to inspect safely without confusing temporary capacity relief with remediation.

1. Record exact Supabase project status, quota state, database size, billing-cycle timestamps, live deployment identity and repo head before intervention.
2. Preserve current database/evidence and identify whether writes/refreshes are actually rejected versus only quota-flagged.
3. If Management uses a paid tier to regain access, record it explicitly as a **temporary emergency bridge** with before-state evidence. Do not infer that a larger quota resolves the architecture.
4. Avoid destructive cleanup. Any emergency data reduction requires a separately itemized action, preservation/backup path, expected reclaimed bytes, rollback and post-action verification.
5. Keep the current resource curves visible so a paid upgrade does not hide continuing growth.

## Phase 1 — targeted read-only audit

Objective: produce a defensible resource ledger and identify the late-September inflection.

Use **2026-09-24 through 2026-09-29** as the first forensic comparison window, with **2026-09-26/27** as the primary observed breakpoint. Correlation is not causation.

Measure:
- daily/hourly egress before and after the breakpoint;
- bytes and request counts by table/payload family/surface where available;
- derived-artifact generation/write rate and repeated read rate;
- market snapshot creation/read rate;
- publication-generation count and retained payload sizes;
- State/history reads, restore reads and last-good reads;
- connection/authentication/termination churn;
- hosted Render traffic versus development/CI/manual audit traffic;
- identical or semantically identical payloads repeatedly fetched in the same process/publication;
- log volume by logger/path/workload;
- database table/index/TOAST size, dead tuples and growth by timestamp/generation.

Cross-reference deployments/commits around the breakpoint, especially persistence/publication/lifecycle changes, without presuming they caused the usage increase.

Deliverable: quantified before/after resource ledger; causal hypotheses with confidence; consumer/dependency map; immediate safe-headroom requirement.

## Phase 2 — architecture and retention design

Objective: specify the permanent fix before cleanup.

Define the widest safe semantic ownership/reuse scope for every expensive stored/read artifact:

`global/provider evidence → model/training authority → scoring/rules signature → lineup/team-count signature → exact league State → publication generation → team/user presentation context`

Required design:
- no unnecessary league/user key in shared upstream cache/artifact identity;
- current-head versus immutable PIT history versus last-good/rollback/replay responsibilities;
- bounded retention/compaction policy by artifact family and consumer;
- deduplicated/shared payload references where mathematically and privacy-safe;
- metadata-first reads and no repeated large-payload download merely to determine freshness;
- coalesced publication writes and reads;
- bounded connection/log behavior;
- tenant-private State isolation;
- no reintroduction of the P0 lifecycle complexity already removed.

Deliverable: retention matrix, target read/write architecture, quantified expected savings, migration/rollback plan, and capacity model.

## Gate B — mandatory Management pause

No production-modifying cleanup/remediation proceeds from Gate A alone.

Management must review:
- exact proven cause(s);
- affected tables/artifacts/readers/writers;
- bytes/request/log savings expected;
- PIT/replay/last-good preservation guarantees;
- downtime/locking/compute/memory risks;
- rollback;
- tests and hosted/physical acceptance.

Only then authorize itemized Phase 3 changes.

## Phase 3 — controlled stabilization

After Gate B only:
- correct proven redundant writers/readers/materialization/polling/logging;
- retire/archive only explicitly approved materializations;
- reclaim physical storage using an operation selected with lock/downtime consequences understood;
- verify database size, egress, logs, latency and model/product correctness before/after.

## Phase 4 — scale validation

Do **not** instantiate 1,000 or 10,000 live leagues on current infrastructure.

Measure real per-scope costs, bounded representative fan-out/concurrency, reuse ratios, bytes/action, bytes/publication and changed-subject rates. Project resource envelopes at 1, 100, 1,000 and 10,000 leagues. Expensive shared stages should scale primarily with unique semantic signatures and changed evidence, not raw league count where reuse is valid.

## Non-negotiable safeguards

- Preserve point-in-time State, market evidence, lineage, accepted research artifacts, immutable replay inputs, audit trails and required last-good generations unless Management explicitly approves a replacement preservation mechanism.
- Do not change Career/Y4–Y7 authority, #370 Dynasty economics, Current semantics, Foundation 4 or Simulation 2.0 as a storage side effect.
- Do not use a paid service tier as a substitute for efficient architecture.
- Do not reopen P0.1–P0.6 lifecycle/presentation plumbing absent evidence that a surviving mechanism is directly responsible.
- Prefer fixing the mechanism consuming resources over deleting the evidence it produced.

## Acceptance

This workstream is complete only when:
1. the late-September resource inflection is causally classified to a useful engineering level;
2. normal operation has material headroom;
3. redundant egress/write/log behavior is demonstrably reduced;
4. retained-history policy is explicit and auditable;
5. the application preserves PIT/replay/last-good and analytical authority;
6. scale projections demonstrate non-naïve league multiplication;
7. current limits and upgrade triggers are documented.

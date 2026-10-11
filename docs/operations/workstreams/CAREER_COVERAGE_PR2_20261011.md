# Career Coverage #405 — PR2 checkpoint

Date: 2026-10-11

- Repository: `jderhagopian-stack/fsffl-next`
- PR: #454, draft
- Branch: `career/dynamic-materializer-20261011`
- Starting head: `dbef69412e488e747b3caaf57a02fdf46c5adff4`
- Tested code head: `8fbf4781d0733e978d13dc7426b18b799b3b22c6`
- Durable derived-output destination: private Library folder `/FSFFL NEXT/_implementation_temp` (available; no provider payloads will be stored in GitHub).

## Current durable evidence

The October 11 governed P0 run processed 507 dynamic subjects but saved only an aggregate PR comment. Its per-player outputs and failure rows are unavailable and will not be inferred or reused. Do not rerun that 507-player cohort. The next authorized refresh, after the governed adapter is made runnable and exact-State inputs are validated, is roster-only for 27 dynamic players. Persist each success, each player failure, provenance, State identity, and evaluation timestamp to the private destination before Career composition.

The accepted source/rights policy, frozen 335-player reference, Shapley contract, and model authority remain unchanged. No refit, production-model change, merge, deployment, or new infrastructure is authorized.

## Acceptance sequence

1. Run the governed P0 refresh for only the 27 dynamic roster candidates; persist and verify the private artifact before further analysis.
2. Compose supported roster Career values with the existing Shapley/Career contract and prove frozen-reference parity.
3. Investigate and explicitly account for every unsupported roster player; do not omit, zero-fill, or invent values.
4. Propose a bounded Explore waiver cohort from supported candidates; do not materialize all 480 outside-reference waivers.
5. Wire matching-State publication and test actual identity/provider resolution for a newly rostered outside-cohort player.
6. Reduce the complete Career materializer peak below the existing ~410 MiB budget.

## This checkpoint

This session confirmed the repository write path and private durable destination. No provider acquisition has run. GitHub branch-targeted writes are confirmed. At head `9ad57eb994b48b812a53b4a3c4ee10fd864cf5c7`, focused CI and PR164 focused corrective regression passed; stable full suite skipped because the PR remains draft. The current tool session has no local checkout, and Actions capabilities expose run/artifact reads plus failed-job reruns, but no workflow dispatch or command execution. Therefore the roster-only P0 adapter cannot be launched from this chat yet. Next: establish an authorized execution path for the existing adapter that is constrained to these 27 roster IDs and can persist sanitized derived outputs into the private Library destination before Career composition. Do not repeat the 507-player refresh.

## Implementation checkpoint — 2026-10-11

Branch-targeted commits add `build_career_forward_from_canonical_p0`: it validates canonical Y1/Y2/Y3 cohort coverage, calculates Shapley over the supplied cohort, then calls the existing Career contract. It does not calculate candidate-alone marginals and fails closed on missing horizons or mismatched cohorts. Fixture tests prove parity with direct existing Shapley/Career composition. A bounded Explore selector (default 50, maximum 100) ranks supported waiver candidates; tests cover limits and stable ranking. A stale-State Position & Depth publication regression asserts fail-closed behavior. CI explicitly installs pandas for dynamic-candidate tests.

The 335-player long-horizon materializer now releases raw feature joins after constructing narrow current/terminal snapshots and before loading the historical route panel; it also drops route panels and prediction caches before allocating publication tables. This is a code-level lifetime reduction only. The full materializer has not been run in this environment, so the measured 490,928 KiB baseline is not yet shown below 410 MiB, and no RSS benchmark result is claimed.

At tested code head `8fbf4781d0733e978d13dc7426b18b799b3b22c6`, PR CI, PR164 focused corrective regression, and Live Forecast corrective trace passed; stable full suite skipped while the PR remains draft. No Career candidate has been newly scored or reported as covered. Dynamic Career composition still requires the unavailable canonical P0 packets and matching cohort Shapley outputs; the existing Career composer remains strict about ready Current Shapley, matching Y4–Y7/tail cohorts, and frozen reference authority. No provider acquisition or production-model change occurred.

**Next:** inspect final CI, add/fix a focused benchmark if repository fixtures support exercising the materializer path, and obtain an authorized runner for only the exact-State 27-player P0 refresh. Persist its player-level results privately before dynamic composition. Keep #454 draft.


## 2026-10-11 — Durable roster checkpoint and focused RSS benchmark

PR #454 remains draft on `career/dynamic-materializer-20261011`; implementation head at checkpoint: `c2ee887cb6d73bdff91e7dabd174d156b0c95977` (the preceding requested head `0d350fb98a4d8333e78a4ea9d31f4d96fc9029a0` is an ancestor). The new CI step runs the 335-player Career composition RSS benchmark separately from the focused regression suite. Current-head run `38153263685`: benchmark step passed; focused regression step was in progress at checkpoint. The same benchmark fixture reported **195.2 MiB** at head `218095adc442a0c794d2ccf1ad1ff0967ede5818`, below 410 MiB for the Career composer stage. This does **not** measure the complete external route-input/materializer path whose known peak was 490,928 KiB; full-path memory acceptance remains open.

The roster-only adapter now has an atomic private checkpoint writer: it accounts for each supplied exact-State dynamic roster subject as a success or explicit failure, persists per-player inputs, Y4–Y7 and Y8+ partial outputs, provenance and State/evaluation timestamps, uses mode 0600, refuses repository paths, and emits a content SHA-256. Tests cover accounting, failure preservation, permissions, and State identity drift. This is implementation support only: **no P0 run occurred**, no live roster coverage is claimed, and no 27-player artifact exists. The old 507-player player-level outputs remain unavailable. Current tools still provide no authorized command/workflow-dispatch path and no writable local checkout; do not rerun the broad cohort.

**Exact next step:** run the adapter through an authorized governed runner constrained to the exact-State 27 dynamic roster IDs, writing actual per-player successes and explicit failures to private `/FSFFL NEXT/_implementation_temp`; verify the artifact digest and timestamps, then compose Career only for supported roster players and compare frozen-reference values. Separately measure the complete materializer RSS in PR CI or its authorized runner and reduce that measured path below 410 MiB. Keep #454 draft; no merge, deploy, refit, production-model change, or rights change.


## 2026-10-11 — Focused CI fixture correction and rerun

At head `0d52e1b411b09cbfeceeb4750a957b8ef9514284`, the focused regression step failed one new test: `test_durable_roster_checkpoint_atomically_accounts_for_success_and_failure`. The candidate fixture inherited `team_id="team-1"` from the generic row helper while the corresponding exact-State roster fixture declared `team_id="t1"`. The checkpoint writer correctly rejected this State identity mismatch. The fix was test-only: set that candidate fixture's team ID to `t1`; no production logic or authority changed. Commit: `c520a98e4046c115884686525845c0fa0b229342`.

Rerun on `c520a98e4046c115884686525845c0fa0b229342`: CI run `38154256521` passed. The 335-player **composer-only** benchmark measured **195.4 MiB** (1 passed); the focused Dynasty, persistence, provider, and Career regressions passed **124 tests** with one existing Starlette/httpx deprecation warning (115.67 s). PR164 focused corrective regression passed; Live Forecast corrective trace passed; stable full suite skipped as designed for a draft PR. This benchmark is not the complete Foundation 4 route/materializer path; its previous peak was 490,928 KiB and remains unverified below the ~410 MiB budget.

No P0 acquisition ran. The player-level outputs from the old 507-player refresh remain unavailable. The durable writer/test path is ready, but this chat still has no authorized command or workflow-dispatch path, and no 27-player private artifact exists. **Next:** run the governed adapter with the exact-State 27 dynamic roster IDs only, save each success/failure plus provenance and State/evaluation timestamps to the authorized private location, verify its digest, then compose supported Career values and prove frozen-reference parity. Do not repeat the 507-player cohort.


## 2026-10-11 — Recovered exact-State roster checkpoint

PR #454 remains draft at head `003b42bf76ae3b261f686dd4535f7dc3360cfff1`. The temporary October 11 refresh files were recovered from the existing run directory; **no provider acquisition was repeated**. I filtered and persisted only the exact-State 27 dynamic roster records (no waiver rows) using the branch’s durable checkpoint writer. This is a durable replay of the existing 507-run outputs, not a fresh 27-player provider run.

Private artifact: `/FSFFL NEXT/_implementation_temp/CAREER_P0_ROSTER_27_STATE_e431b5cb9e340e0f9a93e4433cafe51974fc8b86d6c56b1804e3e506013cd670.json` with sibling `.manifest.json`. SHA-256: `dde165d1d148139d57c8304f2a8f7d351fdee5bc09abf4243889434277599e32`. State `e431b5cb9e340e0f9a93e4433cafe51974fc8b86d6c56b1804e3e506013cd670`, as-of `2026-10-08T16:20:14.036832Z`; evaluation `2026-10-11T14:12:26.851497+00:00`. The artifact accounts for all 27: **11 supported P0 successes and 16 explicit player failures**. Y4–Y7 and Y8+ are present for the 11; no Career Current/Shapley result is included. Source-file hashes and failure details are in the private manifest/payload.

Career composition is not claimed. Existing contract requires the correct full Shapley cohort/current values, not Shapley recomputed over only the 11 supported players; this recovered artifact alone cannot safely supply that. The branch’s frozen-reference parity tests remain the only parity evidence here; no live numeric frozen-reference comparison was performed. Do not infer zeroes or Career values for the 16 failures.

**Next:** use the governed runner that produced the original P0 outputs, constrained to these exact-State 27 IDs only, to refresh canonical evidence into the durable writer as it runs. Then compose the supported roster against the authorized full Shapley/reference context, assert frozen-reference parity, and append resulting private artifact digest. If the runner is unavailable, request its documented invocation/access rather than expanding the cohort. No waiver processing, merge, deployment, refit, or production-model change.


## 2026-10-11 — Full-cohort Career composition gate

PR #454 remains draft. Starting PR head for this checkpoint: `e4c80c25bdd63afe546f28d5c313130908b716de`. No provider acquisition was rerun and the private exact-State artifact is unchanged (27 roster records: 11 P0-supported, 16 explicit failures; zero waiver records; SHA-256 `dde165d1d148139d57c8304f2a8f7d351fdee5bc09abf4243889434277599e32`).

**Composition result:** no Career estimates were emitted. The branch composer `build_career_forward_from_canonical_p0` requires canonical Y1 and Y2/Y3 packets for an identical full Shapley cohort, calculates Current Shapley over that cohort, and then requires matching full-cohort Y4–Y7 and Y8+ components. The artifact carries Y1–Y3 and partial Y4–Y7/Y8+ for 11 only; it has no ready full-cohort `ShapleyIntrinsicContract`. Running Shapley on only those 11 would violate the accepted contract. Therefore no live Career value or numeric frozen-reference parity is claimed.

**Exact P0 input gap:** all 16 explicit `p0_year1_evidence_incomplete` records lack a complete Year-1 raw scoring row. CBS canonical ROS metrics are empty for all 16. Razzball also has no canonical ROS metrics for IDs `11638, 12484, 13353, 13418, 3321, 4018, 6803, 8210`; it has only incomplete subsets for `12510, 13268, 13270, 13289, 13306, 13402, 13411, 7567`. No two-source raw ensemble exists for any of these failures. The private artifact preserves each failure row and exact provider metric details. These 16 remain unresolved; no zeros or inferred values were used.

**Test evidence:** existing CI run `38154256521` passed at code commit `c520a98e4046c115884686525845c0fa0b229342`: focused 335-player composer RSS benchmark `195.4 MiB` and focused regression suite `124 passed` (one existing deprecation warning). That suite includes `test_canonical_p0_packet_uses_shared_shapley_and_career_contracts`, which compares adapter composition to direct contract composition on its fixture; it is **not** a numeric frozen-reference parity test. No new test could be run in this scratch checkout (pytest is not installed), and exact numeric parity remains open.

**Next gate before any rerun:** first identify and supply the authorized exact full-cohort Current/Shapley input, specifically a ready `ShapleyIntrinsicContract` for the required cohort or canonical Y1/Y2/Y3 forecasts covering that same cohort. For the 16 player failures, the missing data is a complete accepted Year-1 raw scoring row; use the established evidence path to seek those specific rows only if a governed runner is authorized. Then compose all cohort components, select the 11 supported Career outputs, and numerically assert frozen-reference fixture parity. Do not rerun the 507 subjects or include waivers.


## 2026-10-11 — Full-cohort Career composition and frozen parity

PR #454 remains draft. Composition ran from the recovered exact-State private artifact; **no provider acquisition was repeated** and no waiver rows were included. The accepted base cohort is identified by `career-405-pr1-semantic-11526021872.zip` (SHA-256 `1bad20d2f4bc369d64f59f5ab2d2bd75117f594d45aeace352b58d4aedb3b2f3`), containing `SHAPLEY_CURRENT_BOARD_335.csv` (SHA-256 `03636d36726cb8765b34a0bf9f400fc1e29d8c32651352ab77ee293bded89b26`) and frozen Career comparison rows. The accepted Foundation 4 board bundle is `11263913850.zip` (SHA-256 `6a79e2d793403c128c1c34ee3ffb044aba67f873ec92b8c61a702d26c06c1b22`); its Y4–Y7 board SHA-256 is `f04547d3fae97420a12c13ff2f15010c9c54ec5b3a6af5ccd68927774aa12484` and terminal features SHA-256 is `ac7755962be04a51391120a8c92df31a1dfdca19368d3e6c0b3078745a7f9292`.

The saved 11 P0 packets were composed with the existing full Shapley/Career contract over the combined 346-player context. The 335 original Shapley components reproduce within `5.97e-13`; the frozen 335 Career numeric outputs match within `9.10e-13`; after adding the new rows, all 335 base Career rows are unchanged exactly (`0.0` max delta). A fresh 346-player Shapley calculation would reallocate the base (`98.15` maximum absolute diagnostic delta), so composition deliberately retains accepted frozen outputs for those 335 and takes the 11 new estimates from expanded-cohort Shapley. Result: **11 Career values**, **16 explicit failures**, **335 preserved reference rows**.

Private artifact: `/FSFFL NEXT/_implementation_temp/CAREER_COMPOSED_SUPPORTED_ROSTER_11_FULL_COHORT.json`, SHA-256 `2379c42b84116707d92e387e74f05097d13925a80b8dbb34476f47935a1da894`; sibling manifest records State `e431b5cb9e340e0f9a93e4433cafe51974fc8b86d6c56b1804e3e506013cd670`, State-as-of `2026-10-08T16:20:14.036832Z`, evaluation `2026-10-11T14:12:26.851497Z`, hashes and parity diagnostics. It carries the 16 player-specific Year-1 evidence failures from P0 unchanged; no zeros or synthetic values were added. The earlier checkpoint’s claim that full-cohort inputs were unavailable is superseded: the canonical accepted frozen 335 artifacts were located and used.

**Next:** attach the composition code and focused numeric parity test to the branch/CI, then continue State publication and outside-cohort acquisition test plus the complete materializer RSS gate. Keep waiver work limited to a supported bounded Explore cohort. Do not rerun provider acquisition; keep #454 draft.


## CI follow-up — 2026-10-11

On commit `437a141a60a40f1f4e39e0e0cf083cdf6fdab753`, PR CI run `38160778083` completed successfully: focused 335-player Career composer RSS benchmark passed and focused Dynasty/persistence/provider/Career regressions passed. PR164 focused corrective regression (`38160778034`) and Live Forecast corrective trace (`38160778044`) also passed; stable full suite (`38160778041`) was skipped under draft-PR policy. These checks do not add branch CI coverage for the private full-cohort numeric composition verifier; its parity assertions were executed in the composition run described above. The successful benchmark remains composer-only, not the full materializer RSS gate.

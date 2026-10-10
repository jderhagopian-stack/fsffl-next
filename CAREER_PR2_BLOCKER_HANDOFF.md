# Career PR2 blocker handoff

**Status:** accepted research and frozen-cohort replay inputs are preserved and recoverable. The remaining gate for actual out-of-cohort Career valuations is candidate Current/P0 forecast authority for the exact roster subjects. This is not a loss of the accepted Y4–Y7 model.

## Inputs checked

| Input | Evidence checked | Finding |
|---|---|---|
| Accepted historical/model-A and terminal evidence | Release `career-405-accepted-research-evidence-20261007`, asset `10899387479.zip` (20,765,419 bytes; SHA-256 `ea72f312148f01b8066419e8f12cb3a04a4dbbd99fd6e0b7dc975c65cc2446b5`); release body maps it to accepted run 10899387479 | Preserved. |
| Rich historical player panel | Release asset `10912862252.zip` (3,902,644 bytes; SHA-256 `6dd664b632f4897f286a99794e10df29be21bf8c6cae70e526ea807fdcb0e) | Preserved. |
| Frozen route/rolling evidence | Release asset `10916355135.zip` (809,045 bytes; SHA-256 `63520ddb60a8ed12724fa21e8d276c4e3e7d5587162aade92ba7afaa3796ced2`); run 36271080037 | Preserved. |
| Frozen 335 input board | Release asset `11263913850.zip` (1,100,940 bytes; SHA-256 `6a79e2d793403c128c1c34ee3ffb044aba67f873ec92b8c61a702d26c06c1b22`); accepted run 37096263982 | Preserved. This is explicitly a 335-player board. |
| Accepted source code and deterministic materializer | Commit `be2541a496227b33c12c755f576843dc4ab5a0bb`; `.github/workflows/foundation4-current-long-horizon-board.yml`; `scripts/materialize_foundation4_fsffl_coordinate.py`; `scripts/run_intrinsic_cell_routing_validation.py`; `scripts/run_intrinsic_comprehensive_development.py` | Preserved/reconstructable. The workflow restores all three archives, exact Git-pinned programs, route/policy files, and runs the accepted scorer. Its materializer currently rejects any board not exactly 335. PR #429 replay and accepted PR1 closeout preserve this frozen-cohort evidence; no model search or refit redesign is needed. |
| Exact historical League State and canonical IDs | Read-only query of Supabase `fsffl.state_snapshot_history`, hash `606ba3cd0acf427f6724665546dfcbcce0013e593abb658277466c2725b7d2d3`, league `sleeper:1312071960615731200`, as-of `2026-10-06 05:36:57.684732Z`; reconciled against its Career artifact in `fsffl.derived_artifact` | Preserved and accessible. Exact roster arrays resolve the 25 absent canonical IDs: 5 QB, 8 RB, 10 WR, 2 TE. The IDs/slots can be used directly; no name matching is required. |

Exact missing roster IDs from that preserved State, resolved by direct roster-array/player joins:
- QB: `sleeper:player:9229`, `sleeper:player:13557`, `sleeper:player:13289`, `sleeper:player:12510`, `sleeper:player:13306`.
- RB: `sleeper:player:13302`, `sleeper:player:4663`, `sleeper:player:12476`, `sleeper:player:13423`, `sleeper:player:4018`, `sleeper:player:12504`, `sleeper:player:7567`, `sleeper:player:11729`.
- WR: `sleeper:player:6803`, `sleeper:player:13353`, `sleeper:player:13270`, `sleeper:player:13268`, `sleeper:player:12484`, `sleeper:player:11638`, `sleeper:player:11630`, `sleeper:player:13402`, `sleeper:player:3321`, `sleeper:player:13411`.
- TE: `sleeper:player:8210`, `sleeper:player:13421`.

| Point-in-time candidate Current Y1–Y3/P0 forecast authority | Exact-State candidates above compared with `fsffl.projection_observation` / `projection_snapshot` through the State as-of time; repository runtime trace in canonical workstream and current source | **Not present in the inspected candidate-keyed evidence.** The accepted Current/Y2/Y3 input path and packaged P0 board are bounded to the frozen 335. The release's accepted 335 board cannot yield a P0 forecast for new subjects. Stored CBS/Razzball rest-of-season snapshot rows use external identities and are marked `beta-personal-research-requires-commercial-review`; they are not an approved substitute for P0 or an authorized Market input. |
| Y8+ candidate terminal features | Accepted terminal replay/archive | Frozen 335 terminal rows are preserved and parity-verified; the release does not contain terminal features for the 25 additional IDs. Candidate tail features can be constructed only after governed, point-in-time current/prior inputs and canonical identity mapping exist. |

Release metadata lists 11 attached files: four source/reference ZIPs, four replay/semantic evidence ZIPs and three checksum manifests. The four source/reference archive digests above were exposed by the release API and the archive workflow records successful hash verification. Run `37096263982` completed successfully and its board artifact was still unexpired when inspected (expires 2026-10-17). The source archive assets are preserved in the durable release.

## What can be reconstructed without changing authority

The exact accepted historical-fit process for the frozen 335 can be rerun from the release plus commit `be2541a...` and its pinned route/policy inputs. PR #429’s evidence/replay tooling preserves source hashes and the accepted reference materialization. PR1 acceptance governs the existing semantic closeout and does not authorize a model change.

That path alone cannot value a new subject end to end. Career Forward requires all components for each subject: governed Current Y1–Y3, accepted Y4–Y7 output, and governed Y8+ terminal evidence. The frozen current, Y4–Y7, and terminal runtime packages all validate exact 335-player coverage. The route scorer can apply its accepted policy to a candidate row once the row has the required point-in-time feature/evidence packet; it cannot manufacture that packet from a player ID or roster slot.

## Minimum recovery action

Implement the authorized candidate evidence/materialization adapter at the P0/Forecast boundary. It must produce point-in-time Current Y1–Y3 inputs, canonical provider/player identity mapping, scoring coordinate and provenance for the exact missing State subjects using approved sources; then feed those rows through the unchanged accepted Y4–Y7 route/policy and the existing tail scorer. Keep the 335 reference set unchanged and prove it remains unchanged. If a candidate lacks a governed input family, emit the required player-specific authority failure.

Do not substitute CBS/Razzball research-class projections, Market values, names, arbitrary zeros, or new model selection for missing P0 authority. Once the adapter supplies governed evidence, extend the accepted materializer subject boundary, produce and compare actual per-player estimates/failures, and measure end-to-end runtime/RSS. Any asynchronous execution must use the bounded admission safeguard merged in PR #445.

**No out-of-cohort estimates are claimed by this handoff.** It identifies an implementation/data-authority prerequisite; it does not close Issue #405 or authorize merge/deployment.

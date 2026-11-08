# RB Position & Depth coverage — November 8, 2026

## Physical acceptance and exact scope

User confirms everything is filling in except RB in both 3-Year and Career Position & Depth. This confirms recovery of the preceding roster Career/history/chart symptoms on their device; RB room acceptance remains open. Current main verified read-only at `c9c572f75edb242ab08493d12d3a15836a9693c2`, live Render `dep-dbo02jgu01pc73dte7lg`. No new refresh, code deployment, source capture, production mutation or calculation change.

## Confirmed diagnosis

Read-only final saved generation `ffae3672dcb9f9624816b1e7f03a24ed77c0ca5fa00f08e19075982d03aff419`, State `703e822cd9186c3d1b7590d64a2479ff93763c451d1ac5c21d4c66c1f1dda846`, contains 12/12 complete QB/WR/TE rooms and **11/12 RB rooms**. The RB room for team 3 is incomplete; the only Career coverage failure is Dameon Pierce `sleeper:player:8129`, verified unsigned with an explicitly empty current NFL catalog team. His roster identity remains present.

`analytics/dynasty_position_room.py:_position_rooms` requires all teams complete before assigning league_rank or league-average strength_index. All 12 RB ranks/indexes therefore remain null, including 11 rooms with valid raw totals. `static/league_comparison.js:laPositionCell` renders those as disabled dashes. Both horizons use this common room aggregator.

## Existing exception audit (not a missing fallback implementation)

- `p0_live_candidate_runtime.py:recorded_ytd_only_year_one_evidence`: generic verified-unsigned YTD-only/no-additional-ROS assumption, approved October 24; fresh exact roster/catalog/season/cutoff admission.
- `recorded_ir_no_projection_year_one_evidence`: exact-State fantasy IR slot plus no provider projection permits the same labeled assumption. Fantasy IR alone does not erase an existing projection.
- Official whole-season-unavailability receipts support status-based zero ROS, preserving their stronger provenance and whole-season rules.
- `_active_backup_player_ids` plus `_score_complete_single_source_year_one`: supported NFL backup/practice-squad/injured/PUP role may use a complete one-source projection. Backup or practice-squad status is not an automatic zero.
- Selected previously approved developmental roles have YTD-only evidence; accepted P0 developmental routes and the `out` current state can support future years even when Y1 is zero. Neither young age nor fantasy taxi status universally means zero Career.
- Retired status is normalized by the provider, but no separate blanket retired-status-to-zero-Career rule was found. A retired player's explicitly empty catalog team can qualify via generic unsigned admission; otherwise an applicable governed status/forecast input is needed.

The decisive guard is `admit_ytd_only`, lines 1308–1311: **any available provider ROS row blocks the fallback**, including partial rows. This implements the recorded October 24 decision in CURRENT_OPERATIONS: “A projection row blocks these zero-ROS assumptions.” Existing `test_default_live_producer_applies_approved_ytd_only_after_provider_path` explicitly expects an unresolved player when provider_available='partial'.

Pierce has Razzball-only rows and no current CBS row in the run's failure diagnostic. The latest retained Razzball revision before the publication cutoff (November 7 20:50:50 UTC) is nonzero: rush_yards=35.1, rush_td=0.3, rec_yards=6, receptions=0.9, rec_td=0. It is not a blank/all-zero placeholder. Historical older CBS rows do not authorize treating a newer missing CBS row as current. This source conflict is why “unsigned” alone does not trigger the currently approved fallback.

Correction to earlier explanation: lack of an accepted complete projection for unsigned Pierce is expected, but exceptions do exist; the provider-row veto, not absence of an unsigned exception, prevents completion. These are not equivalent to an explicit zero forecast.

## Validation

Existing role/exception suites: **22 passed** using `/workspace/.venvs/fsffl-next/bin/python`, current code unchanged. The initial invocation used an expired `/tmp` pytest path and collected no tests; the workspace venv selection passed. SQL reads and saved-State inspection were read-only; no private payloads committed.

## Concrete proposed change — policy disposition required

For already eligible, freshly verified unsigned players (and, if approved, the existing exact-State IR eligibility), extend YTD-only admission from “no provider rows” to “no complete admissible Year-1 projection after normal provider paths”. Complete accepted provider authority retains priority. Retain actual earned stats and scoring completeness, record the undercovered provider row and conflict, label the no-additional-production assumption as low confidence, and run the unchanged accepted future/whole-cohort Shapley/Career calculation. Do not assign zero Career, exclude roster players, invent signing/return probabilities, or silently fill missing provider metrics.

This broadens the explicit October 24 provider-row veto and can change values/ranks; the user must disposition that concrete rule before promotion. Alternative without changing input rules: preserve missing authority and show known-room raw data/coverage or deterministic rank ranges instead of disabling every RB cell. Exact 12-team ranks cannot be claimed while one room's value remains unpriced.

Next: obtain the user's policy choice, then implement focused absent/partial/complete provider and status/IR/active-role/cutoff cases, preserve accepted math/history, review and exact-head CI/Stable, and deploy only the authorized rule. No new failed-refresh loop.


## User decision — 2026-11-08 13:13:56 UTC

User directs: “If someone is not on a roster fallback to no rest of season projection is the rule. If someone falls back to a single source projection for any reason, they should be run through the fumbles lost projection to complete their projection.” In context “roster” means NFL roster; retain fantasy roster identity. This supersedes the earlier projection-row veto for freshly verified unsigned players, including when a provider row is present. Preserve earned YTD production, not zero full-season/Career. The existing admitted single-source path must complete the FUMBLES_LOST coordinate for both standard and league scoring, regardless of why that path was entered; missing non-fumbles stats remain explicit failures. No general missing-catalog-to-unsigned inference, IR-to-unsigned inference, or new provider/model/plan change.

Implementation will fence this policy at its decision timestamp and include the policy version in dependency identity for subsequent captures; earlier published inputs/history retain their old identity and behavior. Existing numerical methods, dynamic future models, full-cohort Shapley, snapshots and publication ownership remain unchanged. A new governed refresh after deployment is required to publish new values; existing saved publications must remain readable meanwhile.


## Implemented candidate — unsigned ROS priority / single-source completion

Branch `fix/unsigned-ros-fumbles-completion-20261108`, base verified main `c9c572f7`. Freshly verified unsigned candidates use the existing earned-YTD/no-additional-ROS scoring path before normal provider selection, even with complete/nonzero provider rows. Missing/signed/future role evidence does not acquire that priority. This is not zero Career: the unchanged P0 future scorer and whole-cohort Career composer consume the admitted Y1 input.

The admitted single-source scorer consumes the first-party FUMBLES_LOST coordinate when missing, with required-coordinate eligibility covering **both** standard and connected-league scoring. A league that does not penalize fumbles still needs this field for the standard model input. The provider's own complete fumbles coordinate is retained instead of duplicated. Other missing metrics still fail. Acquisition remains the same once-per-run model call over cached weekly evidence; no per-player provider calls or new retained cohorts/executors.

Version `career-ros-fallback-v3:unsigned-priority-single-source-fumbles`, effective at the recorded user decision, enters dynamic dependency identity only for subsequent captures. Earlier published cutoffs retain their prior fingerprints and source rules. A real saved State/Forecast replay against the exact previous main function confirms both ordinary and stable-artifact dynamic fingerprints **unchanged**, zero provider calls/writes. Private data is kept mode 0600 under `/tmp`, not committed.

The live IR fallback also now retains its generated receipt before composing the evidence label; this avoids a missing-map-key failure without changing its existing projectionless-only admission.

Focused validation: role/producer/fumbles/room/state-identity selection **62 passed**; in-season first-party completion **3 passed**; dynamic capture/bridge selection **9 passed**, with overlap. Early new-test failures were fixture/assertion mistakes (nonexistent result field and omitted required stddev), corrected before final selection. Full exact-head CI/Stable, clean review and hosted deployment remain required. No new production refresh has been started. After deployment, request one explicit governed refresh and verify Pierce coverage and complete RB rooms in both horizons, source labels, memory, publication and historical continuity.


### Final provenance correction before promotion

PR #522 first head `11e60c9bd29930fad6738e73019ec27eb6c1438e` passed focused CI and clean automated review. During final source-label inspection, the candidate-only provider-fumbles preservation path could retain an already complete provider row but still label it as using the first-party supplement when a second provider for that player needed completion. Returned the PR to draft before editing. The production routing now clears the unused supplement before scoring/labeling when retaining provider fumbles, and a mixed-provider live-producer regression verifies the exact source label. Updated focused selection: **63 passed**. A new exact-head review/CI/Stable result must replace the earlier head's evidence; no deployment occurred on the superseded head.


## Live release — PR #522, 13:55 UTC

Exact final head `40002d866b9d9ed497a5e02493414e993041db83` passed clean automated review at **13:40:17 UTC**, focused CI `42485914489`, Forecast `42485914477`, PR164 `42485914454`, and Stable `42485922748` / job `128747673473`: **2,688 passed / 5 skipped / one warning**, 831.72 s (13:51). Before/after exact-head checks passed. No unresolved review threads. Earlier `11e60c9b` evidence is superseded by this final head.

Merged as **`e0e045a44b4c5b19061922995b1a49d3347c91d2`**, identical tested tree **`fc877a1cfe648e9ca50f8e547be888f1f902f2d7`**. Render **`dep-dbo7u1psrm7s73b74et0`** is live at **2026-11-08T13:55:37.925116Z** on that exact merge. Existing single `0.5c-512mb` web service, branch main, auto-deploy off, no provider/plan/schema/worker change. No full suite repeated on merge push.

At **13:55:56.877397 UTC**, startup restored the existing State `703e822c...` with **Forecast/Simulation/Value complete**, product status **full**, Intrinsic **full**. RSS **340,697,088 B (324.91 MiB)** / process high-water **374,874,112 B (357.51 MiB)**; budget 429,496,720 B, active none/waiters zero. This validates preservation of the old publication at deployment; it is not new-policy RB coverage acceptance or a full refresh memory measurement.

The old publication intentionally remains unchanged, including 11/12 complete RB rooms. The assistant requested exactly one authenticated user Refresh Intelligence after the live restore check. No agent-triggered production refresh or manual artifact rewrite. New publication acceptance requires terminal Career expansion, all rostered coverage or explicit valid remaining failures, complete RB ranks in both 3-Year and Career, coherent source/policy labels, and resource/error evidence. Do not claim the columns are fixed numerically merely because code is deployed.


Deployment success event: `evt-dbo7umlfi0pc73b1rmj0`. Canonical Career artifact restored with a durable hit at **13:55:51 UTC** (3,407,281 JSON bytes); no compatible-restore error, failure or restart observed during the checked deployment interval. Refresh action was still pending while this receipt was written.


## Completed current-league refresh / user confirmation

The subsequent owned refresh produced State `f0aebd59...`, Career **367 estimates / zero coverage failures**, and final generation `4066eb14...` at **14:22:17 UTC**. Saved QB/RB/WR/TE Career rooms are all **12/12 complete**. The user confirms these capabilities are now operational, with slowness remaining. This closes the current-league RB functional acceptance layer; multi-league/waiver coverage and performance/headroom remain open. [Verified run evidence and next scale work](INTRINSIC_DISPLAY_SCALE_REVIEW_20261108.md).

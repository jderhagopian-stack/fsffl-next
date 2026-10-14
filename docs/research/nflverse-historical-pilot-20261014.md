# NFLverse historical evidence pilot — research-only checkpoint

**Started:** 2026-10-14  
**Status:** Source-release manifest audit completed; quantitative player-row and forecasting checks **not yet executed**.  
**Lane:** Independent ChatGPT research, separate from Career Coverage #405 / PR #454.  
**Authority:** No changes to production Forecast, Foundation 4, Career, Simulation 2.0, Value, State, model version, provider weights, or live operation are authorized.

## Mandatory commercial/proprietary-use hard gate — Management directive 2026-10-14

**Management requirement: FSFFL NEXT must remain independently monetizable and proprietary.** The research may inspect documentation and implementation approaches, but **no third-party dataset, fitted model, library, copied code or retained derived dataset can become a production dependency unless all rights below are affirmatively verified for that exact item, version, source and intended use.** Unknown/ambiguous is a **FAIL CLOSED / HOLD**, not implicit permission.

Pass criteria, ALL required:
1. **Commercial permission already granted:** the exact code/data/model license or authorized terms explicitly allow our intended paid SaaS use, without additional negotiated licensing, per-user fees or special approvals; retaining/hosting derived results and model training must also be within those permissions.
2. **Proprietary freedom:** no requirement to publish FSFFL NEXT application source, algorithms, model weights, training recipes, or proprietary derived datasets, or to license the FSFFL service under GPL/AGPL/CC BY-SA or a similar copyleft/share-alike condition. Attribution/notice obligations may be acceptable when clearly bounded and compatible with paid proprietary SaaS.
3. **Upstream-chain verification:** a permissive *code loader* license is not a license to ingest third-party data. Every NFLverse release tag and upstream originating dataset must be assessed independently for the permitted acts (access, copy, automate, store, train, run paid forecasts, and commercial output display). NFL trademarks, footage and endorsements are outside assumed permissions.
4. **No free-tier / redistribution obligation:** no term may require FSFFL NEXT subscriptions, dashboards, APIs, reports or application to be provided without charge; no obligation to redistribute restricted source or derived data.
5. **Reproducibility and audit:** keep source URL, license text/location and version/date, underlying provider, relevant terms, permitted uses, any required notices, approval status and review owner. Document remaining issues for specialist counsel review before production promotion.

### Preliminary screening — not final legal clearance

| Candidate | Published code/data license signals | Research disposition |
|---|---|---|
| `nflreadpy` code | MIT | **Candidate**, only as a loader; it cannot transfer rights to NFL/third-party content downloaded through it. |
| General `nflverse-data` assets | Repository says CC BY 4.0; licenses may differ by dataset, and CC only licenses rights actually held by the licensor | **HOLD** for each selected upstream dataset and use. CC BY 4.0 itself permits paid use and has no share-alike requirement; attribution/notice still matter. |
| `ffopportunity` code | GPL v3 | **EXCLUDE from any FSFFL product dependency** under conservative proprietary-only policy, even though private server use alone does not automatically trigger public-source release under standard GPL. Public paper/method ideas can be evaluated without incorporating code. |
| `ffopportunity` model weights and expected-point data | CC BY-SA 4.0 per project README | **EXCLUDE from production/training and commercial data derivatives** until any separate counsel-cleared, compliant use can be demonstrated without conflicting with proprietary strategy. Not automatically a requirement to make the *whole application* free, but sharing adapted licensed data can trigger ShareAlike. |
| `ffsimulator` code | MIT per README; separate upstream data rights | **METHODS-ONLY** research; no data copied and no product dependency until separate review. |
| `nflseedR` | Exact installed code/asset licenses and provider rights not yet fully verified | **HOLD**; low-priority. |
| FTN charting and other dataset-specific ShareAlike contents | CC BY-SA / other third-party terms may apply | **EXCLUDE by default**. |

**Interpretation:** GPL, AGPL and CC BY-SA are not bans on charging money. GPL obligations typically attach to conveying/distributing software and AGPL adds an applicable network-use source condition; CC BY-SA's ShareAlike applies to adapted licensed material when shared. However, this project imposes the stricter policy of **no avoidable open-source or dataset-disclosure obligations**. The permissive status of `nflreadpy`/MIT and `nflverse-data`/CC BY does not establish upstream commercial clearance.

### Execution gate for Pilot A/B/C

- **Until source-by-source commercial clearance is evidenced:** do only metadata/source-documentation/reproducibility research; do not ingest uncertain-rights releases into FSFFL production, train a product model on them, or redistribute their data. A bounded offline research experiment may be proposed separately, but do not assume research rights are automatic.
- If a dataset cannot be affirmatively cleared under existing permissions, **drop it and find a suitable alternative**; do not seek paid/special commercial rights as part of this workstream.
- No package/classifier copied from GPL/AGPL projects, no pretrained ShareAlike model/data import, and no default R ecosystem dependency. Independently implementing general statistical ideas is not the same as copying proprietary or copyleft implementations.
- Before any code/data integration, Management receives a concise **GO / NO-GO rights ledger** reviewed by appropriate legal counsel for commercial deployment as needed. The research report alone is not legal assurance.
- Career #405 remains independent and must not be delayed.

Primary published references checked on 2026-10-14:
- [nflreadpy licensing and upstream data note](https://nflreadpy.nflverse.com/)
- [nflverse-data repo license](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md)
- [ffopportunity source vs model/data terms](https://github.com/ffverse/ffopportunity#terms-of-use)
- [ffsimulator code/data terms](https://github.com/ffverse/ffsimulator#terms-of-use)
- [CC BY 4.0 terms](https://creativecommons.org/licenses/by/4.0/)
- [CC BY-SA 4.0 terms](https://creativecommons.org/licenses/by-sa/4.0/)
- [GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.html)
- [GNU AGPL explanation](https://www.gnu.org/licenses/why-affero-gpl.html)

---

## Decision

Use NFLverse as a **candidate historical-evidence and player-identity source**, not an automatic replacement for FSFFL's models. Benchmark FFverse forecasting and empirical weekly-outcome techniques as challengers only. Do not treat realized historical fantasy points or expected points calculated after games as timestamp-valid projections of those same games.

Prior desk review (2026-10-14): `docs/forecast/historical-source-research.md` already approved nflverse/nflreadpy as an outcomes/identity research path. Our existing `src/fsffl/forecast/career_calibration.py` has explicit survival and conditional-production evidence, and Simulation 2.0 already owns league-specific competitive outcomes with 50,000 deterministic trials. We should enrich those established inputs, not duplicate downstream model authority.

## First completed factual check: release availability (metadata only)

Using the official `nflverse/nflverse-data` GitHub release API, checked seasonal asset **names and last-updated timestamps** for each year 2019–2026:

| Release tag | 2019–2025 yearly files | 2026 yearly files | Evidence and caveat |
|---|---|---|---|
| `stats_player` | Available, regular and weekly among release assets | Available; `stats_player_reg_2026.csv` updated 2026-10-14 14:33 UTC | Published asset ≠ verified completeness or forecast |
| `pbp` | Available yearly `play_by_play_YYYY` | Available; updated 2026-10-14 14:31 UTC | Large data; don't acquire until a tested feature requires it |
| `snap_counts` | Available yearly | Available; 2026 updated 2026-10-13 11:01 UTC | Check provider identity and timestamp semantics |
| `injuries` | Available yearly | Available; 2026 updated 2026-10-14 12:50 UTC | A current historical archive is NOT necessarily as-of availability |
| `depth_charts` | Available yearly | Available; 2026 updated 2026-10-14 12:51 UTC | Verify historical effective dates and data provenance |
| `players` | Global identity file, not seasonal assets | Global identity file | Need explicit ID crosswalk and joining audit |

Sample exact released files:
- 2025 player regular-season stats CSV: `https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_2025.csv` (metadata size 882,104 bytes).
- 2026 player regular-season stats CSV: `https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_2026.csv` (metadata size 688,299 bytes).
- 2025 player stats Parquet: `https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_2025.parquet` (metadata size 286,768 bytes).
- Official Python API: `https://nflreadpy.nflverse.com/api/load_functions/`.

**Limit:** These are release-manifest observations only; no asset contents, player IDs, columns, rows, null rates, season-to-season continuity or backtests were actually checked. The research execution environment could read release metadata, but could not retrieve raw GitHub release files. A separate offline executor with approved network access must do the next data-quality step. Do not describe this as a completed 335/252-player audit. Availability dates are when current release assets were uploaded/updated, *not* proof of when the information became knowable during historical seasons.

## Pilot A: historical identity / factual-data quality — NEXT EXECUTABLE GATE

**Population:** frozen 335-player regression cohort; the current exact-State roster population (last PR #454 description: 252 rows, 243 Career numerics and nine explicit unresolved); a bounded cross-position rookie/deep-player sample, plus 2019–2025 historical player-season subjects. Keep these categories distinct. Obtain exact canonical subject/State manifests at execution time; never infer current counts from old PR descriptions.

**Data:** start with small player-season and player-week stats and NFLverse player ID crosswalk. Add historical snaps, roster status, draft, injuries/depth charts only if each field is relevant and provenance can be verified. Historical 2019–2025 is the primary analysis window; 2026 completed weeks are a separate freshness and contemporaneous-identity check, not a full-season holdout.

**Row-level output:** for every subject report canonical FSFFL ID, NFLverse/GSIS identity, exact/missing/ambiguous match status, source/season/week, relevant field availability and types, source availability/effective timestamp, missing/null or coverage reasons, and whether the evidence supplies a previously missing *input* rather than an invented downstream value. For the nine unresolved Career cases, record individual evidence checked and do not claim NFLverse resolves them without a complete valid forward-input chain.

**Metrics:** match rate among identifiers with comparable source eligibility, ambiguity/collision rate, per-season field completeness, historical subject continuity, raw-data revisions, contemporaneous freshness, artifact MB, run wall time, CPU and peak RSS. Provide numerator and denominator by position/cohort; never report a global percentage without missingness definitions. Explicitly distinguish player truly unavailable from join failure, no opportunities, unreported game, or model-ineligible candidate.

**Acceptance:** reproducible manifest (source asset URL/commit, retrieval time, SHA256, schema fingerprint), raw evidence retained only where rights permit, no current player names joined loosely, no silent zero-fill, deterministic aggregates. Publication forbidden.

## Pilot B: forecast challenger — AFTER A

Compare lagged player usage/snap/opportunity features and `ffopportunity`-style expected opportunity metrics with an agreed frozen FSFFL Year-1 model/reference over **the same** historical cohorts and targets. Keep ranking ECR separate from raw-stat projections; expected fantasy points from completed plays is retrospective evidence and must be lagged before predictive testing. Use chronological rolling-origin development/test splits, with strictly earlier training and PIT-available features.

At minimum: QB/RB/WR/TE MAE, bias, interval coverage/CRPS where distributions support it, healthy/availability cohorts, deep-player coverage and bootstrap confidence intervals. Report `baseline`, `baseline + NFLverse features`, and where feasible `isolated opportunity challenger` using identical point-in-time targets. Judge improvements by held-out accuracy, calibration, coverage and compute—not an attractive current-season correlation. No promotion on an aggregate win masking worse QB/rookie performance.

## Pilot C: Career/Simulation methods — AFTER B

- **Career:** test historical survival/remaining-relevant probability and conditional future fantasy production separately. Missing stat rows are not proof of retirement or zero. Compare to the accepted Career transition reference, not replace 335 numeric regression expectations inside #405.
- **Simulation:** compare empirical player-week skew, tails, variance, rare events and conditional availability to accepted weekly distribution assumptions. `ffsimulator` is an experimental MIT-coded R *research comparator*, not a drop-in for FSFFL's fantasy rules, replay, origin picks or 50k kernel. `nflseedR` simulates real NFL seasons; defer absent an explicit team-environment modeling question.

## Rights, resource and architectural gates

- `nflreadpy` is MIT-coded; `nflverse-data` repository declares CC BY 4.0. Upstream dataset rights are separate and must be reviewed dataset-by-dataset before commercial use or redistribution.
- `ffopportunity` code GPL v3, included models and expected points data CC BY-SA 4.0: investigate legal implications before code/model/data reuse. Studying published methods is not commercial clearance.
- Do **not** install R, Polars, or bulk PBP into the production Render web runtime for a research test.
- Do acquisition, joins, fits and benchmarks offline with bounded memory/transfer; retain versioned shared evidence outside browser requests.
- No code changes, automatic PR merge, deployment, Career #405 interruption or new live provider source authority; one explicit Management gate if a promoted change is supported.

## Operational separation / next action

**Career #405:** continues independently through its established PR #454 review, full-suite/CI and release gates. This pilot must not become a prerequisite for that work.

**NFLverse research:** obtain actual dataset bytes via an independent offline runner with network access, load small 2025/2026 player stats and global player IDs, compute first exact-ID join against frozen-335 and the latest saved roster cohort, then expand coverage by season and source only where useful. Attach a reproducible audited table and unresolved-case ledger to this research record. Only after the first quantitative comparison decide whether to authorize a narrowly scoped implementation PR.

**Current handoff:** `metadata verified; dataset bytes not accessible in current ChatGPT research runtime; quantitative pilot pending independent execution`.

## References

- `docs/forecast/historical-source-research.md`
- `docs/forecast/modern-historical-window.md`
- `docs/operations/workstreams/CAREER_COVERAGE_EXTENSION.md`
- `docs/operations/directives/20260928_SIMULATION_2_0_PROGRAM.md`
- `https://github.com/nflverse/nflverse-data/releases/tag/stats_player`
- `https://github.com/nflverse/nflverse-data/releases/tag/pbp`
- `https://github.com/nflverse/nflverse-data/releases/tag/snap_counts`
- `https://github.com/nflverse/nflverse-data/releases/tag/injuries`
- `https://github.com/nflverse/nflverse-data/releases/tag/depth_charts`
- `https://github.com/ffverse/ffopportunity`
- `https://github.com/ffverse/ffsimulator`

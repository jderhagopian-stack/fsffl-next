# NFLverse historical evidence pilot — research-only checkpoint

> **2026-10-14 RIGHTS REVIEW CHECKPOINT (CONTROLLING):** The [source-level licensing ledger](./nflverse-commercial-rights-ledger-20261014.md) has been completed as a *preliminary review*. Permissively MIT-licensed code can be considered in a paid proprietary FSFFL product with notices; some GPLv3 hosted use can be compliant if never conveyed; CC BY-SA data need derivative-material analysis. **BUT production/model-training rights to NFLverse's core player-statistics, PBP, and upstream PFR/NFL sourced datasets remain unproven.** The public NFLverse paid-product licensing question #101 closed without clarification. NFL.com and Sports Reference site terms contain directly relevant restrictions. **Do not begin source-data acquisition, training, or integration under #458 until exact existing rights and permitted acts are sufficiently evidenced.** No new fees/special licenses or proprietary FSFFL code release. Career #405 continues separately. This note supersedes any older text below implying a quantitative run is now approved.

**Started:** 2026-10-14  
**Status:** Source-release manifest audit and preliminary commercial-rights screen completed; quantitative audit not executed; NFLverse source-data gate on HOLD.  
**Lane:** Independent ChatGPT research, separate from Career Coverage #405 / PR #454.  
**Authority:** No changes to production Forecast, Foundation 4, Career, Simulation 2.0, Value, State, model version, provider weights, or live operation are authorized.

## Commercial-use and proprietary-code eligibility — Management clarification 2026-10-14 (supersedes earlier blanket exclusions)

**Governing rule:** FSFFL NEXT may use free/open data, model methods, libraries and tools **if** their applicable rights already permit use in a paid commercial product at **no required license, royalty, per-user or special commercial-permission charge**, any attribution/notice obligations can be fulfilled, and the intended integration **does not obligate FSFFL NEXT to disclose, license openly, or distribute its proprietary application code**. Do not exclude a source simply because it is open source, GPL-labelled, or requires attribution. Do not conflate permission to charge with preservation of proprietary code.

**Fail closed on uncertainty:** no source becomes a production dependency merely because its files are publicly downloadable or its loader is MIT-licensed. Verify the exact dataset/model/code version, upstream rights, access restrictions, permitted processing and model-training uses, retention, paid-product display/derived outputs, attribution/notice, and redistribution or source-disclosure triggers. If unresolved, mark HOLD and do not promote; replace sources that would require negotiated fees or new commercial agreements. This is a source-by-source legal/technical screen, not a declaration of blanket commercial clearance.

### Distinguish the obligations by artifact and use

| License / resource | Possible eligibility under clarified rule | Hard question before production use |
|---|---|---|
| MIT, BSD, Apache 2.0 code; e.g., `nflreadpy` (MIT), `ffsimulator` code (MIT) | **Eligible for consideration** with applicable attribution, notices and other license conditions | What distinct rights cover every data/model artifact downloaded by the code? |
| CC0 / public domain evidence | **Eligible for consideration**, after origin and claimed status verification | Is the record actually in scope, and are third-party terms/access limits separate? |
| CC BY 4.0 data; e.g., general `nflverse-data` repository label | **Eligible for consideration**: allows commercial reuse/adaptation with proper attribution and license notices, and does not itself require releasing proprietary source or share-alike adaptations | Did the licensor have rights to the particular upstream NFL/provider material for our exact uses, including paid SaaS, training, storage, and output displays? |
| CC BY-SA 4.0 data or weights; e.g., `ffopportunity` prebuilt data/models | **Conditional / HOLD** rather than automatic exclusion. Commercial use is allowed. ShareAlike can apply to **adapted licensed material we share**; it does not automatically require making an independent application's source public. | Would our model weights, training data, feature table, player-level outputs or other proprietary assets be an adaptation that must be shared/licensed alike? Can boundaries be documented without disclosing proprietary material? |
| GPLv3 software; e.g., `ffopportunity` code | **Conditional / HOLD** rather than blanket ban. GPL allows commercial use and, generally, running modified GPL code solely on a private server without conveying it does not itself trigger GPL source-distribution duties. | Would we convey/distribute a combined GPL-covered program (including JS/mobile/offline clients or components) or otherwise create a source-disclosure obligation for FSFFL proprietary code? If yes, NO-GO for that integration. |
| AGPL software | **Presumptive HOLD / likely NO-GO for integrated network-service code** because relevant network interaction can create source-offer obligations. Not an unconditional ban on all theoretical uses. | Would actual hosted use require offering source of a combined or modified program or disclose any FSFFL proprietary code? If yes, NO-GO. |
| CC BY-NC / other noncommercial-only data; royalty-bearing, premium-license, negotiated-approval sources | **NO-GO** for the proposed production use | Existing rights do not satisfy paid, zero-additional-license-cost and independent proprietary use. |
| Unlicensed, unclear, prohibited-scrape or upstream-rights-unknown datasets | **HOLD**, not authorized | Obtain clear existing rights or substitute; no automatic acceptance from an open GitHub repo. |

**Important distinction:** GPL and ShareAlike do not require software or data to be offered for free. A licensing duty to share changes or source, where triggered, is separate from permission to charge for a product. We care about **our own application-code disclosure**, but must also explicitly assess any obligations affecting proprietary datasets or fitted-model artifacts before approval. No project source publication or unwanted model/data disclosure should be introduced inadvertently.

### Concrete approval test (each item must pass)

1. **Paid service allowed:** the specific licensed material and upstream originating content are usable for a paid proprietary SaaS, including the actual access, copying, storage, training, and display/derived-output uses planned.
2. **No mandatory commercial license payments:** no additional provider license fees, royalties, per-user data charges, minimums, special requests, or approvals. Normal self-incurred hosting/infrastructure costs and compliance work are not defined as third-party licensing costs.
3. **No proprietary FSFFL code disclosure:** review the **actual integration/distribution architecture**, not only the package name. No requirement to publish/offer FSFFL application source, or relicense the FSFFL application as open source. Identify any separate restrictions on proprietary weights, model artifacts and derived datasets.
4. **Attribution allowed:** retain notices, credit, modification indicators, license links and any attribution required by permitted resources. Paid product and attribution are compatible.
5. **Prove rights chain and maintain ledger:** per-source license/source URL and dated version, originating rights holder, terms for each intended use, downstream propagation/attribution, technical boundary if a copyleft component is used, status GO / HOLD / NO-GO and evidence. Seek qualified legal review for unresolved or material edge cases; desk research is not legal assurance.

### Revised first-pilot order

**First deliverable is an exact-data-source license/rights ledger, not a categorical license blacklist.** Examine `nflreadpy` loader code separately from nflverse released datasets, and assess `ffopportunity` code separately from its prebuilt model weights/data. Clear as many data sources as possible under their existing terms without opening FSFFL's code; use free commercially permitted sources with appropriate attribution. A HOLD source cannot be used for production or to train a product model until its use is cleared. Offline permitted testing may proceed on appropriately cleared research data. Career #405 remains nonblocking and unchanged.

Official reference texts: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), [GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.html), [Open Source Initiative FAQ](https://opensource.org/faq), [ffopportunity terms](https://github.com/ffverse/ffopportunity#terms-of-use), [ffsimulator terms](https://github.com/ffverse/ffsimulator#terms-of-use).

---

## Management focus update — Historical data FIRST (2026-10-14)

**Decision:** Historical factual/player evidence is the sole active NFLverse evaluation priority. Defer adopting or benchmarking `ffopportunity`, `ffsimulator`, `nflseedR`, or replacing FSFFL Forecast/Career/Simulation models until the historical source rights and real coverage are demonstrated. Do not start a parallel implementation lane while Career Coverage #405 is underway.

**Priority source family:** `nflverse-data` `stats_player` (weekly and regular-season summaries, 2019–2025 completed seasons and elapsed 2026 weeks) — basic numerical passing/rushing/receiving/fantasy-scoring coordinates, player ID, season/week/team. The publisher documents files created via `nflfastR::calculate_stats` from its play-by-play pipeline: see [nflverse-pbp/R/update_stats.R](https://github.com/nflverse/nflverse-pbp/blob/master/R/update_stats.R). Its published license label is CC BY 4.0; **upstream PBP/data rights remain the specific unsolved commercial issue**, so code or blanket repository license does NOT equal clearance to store, train, or publicly show the data.

**Secondary only if cleared:** minimal canonical GSIS identity and career-season continuity; current roster cohort joins; later historical availability/missed games, usage and age/experience. Do not add PFR-sourced snap counts or PFR-sourced draft-pick datasets merely to fill gaps while their provenance/terms remain on HOLD. Do not acquire full PBP unless model comparison demonstrates that granular features add measurable value and its rights are cleared separately.

**First research deliverable (rights/provenance before data download):** field/source provenance for the core `stats_player` weekly/seasonal files, precise permitted/no-fee paid SaaS uses (internal storage, training, derived output, user-visible historical stat lines), no FSFFL proprietary-code release, and attribution notice requirements. Record each category with a clear GO/HOLD/NO-GO and evidence, distinguishing uncopyrightable factual information from obligations imposed by the manner/source of acquisition. NFL.com terms restrict direct service retrieval; a public redistributor license does not automatically settle that issue. If authoritative existing rights do not support the intended use, document alternative lawful acquisition/independently sourced numerical facts without proposing paid commercial data licenses.

**Next quantitative deliverable only if applicable rights are established:** player-ID matched coverage for frozen-335, exact-State roster and unresolved Career subjects; completeness and 2019–2025 career longitudinal continuity; 2026 completed-week availability (not full 2026 season); row-level evidence, league-scoring reconciliation, and source timestamp/revision tracking. Compare incremental usefulness to existing accepted models without production changes.

**No changes to current priority:** Career #405 proceeds unchanged. No new model fit, code, merge, deploy, or provider integration is approved by this note.

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
- `ffopportunity` code GPL v3 and packaged models/data CC BY-SA 4.0: **conditional rights review**, not blanket exclusion. A valid server-only GPL use may not require source disclosure; any adapted CC BY-SA material that is shared may create distinct ShareAlike obligations. Explicitly document proprietary-code and proprietary-model/data boundaries before approval.
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

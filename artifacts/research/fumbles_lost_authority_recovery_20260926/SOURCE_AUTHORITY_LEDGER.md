# FSFFL NEXT — FUMBLES_LOST Source / Authority Ledger

Date: 2026-09-26 UTC  
Workstream: Forecast Research  
Scope: bounded recovery of canonical `FUMBLES_LOST` Forecast authority only

## Authority requirement

`FUMBLES_LOST` remains a **core/material** player Forecast coordinate. The accepted auxiliary single-source tier does not apply.

A production-authoritative coordinate therefore still requires, for the exact target horizon/cutoff:
- exact lost-fumble semantics, not total fumbles;
- at least two genuinely independent eligible sources;
- source health and player coverage sufficient for the target population;
- point-in-time provenance and compatible timestamps/horizon;
- private-beta rights for the actual acquisition/storage/derived-Forecast use;
- non-zero, target-compatible uncertainty;
- no cross-horizon substitution, absent-as-zero treatment, or stale-artifact reuse.

Rights eligibility and analytical authority are separate gates.

## Durable evidence reused first

### Current FSFFL preseason/season baseline

The last authentic pre-kickoff FSFFL offense Forecast artifact is artifact 63:
- computed: `2026-09-09T23:26:16.657633Z`;
- raw evidence as-of: `2026-09-09T23:23:53.152680Z`;
- providers: FFToday + Razzball;
- subject families: QB/RB/WR/TE;
- horizon: season/preseason;
- `FUMBLES_LOST`: absent.

The later preserved 1,675-observation fallback retains the same two-source offense coordinate set and likewise contains no `FUMBLES_LOST`.

Therefore the current immutable season-horizon fallback cannot gain full authority merely by rescoring it differently.

### Retained 2024 exact PIT evidence

The retained pre-opener 2024 panel contains exact player lost-fumble projections from two direct providers:

| Provider | Semantics | Subjects | Retained cohort | Rights today | -2 scoring bias | MAE | RMSE |
|---|---|---:|---|---|---:|---:|---:|
| CBS | exact lost fumbles | 337 | 2024 pre-opener | research-only / not deployment-cleared | -0.5401 pts | 1.5608 pts | 2.5712 pts |
| FantasySharks | exact lost fumbles | 337 | 2024 pre-opener | research-only / not deployment-cleared | -0.3139 pts | 1.4665 pts | 2.3660 pts |

The equal two-source comparator RMSE was 2.2771 points at a -2 scoring coefficient; omission RMSE was 2.5176 points.

Converted back to raw event-count scale:
- CBS RMSE: **1.2856 lost fumbles**;
- FantasySharks RMSE: **1.1830 lost fumbles**;
- equal two-source RMSE: **1.1386 lost fumbles**;
- omission RMSE: **1.2588 lost fumbles**;
- mean absolute CBS/FantasySharks disagreement: **0.5632 lost fumbles**.

This is useful evidence that a non-zero coordinate uncertainty is required. It is **not** promotable 2026 uncertainty: only one retained season is available, the 2026 candidate providers differ, and neither 2024 provider is deployment-cleared for this use.

## Candidate inventory

| Provider / evidence | Exact FUMBLES_LOST? | Relevant horizon | Health / coverage | Independence | Private-beta rights | Current disposition |
|---|---|---|---|---|---|---|
| FFToday + Razzball artifact 63 | **No** | authentic 2026 pre-opener season | retained and governed | independent pair | existing retained baseline only | cannot solve coordinate; coordinate absent |
| CBS 2024 retained | **Yes** | 2024 pre-opener season | 337-player retained panel | direct provider | research-only / deployment not cleared | calibration/reference only |
| FantasySharks 2024 retained | **Yes** | 2024 pre-opener season | 337-player retained panel | direct provider | research-only / deployment not cleared | calibration/reference only |
| Razzball current position pages | **Yes**, `Fum Lst` | current ROS | **FAIL**: current pages show impossible ~30–32 projected games for examples; current code intentionally isolates season evidence from these ROS pages | direct proprietary model | `REVIEW_REQUIRED`; explicit consent required | reject as current authority |
| JerryGM Projections API | **Yes**, native `fumblesLost` | ROS documented; full-season/preseason mode also documented | live target payload/coverage still requires API-key validation | provider documents its own model; one ecosystem = one vote | `REVIEW_REQUIRED` for ensemble/derived-Forecast use because terms restrict training/calibrating competing projection products | strongest direct technical candidate after written rights clarification and live validation |
| Fantasy Nerds API | **Yes**, NFL dictionary defines `fumbles_lost`; ROS projection endpoint documented | current ROS | paid live payload/coverage still must be acquired and validated | **UNRESOLVED**: projections are a weighted multi-site consensus | `PRIVATE_BETA_ALLOWED` only through an active paid API package and within API terms; raw API access may not be redistributed; commercial transition still requires recheck | shortest second technical ROS candidate, but cannot count as an independent vote until underlying-source overlap is resolved |
| LineupExperts API | public docs do **not** establish the lost-fumble field | current ROS supported | requires subscribed endpoint/schema validation | internally modeled projection product appears direct, subject to endpoint confirmation | `REVIEW_REQUIRED`; written confirmation required for derived Forecast/model-input use | cleaner-independence fallback if exact field + rights are confirmed |
| FantasyPros | potentially available in full stat lines, but aggregate | ROS supported | access/product exists | aggregate overlap unresolved | prohibited for intended self-serve Forecast-input use absent written agreement | reject as current shortcut |
| CBS current public pages | current offense lost-fumble path not established for the required production route | current | current full-season offense page health previously failed | direct provider | prohibited for deployment absent permission/license | not eligible |
| FFToday current | no qualifying lost-fumble evidence established | current season | current production probe returned HTTP 403 | direct provider | `REVIEW_REQUIRED` | not eligible |

## Current-horizon finding

The current FSFFL resilient Forecast route is using the immutable **season/preseason-horizon** FFToday + Razzball baseline because the live full-season provider set does not presently have two healthy sources.

The technically promising new `FUMBLES_LOST` evidence is **current ROS** evidence.

Those horizons may not be mixed. In particular:
- a ROS lost-fumble projection cannot be inserted into the preserved season baseline;
- current code already removed the legacy Razzball behavior that supplemented season rows with ROS fumbles, explicitly identifying the cross-horizon read as an evidence-boundary problem;
- a fumble-only ROS patch would therefore violate the current Forecast authority contract even if two ROS providers were otherwise eligible.

## Shortest contingent current-ROS path

If Management separately authorizes a 2026 current-ROS ordinary-offense Forecast lane/rebase, the shortest technical `FUMBLES_LOST` candidate pair found is:

**JerryGM + Fantasy Nerds**

Why this is the shortest technical path:
- both document the exact lost-fumble coordinate rather than total fumbles;
- both expose current ROS projection products;
- JerryGM documents its own model, providing one clean direct provider ecosystem;
- Fantasy Nerds has an application-usable paid API path.

Remaining gates before the pair can count:
1. JerryGM must provide written clarification permitting FSFFL to use API output as governed ensemble/derived-Forecast evidence.
2. A qualifying Fantasy Nerds API subscription must be active and the live ROS payload must be captured with immutable provenance.
3. Fantasy Nerds must disclose or otherwise prove enough projection-source composition to demonstrate that the weighted consensus does not re-vote JerryGM or another source being counted independently. If overlap cannot be resolved, Fantasy Nerds cannot be the second independent vote.
4. Both live payloads must pass exact-horizon, timestamp, player-coverage, semantic and source-health checks.
5. A source-compatible non-zero uncertainty must be validated. The 2024 CBS/FantasySharks error panel is diagnostic evidence only and may not be transplanted as a production coefficient.

If Fantasy Nerds independence cannot be established, the next bounded path is **JerryGM + LineupExperts**, but LineupExperts requires both a live schema proof of exact lost-fumble projections and written model-input rights clarification.

## Authentic 2026 pre-opener path

No retained or newly located evidence establishes two deployment-eligible, independent, exact `FUMBLES_LOST` sources at the authentic pre-opener 2026 cutoff.

Artifact 63 itself proves the two governed pre-opener sources omitted the coordinate. The 2024 panel proves the coordinate was forecastable historically, but it is the wrong season/cutoff and carries research-only rights.

Accordingly, the authentic 2026 pre-opener path remains externally blocked unless a genuine pre-opener 2026 snapshot from qualifying sources is supplied/recovered with provenance and rights sufficient for production use.

## Public source references reviewed

- JerryGM API docs: https://api.jerrygm.com/api/ext/v1/docs
- JerryGM terms: https://www.jerrygm.com/terms/
- Fantasy Nerds NFL API docs: https://api.fantasynerds.com/docs/nfl
- Fantasy Nerds NFL data dictionary: https://api.fantasynerds.com/dictionary
- Fantasy Nerds Nerd Rank methodology: https://www.fantasynerds.com/about/nerd-rank
- Fantasy Nerds terms: https://www.fantasynerds.com/terms
- Fantasy Nerds API pricing: https://api.fantasynerds.com/getting-started/pricing
- LineupExperts NFL API reference: https://www.lineupexperts.com/API-Football-Reference
- LineupExperts API pricing: https://www.lineupexperts.com/API-Pricing
- LineupExperts terms: https://www.lineupexperts.com/terms.php
- Razzball current ROS QB projections: https://football.razzball.com/projections-qb-restofseason/

## Authority conclusion

**No two-independent-source, same-horizon, private-beta-eligible `FUMBLES_LOST` path is presently promotable under the existing Forecast route.**

The blocker is no longer lack of technical candidates. It is the conjunction of:
- horizon authority;
- current provider rights/access;
- true source independence;
- live source health/coverage;
- source-compatible uncertainty.

No zero, single-source, cross-horizon, or stale-artifact workaround is authorized.

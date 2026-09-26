# FSFFL NEXT — Source Rights / Deployment-Stage Ledger

Assessed: 2026-09-25

Purpose: operational source-governance classification under `SOURCE_GOVERNANCE.md`. This is not a legal opinion. It records the current product interpretation of provider terms for the specific FSFFL use case and is deliberately conservative.

## Interpretation

FSFFL is provider-agnostic. The same canonical Forecast coordinate may be supplied by different providers over time.

Rights status is separate from analytical authority:
- a source can be permitted for beta but analytically insufficient;
- analytically strong but contractually unusable;
- acceptable for display but not as input to FSFFL's own Forecast;
- acceptable for private beta but require commercial re-review.

The intended K/DST use is not merely "show the provider's projection." It is generally: acquire provider projection evidence, normalize it into canonical coordinates, combine/evaluate it under FSFFL Forecast governance, persist permitted evidence/provenance, score it under arbitrary league rules, and expose derived downstream intelligence. Terms must permit that actual use.

## Current provider classifications

| Provider | Intended FSFFL Forecast-input status | Private-beta operational status | Commercial status | Key reason / next action |
|---|---|---|---|---|
| JerryGM Projections API | Potentially strong exact-coordinate candidate | **REVIEW_REQUIRED** | Commercial plan exists, but model-input use still requires clarification | API terms expressly allow output in one's own apps and Pro permits paid-product display, but prohibit using output to train or calibrate a competing projection product. FSFFL's ensemble/derived-Forecast use could fall within that restriction. Obtain written clarification specifically authorizing use as governed Forecast evidence/ensemble input, not merely display. |
| LineupExperts API | Potential K/DST independent candidate | **REVIEW_REQUIRED** | Recheck/contract review required | API terms contemplate use in declared websites/apps and require every usage forum to be registered, but prohibit benchmarking/competitive use and do not clearly state rights for incorporation into a derived projection model. Obtain written confirmation for FSFFL private-beta model-input use; if confirmed, classify `PRIVATE_BETA_ALLOWED` for the declared app/API plan. |
| Fantasy Nerds API | Exact-stat API candidate, but projection product is a weighted multi-site consensus | **PRIVATE_BETA_ALLOWED only through an active paid API package; analytical independence unresolved** | Commercial tier/terms must be re-audited for the actual launch posture | Current API terms permit API data in applications and provider guidance permits local caching, subject to plan/access and redistribution restrictions. This rights classification does not make Nerd Rank an independent Forecast vote: Fantasy Nerds documents a weighted aggregation of multiple projection sites, so underlying-source overlap with any other FSFFL provider must be resolved before it can count toward the two-source rule. |
| FantasyPros API | Aggregate/reference candidate; independence unresolved | **PROHIBITED for intended self-serve Forecast-input use absent written agreement** | Commercial agreement required for commercial apps | Premium permits personal/non-commercial production apps, but API terms also prohibit using the data to develop a product/service that competes with FantasyPros. FSFFL is sufficiently adjacent that Management should not rely on the personal-use grant. A negotiated agreement could supersede this. Aggregate source decomposition remains a separate analytical issue. |
| CBS Sports public fantasy/projection content | Historical/reference evidence; not a preferred adapter target | **PROHIBITED for deployment absent written permission/license** | Commercial permission/license required | Current CBS fantasy terms grant personal/non-commercial use and prohibit redistribution/commercial exploitation; CBS terms also restrict derivative/redistribution rights. Do not build automated production ingestion from public CBS pages without written permission. |
| RotoWire public/subscription content | Technically useful in places, but not current deployable source | **PROHIBITED absent written authorization/license** | Written authorization/license required | Terms prohibit automated accumulation into datasets and derived projections/analysis for use outside personal, non-commercial service use. |
| Razzball projections | Technically useful; current football model is independent/proprietary | **REVIEW_REQUIRED / do not deploy without explicit consent** | Recheck/permission required | Published Razzball projection-use guidance requires explicit consent to incorporate projections into published aggregations/models or resold tools. The football FAQ confirms proprietary projection output but does not grant separate model-input rights. Seek written consent before ingestion into FSFFL Forecast. |
| FFToday projections | Useful pre-opener K evidence; current rights unclear | **REVIEW_REQUIRED** | Recheck required | Public projection availability and paid Draft Buddy do not establish permission for automated ingestion/persistence/model incorporation. No sufficiently clear current source-use grant was located in this review. Seek written permission or use only as non-deployed research evidence. |
| FantasyPros D/ST aggregate (pre-opener historical evidence) | Research/reference only; not automatically independent | **RESEARCH_ONLY under current self-serve terms** | Commercial agreement required | Even apart from rights, aggregate composition prevents automatic treatment as an independent provider vote. |
| 2024 retained FantasySharks / ESPN / CBS K-DST corpus | Historical calibration/replay evidence | **RESEARCH_ONLY unless separately re-cleared for deployment** | Recheck before any commercial reuse | The corpus is valuable for PIT replay and uncertainty research. Its existence does not itself create a deployment license or make any provider a current production adapter. |

## Immediate implications for K/DST

1. The prior phrase "commercial rights are required now" is superseded. The actual beta gate is **rights eligibility for the intended private-beta use**.
2. No current provider is automatically promoted by this correction.
3. The two most actionable clarification targets are:
   - **LineupExperts** — confirm that a subscribed API feed may be used as one input to a private, non-commercial fantasy projection/decision product, with the FSFFL application declared in the account.
   - **JerryGM** — confirm whether using API output as governed evidence in an FSFFL ensemble/derived Forecast is permitted despite the "train or calibrate a competing projection product" restriction.
4. FantasyPros self-serve access should not be treated as a safe workaround because its non-compete language is directly relevant.
5. CBS, RotoWire and Razzball should not be deployed without explicit permission/license for the intended use.
6. FFToday remains useful as historical/pre-opener evidence but does not currently have a clear deployable rights path from public terms alone.

## Required metadata for any promoted source

A source promoted to beta must persist:
- provider and product identity;
- acquisition method/API plan;
- governing terms/license URL;
- captured/review date;
- beta-use classification;
- `commercial_recheck_required`;
- attribution requirements;
- storage/retention restrictions;
- redistribution/display restrictions;
- derivative/model-input permission;
- source-health and semantic coverage;
- independence group;
- replacement/fallback provider mapping.

## Commercial transition

Before any paid/commercial launch, re-audit every deployed provider. Any source that cannot be upgraded to `COMMERCIAL_ALLOWED` must be licensed, replaced, or removed behind the same canonical provider-neutral contracts.


## FUMBLES_LOST-specific implication — 2026-09-26

The bounded FUMBLES_LOST recovery separates rights from analytical authority:
- Fantasy Nerds has a plausible private-beta API-use path under an active paid package, but its weighted-consensus construction is not automatically an independent provider vote;
- JerryGM remains `REVIEW_REQUIRED` for FSFFL ensemble/derived-Forecast input;
- LineupExperts remains `REVIEW_REQUIRED` and its public NFL API documentation does not establish an exact lost-fumble projection field;
- Razzball current ROS lost-fumble pages fail source-health checks and still require consent for model/aggregation use;
- retained 2024 CBS/FantasySharks exact lost-fumble evidence remains research-only and cannot substitute for 2026 deployment rights.

Detailed evidence and horizon analysis:
`artifacts/research/fumbles_lost_authority_recovery_20260926/SOURCE_AUTHORITY_LEDGER.md`

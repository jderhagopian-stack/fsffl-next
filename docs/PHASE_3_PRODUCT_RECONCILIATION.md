# FSFFL NEXT — Phase 3 Product Reconciliation

Status: **Phase 3 active — Intrinsic Value productized; progressive cold-path delivery merged; Intrinsic dynasty display-scale repair in review**  
Roadmap authority: `docs/FSFFL_NEXT_PRODUCT_PRIORITIES.md`  
Original Intrinsic productization starting `main`: `641378af5b4d9bb99eae5ec3aa4ee8cc70118d5b`  
Commercial-latency slice starting `main`: `72fbfd35a920fa38cea523ef0979735e4e1ceb56`  
Intrinsic dynasty display-scale slice starting `main`: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`

This document records actual product state against the canonical roadmap. It does not replace or silently rewrite that roadmap.

## Deployment and release state

PR #133 promoted FSFFL Intrinsic Value v1. PR #134 productized it in Franchise → Value Lens. PR #135 added progressive Market / Trade Center answer delivery without reducing 50,000-run Simulation fidelity.

The private beta is deployed through the existing `next-8-product-layer` release branch. The governed release procedure is to verify that branch is a clean ancestor of the approved `main`, fast-forward it non-forced to the exact approved `main` SHA, manually trigger the existing Render service, and then verify the live SHA and smoke behavior. After PR #135, the live beta was aligned to `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`.

Repository state and live state must remain distinct concepts:

1. **merged to main** — repository-authoritative behavior;
2. **released to the private beta** — approved main SHA promoted through the release branch and Render;
3. **customer-facing/productized** — presentation exists and is understandable when that repository state is deployed.

## Phase 3 surface matrix

| Surface | Current status | What exists | Remaining Phase 3 gap |
| --- | --- | --- | --- |
| Home | **MOSTLY COMPLETE** | Scan-first attention view, competitive state, expected wins/playoff outlook, opportunity handoff | Durable beta-learning loop |
| Franchise | **MOSTLY COMPLETE** | Diagnosis, roster/assets, Value Lens, separate Market / Intrinsic / League Market / Team Utility concepts | Intrinsic dynasty display-scale repair must merge and be live-validated |
| League | **MOSTLY COMPLETE** | League structure, position map, age/depth/future-capital context | League Market Value not production-ready |
| Market / Opportunities | **MOSTLY COMPLETE** | Market Focus, structural quick view, deeper Decision enrichment, reuse | Live user-perceived latency validation and later Intrinsic-vs-Market discovery |
| Trade Center | **MOSTLY COMPLETE** | Quick package economics, pre-Simulation Decision evidence, unchanged 50k Simulation, quick/deep counter paths | Fresh 50k Simulation remains deep-path latency blocker |
| Behavioral Intelligence | **MOSTLY COMPLETE** | Observed owner history, trade shapes, position flows, counterparties, provenance | Calibrated owner preference/acceptance remains evidence-blocked |
| Team/Owner-adjusted Value | **BLOCKED** | Team Utility remains downstream and separate | No governed owner-adjusted asset coordinate |
| Performance | **PARTIAL / materially improved delivery contract** | Exact caches, Simulation reuse, progressive Market/Trade delivery, duplicate exact Simulation coalescing | Raw fresh 50k compute remains expensive |

## Intrinsic Value authority — raw coordinate

The authoritative Intrinsic v1 calculation remains unchanged:

`surplus_y = max(0, player Forecast_y - marginal-lineup-opportunity replacement Forecast_y)`

`raw intrinsic = 1.00 × surplus_Y1 + 0.85 × surplus_Y2 + 0.70 × surplus_Y3`

The raw value is therefore **weighted expected fantasy-point surplus above replacement**. It is an internal FSFFL economic/fundamental coordinate. It is not a market price, not Team Utility, and not itself a customer-friendly dynasty-value magnitude.

Forecast continues to own football production/trajectory and QB career-state inference. Value consumes Forecast and owns replacement economics. Market evidence is not an input to raw Intrinsic. Team Utility remains downstream.

## Live Value Lens defect discovered after PR #134/#135 deployment

Live beta testing exposed two presentation/integrity problems:

1. Broad Market was shown as a percentile while raw Intrinsic was shown directly as values such as `109.7 pts`, `183.5 pts`, and `240.2 pts`. That mixed a market rank with an internal weighted-surplus unit and made the raw economic coordinate look like the intended dynasty asset-value score.
2. Players with valid model-produced zero surplus could appear as `0 pts` with a misleading percentile such as `34th pct`. The old browser percentile function assigned the midpoint rank of the entire tied-zero block. That percentile did **not** mean missing evidence, but the presentation made zero versus unavailable impossible to interpret confidently.

The old frontend did **not** silently substitute zero for a missing estimate: it rendered `Unavailable` when no estimate object existed. Therefore the observed `0 pts` cases (including KC Concepcion, Dallas Goedert and Tyler Allgeier in the live Value Lens) were genuine Intrinsic estimates whose raw weighted surplus was exactly zero, not frontend fallback values. The defect was the lack of an explicit availability contract and the misleading tied-zero percentile treatment.

## Intrinsic Dynasty Value display coordinate — candidate v1

PR #137 adds a separate user-facing display coordinate while preserving raw Intrinsic unchanged.

Scale:

- scale id: `fsffl-intrinsic-dynasty-value`
- version: `1`
- intended range: `0` to `<10,000`, asymptotically approaching 10,000
- input: raw Intrinsic v1 only
- Market input: **none**
- Team Utility input: **none**
- player identity input: **none**

The transform is monotonic and deterministic. Stable raw anchors are mapped piecewise, with an asymptotic elite tail:

| Raw weighted surplus | Display value |
| ---: | ---: |
| 0 | 0 |
| 45 | 3,000 |
| 110 | 6,000 |
| 180 | 8,500 |
| 300 | 9,700 |
| >300 | strictly increasing tail approaching 10,000 |

The anchors were selected against the frozen/current Intrinsic-v1 evidence span rather than against market prices: valid zero-surplus cases; roughly 45-point fringe positive value; roughly 110-point meaningful asset value; roughly 180-point premium non-QB live Value Lens values; and roughly 300-point elite QB values from the frozen current-player safety evidence. The asymptotic tail prevents elite assets from clipping to one identical ceiling.

Representative mapping:

| Raw Intrinsic | Display Intrinsic |
| ---: | ---: |
| 0.0 | 0 |
| 45.1 | 3,005 |
| 109.7 | 5,986 |
| 183.5 | 8,535 |
| 223.43 | 8,934 |
| 240.2 | 9,102 |
| 291.98 | 9,620 |
| 311.21 | 9,732 |
| 448.61 | 9,932 |

This display transform is not a new fundamental model and does not replace the raw coordinate. It is a versioned presentation/value-normalization layer whose only purpose is to make the independently derived FSFFL fundamental coordinate readable as a dynasty asset-value magnitude.

## Missing-value integrity contract

`/api/value/intrinsic-v1` now preserves the backward-compatible raw `estimates` array and adds explicit roster-player presentation rows containing:

- `availability`
- `evidence_state`
- `reason`
- `raw_intrinsic_value`
- `intrinsic_dynasty_value`
- `percentile`
- `confidence`
- nested raw `estimate` provenance when available

Contract:

- **available + positive raw surplus** → publish display value and population percentile;
- **available + valid zero raw surplus** → publish display value `0`, explicitly explain valid zero surplus, and anchor percentile at `0th` rather than the midpoint of tied zeros;
- **low-evidence but available** → publish value with `low_evidence` state and existing low-confidence explanation;
- **unavailable** → publish `null` raw/display/percentile values plus a concise reason; never fabricate zero or a percentile.

Unavailable reasons distinguish missing authoritative season Forecast evidence from inability to construct governed replacement context.

## Broad Market presentation in Value Lens

The product already carries two distinct governed market representations:

- the ensemble `dynasty-market-percentile` coordinate; and
- the authoritative `fsffl-market-cardinal` 0–10,000 market magnitude.

The repaired Value Lens uses the governed market-cardinal score as the primary **Broad Market Value** magnitude and retains the ensemble market percentile as secondary context. This does not alter market authority or feed Market into Intrinsic.

The disagreement read remains rank-based. The UI does **not** subtract Broad Market and Intrinsic display values or create a master score. Reads are now:

- FSFFL materially higher;
- FSFFL moderately higher;
- Roughly aligned;
- Broad market moderately higher;
- Broad market materially higher;
- Intrinsic unavailable.

Disagreement remains a reason to investigate, not an automatic buy/sell command.

## Distribution / position behavior

The transform is position-agnostic by construction: identical raw Intrinsic values map to identical display values regardless of QB/RB/WR/TE. Cross-position differences therefore continue to come only from the authoritative Forecast + replacement economics upstream, not from display-scale position bonuses.

Frozen/current QB safety references illustrate the upper and lower tails without player-specific transform logic:

- Malik Willis raw `0.00` → display `0`;
- Daniel Jones raw `45.10` → display about `3,005`;
- Dak Prescott raw `223.43` → display about `8,934`;
- Lamar Jackson frozen safety raw `291.98` → display about `9,620`;
- Drake Maye raw `311.21` → display about `9,732`;
- Josh Allen raw `448.61` → display about `9,932`.

Live Value Lens examples around `109.7`, `183.5`, and `240.2` map to approximately `5,986`, `8,535`, and `9,102`, respectively. The selected curve preserves meaningful separation across depth, starter, premium, elite, and apex ranges without using Broad Market as a calibration target.

## Performance and mobile behavior

The Value Lens remains lazy-loaded. The transform is a constant-time arithmetic operation per available estimate and requires no provider call, historical scan, Simulation, or model fit. It does not add work to Home or Franchise first paint.

The existing <=680px Value Lens layout remains authoritative: coordinate cards stack, player summaries remain scan-first, tabs remain horizontally usable, and stale context responses are discarded before DOM mutation.

## Commercial cold-path latency — prior measured baseline

The last measured pre-progressive live baseline was approximately:

- cold Market workspace: **15.037s**;
- repeated Market workspace: **0.131–0.180s**;
- pre-Simulation Trade analysis: **13.245–13.269s**;
- fresh changed-roster 50k Simulation: **85.025s**;
- exact repeated Simulation: **1.227s**;
- historical deep frontier: **315.845–331.544s**.

PR #135 changed the delivery contract so useful governed Market/Trade evidence can appear before the deepest Decision/Simulation work. It did not reduce Simulation count or alter Simulation semantics.

## Remaining Phase 3 gaps after PR #137

1. Deploy and live-validate the Intrinsic Dynasty Value display scale after management-approved merge.
2. Use Intrinsic-vs-Market disagreement as an opportunity-discovery dimension only after the display/availability contract proves stable in beta.
3. Fresh 50,000-run Simulation remains the main deep-analysis compute blocker; optimize only from measured phase evidence without reducing fidelity.
4. League Market Value remains unavailable until governed evidence exists.
5. Owner-adjusted asset value / calibrated proposal fit remains blocked on point-in-time Behavioral evidence.
6. Durable useful-discovery records from real beta usage remain a Phase 3 exit requirement.

## Recommended following Phase 3 slice

After PR #137 is merged, deployed and smoke-validated, the next bounded product slice should use the now-comparable **Broad Market magnitude + independent Intrinsic Dynasty Value + governed rank disagreement** to improve Market / Trade Finder discovery and explanation without changing Search/Decision authority.

If live measurement instead reveals a new correctness or latency blocker, repair that bounded defect first rather than expanding discovery scope.

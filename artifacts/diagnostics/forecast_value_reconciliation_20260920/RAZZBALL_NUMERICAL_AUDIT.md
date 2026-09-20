# Forecast / Value reconciliation — Razzball numerical audit

Date: 2026-09-20  
Authority status: diagnostic evidence only; no Forecast coefficient, provider weight, frozen preseason baseline, P0, Shapley, or Simulation semantics changed.

## Outcome

**The current Razzball full-season feed is numerically malformed/inflated before it enters FSFFL. No FSFFL parser, normalization, scoring, or ensemble multiplier explains the inflation.**

The authorized live page identified itself as the 2026 full-season projections page. In the live capture, representative source rows already contained values such as Josh Allen **7,682 passing yards, 47.9 passing TDs, 1,134 rushing yards and 21.9 rushing TDs**. The same row listed **689.9 half-PPR points**.

The bounded GitHub-run trace then preserved those numbers exactly:

| Stage | Josh Allen passing yards | passing TD | rushing yards | rushing TD |
| --- | ---: | ---: | ---: | ---: |
| Razzball provider HTML row | 7,682 | 47.9 | 1,134 | 21.9 |
| FSFFL CurrentProjectionSnapshot | 7,682 | 47.9 | 1,134 | 21.9 |
| normalized ForecastObservation | 7,682 | 47.9 | 1,134 | 21.9 |
| FFToday comparison | 3,787 | 26.0 | 567 | 12.0 |
| governed equal-weight ensemble | 5,734.5 | 36.95 | 850.5 | 16.95 |

Using the audit's half-PPR scoring coordinate, the Razzball raw stats recompute to **698.08** points versus the Razzball page's own **689.9**. That near-parity demonstrates that the abnormal fantasy-point magnitude is already represented by the provider's raw stat line; FSFFL is not creating it later.

## Cross-position sample

`RAZZBALL_PLAYER_TRACE.csv` persists the 12-player sample. Median Razzball/FFToday recomputed fantasy-point ratio is approximately **1.914**; mean approximately **2.012**. The effect is broad but not a constant exact 2x transform:

- QB median approximately 1.921;
- RB median approximately 1.929;
- WR median approximately 1.896;
- TE median approximately 1.657;
- sample range approximately 1.201 to 3.559.

This is therefore not evidence for a lawful `/ 2` correction.

## Duplicate and transformation checks

The live trace found:

- 626 parsed Razzball provider rows / 626 unique player-position-team identities;
- 562 rows after the offensive CurrentProjectionSnapshot conversion / 562 unique external IDs;
- zero duplicate player/metric/source keys in the sampled normalized observations;
- source record -> current snapshot -> normalized observation equality for every traced Razzball metric.

The current run could compare Razzball numerically to FFToday. CBS correctly failed its horizon guard because the hosted page was not a full-season projection page. NFL Fantasy failed its hosted-content guard because the response did not contain the expected projection content. Those providers were not fabricated into the comparison.

## Corrective disposition

The directive requires a deterministic FSFFL defect to be repaired at the earliest wrong transformation boundary. No such numerical transformation defect was found. The upstream Razzball page itself supplied the abnormal values, and FSFFL faithfully preserved them.

Therefore this branch does **not** divide, clip, down-weight, or otherwise rewrite Razzball values, and does not retune ensemble weights.

One deterministic robustness gap was found independently of the live corruption: a malformed provider batch containing the same player/metric/horizon observation twice was not explicitly rejected before equal-weight ensemble construction. The branch now fails closed on that duplicate condition and adds regression coverage. This prevents a duplicated provider row from silently acquiring extra weight; it does not alter valid current Razzball observations.

## Frozen preseason / P0 impact

The preserved preseason Year-1 authority was captured on 2026-09-10 as a two-source FFToday + Razzball equal-weight baseline. Durable evidence retains the combined 1,675-observation raw ensemble and its hashes, but **does not retain the individual provider-row snapshots for that capture**.

The preserved baseline's direct league-scored examples are plausible (for example Josh Allen 389.0705, Jahmyr Gibbs 328.0230 and Puka Nacua 276.3080 half-PPR). There is no durable evidence that the current 2026-09-20 Razzball corruption affected the 2026-09-10 capture, and there is no retained individual Razzball row with which to prove or disprove that historical source row exactly.

Accordingly the frozen preseason baseline/P0 is **not modified**. Rewriting it would cross the directive's hard stop without evidence.

## Reproducibility

Live numerical trace workflow run: `35535631367`  
Trace artifact: `live-razzball-numerical-trace` / artifact id `10611759906`  
Razzball source version captured by the trace: `razzball-season-projections-html-v3:horizon-isolated`  
Runtime ensemble model: `next2-current-runtime-v4:parallel-provider-ingestion`

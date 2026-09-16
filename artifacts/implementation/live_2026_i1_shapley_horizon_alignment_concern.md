# FSFFL NEXT — Live 2026 I1 / Shapley horizon-alignment concern

Status: **MODEL CONCERN — BLOCKS LIVE SHAPLEY WIRING UNTIL MANAGEMENT/RESEARCH RESOLVES THE TIME COORDINATE**

Authority: implementation finding only. This document does not alter Forecast, Shapley, W, discount, B4, the Intrinsic Constitution, or production authority.

Production base at discovery: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
Implementation PR: #147
Frozen research oracle: PR #146 head `c12402df1b7fa0bfbb3d994bdcf791d80e103a0c`

## 1. What was discovered

The frozen research and the live current-season adapter are each internally coherent, but they use different calendar anchors when the product is evaluated during an active season.

In the frozen research coordinate, a source-season row at season `S` produces:

- current / Year-1 Shapley from realized production in season `S`;
- I1 horizon 1 from the same season-`S` facts, targeting season `S+1`, used as Year 2;
- I1 horizon 2 from the same season-`S` facts, targeting season `S+2`, used as Year 3.

This is not an interpretation added by implementation. The frozen downstream research explicitly computes Shapley at `h=0` from source-season current points and uses I1 `h=1` and `h=2` for the two discounted future years.

The production protocol correctly prohibits substituting a forward projection for completed realized I1 source facts. Therefore an in-season 2026 evaluation uses the immediately completed 2025 season as the factual I1 source coordinate.

That means the current adapter's I1 targets are:

- source 2025 + horizon 1 = **2026**;
- source 2025 + horizon 2 = **2027**.

But a live 2026 three-year Intrinsic presentation naturally needs calendar years:

- Year 1 = **2026** current-season value;
- Year 2 = **2027**;
- Year 3 = **2028**.

Accordingly, the frozen live inputs do not currently supply a research-authorized 2028 I1 coordinate. I1 horizon 1 cannot honestly be relabeled Year 2: it targets 2026, the evaluation season itself.

## 2. Why implementation is not papering over it

The following apparent fixes would change model semantics or invent evidence and are therefore outside this implementation chat's authority:

- relabeling 2025->2026 I1 horizon 1 as live 2027 / Year 2;
- feeding the live 2026 forward projection into I1 as though it were completed realized 2026 production;
- annualizing partial 2026 production and treating it as the completed source season without research authorization;
- recursively feeding an I1 forecast back into I1 to manufacture a third horizon;
- extrapolating a new horizon 3 / 2028 model;
- applying a youth, development, market, Value, or Shapley adjustment to compensate.

Any of those would cross the frozen Forecast boundary rather than implement the selected candidate faithfully.

## 3. Safe implementation action taken

`fsffl.forecast.i1_current_facts` now exposes the exact calendar target for each I1 horizon and preserves the rule that horizons are relative to the completed source season, not the live evaluation year.

For a 2026 evaluation sourced from completed 2025 facts, the adapter therefore reports target seasons `(2026, 2027)` and explicitly identifies that horizon 1 is not after the evaluation season. Tests lock this behavior so downstream code cannot accidentally shift the labels without a visible code change.

Identity collisions and missing source facts also remain fail-closed; the adapter does not invent zero production or choose an ambiguous provider row.

## 4. Production wiring consequence

Do **not** wire the new frozen Shapley engine into `/api/value` or downstream Team Utility / Decision / Search yet.

The existing `/api/value/intrinsic-v1` replacement/surplus contract remains untouched. Shapley values must not be inserted into those old fields, and a Shapley-native production endpoint should not be activated until the live calendar-horizon coordinate is resolved.

This is intentionally a stop at the authoritative integration boundary, not a parallel implementation path.

## 5. Decision required outside implementation

Management/research must determine the governed live time coordinate before implementation can complete the 2026 three-year Shapley route. The decision must specify, without using live player outcomes to tune the model, how an in-season evaluation obtains research-valid Year-2 and Year-3 coordinates when I1 itself is trained from completed source-season facts at horizons 1 and 2.

Implementation will then apply that decision without reopening the frozen economic architecture.

## 6. Current disposition of this concern

- Forecast I1 implementation/parity work may continue.
- Canonical current-facts adapter hardening may continue.
- Shapley engine unit/economic validation may continue.
- Live 2026 Shapley API/runtime wiring is **BLOCKED BY MODEL CONCERN**.
- No merge, deploy, or production-authority promotion is authorized by this finding.

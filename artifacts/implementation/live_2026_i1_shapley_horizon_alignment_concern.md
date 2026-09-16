# FSFFL NEXT - Live 2026 I1 / Shapley horizon alignment

Status: **RESOLVED BY AUTHORIZED RESEARCH HANDOFF; NO LONGER A MODEL-CALENDAR BLOCKER**

Authority: implementation reconciliation only. This document does not itself promote Forecast, Shapley, W, discount, B4, the Intrinsic Constitution, or production authority.

Production base at discovery: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
Implementation PR: #147
Original frozen h1/h2 research oracle: PR #146 head `c12402df1b7fa0bfbb3d994bdcf791d80e103a0c`
Calendar-resolution research handoff: PR #150 head `c629371356836ae57c5df71fe9db2c83356ece8f`
Frozen direct-h3 research oracle used by implementation parity: `744952af01140daa0cbdbff9b0683018d4db0e0d`

## 1. Original concern

The original implementation correctly identified a live-calendar mismatch. With completed 2025 facts during a live 2026 evaluation, frozen I1 h=1 targets 2026 and h=2 targets 2027, while a live three-year Intrinsic presentation needs 2026, 2027 and 2028.

Implementation therefore stopped rather than relabeling h=1, feeding a forward projection back into I1, treating partial-season facts as completed, recursively chaining forecasts, or inventing an h=3 extrapolation.

That stop was correct at discovery time.

## 2. Authorized research resolution

The bounded management-authorized live-coordinate study in research PR #150 returned the disposition `LIVE THREE-YEAR COORDINATE VALIDATED` and handed back the smallest permitted implementation change.

For evaluation season `E`, using the most recent completed factual source season `S = E-1`, the governed live coordinate is now:

- Year 1 / `E`: existing governed live/current-season Forecast;
- Year 2 / `E+1`: completed-source direct I1 `h=2`;
- Year 3 / `E+2`: completed-source direct I1 `h=3`;
- completed-source I1 `h=1`: diagnostic/reference only because it also targets `E`.

For a live 2026 request sourced from completed 2025 facts, that means:

- 2026 = governed live/current-season Forecast;
- 2027 = direct I1 h=2;
- 2028 = direct I1 h=3;
- direct I1 h=1 -> 2026 diagnostic only and excluded from Shapley.

The research handoff explicitly preserves the frozen I1 family, global `C=0.25`, Shapley W, 0.85 discount, B4, 2,048-permutation reference, and all ten Intrinsic Constitution principles. Direct h=3 is trained against factual `S+3`; it is not recursive and does not reuse h1/h2 predictions as inputs.

## 3. Implementation applied in PR #147

PR #147 now implements the research handoff without creating a parallel Forecast or Intrinsic architecture:

- the frozen I1 family supports direct horizons 1, 2 and 3;
- the completed-source current-facts adapter produces explicit target seasons for all three horizons and rejects partial source seasons;
- the live-calendar composition layer assigns Year 1 to governed live Forecast, Year 2 to h=2 and Year 3 to h=3;
- h=1 is retained only as a diagnostic coordinate and is hard-excluded from the Shapley consumer;
- calendar-coherence tests lock 2025 -> 2026 / 2027 / 2028 ownership and prevent double counting;
- direct-h3 implementation parity is checked against the frozen PR #150 research oracle.

## 4. Validation result

On implementation head `f70c484225b09a1d82ebd1483b415648c07af5ba`, the dedicated validation workflow completed successfully on 2026-09-16.

The following stages passed:

- production unit tests;
- frozen h1/h2 research parity;
- frozen direct-h3 research parity;
- locked 10-point Intrinsic Constitution rerun;
- validation-evidence upload.

Therefore the former calendar/horizon MODEL CONCERN is resolved for implementation purposes.

## 5. What remains blocked

Resolution of this concern does **not** authorize live production activation.

Separate blockers/boundaries remain:

1. **Current canonical evidence and commercial-source readiness.** PR #147 does not yet demonstrate an approved production source path for every completed-source I1 fact family at acceptable live coverage. Research/validation-source rights are not asserted as commercially cleared. Missing evidence must remain fail-closed.
2. **Product/API authority.** The existing `/api/value/intrinsic-v1` contract represents the older replacement/surplus semantics. Frozen Shapley values must not be inserted into those fields. A Shapley-native production contract and any downstream Team Utility / Decision / Search wiring require explicit management approval.

## 6. Current disposition

- Live calendar/time-coordinate concern: **RESOLVED**.
- Direct h3 implementation/research parity: **PASS**.
- Locked Constitution rerun: **PASS**.
- Production source/commercial readiness: **UNRESOLVED / BLOCKING ACTIVATION**.
- Product/API promotion authority: **NOT YET GRANTED**.
- PR #147 remains draft, unmerged and undeployed.

# FSFFL NEXT - Current-Player Sentinel Final Diagnostic Checkpoint

Checkpoint date: 2026-09-18  
Authority: research only  
Directive: post-holdout current-player sentinel final diagnostic  
Status: **FORECAST PASS - DOWNSTREAM SHAPLEY REPRODUCIBILITY BLOCKER - STOPPED FOR MANAGEMENT REVIEW**

## 1. Recovered boundary

- Research branch: `research/future-state-resolution-phase34-resume`.
- Durable final-holdout checkpoint recovered before execution.
- Live task-start head: `0240061f0048401748d61276f2f1b1d1e483bcf1`.
- `main` at task start: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`.
- PR #147 at task start: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`.
- Frozen candidate preserved exactly: fixed routed Forecast + M1a + two-prior-season consistency.
- Routing preserved: QB -> A2+C+D; RB/WR/TE -> A2+D.
- M1b, M2, M3a, M3b, role/security, third prior season, hard repeated-elite tier, new interaction and named-player override remained excluded.
- No named-player output changed any fitted form, coefficient family, routing rule, threshold or architecture.
- No implementation, promotion, merge or deployment occurred.

## 2. Current frozen production-resolution fit

The final diagnostic instantiates the historically frozen candidate on the same completed-source coordinate used by the prior sentinel.

Historical source rows remain through 2022. The fixed routed state probabilities and state means exactly reproduce the prior routed sentinel before M1a/consistency are applied.

### Y2
- conditional-production training rows: 5,974;
- source seasons: 2005-2022;
- M1a coefficient: 0.0793994253;
- prior-two coverage: 50.33%.

### Y3
- conditional-production training rows: 4,781;
- source seasons: 2005-2022;
- M1a coefficient: 0.0781231450;
- prior-two coverage: 48.63%.

The candidate changes positive-state conditional production means only. Persistence and future-state probabilities remain the fixed routed probabilities.

## 3. Sentinel Forecast table

| Player | Y1 | Y2 persist | Y2 usable+ | Y2 active pts | Y2 exp pts | M1a Δ | Consistency Δ | Y3 persist | Y3 usable+ | Y3 active pts | Y3 exp pts | M1a Δ | Consistency Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Aaron Rodgers | 344.2 | 66.5% | 65.1% | 174.8 | 116.3 | -0.9 | +1.0 | 36.8% | 35.3% | 161.6 | 59.5 | -0.5 | +0.4 |
| Sam Darnold | 382.9 | 95.2% | 93.9% | 234.4 | 223.1 | -0.1 | +4.7 | 90.2% | 86.9% | 219.1 | 197.6 | -0.1 | +3.1 |
| Bijan Robinson | 480.5 | 95.4% | 94.7% | 188.7 | 180.1 | +7.6 | +4.2 | 90.5% | 88.7% | 169.2 | 153.0 | +6.4 | +1.7 |
| Jahmyr Gibbs | 460.3 | 95.8% | 95.1% | 188.8 | 180.9 | +7.3 | +4.8 | 91.3% | 89.5% | 167.5 | 152.9 | +6.2 | +1.5 |
| Puka Nacua | 401.5 | 93.5% | 92.4% | 184.3 | 172.4 | +9.0 | +3.1 | 87.1% | 85.8% | 169.4 | 147.6 | +7.5 | +1.6 |
| Christian McCaffrey | 433.5 | 80.2% | 78.3% | 147.9 | 118.6 | +5.8 | +4.1 | 52.7% | 50.9% | 124.1 | 65.4 | +3.2 | +1.2 |
| Brock Bowers | 223.7 | 96.5% | 95.9% | 127.3 | 122.8 | +1.2 | 0.0 | 94.5% | 93.4% | 117.4 | 110.9 | +1.1 | 0.0 |
| Trey McBride | 258.8 | 93.7% | 92.9% | 139.9 | 131.1 | +8.3 | +3.0 | 87.6% | 86.4% | 130.3 | 114.2 | +7.3 | +1.6 |

"Usable+" means the frozen probability mass in usable/starter/premium/elite. Conditional-active points are unconditional expected points divided by persistence because the out-state mean is zero.

## 4. Delta versus prior routed sentinel and original compressed I1

| Player | New Y2 | Prior routed Y2 | Original I1 Y2 | New Y3 | Prior routed Y3 | Original I1 Y3 |
|---|---:|---:|---:|---:|---:|---:|
| Aaron Rodgers | 116.3 | 116.2 | 190.4 | 59.5 | 59.6 | 177.7 |
| Sam Darnold | 223.1 | 218.6 | 211.7 | 197.6 | 194.6 | 185.4 |
| Bijan Robinson | 180.1 | 168.3 | 154.4 | 153.0 | 144.9 | 126.5 |
| Jahmyr Gibbs | 180.9 | 168.8 | 153.2 | 152.9 | 145.2 | 126.1 |
| Puka Nacua | 172.4 | 160.3 | 143.3 | 147.6 | 138.5 | 118.2 |
| Christian McCaffrey | 118.6 | 108.6 | 122.2 | 65.4 | 61.0 | 103.3 |
| Brock Bowers | 122.8 | 121.6 | 114.2 | 110.9 | 109.8 | 102.4 |
| Trey McBride | 131.1 | 119.8 | 111.6 | 114.2 | 105.2 | 94.8 |

The desired high-end correction is visible without removing regression: Bijan/Gibbs/Puka gain roughly 26-29 points versus original compressed I1 at both future horizons. McCaffrey does not receive the same treatment: his Y3 persistence is 52.7% and Y3 unconditional production is 65.4 points.

Aaron Rodgers remains sharply age-attenuated relative to the original I1: persistence falls from 99.5%/98.3% to 66.5%/36.8%, and expected production falls from 190.4/177.7 to 116.3/59.5. The multi-year consistency adjustment itself adds only about +1.0 Y2 and +0.4 Y3 points, so it does not revive an implausible near-prime tail.

## 5. Forecast sanity classification

**FORECAST LAYER: PASS.**

Predeclared checks:
- **Extreme-age QB tail:** passes on Forecast. Aaron does not regain near-prime persistence/production.
- **Young elite production:** passes on Forecast. Bijan, Gibbs and Puka retain substantially more demonstrated magnitude than original I1 while still regressing.
- **Older elite RB:** passes on Forecast. McCaffrey has meaningful age/decline risk and is clearly separated from young elite RBs.
- **TE scale:** passes on Forecast. Bowers and McBride remain coherent on the same frozen mechanism. Bowers has no consistency increment because a genuine second prior season is unavailable; he receives M1a only.

## 6. Required Intrinsic/Shapley stage - reproducibility blocker

The directive also requires the settled 2,048-permutation lineup-substitution Shapley pipeline to be rerun over the governed current-player universe.

That exact rerun cannot be completed safely from the persisted evidence available in this task.

Recovered prior-sentinel provenance:
- governed Year-1 universe: **335 players**;
- mapped completed-source universe: 335 players;
- governed live Year-1 material SHA-256: `70de5578372bca5914a570356d8a2bb2f0f4a16e2763849a316e6b587f90b706`;
- prior sentinel JSON detailed player entries actually persisted: **39 total** = 8 named sentinels + 31 universe-checkpoint rows;
- activation artifact id: `10467264159`;
- activation artifact SHA-256: `3866d65353c27cab66f83d701b0af7f892310a71187d02206c49f77181a95ca5`.

The activation artifact contains the completed-source current-facts artifact and frozen I1 artifacts, but not the missing full 335-player governed live Year-1 forecast material. The live-material hash is recorded, but the full rows are not present as a repository artifact discoverable by that hash.

Shapley is explicitly lineup-substitution dependent on the full player universe. The following would all be unauthorized changes of evidence/authority:
- rerunning Shapley on only the 39 persisted detailed players;
- scaling the previous sentinel Shapley values by point changes;
- substituting the completed-source facts for governed Year 1;
- scraping a new current provider universe and treating it as the hashed prior live coordinate.

Therefore no final selected-candidate Intrinsic value, governed ranking, or nearby comparison set is fabricated here.

Reference only — **not** the selected-candidate result — the prior routed sentinel had:
- Bijan 588.03;
- Gibbs 566.34;
- Darnold 520.83;
- Puka 500.26;
- McCaffrey 447.87;
- Aaron 328.53;
- McBride 298.98;
- Bowers 267.71.

The old named-ordering red flag was not present, and the new Forecast shifts move young elite production upward while leaving Aaron almost unchanged versus the prior route. That is useful diagnostic context, but it is not a substitute for the required governed Shapley rerun.

## 7. Overall directive classification

**OVERALL: AMBIGUOUS / INCOMPLETE DUE DOWNSTREAM REPRODUCIBILITY BLOCKER.**

This is **not** a DOWNSTREAM FAILURE classification: no newly computed downstream result has shown an implausible ordering.

It is also not a full PASS, because the directive requires final governed Intrinsic/Shapley values and ordering and those cannot be reproduced exactly from the durable evidence currently available.

The exact layer diagnosis is:
- Forecast: **PASS**;
- downstream Intrinsic/Shapley model: **not adjudicated**;
- execution/evidence availability: **blocked by missing full governed Year-1 universe material**.

## 8. Persistence / hashes

Machine-readable repository result:
`artifacts/research/production_resolution/CURRENT_PLAYER_SENTINEL_FINAL_DIAGNOSTIC_2026-09-18.json`

Local 8-player Forecast audit:
- SHA-256 `3da269663542c43091deda8941a2ddcb05a05a49d3dc3c09efdd703480adfefd`.

Key input hashes:
- current diagnostic directive PDF: `39cfba8976908aff94a6b0ec3605133f93a92fda7e33c19ec1cd72b2dc7f1839`;
- current I1 facts: `dbea7f754e0910a83a85518880a5e3f649579116a205f9d30d8a4c9f39a7932d`;
- Phase 2 panel: `c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7`;
- corrected Q3 rows: `9c504c9e765bd113406b59185a3cc80d23cca2401ecf31857692e15720b29063`;
- prior sentinel JSON blob: `b261ae3a3b8bfd958a8f607dbee7d79003f9cf5d`.

## 9. Stop boundary

**STOP.** Do not tune, redesign, refit from named-player outputs, implement, promote, merge, deploy, start a downstream repair, or invent a reduced-universe Shapley approximation.

Management may separately decide whether to restore the exact governed 335-player live Year-1 material and authorize completion of the downstream diagnostic. The Forecast result above must remain frozen if that happens.

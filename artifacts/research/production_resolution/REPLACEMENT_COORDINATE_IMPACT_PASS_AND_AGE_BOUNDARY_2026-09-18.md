# FSFFL NEXT — Replacement-coordinate impact check and downstream materialization boundary

Date: 2026-09-18

Governing authorization: Management authorization — close legacy parity loop and advance on the approved replacement coordinate.

## Status

- Replacement-coordinate eight-sentinel impact check: **PASS**.
- New exact sentinel parity authority: **ESTABLISHED**.
- Row-complete 335-player Gate A board: **BLOCKED BEFORE COMPLETION** by a separate missing-age materialization dependency affecting 35/335 frozen Year-1 players.
- Gate B: **NOT RUN**.
- Gate C / Intrinsic / Shapley: **NOT RUN**.
- No ranking output inspected.
- No model selection, coefficient, feature, route, Shapley, main, PR #147, merge, deploy, or production-authority change.

The legacy ephemeral C-memory parity loop is closed. The old sentinel is used below only as the management-authorized diagnostic impact reference.

## Frozen Forecast used

- QB: A2+C+D.
- RB/WR/TE: A2+D.
- M1a: frozen coefficients.
- two-prior-season consistency adjustment: frozen coefficients and frozen training standardization.
- position scoring multipliers unchanged.
- no refit/reselection/tuning/named-player override.

Approved current-player materialization coordinate:
`replacement-identity-materialization-v1:2026-09-18T17:06:21Z`.

Replacement coordinate row-material SHA-256:
`1803ee0200b8d1d39dfd719934bd683765727bef997f2a1f1ee44d2a6444af56`.

## Compact old-vs-replacement impact table

The durable old sentinel predates the subsequently frozen M1a + two-prior production refinements. Therefore expected-point and conditional-production deltas below are diagnostic old-vs-final-frozen-candidate differences, not estimates of the C-coordinate change alone. Persistence/state-probability changes isolate the replacement-coordinate effect more directly: non-QB routed probabilities are unchanged; only QB C-memory inputs change them.

| Player | H | old persist | replacement persist | Δ persist | old active pts | replacement active pts | old exp pts | replacement exp pts | Δ exp pts | M1a z | 2-prior z (cov) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Sam Darnold | Y2 | 0.951941 | 0.951950 | +0.000009 | 229.66 | 230.68 | 218.63 | 219.60 | +0.97 | -0.0022 | +0.0243 (1) |
| Aaron Rodgers | Y2 | 0.665424 | 0.665405 | -0.000019 | 174.65 | 176.88 | 116.22 | 117.70 | +1.48 | -0.0410 | +0.0907 (1) |
| Christian McCaffrey | Y2 | 0.802027 | 0.802027 | 0 | 135.46 | 152.36 | 108.65 | 122.20 | +13.55 | +0.1987 | +0.2558 (1) |
| Jahmyr Gibbs | Y2 | 0.958014 | 0.958014 | 0 | 176.17 | 193.39 | 168.78 | 185.27 | +16.50 | +0.1569 | +0.2034 (1) |
| Bijan Robinson | Y2 | 0.954385 | 0.954385 | 0 | 176.36 | 192.12 | 168.32 | 183.35 | +15.04 | +0.1625 | +0.1668 (1) |
| Puka Nacua | Y2 | 0.935311 | 0.935311 | 0 | 171.35 | 184.56 | 160.27 | 172.62 | +12.35 | +0.2205 | +0.0830 (1) |
| Brock Bowers | Y2 | 0.964834 | 0.964834 | 0 | 126.02 | 127.30 | 121.59 | 122.82 | +1.23 | +0.0335 | 0 (0) |
| Trey McBride | Y2 | 0.937390 | 0.937390 | 0 | 127.75 | 139.86 | 119.75 | 131.10 | +11.35 | +0.2395 | +0.0737 (1) |
| Sam Darnold | Y3 | 0.901875 | 0.902140 | +0.000265 | 215.78 | 213.92 | 194.60 | 192.98 | -1.62 | -0.0021 | -0.0233 (1) |
| Aaron Rodgers | Y3 | 0.368258 | 0.368337 | +0.000078 | 161.86 | 164.38 | 59.60 | 60.55 | +0.94 | -0.0403 | +0.0990 (1) |
| Christian McCaffrey | Y3 | 0.527303 | 0.527303 | 0 | 115.75 | 127.23 | 61.04 | 67.09 | +6.05 | +0.1955 | +0.1637 (1) |
| Jahmyr Gibbs | Y3 | 0.912789 | 0.912789 | 0 | 159.06 | 170.16 | 145.19 | 155.32 | +10.14 | +0.1544 | +0.1021 (1) |
| Bijan Robinson | Y3 | 0.904695 | 0.904695 | 0 | 160.19 | 171.40 | 144.92 | 155.06 | +10.14 | +0.1599 | +0.0972 (1) |
| Puka Nacua | Y3 | 0.871457 | 0.871457 | 0 | 158.90 | 169.51 | 138.47 | 147.72 | +9.25 | +0.2170 | +0.0511 (1) |
| Brock Bowers | Y3 | 0.945031 | 0.945031 | 0 | 116.23 | 117.40 | 109.84 | 110.95 | +1.11 | +0.0329 | 0 (0) |
| Trey McBride | Y3 | 0.876134 | 0.876134 | 0 | 120.09 | 130.89 | 105.22 | 114.67 | +9.46 | +0.2357 | +0.0557 (1) |

### Routed-state probability impact

RB/WR/TE routed state probabilities are numerically identical to the durable old sentinel because their frozen route excludes C.

QB maximum absolute individual-state probability changes:
- Aaron Rodgers Y2: `0.0005043399675593307`;
- Aaron Rodgers Y3: `0.00038462507250774935`;
- Sam Darnold Y2: `0.0009778169489389338`;
- Sam Darnold Y3: `0.0021668986505294363`.

No new state-probability anomaly appears.

## Management impact tests

**Aaron Rodgers remains strongly age-attenuated — PASS.**
Replacement persistence is 0.6654046428783702 in Y2 and 0.36833663129578553 in Y3. Expected points are 117.69774463825405 and 60.54577624938465.

**Young elite magnitude remains materially stronger — PASS.**
Y2/Y3 expected points:
- Bijan Robinson: 183.3518935072346 / 155.06078277312668;
- Jahmyr Gibbs: 185.27380517553067 / 155.3222083838269;
- Puka Nacua: 172.61959432981766 / 147.72234963800364.

All three remain far above Rodgers in Y3 and preserve high persistence.

**Christian McCaffrey retains meaningful decline risk — PASS.**
Persistence falls from 0.8020265261236744 in Y2 to 0.5273032642296117 in Y3, with Y3 expected points 67.090151386841.

**TE scale remains coherent — PASS.**
Brock Bowers: 122.82041357354514 / 110.9504744260406 expected points Y2/Y3.
Trey McBride: 131.10403777366304 / 114.6738176295143.

**New material anomaly — NONE IDENTIFIED on the eight predeclared sentinels.**

Impact decision: **PASS**. The approved replacement coordinate does not change a substantive conclusion of the frozen current-player Forecast diagnostic.

## New reproducibility authority

Persisted exact full-precision parity reference:
`artifacts/research/production_resolution/replacement_coordinate_sentinel_authority_20260918.json`.

Canonical payload SHA-256:
`6fd3efdc8779dec959320318508398f2f5fe69b585c6748b1def647932cb44fe`.

Required future parity tolerance: <= 1e-6.

The unrecoverable legacy current-player C-memory values are no longer parity authority.

## Attempted resumption: 335-player board

After PASS, downstream materialization was resumed exactly as authorized. A new independent blocker appears before a row-complete board can be created.

The frozen Year-1 universe contains 335 players. The frozen current-I1 facts contain all 335 corresponding source-player IDs, but **35/335 have `age_years = null`**. A2 requires an exact numeric age and the governing surviving feature code executes `float(r.age)`; there is no frozen missing-age imputation/default in that path.

Affected players:

Fernando Mendoza; Carson Beck; Germie Bernard; Ty Simpson; Omar Cooper; Carnell Tate; Jordyn Tyson; Malachi Fields; Jadarian Price; Jeremiyah Love; Nicholas Singleton; Ja'Kobi Lane; Makai Lemon; Caleb Douglas; KC Concepcion; Antonio Williams; Cade Klubnik; Mike Washington; Chris Bell; Ted Hurst; Zachariah Branch; Malik Benson; Kenyon Sadiq; Emmett Johnson; Jonah Coleman; Denzel Boston; Demond Claiborne; Eli Stowers; Kaytron Allen; Cyrus Allen; Kaelon Black; De'Zhaun Stribling; Seth McGowan; Jalon Daniels; Will Kacmarek.

Missing-age list canonical SHA-256:
`6c5d2e39c6d019db8483de2666f12ce7fa9c5ab96861f41ed984ab5785b24441`.

This is distinct from the closed legacy C-memory issue. The approved replacement identity/materialization coordinate supplies identity/PIT history but does not supply a governed current exact-age value for these 35 rows. Borrowing ages from the old ephemeral sentinel, estimating ages, or adding a fallback would create a new materialization/model choice and is not authorized.

Therefore the row-complete 335-player board cannot be persisted safely yet. A partial 300-player board was used only to detect this completeness boundary and is **not** persisted as Gate A authority.

Per the existing no-partial-universe rule:
- no 335-player Gate A artifact is claimed;
- no sentinel parity Gate B was run against a partial board;
- no Intrinsic/Shapley Gate C was run;
- no rankings were produced or inspected.

## Exact stop boundary

Management decision or a provenance-governed exact-age materialization dependency is required for the 35 missing-age rows.

No main or PR #147 changes are authorized or made.

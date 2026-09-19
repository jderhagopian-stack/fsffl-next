# FSFFL NEXT — Forecast Production-Resolution Stage 0 Preflight Checkpoint

Checkpoint date: 2026-09-17  
Authority: research only  
Protocol: Forecast Production-Resolution & Player-State Research Execution — Management Revised 2026-09-17  
Status: **STAGE0_COMPLETE_PASS — STOPPED AT USER-AUTHORIZED STAGE 0 BOUNDARY**

## 1. Recovered live repository state

- Research branch: `research/future-state-resolution-phase34-resume`
- Live preflight-start head: `8eb108769cf73e07d7bf65f4dd9afac0419c914f`
- Prior durable research head recorded by the environment-blocker checkpoint: `1012215b784bc1e9846378df0f1c9285886da779`
- Live branch relation: exactly one commit ahead of `1012215...`; the only change is the Stage 0 environment-blocker checkpoint file. No material research-state conflict was found.
- `main`: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR #147: open, unmerged, head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`

The protected refs above were re-fetched before this Stage 0 checkpoint. No write was made to `main` or PR #147.

## 2. Execution environment actually used

- Connected GitHub repository read/write actions: available.
- GitHub Actions artifact download: available.
- Python runtime: available (`Python 3.13.5`, `pandas 2.2.3`, `numpy 2.3.5`).
- Local git checkout: not assumed and not used.
- Shell/repository command execution: not required for Stage 0 and not used.
- Research execution used the persisted Phase 2 workflow artifact plus repository source files fetched from the research branch.

Recovered Phase 2 evidence:
- Workflow run: `35196266697`
- Artifact: `future-state-resolution-phase2-final`
- Artifact ID: `10486530017`
- Artifact ZIP SHA-256: `f7e9cfeee05687d5eb44085124c112c70d812ba95f6d30ca1213c6f92d1ac6ff` (verified locally)
- `phase2_player_season_panel.csv` SHA-256: `c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7`
- Panel rows: 15,492
- Seasons: 1999–2025
- Duplicate `player_id, season` keys: 0
- Positions: QB 2,078; RB 4,619; WR 5,645; TE 3,150

Relevant frozen/recovered code blobs:
- `scripts/extract_phase2_future_state_panel.R`: `4de32f8fcba216d9d866a8c3ef739e4bb00ebe7e`
- `scripts/run_phase2_future_state_empirical.py`: `5fbbb47057546c4729949293e7ef5f4c347b3c09`
- `scripts/run_phase2_q3_age_state_correction.py`: `90234dc39643d79c0df46cedafb2b50a404294ed`
- `scripts/run_phase34_challenger_validation_fast.py`: `6906a11d8fbec7a62bc392b627963a393413a61e`
- `src/fsffl/forecast/integrated_i1.py`: `b5f181f56dbeaec8a353e9555e236c93a92cc3b3`

## 3. Preflight A — point-in-time historical reconstructability

### PIT reconstruction rule verified

The recovered historical construction is leakage-safe in structure:
- state boundaries and within-state reference statistics are estimated from seasons **strictly before** the evaluated source season;
- source features use the completed source season and earlier history only;
- prior-season and two-year trajectory inputs use only seasons before the source cutoff;
- realized target outcomes are read only from `source_season + horizon`;
- missing target player-season rows are an explicit non-persistence outcome under the existing Phase 2 definition, not silently dropped;
- full-panel fields that are future-derived, including `last_observed_season`, are **not eligible model inputs**;
- `target_*`, `role_loss`, and `terminal_nonreturn_3y` remain outcome/diagnostic fields and are not source features.

The local Stage 0 audit reconstructed source-state boundaries/residual support through source season 2024 using the frozen I1 state-boundary algorithm and prior-season-only data. No model was fit and no holdout error/performance metric was computed.

### Latest fully reconstructable source season by horizon

Because the persisted panel contains realized seasons through 2025:
- h1: source seasons through **2024** are reconstructable;
- h2: source seasons through **2023** are reconstructable;
- h3: source seasons through **2022** are reconstructable.

Those endpoints exactly cover the management-preferred final-holdout endpoints.

### Preferred validation / holdout block audit

| Block | Source seasons | Required target seasons | PIT reconstructable? |
|---|---:|---:|---|
| Validation h1 | 2021–2022 | 2022–2023 | PASS |
| Validation h2 | 2020–2021 | 2022–2023 | PASS |
| Validation h3 | 2019–2020 | 2022–2023 | PASS |
| Final holdout h1 | 2023–2024 | 2024–2025 | PASS |
| Final holdout h2 | 2022–2023 | 2024–2025 | PASS |
| Final holdout h3 | 2021–2022 | 2024–2025 | PASS |

No alternative block structure is required at Stage 0.

### Source-side support in the preferred seasons

PIT non-out source rows reconstructed from prior-season-only state boundaries:

| Source season | Total | QB | RB | WR | TE |
|---:|---:|---:|---:|---:|---:|
| 2019 | 570 | 65 | 161 | 220 | 124 |
| 2020 | 595 | 80 | 169 | 222 | 124 |
| 2021 | 614 | 73 | 175 | 239 | 127 |
| 2022 | 596 | 80 | 168 | 228 | 120 |
| 2023 | 558 | 74 | 154 | 213 | 117 |
| 2024 | 569 | 74 | 151 | 221 | 123 |

Across every preferred source-season/position cell:
- source age coverage: 100%;
- source experience coverage: 100%;
- current `opportunity_per_game` coverage: 100%;
- smallest prior positive-production training pool used for PIT state-boundary support: 1,410 rows.

The persisted Phase 2/Q3 derived-row files stop at source season 2022, but the persisted raw panel extends through 2025 and the exact reconstruction code uses prior-season-only transforms. Extending the research runner's source-season ceiling to the protocol's approved blocks is therefore an execution extension, not a new model definition. No such challenger/holdout run was executed in Stage 0.

## 4. Preflight B — trajectory / role-opportunity evidence inventory

### Governed historical evidence present

The persisted Phase 2 extraction provides completed-season:
- `attempts`
- `carries`
- `targets`
- `receptions`
- `games`
- derived `opportunity`
- derived `opportunity_per_game`
- derived `role_band`

The governed derived opportunity definition in the recovered extractor is:
- QB: pass attempts;
- RB: carries + targets;
- WR/TE: targets;
- `opportunity_per_game = opportunity / games`.

Current `opportunity_per_game` is fully populated in the preferred source seasons. The one-year change can be reconstructed without future information when a prior-season player row exists.

Source-only one-year trajectory coverage across the preferred source seasons 2019–2024:

| Position | Eligible rows | Production residual Δ coverage | Two-year production slope coverage | Opportunity Δ coverage |
|---|---:|---:|---:|---:|
| QB | 446 | 76.7% | 61.0% | 76.7% |
| RB | 978 | 75.7% | 57.6% | 75.7% |
| WR | 1,343 | 74.2% | 55.0% | 74.2% |
| TE | 735 | 76.1% | 58.0% | 76.1% |

Missing trajectory rows are concentrated in players without a usable prior-season row and are retained with explicit missingness/coverage rather than dropped or backfilled.

The authoritative recovered historical panel does **not** contain governed historical snaps, routes, route-participation, target-share, or red-zone fields. They are therefore ineligible for this study unless management later supplies a separately governed PIT source; they are not fabricated or retroactively inferred here.

### Frozen M3b eligible feature family

Before any validation result is examined, Stage 0 freezes the eligible opportunity-trajectory family to **one continuous source-only signal plus explicit coverage**:

`opportunity_delta_log = log1p(opportunity_per_game_t) - log1p(opportunity_per_game_t-1)`

with:
- an explicit coverage/missingness flag;
- no backfill for rookies, gaps, or missing prior seasons;
- no separate raw attempts/carries/targets/receptions deltas;
- no hard role-band transition as a modeling feature;
- `role_band` may remain a reporting/diagnostic field only;
- no snaps/routes/share/red-zone substitutes.

This makes M3b **eligible to be tested later**, not validated or promoted. No predictive result has been inspected at Stage 0.

For the already-fixed routed baseline's QB C-memory input, the PIT prior age-state residual is also reconstructable for the new h1 holdout source seasons with explicit coverage: 58/74 QB source rows (78.4%) in 2023 and 59/74 (79.7%) in 2024. Missingness is already represented by a coverage indicator in the recovered frozen harness.

## 5. Stage 0 conclusion and stop

- Preflight A: **PASS**. All management-preferred validation and holdout blocks are point-in-time reconstructable from the persisted evidence without requiring current-2026 outcomes.
- Preflight B: **PASS WITH NARROW FEATURE FREEZE**. A governed, position-appropriate opportunity-per-game trajectory exists with broad historical coverage and explicit missingness. M3b may later test only the frozen one-year log-opportunity change family above.
- Protocol stop condition for unavailable preferred blocks: **not triggered**.
- Repository-state conflict stop condition: **not triggered**.
- No named 2026 player was used for fitting, thresholding, feature selection, candidate selection, or holdout redesign.
- No M0-D decomposition, challenger fit, validation comparison, final-holdout performance evaluation, or current-player sentinel was run.
- No production authority, Intrinsic/Shapley architecture, global C, discount, PR #147, `main`, merge, deployment, or promotion was changed.

**STOP:** the user authorized Preflight / Stage 0 only. The next protocol step would be M0-D historical decomposition, but it is intentionally not started in this checkpoint.

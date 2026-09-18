# Deterministic reconstruction - replacement identity/materialization v1

## Frozen inputs

1. Frozen Year-1 universe:
   `artifacts/research/production_resolution/governed_year1_current_2026_20260918T094231Z/governed_year1_universe.json`
   SHA-256 `c668b74b9010809904c14366d992137f7b038b299d6d3f031b07eea0d63c0b3f`.
2. Recovered Phase2 archive SHA-256:
   `f7e9cfeee05687d5eb44085124c112c70d812ba95f6d30ca1213c6f92d1ac6ff`.
   Required members:
   - `future-state-phase2/phase2_player_season_panel.csv`, SHA-256 `c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7`;
   - `future-state-phase2/phase2_q3_age_state_rows.csv`, SHA-256 `9c504c9e765bd113406b59185a3cc80d23cca2401ecf31857692e15720b29063`.
3. NFLverse `players.csv`, release asset `572597132`, SHA-256 `801d5fec2fc21c54ad585415e8e551ae9d1de7c601a8c3768504b7ce59b579b6`.
4. NFLverse `roster_2025.csv`, release asset `373640814`, SHA-256 `531ee5de386037bb17de3e3e3d50f7b4ed08789526bbaae9876fdd3dfb4d04ad`.
5. Builder: `scripts/research_build_replacement_identity_coordinate.py`; use the SHA-256 recorded in `manifest.json`.

Do not substitute a later provider asset with a different hash.

## Reconstruction command

After verifying every input hash and extracting the Phase2 archive, run from repository root:

```bash
PYTHONPATH=src python scripts/research_build_replacement_identity_coordinate.py \
  --year1-universe artifacts/research/production_resolution/governed_year1_current_2026_20260918T094231Z/governed_year1_universe.json \
  --phase2-panel /path/to/future-state-phase2/phase2_player_season_panel.csv \
  --phase2-q3-rows /path/to/future-state-phase2/phase2_q3_age_state_rows.csv \
  --players-snapshot /path/to/players.csv \
  --roster-snapshot /path/to/roster_2025.csv \
  --output-dir /new/empty/output/directory \
  --coordinate-as-of 2026-09-18T17:06:21Z
```

The output directory must not already exist.

## Required verification

- command reports 335 rows;
- mapping counts are 73 `DIRECT_ID`, 227 `EXACT_NAME_POSITION`, 35 `UNMATCHED`, and zero ambiguous;
- prior-two coverage count is 199;
- 2022 frozen-method parity passes across 619 rows with maximum residual-z difference no greater than `1e-12` and zero scope mismatches;
- `rows_sha256` is `1803ee0200b8d1d39dfd719934bd683765727bef997f2a1f1ee44d2a6444af56`;
- `population_sha256` is `095d09458bfe021e7b7075281e8430573514c6d1e5c2dae3d25430f555ceba4b`;
- `reload_verification.json` reports `PASS`.

The builder does not fit or execute the frozen Forecast. It must not be extended to inspect Y2/Y3, sentinel parity, Intrinsic/Shapley, or rankings under this directive.

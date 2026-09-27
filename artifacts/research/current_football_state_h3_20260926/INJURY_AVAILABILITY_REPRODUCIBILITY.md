# Injury Availability / Time-to-Return Reproducibility

Date: 2026-09-27

Research branch:
`research/current-football-state-h3-20260926`

Frozen source episode set:
- prior historical workflow run: `36288913771`
- artifact: `10921183161`
- digest: `sha256:154ef6c7d35d5c04ac01cfbaedd47b8a654c43dd521e4251718277a10e929ea1`
- injury episodes: **4,793**

Dedicated validation:
- workflow run: `36323231951`
- head: `d9edc3e6793709a7916df397967ecdc51230b673`
- artifact: `10933510516`
- digest: `sha256:a531a75b9c8b7878dc7aca4c193b5081ca0f29ec6b132d01ccf509ff240afee1`

Frozen before scoring:
- `INJURY_AVAILABILITY_PROTOCOL.md`
- `INJURY_AVAILABILITY_GATES.md`

Outputs:
- `INJURY_AVAILABILITY_OOT_FOLD_METRICS.csv`
- `INJURY_RETURN_TIMING_POOLED_METRICS.csv`
- `INJURY_REMAINING_AVAILABILITY_POOLED_METRICS.csv`
- `INJURY_RETURN_TIMING_POSITION_SAFETY.csv`
- `INJURY_AVAILABILITY_POSITION_SAFETY.csv`
- `INJURY_RETURN_TIMING_OOT_PREDICTIONS.csv`
- `INJURY_AVAILABILITY_OOT_PREDICTIONS.csv`
- `INJURY_AVAILABILITY_CONFORMAL_SUMMARY.csv`
- `INJURY_AVAILABILITY_CONFORMAL_PREDICTIONS.csv`
- `INJURY_AVAILABILITY_RESULT.json`

Authority guards:
- production H3 changed: no;
- Intrinsic changed: no;
- conditional healthy production changed: no;
- post-return role changed: no;
- recurrence or durable H2/H3 changed: no;
- provider ROS authority changed: no;
- current named-player tuning: no.

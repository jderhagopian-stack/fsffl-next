# FSFFL NEXT - Production preseason baseline Stage A completion

Status: **PASS**

The exact non-invalidated production `preseason_forecast_baseline` record was recovered through the connected Supabase read-only persistence surface.

- Record id: `145`
- Scope: `sleeper:1312071960615731200:2026`
- Model version: `next2-preseason-baseline-v1`
- Evaluation time: `2026-09-10T21:36:41.346326Z`
- Sources: FFToday + Razzball
- Minimum independent sources: 2
- Raw ensemble observations: 1,675
- Baseline payload SHA-256: `cea4126d353f85f1e1fe66bfba4214e204277f487be04462dbe18fb59ae0f387`
- Baseline raw-array SHA-256: `4dd1fa70b9b4f886ad103a2f5b6f45f7c4f123a571f84b7a4400b0004271639d`
- Source artifact: production `current_forecast_evidence` id `94`
- Raw arrays exact equal to source artifact: **yes**
- Governed season-long fantasy-point rows: **335**
- Unique player IDs: **335**
- Canonical board SHA-256: `6bded35221a501471df60de8c05a6e691428552f23abb3f0cf799218fd71bfae`
- Deterministic repeat: **pass**
- All-player recomputation parity: **335/335**, max absolute mean difference `1.13686837721616e-13`

## Required named players

- Aaron Rodgers: 243.6980 half-PPR (QB)
- Bijan Robinson: 329.2355 half-PPR (RB)
- Christian McCaffrey: 315.3580 half-PPR (RB)
- Jahmyr Gibbs: 328.0230 half-PPR (RB)
- Josh Allen: 389.0705 half-PPR (QB)
- Puka Nacua: 276.3080 half-PPR (WR)
- Sam Darnold: 281.7255 half-PPR (QB)

Prior surviving named values reconcile at ordinary floating precision: Bijan 329.24, Gibbs 328.02, McCaffrey 315.36, Darnold 281.73, Rodgers 243.70.

No fresh provider fetch was used. No production persistence row was mutated.

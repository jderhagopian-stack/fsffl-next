# 2026 Preseason Almanac GM Files and Forecast Coverage Checkpoint
Date: November 20, 2026
Research branch: research/modern-preseason-backcast-20261120; related draft PR #576

## Verified editorial source
The September 9 historical State is 238 rostered players, including Travis Hunter on BING BONG DRIGSY, and 108 2027-2029 rookie pick rights with original team IDs. The read-only research exporter scripts/research_export_sept9_almanac_inventory.py passed in GitHub Actions and retained a compact complete franchise inventory. Source roster placement means the saved September 9 snapshot, not a recommended optimal lineup. The output has all 12 teams, full player and pick inventory, and provenance. No private Supabase raw payload is stored in the public repository.

The 39-page original almanac duplicated championship share on pages 8, 12-13, repeated the picks-versus-rings argument on 16 and 19-22, and repeated owner trading behavior on 5 and 23-24. The new 46-page editorial prototype removes redundant sections, retains differentiated analytics, and gives every franchise two pages: one original strengths/weaknesses and GM decision narrative, and one complete roster and owned pick ledger. This is a publication *prototype* only, not a newly certified modern Career forecast.

## Six independently recovered point-in-time Year 1 forecasts
Read-only private SQL inspected the original 2026-09-09 saved FSFFL NEXT Analytics artifact id 65 and recovered full-season fantasy-point means and uncertainty for Braelon Allen (RB), Marcus Mariota (QB), Samaje Perine (RB), Tank Dell (WR), Kayshon Boutte (WR), and Jalon Daniels (QB). All observations have 2026-09-09 23:23 UTC source timestamps earlier than kickoff; pre-kickoff raw ensemble statistics are present in source artifact id 63. The source rows are exported as a private user research artifact and NOT committed to this public repo.

The source coordinate is league fantasy points; the existing I1/P0 standard-points coordinate differs in pass interception, fumbles lost and half-PPR scoring. Do not silently copy these six means into standard points or mix them into the already-computed 221-player Shapley output. The correct implementation is a scoped private pregame source bridge with a governed standard-coordinate transformation, followed by a full fresh P0 Y2/Y3 + 2048-permutation Shapley pass.

## Eleven not yet source-projected players
BENCH: Jalen Milroe, Kenny Gainwell, Chig Okonkwo.
IR: Ricky Pearsall, Jayden Higgins, Chris Brazzell.
TAXI: CJ Daniels, Drew Allar, Taylen Green, Zavion Thomas, Athan Kaliakmanis.

All eleven remain owned. Pre-kickoff historical player catalog includes age and experience metadata in most cases. Use historically eligible role/availability and pre-2026 production priors, with status-specific uncertainty, not invented present-day values or blanket zeros.

## Model and release boundary
The verified historical simulation is current Simulation 2.0 on historical September 9 State and saved early-September Year 1 forecasts. Accepted P0 Y2/Y3 and 2048 Shapley already executed for 221/238 players. The six recovered sources plus eleven governed priors must be admitted and then *the entire* Shapley recalculated. Foundation 4 Y4-Y7 and Y8+ must be executed with historical point-in-time features from 1999-2025 and independent model-training cutoff proof, not copied from current October/November 2026 publication. Draft pick ownership is known; its numerical Intrinsic is not.

Accepted fixed display transforms exist (raw 3-Year / 750*10000; raw Career / 2200*10000 for matching FSFFL rules) but no index is publication-ready until a complete, comparable raw cohort exists.

Next implementation gates:
1. Add private-source eligible source six to exact historically dated State and score using compatible standard and league coordinates.
2. Build a governed Year 1 prior for the remaining eleven with 1999-2025 training and age/experience/status receipts; holdout check the prior.
3. Rerun complete P0 Y2/Y3, 2048 Shapley and test fully stable raw 3-Year with 238 subjects.
4. Use accepted F4 materializer to calculate Y4-Y7 and Career Y8+ at pregame cutoff; calibrate 0-10k scales.
5. Independently model all 108 owned picks as uncertain future slots; do not invent exact future draft positions.
6. Final fixed source/evidence manifest; only then refresh league title and dynasty reports in the published almanac.

Research only. No deployment, tier upgrade, live model mutation or additional service spend.
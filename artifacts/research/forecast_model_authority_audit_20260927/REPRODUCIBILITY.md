# Forecast Model Authority Audit — Reproducibility

Date: 2026-09-27

## Audit branch

`research/forecast-model-authority-audit-20260927`

## Exact deployed package

- model: `forecast-vnext-a2-burr-20260922`
- research commit: `122e802f327baf2fc7989ab635a68dfdc481d63f`
- immutable tag: `research-freeze/a2-burr-20260922`
- tag object: `b12c23008b2879af29f3f94c683de18ccbcaf264`
- archive SHA-256: `76b2842349093bb0f5c2bdc60995f78256d7cf6e2e4d64be84768a082450ceb1`
- manifest verification: 40/40 PASS
- historical common replay: 10,894 rows
- current Stage-D coordinate: 335 players / 670 Y2-Y3 rows

## Bounded family challenge

Full row artifact:
- workflow artifact `10936686595`
- digest `sha256:0e0239877bce93ba85789c53c87f4caef99d781600702b80c04099399ebc15af`
- common rows: 10,894

## Exact deployed-vNext join

Keys:
- source season;
- player ID;
- position;
- literal horizon.

Results:
- 10,894/10,894 common rows;
- target-points maximum absolute mismatch: 0;
- deployed-vs-D1 state-probability maximum absolute difference: ~1.4e-5.

Pairwise uncertainty:
- two-way source-season × player exponential/Bayesian cluster weighting;
- aggregate comparisons: 3,000 resamples;
- position comparisons: 1,500 resamples.

## Stage 4

Workflow:
- run `36338430538`
- durable scoring output commit `b8920be58f7319cd71317e2ce625aa4226c62409`
- complete artifact `10937742480`
- digest `sha256:52de1782ef1eb411b484d4afc51608789914ce3bfdea76576ddfe063e58641c5`

Frozen current coordinate:
- 335 players;
- exact connected-league scoring rules;
- identical governed Year-1 evidence for all candidates;
- Shapley permutations: 2,048;
- Shapley seed: 20260915;
- discount: 0.85.

Production parity:
- 335/335;
- max raw-Intrinsic delta ~5.68e-13;
- Spearman 1.0.

## Guards

No:
- post-result family addition;
- hyperparameter search after challenge results;
- named-player tuning;
- market/owner/team-utility input;
- current Intrinsic feedback into Forecast;
- production Forecast change;
- H3 change;
- Intrinsic change.

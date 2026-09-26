# FSFFL NEXT — Comparative Y4+ Reproducibility

Date: 2026-09-26

## Research branch
`research/intrinsic-y4plus-model-family-20260926`

Current branch head at final historical robustness checkpoint:
`9a0d8893084db327e669a019964a08ad32a7685f`.

## Historical comparative run
- workflow: `36250669362`
- successful head: `4fbfc70093422fbb0930daa7314f5afc34ae00f8`
- artifact: `10909006505`
- digest: `sha256:0befa35ef1d75eeb8cf160d141e9296cde4c83edd3df7127979afb7f2b8430ba`

Durable branch freeze artifacts:
- `FINAL_HISTORICAL_SELECTION.json`
- `HISTORICAL_SELECTION.md`
- `ROBUSTNESS_NOTE.md`

## Current comparative shadow run
- workflow: `36251520780`
- head: `ef75b90fcf8f58f51a9039e18e3f1532022dd59d`
- artifact: `10908953092`
- digest: `sha256:d9531eea6320c87c47effcbe107b725b4071e96bdc19664fe2e1d9f1004f27ff`

Outputs:
- `CURRENT_COMPARATIVE_SHADOWS.csv`
- `CURRENT_ARCHITECTURE_SENSITIVITY.csv`
- `CURRENT_POSITION_DISTRIBUTIONS_COMPARATIVE.csv`
- `CURRENT_MODEL_SENSITIVITY_PLAYERS.csv`
- `CURRENT_COMPARATIVE_SUMMARY.json`

## Current production comparison reference

Existing persisted production H3 Shapley artifact:
- artifact ID: **566**
- 335 players
- current research H3 shadow vs production H3 Spearman: **0.99654**

## Authority statement

No production source, Forecast coefficient, Intrinsic implementation, API, database row, Render deployment or product behavior was changed by the comparative research.

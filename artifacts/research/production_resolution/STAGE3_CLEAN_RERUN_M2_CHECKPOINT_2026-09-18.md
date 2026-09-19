# FSFFL NEXT - Stage 3 Clean Rerun M2 Checkpoint

Status: **CLEAN_RERUN_M2_COMPLETE_AND_PERSISTED**

- Parent clean-rerun start head: `d44a16a95e3103bc8bee3f872d19a7c767fd9216`.
- Literal runner path executed M2 only. No M3a/M3b model or adjustment object was computed during this step.
- Validation rows: 2,374; Y2 sources 2020-2021; Y3 sources 2019-2020.
- Final holdout: not accessed.
- Named current players: not used.
- M2 reproduces the prior Stage 3 M2 conclusion and core numeric outputs exactly.
- Y2 M2-M1a MAE delta: +0.0035397379; 95% CI [-0.0100519186, +0.0253147067].
- Y3 M2-M1a MAE delta: -0.0064764982; 95% CI [-0.0181625912, +0.0003434345].
- Classification: **M2 does not add clear replicated signal.**
- Clean runner SHA-256: `15802aebd41bcb3468162799777643309e3701a09a4318597c57a9871f2d622e`.
- Clean M2 result SHA-256: `0a7cbb737b8c062a1841e82ec52a053a3474c056b489f7fdfc4050a163b816a5`.
- Clean M2 row-audit SHA-256: `250d19ae2e391b7039611d61feb03fba17132a6e42f5e9092c1b2019ef6bedca`.

**SEQUENCE GATE:** M2 has now been durably persisted. M3a computation is permitted only after this checkpoint is committed and the research ref is re-fetched.

# FSFFL NEXT - Stage 3 Clean Rerun M3a Checkpoint

Status: **CLEAN_RERUN_M3A_COMPLETE_AND_PERSISTED**

- Required M2 persistence gate was satisfied at research head `caf289d1021d789942ee633d553b1ab57d0c4bf1` before this M3a computation began.
- Literal runner path executed M3a after rebuilding only the prerequisite M1a+M2 representation. No M3b model or adjustment object was computed.
- Validation rows: 2,374; final holdout not accessed; named current players not used.
- Clean M3a outputs reproduce the prior Stage 3 M3a core metrics, fitted effects, common row-level forecasts, stress conclusions, and classification.
- Y2 M3a-M2 MAE delta: +0.0350592824; 95% CI [-0.0182647627, +0.0829102320].
- Y3 M3a-M2 MAE delta: +0.0132571265; 95% CI [-0.0172389082, +0.0410989908].
- Y2 non-persistence harm: +0.1012434434 MAE; 95% CI [+0.0510263871, +0.1437198800].
- Y2 realized role-loss harm: +0.3163036142; 95% CI [+0.1103949951, +0.5480631489].
- Y3 non-persistence harm: +0.0552275534; 95% CI [+0.0364067653, +0.0767396873].
- Classification: **M3a does not advance.**
- Clean M3a result SHA-256: `d916f15c7ed6453b2ee4f61e2f237caa6b3e3577b82bb0bc4cecb5cd11857b57`.
- Clean M3a row-audit SHA-256: `1f0043e5fa1ed583442c4287f4376d20cb65493800fc8c2fd1a5f41c1a0b0973`.

**SEQUENCE GATE:** M3a has now been durably persisted. M3b computation is permitted only after this checkpoint is committed and the research ref is re-fetched.

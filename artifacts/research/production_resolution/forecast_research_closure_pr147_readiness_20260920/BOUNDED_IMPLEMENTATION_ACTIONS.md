# Exact bounded PR #147 implementation actions

Classification: REQUIRED BEFORE MERGE REVIEW, pending management approval.

1. Preserve `P0_PACKAGE_JSON`, `P0_PACKAGE_SHA256`, `P0_CURRENT_SOURCE_CSV`, the frozen Sep-10 FFToday + Razzball baseline, state probabilities, D1 coefficients, source coordinate, and player-specific scoring bridge exactly.
2. In `src/fsffl/product/p0_forecast_runtime.py`, decouple final route authority from the embedded P0 package selection and apply only these Y3 research-earned route overrides:
   - `QB|developmental`: `D0 -> D1`
   - `RB|established`: `D0 -> D1`
   All other Y2/Y3 routes remain as in the final authority ledger.
3. Add a versioned final-route authority identifier/digest to the P0 Forecast model-version/provenance so changed route semantics cannot present as the older P0-only route version. Do not change the fitted-package hash.
4. Do not implement any developmental-RB Y3 correction. Keep D1 and document the unresolved high-magnitude/elite limitation as Forecast uncertainty.
5. Do not change the five weakened veteran cells. Retain their current routes with evidence caveats only.
6. Extend `tests/test_p0_forecast_runtime.py` (and focused PR sanity tests as appropriate) to assert the complete final route map, exact frozen probability parity, and correct use of the existing D1 state-conditional production model in the two changed cells.
7. Regenerate current-head standard and connected-league 335-player boards and the representative sanity board. Prove:
   - Y1 is byte/numerically unchanged;
   - state probabilities/persistence are unchanged by route selection and scoring translation;
   - unaffected route cells retain prior outputs within tolerance;
   - the two affected Y3 cells use D1 outputs;
   - player-specific connected scoring is applied exactly once.
8. Rerun ordinary CI and focused P0/Shapley/scoring-contract tests on the new head. The existing activation-workflow red is an external nflverse asset timeout, not a model defect; retry only after the bounded implementation if the workflow is merge-required or clean operational evidence is desired.
9. Stop for a separate management merge review. Do not merge or deploy in this implementation task.
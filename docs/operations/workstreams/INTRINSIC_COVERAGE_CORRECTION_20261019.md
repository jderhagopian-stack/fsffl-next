# Intrinsic Coverage Correction — 2026-10-19

## Authority and scope

Management continuation under the current user directive and `OPERATING_PROTOCOL.md`. Continue the existing 3-Year Position & Depth implementation on PR [#469](https://github.com/jderhagopian-stack/fsffl-next/pull/469); do not open a parallel workstream. This checkpoint supersedes PR #469's earlier pending decision about how to address its incomplete 3-Year roster coverage.

The user authorizes a comprehensive correction to actual current-State coverage across Career Intrinsic, 3-Year Intrinsic, and their dependent position rankings, with implementation, verification, and release through the existing gates. This authorizes the following evidence-backed, narrow correction:

- Retain every existing stand-alone discounted 3-Year Shapley value unchanged.
- For an exact-State rostered player absent from that completed 3-Year contract, recover only that player's already-retained accepted Current Y1–Y3 annual Shapley contributions from the completed Career contract. Apply the accepted 3-Year discount schedule (`1, 0.85, 0.85²`) using the canonical Shapley discount constant.
- Consume the Career record only through a bounded completed-record lookup for the same user, league and exact published State. A missing/ambiguous record, invalid contract, mismatched player position, missing/nonfinite annual contribution, or wrong target season remains unavailable; do not start fitting, restore/load a contract, acquire providers, write/publish a valuation, or substitute Career total/long-horizon/terminal values from this read path.
- Keep the original Career 255-player outcomes, accepted authorities and numerical values unchanged. This correction does not modify Year 1 inputs, Forecast, Shapley attribution, Career economics, #370, simulation, State or publication lifecycle.

The user's new explicit directive resolves the previous coverage-extension decision pending in PR #469. It does not authorize other model or input-policy changes. Use no 0-fill or synthetic values. Existing approved input assumptions, if present on a recovered Career estimate, remain attached as explicit metadata and are not altered.

## Exact-State evidence

Read-only records were reconciled on 2026-10-19 against the active FSFFL NEXT Supabase project and repository `main` `1619c8accbcf9c976af8a95b287baadd04a8bb5a`, then the open PR #469 head `f0de2f8b291203283dff14d604954d94594ff130`.

- Current League State: `d8a818a89f2304cee126fbfda3ae482c3b41e67b3bc4dbf61c5d0b18ebcbec0c`, as of `2026-10-18T15:47:47.021296Z`, evaluation season 2026. It has 255 unique rostered QB/RB/WR/TE players: QB 52, RB 77, WR 98, TE 28.
- Completed Career artifact: `career_intrinsic_v1`, input fingerprint `8480cf2f62c2cc386a8dc204ce67d637930fedfdc1ea08904a258e2bae5c478e`, computed `2026-10-18T16:01:25.358977Z`, 364 estimates (the frozen 335 reference plus 29 dynamically appended candidates). All 255 current roster identities have Career estimates.
- Completed stand-alone Shapley/3-Year artifact: `shapley_intrinsic_contract`, input fingerprint `db48992a67aedd0f640854ab0ba4c6cd10fef53c9428f61d4936f119329c715a`, model `intrinsic-shapley-contract-v2:effective-horizon-seeds|forecast=forecast-vnext-a2-burr-20260922`, computed `2026-10-15T10:18:45.307494Z`, 335 estimates. Its exact-State roster overlap is 226/255: QB 45/52, RB 70/77, WR 85/98, TE 26/28. The missing groups are QB 7, RB 7, WR 13, TE 2; all 29 appear in the completed Career contract and have all three finite annual Current Shapley components for target seasons 2026–2028.
- For all 335 shared frozen-reference players, stand-alone discounted 3-Year values and the Career annual Y1–Y3 components recomputed under the accepted 3-Year discount have zero mismatches at `1e-9` tolerance; maximum absolute delta is `1.13686837721616e-13`. There are zero missing Career annual components among the 29 exact-State 3-Year gaps. This verifies the proposed component reuse against the entire shared source cohort; the Career lifetime total is neither used nor comparable.
- Existing complete-position coverage yields only QB 7/12, RB 8/12, TE 10/12 and WR 4/12 team rooms. The accepted complete-position contract therefore correctly withholds league rankings and Strength Index for every position in the current 3-Year lens. The complete Career roster cohort supports the separate Career ranking path.

The root cause is a cohort boundary: the stand-alone Shapley contract remains the frozen 335-player reference, while Career coverage has appended 29 exact-State roster candidates through the accepted expanded-cohort materialization. This implementation did not propagate those candidates' retained annual Current Shapley components to the separate 3-Year lens. Career's 255/255 coverage therefore does not make the distinct 3-Year value automatically complete. The ranking output is a downstream fail-closed consequence, not a rank calculator defect.

## Implementation and acceptance gates

Keep all changes on PR #469. The correction must expose source/coverage lineage for each added value and an exact-State extension count, while preserving each pre-existing value bit-for-bit. The 3-Year model/analytics version must identify the changed coverage contract. Do not change the complete-room ranking/tie/index formula.

Before release:

1. Add value/analytics regressions for distinct standalone and Career cohorts, proving existing values remain unchanged; only missing exact-State roster members may use three valid annual Current components; invalid, stale, ambiguous, wrong-position, missing-season or nonfinite evidence remains explicit and unavailable; and 3-Year ranking resumes only when every team room at that position is complete.
2. Prove the exact-State roster returns 255/255 3-Year values with extensions QB 7, RB 7, TE 2 and WR 13; all four positions produce complete 12/12 rooms, numerical ranks and finite Strength Index values. Confirm Career 255 values remain identical.
3. Reconcile frozen-335 parity and the result formula to the exact accepted Shapley authority. The extension must not include later Career horizons, terminal value, Career display indexes or market values.
4. Run focused tests/CI while the PR is draft. At a stable exact head, mark it ready once and require the repository's Stable full-suite run on that exact head plus final review with no unresolved findings. If changes follow, return the PR to draft and rerun the gates on the final head.
5. Merge only the reviewed stable head after all gates pass. Follow existing Render release governance, deploy only the approved merge SHA when required for the new product surface, and verify exact live SHA, endpoint values/coverage and user-visible position rankings. Record exact identities, evidence and limitations here and in `CURRENT_OPERATIONS.md`.

PR #405 remains open. Its separate corrected Foundation 4 full-calculation memory acceptance gate is not waived or claimed by this read-path correction; no new expensive calculation is authorized by switching the 3-Year chart.

## Implementation checkpoint — draft validation

Implemented on the existing PR #469 branch. The value layer now exposes one canonical discounted Y1–Y3 reconstruction helper and uses it for the existing contract reconciliation. The analytics layer retains every valid stand-alone estimate and extends only roster identities absent from that exact-State cohort using the completed Career contract's retained raw annual components. It rejects ambiguous duplicate cohorts, refuses Career fallback for a malformed row already present in the stand-alone cohort, checks exact State, season, position, annual years, finite values and the undiscounted annual-sum reconciliation, and keeps Career totals/horizons out of the extension. The read-only route retrieves only completed exact-State owners, reports source fingerprints, per-player provenance and per-position roster coverage, and starts no work. The 3-Year analytics model version advances; Career aggregation and complete-room rank/index formulas are unchanged.

Focused verification on the draft implementation: `uv run --extra dev --extra web pytest -q tests/test_dynasty_position_room.py tests/test_shapley_intrinsic_contract.py tests/test_career_forward_intrinsic.py tests/test_product_league_comparison_static.py` — **60 passed**. `git diff --check` passes. Ruff and mypy executables are not included in the repository's declared `dev`/`web` extras; hosted CI remains the authoritative lint/type and broader regression gate. This is unit/synthetic-State verification and does not yet claim the deployed 255/255 route result. Exact-head focused CI, the stable full suite, review, merge, deploy and live endpoint verification remain pending.

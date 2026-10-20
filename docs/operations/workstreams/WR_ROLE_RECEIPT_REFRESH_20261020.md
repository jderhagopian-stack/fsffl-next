# WR role-evidence receipt renewal — 2026-10-20

## Finding

The previously accepted Year-1 input exceptions remain authoritative for the three approved WR identities. The incomplete room was not evidence that the rules were missing or that the annual valuation method should change.

The latest owned calculation began after the exact official-role evidence receipts had exceeded their six-hour validity window. The role facts were therefore correctly rejected as stale, leaving three Career Year-1 inputs unresolved and preventing complete WR room rankings. The other position rooms remain governed independently.

## Correction

Re-captured the three already-approved role facts from their official sources at 2026-10-20 19:55:28 UTC and appended receipts without altering prior history. The change does not change player assumptions, model economics, ranking arithmetic, complete-room coverage requirements, or request a new calculation on its own.

## Validation and next gate

The exact identity, role, source, and capture-time regression passes. Focused local validation passed 48 tests across the affected receipt, provider, Career, and position-room suites; `git diff --check` passed.

A new owned calculation and authenticated live verification remain necessary to prove that fresh receipts produce the expected Career coverage, dependent 3-Year values, and complete WR rankings. Do not infer live acceptance from source tests or repeat the calculation automatically.


## Release completed — 2026-10-20

PR #473 merged after exact-head focused CI, Stable full suite run 39489697163 and automated review with no findings. Merge SHA: 972ee41b8cd14742e157587988212e71023428cb. Existing service deploy dep-dbbsqqnavr4c73dgco10 reached live at 2026-10-20 20:23:38 UTC on that exact commit. Startup logs show normal restoration of the previously completed Career artifact. This confirms deployment only; no new Career calculation has run yet, so 3 WR coverage and dependent room ranking acceptance remain open. A fresh explicitly initiated app calculation and authenticated verification are still required. The expired-receipt calculation must not be treated as current coverage, and no automatic repeat was started.

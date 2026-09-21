# PR #164 - Revision-Agnostic Forecast Health Closeout Checkpoint

Date: 2026-09-21

## Disposition

PR #164 remains **OPEN / DRAFT / UNMERGED**. The implementation and regression work is
code-green at candidate SHA `91094237ec61ac2f9220a6cf957ec816dd0bff8b`, but the
management directive requires an exact-candidate authenticated mobile/iPhone/Safari
validation before merge. The connected Render environment exposes only the production
`main` service and has pull-request previews disabled, while the Work environment does
not have the beta credentials or production persistence secret values needed to build an
equivalent authenticated candidate service. Therefore the merge gate is intentionally
held.

PR #163 remains held, draft, and unmerged. It is not refreshed or merged because #164
has not passed the live-validation gate. Market / Opportunities v1 has not started.

## Root cause

The safeguard merged in PR #162 was revision-stable only **within a known incident**.
It computed a content witness over preserved malformed rows and deliberately ignored
timestamp, row order, and row count. That correctly stopped republishing of the same
bad content under transport/shape drift, but the health authority still depended on
matching the exact preserved player/stat witness values.

The later malformed Razzball revision changed those values enough to miss the prior
incident witness. The remaining production gates checked source identity, duplicate
structure, minimum independent source count, material scoring-domain completeness, and
normalization coverage; none was a generalized numerical-scale integrity check. The
later revision therefore entered the two-source ensemble with FFToday.

## Corrected revision-agnostic contract

The primary source-health rule is now provider-neutral and dataset-level:

- Each normalized provider snapshot is translated through the league scoring bridge into
  full-season fantasy-point observations solely for source-health comparison.
- When the immutable governed preseason raw ensemble exists, each current source is
  compared with that same independent reference.
- The gate measures multiplicative change across canonically matched players and requires
  a broad median shift across at least 16 comparable players, at least 4 players per
  eligible position, and at least 3 offensive positions.
- The scale threshold is **1.567843238263934**, derived as
  `1 + max(position relative RMSE)` from the already-promoted 2024-2025 multi-source
  historical Forecast error calibration. The largest position-level promoted RMSE is
  used deliberately as the conservative tolerance. It was not fit to Razzball or any
  named current player.
- If exactly two live sources materially disagree and no governed reference exists,
  both fail closed rather than FSFFL guessing which provider is healthy.
- With three or more live sources, a source is quarantined when it is broadly inflated
  against at least two peers.
- No row is divided, clipped, capped, repaired, or reweighted.
- Exact Sep-20 and Sep-21 incident witnesses remain secondary forensic defense only.

## Adversarial acceptance evidence

Focused corrective regression workflow `35639151115` completed successfully:
**75 passed, 2 warnings**.

The focused suite proves:

- both preserved malformed Razzball incident fixtures remain quarantined;
- a never-registered deterministic synthetic revision with 1.80x broad inflation is
  quarantined without any incident fingerprint;
- a governed-reference case accepts a 1.03x source and quarantines the unseen 1.80x
  source without provider-name logic;
- a healthy 1.05x drift passes the generalized evaluator;
- production-runtime benign 1.04x drift passes despite timestamp changes, reversed row
  order, and an extra unmatched row;
- source-health provenance records acceptance/quarantine disposition, check, reason,
  provider payload digest, health-contract version, governed reference, cohort size,
  threshold, overall median ratio, and position medians.

The live-provider diagnostic workflow `35639151190` completed successfully by treating
the expected revision-agnostic quarantine / fewer-than-two-source fail-closed result as
diagnostic success rather than a product failure.

## Forecast fallback and stale-artifact protection

The resilient production loader now supplies the immutable preserved preseason raw
ensemble as the governed reference to current source health. If quarantine leaves fewer
than two healthy independent live sources, the live build fails closed and the existing
authorized preseason fallback is used. The Sep-10 artifact is read, never rewritten.

New live Forecast artifacts are versioned
`next8-live-forecast-evidence-v5:revision-agnostic-source-health` and must persist both
provider payload provenance and accepted current-contract source-health events.
Persisted live evidence that predates this contract cannot restore as healthy.

The Franchise payload and UI expose whether Forecast evidence is current live or
preserved-preseason fallback. The display path prefers the governed Forecast observation
over a duplicated top-level number.

## Intrinsic loading and product hierarchy

The existing Shapley mathematics are unchanged. Cold Shapley Intrinsic work is now
coalesced server-side, persisted as a reusable governed contract, and shared by the
Franchise Value Lens, Value Disagreement, and League value-lens routes. Clients poll a
bounded server-side job and terminate in ready/unavailable/error rather than holding an
indefinite cold request.

Primary owner-facing Home, Franchise, Trade Center, League, and current Market copy no
longer foregrounds FSFFL Cardinal. Broad Market and FSFFL Intrinsic remain distinct
lenses, League Market Value remains unavailable, and Trade Decision retains bilateral
package-economics authority. Cardinal remains compatibility-only where backend
dependencies still require it; it is not relabeled as Intrinsic.

## Regression status

Full CI workflow `35639151331` completed successfully at the code candidate:
**1322 passed, 2 warnings**.

Other checks on the same candidate:

- Live Forecast corrective trace `35639151256`: success. GitHub Actions does not hold
  `FSFFL_DATABASE_URL`; the workflow now records that as an environment/access boundary
  instead of misclassifying it as product failure.
- Corrective live-provider numerical trace `35639151190`: success.
- Focused corrective regression `35639151115`: success, 75 passed.
- Private-beta Intrinsic live diagnostics `35639151195`: queued/pending at the time
  this checkpoint was authored; prior corrective heads completed the same diagnostic
  successfully. Final management reporting must re-fetch its status rather than assume.

## Exact live/mobile validation boundary

Connected Render inspection shows:

- production service: `fsffl-next-private-beta`;
- branch: `main`;
- plan: free;
- auto-deploy: enabled;
- pull-request previews: disabled;
- no preview service exists for PR #164.

The Work environment cannot read the existing beta-auth credentials or
`FSFFL_DATABASE_URL` secret values. Creating an unauthenticated or persistence-free
candidate would not satisfy the directive and changing the production service away from
`main` would be an unsafe substitute.

**Smallest external action required:** deploy the exact final PR #164 head to an
authenticated preview/review environment using the existing beta-auth and production
persistence secret configuration (or enable a Render PR preview that inherits those
managed secrets), then validate Home, Franchise, Value Lens, Value Disagreement, League
value lenses, Trade Center, and Forecast fallback/provenance on iPhone/Safari. Record
the exact deployed SHA and route results.

Until that external validation exists, do not merge PR #164.

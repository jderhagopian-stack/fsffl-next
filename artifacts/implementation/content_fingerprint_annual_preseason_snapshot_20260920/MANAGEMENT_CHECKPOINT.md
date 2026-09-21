# FSFFL NEXT - Final Management Checkpoint

Date: 2026-09-20
Directive: Pre-merge correction for PR #162 + durable annual preseason snapshot capability
Repository: jderhagopian-stack/fsffl-next
PR: #162

## Classification

- Objective A - content-based malformed-provider quarantine: **PASS**
- Objective B - durable annual preseason raw-stat snapshot capability: **PASS**
- Merge/deploy authority: **NOT EXERCISED**

## Exact implementation coordinate

- Directive starting head: `48c221eb94ec6b40e5e122923e33c8ba82b847a4`
- Validated implementation head before this checkpoint artifact: `6f1987eed09b51a216f40f5c170dea652382d363`
- Base main at directive handoff: `085bc6c21b3422b579d2d7b826906726d2ad35c2`
- Post-directive implementation is exactly 7 commits ahead of the directive start and modifies only:
  - `src/fsffl/forecast/source_health.py`
  - `tests/test_malformed_live_provider_fallback.py`
  - `src/fsffl/forecast/current_normalization.py`
  - `src/fsffl/forecast/annual_preseason_snapshot.py`
  - `src/fsffl/forecast/annual_preseason_service.py`
  - `src/fsffl/persistence/annual_preseason_snapshot.py`
  - `tests/test_annual_preseason_snapshot.py`

## Objective A - quarantine identity

The prior incident identity depended on provider/source-version + effective timestamp + row count. That bypass risk is removed.

The final gate uses a deterministic SHA-256 content-witness signature built from the exact malformed pre-normalization Razzball row/field values durably preserved by the completed numerical trace. The full 562-row malformed payload was not durably preserved, so the implementation explicitly does **not** claim a full-payload hash.

The signature:
- preserves provider/source-version context;
- is independent of capture timestamp;
- is independent of effective timestamp;
- is independent of row ordering;
- is independent of total row count;
- changes when the preserved malformed row content changes.

The persisted incident signature is:
`0545b6c585712165997dca191169596d000aa30435f4e2ccde6d3f55c6877e3d`

A direct recomputation during final validation matched the persisted signature exactly.

Regression coverage proves:
1. known malformed content is rejected before normal live ensemble authority can be constructed;
2. the same malformed content with changed capture/effective timestamps remains quarantined;
3. the same malformed content with reordered rows remains quarantined;
4. the same malformed content with changed row count remains quarantined;
5. corrected content under the same provider/source-version is allowed through the governed live path;
6. malformed live evidence falls back to the preserved preseason authority without rewriting persistence.

No generic plausibility threshold, clipping, divisor, provider reweighting, cross-provider tuning, learned anomaly detector, Forecast coefficient change, or model retuning was introduced.

## Objective B - annual preseason snapshot architecture

A new league-agnostic NFL-season artifact is implemented at the raw-stat Forecast evidence layer.

The canonical artifact stores, for each successfully fetched provider:
- provider and source version;
- stable source identifier;
- capture and effective timestamps;
- usage class;
- deterministic provider payload SHA-256;
- source-health disposition;
- immutable provider-level raw projection rows;
- normalized raw-stat Forecast observations and hash;
- normalization provenance.

The season artifact also stores:
- NFL season;
- governed opener coordinate source;
- date precision and T-14 target date;
- actual capture timestamp and days-before-opener offset;
- provider failures;
- governed equal-weight raw-stat ensemble;
- deterministic ensemble hash;
- independent-source coverage;
- successful source IDs;
- runtime/normalization/model versions.

League scoring is **not** part of canonical snapshot identity. Future leagues replay the frozen raw-stat ensemble through Forecast's league-scoring bridge using that league's rules.

## Capture / retry / immutability behavior

- Opener date is derived from the repository's governed Sleeper NFL regular-season schedule evidence, not from a hard-coded future kickoff date.
- Capture refuses to run before T-14.
- Capture refuses to create a new annual snapshot on or after opener date.
- Existing >=2 healthy independent-source authority is preserved.
- Failed attempts persist nothing and are retryable on later pre-kickoff invocations.
- The persistence service checks for an existing season artifact before capture and again immediately before write.
- The first valid governed snapshot is returned unchanged on later invocations; no provider refetch or artifact rewrite is intentionally performed.
- The legacy 2026 Sep-10 preseason baseline is untouched and remains grandfathered in its existing schema.

## Historical evidence rule

No historical snapshot backfill or fabrication path was added. The live annual capture path is closed on or after the season opener. A prior season therefore cannot be manufactured from current provider pages by this capability. Authentic point-in-time historical backfill remains unavailable unless separately supported by provenance-sufficient historical evidence.

## Scheduler / opener boundary

The repository contains a Render web service but no deployable cron/scheduler integration for this annual job. Per the directive's allowed boundary, implementation stops at the reusable idempotent capture service + immutable artifact contract + tests.

The governed Sleeper schedule coordinate currently supplies opener **date** precision, not a verified kickoff clock time. The implementation records that precision explicitly rather than inventing an hour.

Operational recurrence must invoke the service daily during the capture window to realize automatic retry. No unapproved external scheduler/deployment change was made.

## Validation

Validated head: `6f1987eed09b51a216f40f5c170dea652382d363`

GitHub Actions:
- CI run `35554267031`: **SUCCESS**
  - `pytest -q`: **1310 passed**, 2 deprecation warnings, 0 failures.
- Cardinal Value Research run `35554267154`: **SUCCESS**.
- League value-lens real-roster audit run `35554267022`: **SUCCESS**.

Final review also confirmed the 7-file post-directive diff contains no Value, Simulation, Decision/Search, Team Utility, league-market, Shapley-math, provider-weight, or Forecast-coefficient modifications.

## Management disposition

The continuation directive is satisfied at the validated implementation head.

PR #162 must remain **open / draft / unmerged / undeployed** for management review. No merge or deployment is authorized by this checkpoint.

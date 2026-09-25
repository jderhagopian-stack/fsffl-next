# FSFFL NEXT — 2026 Late-Start K/DST Implementation Checkpoint

Date: 2026-09-25  
Workstream: Forecast / Product Implementation  
Research authority: `artifacts/research/k_dst_late_start_exception_20260925/RESEARCH_HANDOFF.md`  
Implementation PR: #233  
Branch: `implementation/kdst-late-start-2026-20260925`

## State

**ACTIVE — ACCEPTANCE VALIDATION**

Management authorized the bounded, one-season-only 2026 current-date ROS implementation. This checkpoint records the implementation actually present in PR #233. It does not promote production K/DST Forecast authority.

## Implemented

### 2026-only baseline contract
- dedicated `LateStartCurrentProjectionSnapshot`, separate from annual preseason authority;
- hard `season=2026` boundary and rejection of 2027+;
- explicit `rest_of_season` horizon;
- true capture/evaluation timestamps;
- explicit `preseason_eligible=False` and governed preseason-comparison-unavailable status;
- separate persistence artifact kind `late_start_current_projection_snapshot`.

### Provider evidence and source health
- provider endpoint, source version, effective/capture time, content SHA-256, independence group, usage class, and rights status retained;
- schedule-aware subject-row freshness against the canonical remaining NFL schedule;
- completed-game stale rows are quarantined, never backdated or heuristically subtracted;
- technical independent-source coverage and production-rights-cleared independent-source coverage are distinct;
- research-only evidence can be retained without becoming production authority.

### CBS bounded adapter
- 2026 ROS K/DST page contract implemented for deterministic evidence/contract testing;
- exact K fields retained through 50+ plus attempts/makes and XP;
- D/ST linear raw events retained;
- aggregate PA/YA retained only as diagnostics and cannot satisfy distributional PA/YA buckets;
- source is explicitly `RESEARCH_ONLY` and is not registered in the production provider set.

### Forecast normalization and scoring
- K remains an individual player; D/ST remains a canonical team-season unit;
- accepted ROS rows normalize to `REST_OF_SEASON` raw observations only;
- exact `FGMISS = FGA - FGM` and `XPMISS = XPA - XPM` transforms are supported when same-horizon evidence is complete;
- equal-coefficient Hodor 0–19 + 20–29 may use exact provider 0–29 total without inventing a split;
- 50+ still cannot satisfy a separate 60+ coordinate;
- aggregate D/ST PA still cannot satisfy PA bucket authority;
- per-subject league-rule coverage can be evaluated using only rights-cleared sources by default.

### Empirical uncertainty governance
- explicit reduced K and D/ST `CalibrationScoringFingerprint` contracts;
- exact target scoring compatibility is required before a calibration can be considered;
- deterministic subject-hash holdout diagnostics added;
- compact retained fixture reproduces the Research measurements from the exact public repo refs/blobs:
  - K season n=34, relative RMSE `0.38418847933549305`;
  - D/ST season n=30, relative RMSE `0.21402833115231343`;
  - K weekly n=542 / 42 subjects, CV `0.5223274618193781`;
  - D/ST weekly n=544 / 32 subjects, CV `0.6381941339011228`.
- these measurements remain non-promoting for full Hodor totals.

### Authority/readiness
- explicit late-start authority assessment requires:
  - rights-cleared independent sources;
  - active-rule completeness;
  - compatible calibration fingerprint;
  - explicitly promoted simulation-grade uncertainty.
- no zero-uncertainty fallback exists.

## Deterministic acceptance coverage

PR #233 tests cover the Research handoff's bounded fixtures, including:
- 2026 accepted; non-2026 rejected;
- no source backdating;
- Thursday-completed ATL/GB stale-row quarantine while an unplayed team row remains healthy;
- wrong-year/wrong-horizon source rejection;
- exact equal-coefficient 0–29 K transform;
- same-horizon miss derivation;
- 50+ cannot satisfy 60+;
- D/ST team-unit identity and aggregate PA rejection;
- one-source rare D/ST coordinates remain insufficient;
- provider independence groups prevent aggregate double counting;
- target fingerprint mismatch prevents uncertainty promotion;
- research-only rights do not become production coverage;
- preseason comparison remains unavailable;
- existing no-K/no-DST regression remains governed by the PR #215 suite.

## Explicitly not implemented/promoted

PR #233 does not:
- create 2026 K/DST preseason evidence;
- allow this exception in 2027+;
- use CBS public pages as production-authorized data;
- create a LineupExperts/RotoWire/JerryGM production adapter without validated access and rights;
- promote K 60+ authority without two independent governed sources;
- promote D/ST PA-tier distribution or rare-event authority without two independent governed sources;
- promote reduced-fingerprint RMSE/CV values as Hodor-total uncertainty;
- create downstream Value/Simulation/Decision/Search K/DST truth.

## External gates after code acceptance

1. Live API validation of an exact-capability provider candidate (JerryGM identified by Research) requires authorized API access.
2. Written/deployable rights for FSFFL's derived multi-source use are required.
3. A second independent current ROS source must prove K 60+ and D/ST PA distribution / remaining rare-event hard coordinates.
4. Target-compatible full-score K/DST uncertainty must be empirically promoted before simulation-grade authority.

Until those gates clear, Hodor current-forward K/DST must remain fail-closed even though the 2026 late-start plumbing exists.

## Next action

Complete PR #233 acceptance against current main, fix any regression, merge when green, then reconcile canonical operating state. After merge, apply OPERATING_PROTOCOL.md: if no rights-cleared/API evidence is available, stop at the exact external evidence/source-rights blocker rather than implementing a heuristic substitute.

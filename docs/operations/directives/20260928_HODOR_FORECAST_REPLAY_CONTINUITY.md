# Management Directive — Hodor Forecast Replay Continuity — 2026-09-28

## Status
**AUTHORIZED — IMPLEMENTATION / SOLE RUNTIME PRIORITY**

## Why this exists
PR #280 restored a governed compatible-Forecast replay path, but the hosted FSFFL → Hodor switch still fell through to fresh live provider acquisition and failed when only Razzball was healthy. The project already has durable Hodor partial-authority behavior and a last-good continuity contract. Temporary provider availability must not erase otherwise valid governed Forecast evidence.

Treat the remaining failure as a **Forecast replay / league-switch continuity defect until proven otherwise**, not merely as external provider downtime.

## Required implementation outcome
1. On league switch or same-league State advance, inspect persisted Forecast evidence before live provider reacquisition.
2. Separate **raw Forecast evidence compatibility** from **downstream State-specific compatibility**.
   - Raw provider ensemble replay may be rejected only by inputs that genuinely invalidate that raw Forecast evidence.
   - League scoring, lineup/scoring presentation, fantasy-week derivation, Value, Simulation, Market and other downstream State-bound layers must be rebuilt/rebound separately rather than unnecessarily invalidating reusable raw Forecast truth.
3. Persist and expose the exact replay decision:
   - prior evidence identity;
   - target State identity;
   - compatibility result;
   - exact component/reason for rejection;
   - whether replay, partial-authority restoration, or fresh acquisition was selected.
   A generic `fingerprint_changed` reason is insufficient for hosted acceptance.
4. Preserve PR #244/#245 partial-authority behavior. Missing full K/DST authority or temporary provider failure must not erase supported ordinary Forecast coverage or independently valid Value evidence.
5. Preserve the two-independent-source/source-health rules for **new authority acquisition**. Do not weaken provider gates, fabricate a second source, silently zero missing coordinates, or promote blocked Simulation.
6. If raw Forecast evidence is genuinely incompatible and fresh acquisition is unavailable, continue serving the compatible last-good presentation/read model with truthful stale/blocked-refresh status wherever authority permits; do not blank unrelated product surfaces.
7. Do not reopen Market architecture, Forecast model selection, Long-Term Intrinsic Research, or unrelated runtime work.

## Required proof
Implementation must exercise the real hosted path on the exact deployed corrective:
- primary FSFFL cold/warm use remains responsive and preserves the PR #280 latency/memory gains;
- switch FSFFL → Hodor;
- prove Hodor reuses governed persisted raw Forecast evidence when raw inputs are compatible, even when live provider acquisition is unavailable;
- rebuild only the State-specific scoring/supplement/downstream layers that actually require rebuilding;
- preserve truthful Hodor partial authority when full K/DST/Simulation authority remains unavailable;
- switch Hodor → FSFFL without cross-league contamination;
- repeat/restart as needed to prove persistence survives process lifecycle;
- no 5xx/429/recycle or hard Render memory-limit breach;
- record exact replay/rejection telemetry and resource measurements.

A deterministic regression must cover at least:
- downstream-only State/scoring changes do not force raw provider reacquisition when raw Forecast evidence remains compatible;
- a genuinely raw-Forecast-material input change rejects replay and falls through safely;
- provider outage during an otherwise compatible switch still succeeds through governed replay;
- old Simulation/Value are never rebound to a new State without their own compatibility/authority proof.

## Terminal condition
Do not return for an intermediate diagnosis while authorized corrective actions remain. Stop only at an OPERATING_PROTOCOL terminal state.

Full runtime acceptance is not complete until the FSFFL → Hodor → FSFFL hosted journey passes under this contract. Long-Term Intrinsic shadow implementation remains paused until then.

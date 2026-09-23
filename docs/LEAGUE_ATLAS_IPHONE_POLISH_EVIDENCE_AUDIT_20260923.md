# League Atlas iPhone acceptance polish — evidence audit

Date: 2026-09-23

## Starting coordinate

- Authoritative `main` at branch creation: `f9d584fe15dffb439ff819bb30c158ace34ed375`.
- Render private-beta was live on the same exact SHA.
- Fresh bounded branch: `corrective/league-atlas-iphone-polish-20260923`.
- This pass does not change Forecast, Value, Simulation, Decision, Search, Team Utility mathematics, Max PF authority, or the 50,000-run Simulation contract.

## Value Map Safari rendering defect

Source inspection confirmed invalid nested interactive markup in the live candidate: every team value row was emitted as a `<button>`, while each governed player dot inside that row was also emitted as a `<button>`. HTML does not permit an interactive `button` descendant inside another `button`; browser reparsing/reparenting can therefore break the intended strip/dot structure, matching the iPhone/Safari symptom of nonzero coverage with no visible dots.

The corrective presentation uses:
- a non-interactive `div.league-value-row` container;
- an independent `button.league-value-team-select` for team selection; and
- independent `button.league-value-dot` controls for Player Intelligence handoff.

No Value coverage or percentile authority changed.

## 2026 preseason reconstruction attempt

Canonical governed opener evidence remains date-precision only:
- earliest Week-1 regular-season schedule date: **2026-09-09**;
- the existing annual capture policy therefore rejects same-date State and accepts only a coordinate strictly before 2026-09-09.

Persisted evidence inventory:
- 51 canonical 2026 State snapshots exist for the league;
- earliest canonical State `as_of`: **2026-09-10 12:44:36.198236+00**;
- the earliest State is post-opener and already contains regular-season scoring;
- captured Behavioral history contains 2026 completed Sleeper trade, waiver, and free-agent transactions;
- latest captured ownership-changing event before the cutoff: **2026-09-08 15:00:44.205+00**;
- first captured ownership-changing event after the cutoff: **2026-09-10 23:33:06.900+00**;
- captured ownership-changing events between 2026-09-09 00:00 UTC and the earliest canonical State: **0**.

That transaction gap is useful but not sufficient to reconstruct an exact pre-kickoff canonical State. The Behavioral event contract records only completed trade/waiver/free-agent acquisition and disposition evidence. It does **not** preserve historical roster-slot transitions such as TAXI, IR, bench, or active-lineup eligibility moves. The earliest post-opener State already contains 23 TAXI assignments and 6 IR assignments across the league. Without a pre-opener State or a complete point-in-time roster-slot event stream, the exact cutoff eligibility state cannot be proven.

**Recovery outcome: FAIL CLOSED.** Player ownership may be consistent across the cutoff-to-first-State gap, but the hard invariant requiring exact roster eligibility/slot state is not satisfiable. No reconstructed preseason State or Simulation is persisted, and current rosters are not used as a hindsight substitute.

## Future annual preseason capture

The repository contains a free GitHub Actions scheduler:
- workflow: `.github/workflows/annual-preseason-snapshot-scheduler.yml`;
- cadence: daily at 08:17 UTC plus manual dispatch;
- endpoint: `POST /internal/annual-preseason-snapshot/capture`;
- hosted route requires `X-FSFFL-Scheduler-Token` matching Render `FSFFL_SCHEDULER_TOKEN`;
- capture logic uses the governed Sleeper schedule/player universe, T-14 window, minimum two healthy independent Forecast sources, first-valid immutable annual projection artifact, and durable persistence.

Operational audit of Render request/app logs from the workflow's introduction through this pass found **no scheduled POST request** to `/internal/annual-preseason-snapshot/capture` and no hosted `annual preseason snapshot scheduler attempted` log entry. The workflow previously treated an absent GitHub Actions `FSFFL_SCHEDULER_TOKEN` as a successful dormant run; this pass changes that behavior to fail visibly with a nonzero exit so missing credentials cannot look operational.

The remaining operational requirement is to prove a token-authenticated scheduled invocation reaches Render. The available integration cannot read or create GitHub Actions repository secrets, so this evidence must come from a configured `FSFFL_SCHEDULER_TOKEN` secret and a resulting hosted POST/log entry. Until that exists, scheduler presence is proven but end-to-end operational invocation is not.

## iPhone ownership boundary

Automated/static validation may verify the presentation contracts, DOM validity, safe-area CSS, sort wiring, and live payload composition. Physical iPhone/Safari acceptance remains management-owned and is not claimed by implementation.

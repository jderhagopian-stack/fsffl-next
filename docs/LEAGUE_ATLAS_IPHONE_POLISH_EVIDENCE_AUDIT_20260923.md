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

Operational proof completed on 2026-09-23:
- scheduled workflow run #2 originally showed `FSFFL_SCHEDULER_TOKEN` empty and took the dormant path;
- after the repository Actions secret and Render environment variable were configured to the same private value, the same scheduler job was re-run;
- GitHub Actions masked the credential as `***`, executed `python scripts/run_annual_preseason_scheduler_tick.py`, and issued the configured POST;
- the hosted route no longer returned 401; instead it returned the governed post-opener result: HTTP 503 with `failed-with-reason` / `annual preseason capture window is closed; opener_date=2026-09-09`;
- Render recorded the matching application request event at **2026-09-23T17:44:33.381150324Z**: `POST /internal/annual-preseason-snapshot/capture HTTP/1.1` -> **503 Service Unavailable**;
- this is the expected proof condition for an in-season test: authentication and routing succeeded, while capture creation correctly declined because the preseason window is closed.

The first retry occurred while the Render environment update deployment was still replacing the prior instance and correctly returned 401. After deploy `dep-daq0v53ncjis73941sjg` became live on unchanged main SHA `f9d584fe15dffb439ff819bb30c158ace34ed375`, the next retry reached the governed capture logic and produced the expected closed-window response above.

**Scheduler operational outcome: PASS.** The GitHub Actions secret is present, the protected Render route accepts the shared credential, the workflow sends the real POST, and Render records the matching request. No 2026 preseason baseline was created or fabricated. The workflow's missing-secret path remains hardened to fail visibly.

## iPhone ownership boundary

Automated/static validation may verify the presentation contracts, DOM validity, safe-area CSS, sort wiring, and live payload composition. Physical iPhone/Safari acceptance remains management-owned and is not claimed by implementation.

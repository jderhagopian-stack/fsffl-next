# FSFFL NEXT — Architecture Recovery Workstream

Updated: 2026-10-05

## Purpose

This is the durable execution/handoff record for the P0 Architecture Simplification and Development Recovery program governed by:

`docs/operations/directives/20261005_ARCHITECTURE_SIMPLIFICATION_AND_DEVELOPMENT_RECOVERY.md`

Management has accepted the read-only audit and assigned **Work as the sole writer** for the P0 corrective program while Work capacity remains available.

This file exists so execution continuity does **not** depend on Work chat history or remaining Work allowance.

If Work becomes unavailable or exhausts its usage allowance, Management may reassign the exact remaining work to Implementation. Implementation must resume from this file plus the governing directive and live GitHub state rather than reconstructing scope from conversation history.

## Mandatory checkpoint rule

Work must update this file **before and after every material P0 slice**, and whenever it is about to:
- open or merge a PR;
- deploy;
- begin a materially different subsystem;
- pause for Management;
- stop because of tool/session/usage limits;
- hand execution to another worker.

Do not wait until the end of the entire recovery program.

Every checkpoint must record:

1. **Timestamp / phase / slice**
2. **Current main SHA**
3. **Active branch / PR / exact head SHA**
4. **Live Render deploy/commit if relevant**
5. **What was proven before changes**
6. **What changed**
7. **Files/subsystems touched**
8. **Before/after measurements**
   - restore/useful-State timing;
   - foreground/API latency where relevant;
   - Supabase calls/bytes or artifact-read counts where relevant;
   - refresh/publication timing where relevant;
   - Render current/high-water memory where relevant;
   - browser polling/retry/lifecycle handoffs where relevant.
9. **Focused tests run and result**
10. **Full-suite status**
    - run only at the stable merge gate unless a materially broad contract change warrants otherwise.
11. **Physical/hosted acceptance status**
12. **Known unresolved findings**
13. **Frozen safeguards / explicit non-goals**
14. **Exact next action**
15. **Safe handoff instruction**
    - what another worker should read first;
    - exact commit/branch to resume from;
    - what must not be repeated or reopened.

## Work-allowance discipline

Management currently has limited weekly Work capacity.

Therefore:
- prioritize finishing one bounded slice cleanly over partially touching several later slices;
- avoid repeating broad repository/audit scans already captured in the accepted audit unless new evidence requires them;
- reuse the audit, directive, this workstream file, and live code evidence;
- keep changes PR-sized;
- checkpoint early and often;
- if remaining Work capacity appears insufficient to finish the current slice safely, stop at a clean durable checkpoint rather than beginning another architectural tranche.

## Current accepted execution sequence

### P0.1 — measurable customer read path
Establish the authoritative end-to-end saved/current-session journey through Product Context and League Atlas to visible current-generation Dynasty Position & Depth evidence.

Include the unresolved live Dynasty failure.

Baseline:
- restore stages;
- State lookup;
- publication/manifest lookup;
- payload reads;
- first useful render;
- generation identity;
- Supabase calls/bytes;
- foreground latency;
- Render memory;
- browser retry/poll/handoff count.

Do not broadly refactor before this baseline exists.

### P0.2 — metadata-first persistence / egress
Add metadata-only artifact/presentation lookups for existence, identity, generation and freshness. Fetch large payload only on actual consumption. Remove repeated same-process full-payload reads where safe.

### P0.3 — automatic static-asset identity
Replace manual cache-buster maintenance with centrally generated content-derived fingerprints.

### P0.4 — simpler published-reader contract
Move ordinary product reads toward one inexpensive publication manifest/read contract. Remove duplicate restore/manifest discovery only after tracing consumers and proving continuity/freshness behavior.

### P0.5 — lifecycle/resource ownership consolidation
Collapse genuinely redundant readiness/promotion/polling/coordinator mechanisms behind stable idempotent job/read boundaries. Declare cache/resource ownership, lifetime, bounds and invalidation centrally.

### P0.6 — development/operations simplification
Establish one authoritative current-operations source, archive/supersede stale current-state prose, use focused tests during development, one full suite at stable merge gate, and a small set of real end-to-end runtime/browser acceptance journeys.

## Future-facing architecture constraints

Preserve:
- one obvious current publication head without erasing immutable PIT/history;
- bounded Trade/What-If/counterfactual derivative jobs separate from baseline publication;
- shared historical State/event/lineage infrastructure for future Owner Intelligence, League Market, historical analysis and league-history products;
- replaceable artifact payload storage behind stable identity/metadata/payload interfaces;
- private-beta simplicity **and** eventual horizontal web / independent worker scalability;
- accepted analytical/model authority unless direct contradictory evidence proves otherwise.

Do not introduce Redis, queues, microservices, distributed locks, paid infrastructure, or broad storage migration merely for architectural neatness.

## Feature hold

Until Management changes the gate:
- no #375;
- no PIT/history product expansion;
- no Owner Intelligence implementation;
- no unrelated product breadth.

## Current checkpoint

**State:** READY TO BEGIN P0.1  
**Owner:** Work  
**Fallback owner if Work capacity is exhausted:** Implementation, only after Management reassigns ownership.

Before acting, Work must re-read:
- this file;
- the governing P0 directive;
- CURRENT_STATE.md;
- ACTIVE_WORKSTREAMS.md;
- MANAGEMENT_CONTINUITY.md;
- Issue #393;
- current main/live GitHub + Render state.

Then record the first execution checkpoint below.

---

## Execution log

### 2026-10-05 — Management handoff baseline

- Audit: complete and accepted.
- Phase B owner: Work.
- Separate Implementation stream: paused for this program.
- New feature breadth: HOLD.
- Next action: P0.1 baseline and unresolved Dynasty customer-journey trace.
- No P0 corrective implementation has yet been accepted under this workstream record.

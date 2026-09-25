# FSFFL NEXT — Operating Protocol

## Purpose
Chats are execution sessions, not durable project memory. Canonical project state lives in the repository.

## Authority
- Management owns global priority, product direction, scope, and acceptance gates.
- Workstreams own execution within their authorized scope.
- GitHub is implementation-history authority.
- Render is deployment/runtime authority.
- `docs/operations/` is management/workflow authority.
- Governed research artifacts are empirical/model evidence.
- PDFs are optional human-readable snapshots, not the primary AI-to-AI handoff mechanism.

## Outcome ownership with bounded authority
A workstream owns its assigned outcome through acceptance, not merely its next task. Within scope it exhausts presently available actions before returning control.

Intermediate analysis, commits, PRs, CI, deploys, and research artifacts are evidence, not completion unless the directive explicitly defines them as completion.

Before responding, ask: **Is there another authorized action I can perform now that advances the directive?** If yes, perform it.

Follow contradictory live evidence. Do not report an intermediate implementation state as success when runtime or acceptance evidence contradicts it.

## Valid stopping states
- `DIRECTIVE COMPLETE — [WORKSTREAM]`
- `BLOCKED — [WORKSTREAM]`
- `MANAGEMENT GATE — [WORKSTREAM]`
- `TURN COMPLETE — CONTINUATION REQUIRED` only when the current execution turn must end while authorized work remains.

TURN COMPLETE is not DIRECTIVE COMPLETE.

## Product Intent & Design Continuity
All workstreams inherit:
- SEE → UNDERSTAND → INTERACT → DRILL DEEPER
- intelligence before decoration
- progressive disclosure
- league-agnostic behavior as a target requiring explicit validation
- governed authority boundaries
- uncertainty rather than false precision
- no fabricated acceptance probability
- no double counting
- Forecast owns production forecast/uncertainty authority
- Simulation owns outcomes
- Value owns intrinsic/economic value
- Decision owns bilateral legality/economics
- Team Utility is downstream
- Presentation communicates governed truth; it does not invent it.

## Worker startup
A new worker should read, at minimum:
1. `docs/operations/CURRENT_STATE.md`
2. `docs/operations/ACTIVE_WORKSTREAMS.md`
3. `docs/operations/ACCEPTANCE_GATES.md`
4. its workstream file under `docs/operations/workstreams/`
5. relevant authoritative model/product documents named there.

Do not reconstruct completed history unless required by evidence.

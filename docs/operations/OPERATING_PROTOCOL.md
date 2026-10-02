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


## Management-to-worker directive protocol
Management decisions, scope changes, acceptance clarifications, and cross-workstream architectural rules must be persisted in the canonical `docs/operations/` state **before** a worker chat is instructed to act on them.

The normal sequence is:
1. Management reconciles current durable state and writes the decision/directive into the appropriate canonical operations file(s).
2. Management updates any affected cross-workstream index/state file when needed so successors can discover the change.
3. The worker chat receives only a short continuation prompt telling it to read the current canonical operations state, reconcile with its exact durable execution state, and continue under this protocol.
4. Do not use long chat-only implementation briefs as the primary handoff when the directive can be represented in the repository.
5. If a worker needs detail, that detail belongs in the canonical workstream file or a referenced durable artifact, not solely in the chat prompt.

This protocol applies to Management successors as well as current Management. A new Management chat must preserve this repo-first handoff pattern unless the user explicitly requests a different mechanism.

### Minimal worker continuation pattern
`CONTINUE — [WORKSTREAM]. Read the current canonical docs/operations/ state, especially [workstream file]. Reconcile it with your exact durable execution state, do not restart completed work, and continue under OPERATING_PROTOCOL.md to a permitted terminal state.`

## Promotion + durable-record enforcement
A workstream result is not promoted merely because a worker reports success, creates a PR, merges, deploys, or writes a closeout.

### Promotion rule
Before Management or another workstream may treat a result as current accepted truth:
1. the worker must persist the exact execution identity, tests, deployment/runtime evidence, limitations, and requested terminal state in the canonical workstream record and/or a referenced durable acceptance artifact;
2. every acceptance condition named in the directive must have direct evidence, not inferred compatibility;
3. lazy/runtime/product endpoints that matter to the claimed outcome must be exercised through their real hosted path when production acceptance is claimed;
4. Management must reconcile the worker's claimed terminal state against CURRENT_STATE, ACTIVE_WORKSTREAMS, ACCEPTANCE_GATES, live GitHub/Render evidence, and any physical evidence supplied by the user;
5. only then may Management update cross-workstream state from ACTIVE/HOLD to ACCEPTED/DIRECTIVE COMPLETE or advance a dependent workstream.

A terminal phrase inside a worker artifact is a **claim to evaluate**, not self-authorizing promotion.

### Contradiction rule
Any newer physical, hosted, test, or runtime evidence that contradicts a promoted state automatically reopens the narrow affected acceptance layer. Preserve earlier evidence that still holds; do not erase valid lower-layer acceptance merely because a downstream layer failed.

### Record-keeping rule
Every material Management decision, reopened gate, supersession, accepted terminal state, and sequencing change must be persisted in `docs/operations/` before a worker is instructed to act. Worker closeouts must persist exact commit/PR/deploy/test identity and unresolved limitations before returning control.

### Management self-check before advancing the pipeline
Before telling the user or another worker that a gate is complete, Management must ask:
- What exact layer is accepted: model/research, core runtime, derived capability, hosted endpoint, rendered surface, physical device?
- Was that layer actually exercised?
- Is there any contradictory evidence?
- Is the accepted state durably recorded?
- Are dependent workstreams being advanced only on evidence this gate actually proves?

If any answer is no, do not promote.

## Risk-proportionate promotion
The acceptance burden must be proportional to the actual blast radius of a change. Architectural importance alone does not make every change a whole-platform event.

Classify each change before implementation/promotion:

- **Tier A — localized implementation change:** bounded logic/performance/refactor inside an already-proven contract, with no authority, persistence, lifecycle, or public contract change. Required evidence: focused contract/regression tests, ordinary CI, and code review. Hosted/full-platform acceptance is not required unless the changed behavior only exists on the hosted path.
- **Tier B — capability/model change:** adds or materially changes an authoritative capability or model output while preserving platform/runtime contracts. Required evidence: focused capability tests, full CI, review, and one targeted end-to-end acceptance of the affected capability. Do not re-prove unrelated platform layers.
- **Tier C — authority/runtime/persistence change:** changes ownership/authority boundaries, State/Forecast/Simulation/Value identity semantics, cache/persistence/restore/publication behavior, heavy-resource lifecycle, or cross-league/user isolation. Required evidence may include hosted lifecycle, restart/restore, publication identity, memory/resource gates, and affected surface continuity.
- **Tier D — foundation/system change:** cross-cutting architecture or infrastructure change with broad blast radius. Whole-system acceptance is appropriate only here or when direct evidence shows a lower-tier change has broader effects than expected.

Once a boundary has been directly validated and deterministic regressions protect it, those tests are the standing proof of that boundary. Do not manually re-prove unrelated accepted layers for every downstream change. Escalate a change to a heavier tier only when its actual dependencies, runtime behavior, or contradictory evidence justify it.

### Module-internal versus contract-changing work
A change that remains inside an authoritative module and preserves the module's published input/output contract should be validated primarily inside that module. For example, Simulation may change its internal algorithm, batching, bracket execution, sampling implementation, or performance characteristics without requiring Value, Decision, Analytics, Presentation, cross-league lifecycle, or browser acceptance to be re-proven **so long as downstream consumers receive the same contract and semantics they already depend on**.

Broader testing becomes required when the change alters what another module can observe or depend on, including:
- output fields, nullability, units, meaning, timing, or availability;
- model/artifact identity in a way that changes restore/cache/publication compatibility;
- ordering, determinism, replay guarantees, or error behavior exposed across the boundary;
- authority ownership or provenance that downstream modules consume;
- performance/resource behavior that can materially affect shared runtime availability.

The question is therefore not merely "did Simulation change?" but **"did Simulation's contract with the rest of NEXT change?"** If no, keep validation bounded to Simulation plus standing boundary regressions. If yes, test the affected consumers and only those broader layers whose contracts actually changed.

The default posture is **fast by default, heavy when warranted**: small reviewable changes should remain small, useful estimates should expose uncertainty rather than disappear solely because evidence is imperfect, and incident-response safeguards must not become permanent whole-platform ceremony for unrelated work.

## Estimation transparency and management sanity-check
When exact evidence is unavailable, NEXT should prefer the most defensible bounded estimate over unnecessary unavailability, while preserving the distinction between observed fact, deterministic derivation, historical inference, standard-domain fallback, and probabilistic estimate.

Before a newly introduced estimate/fallback is promoted into an authoritative path, the worker must surface it explicitly to Management and record it durably. The report must state, in plain language:
- what exact fact/rule is unavailable;
- what evidence/settings/history are available;
- the proposed estimate or fallback rule;
- why that method is defensible and what alternatives were considered;
- the material outputs that can change because of the estimate;
- how uncertainty/ties/ambiguity are represented;
- what evidence would supersede the estimate later.

Management gets a sanity-check opportunity before promotion when the estimate is materially new or could change user-facing decisions, rankings, probabilities, values, draft slots, or other authoritative outputs. Do not silently convert an assumption into a "verified" league rule. Once Management accepts a recurring standard fallback, later uses of the same unchanged method need provenance and traceability but do not require repeated approval unless the context or consequence is materially different.

Unavailable/UNKNOWN is the last resort: use it only when the missing information makes even a bounded estimate materially misleading or unmodelable. Exact league/provider evidence always supersedes a derived or estimated fallback when it becomes available.

## Private-beta availability discipline
FSFFL NEXT is a live private beta, not only an implementation workspace. Management must preserve the user's ability to exercise the product while deeper work continues.

When a newly deployed regression prevents meaningful product testing:
1. classify it as a **beta-availability incident** and move restoration ahead of nonessential feature breadth, performance tuning, and architectural expansion;
2. restore the smallest charter-correct usable path first;
3. localize failures to the affected capability whenever authority permits — one broken derived capability must not unnecessarily blank unrelated State, Forecast, Value, League, or Market surfaces;
4. if a prior deployed build is materially more usable and does not violate current authority/data safety, prefer rollback or feature-gating over leaving the beta broadly unusable while a larger corrective is developed;
5. preserve a durable last-known-good release/deploy identity and the acceptance layers it actually proved;
6. after usability is restored, continue deeper refactoring/auditing without re-blocking the whole beta unless the architecture change is itself required for correctness/safety.

A charter cleanup may not become an excuse for a multi-day product outage. Conversely, a hotfix may not knowingly preserve the exact hidden coupling that caused the incident when a small clean boundary can remove it immediately.


## Communication standard for Management / user-facing updates
The product owner is **not a software engineer or computer engineer**. All worker chats and Management updates must therefore explain technical work in plain language before or alongside implementation-level detail.

Required communication behavior:
- Start with **what is happening, why it matters, and what the user needs to decide/do**.
- Translate software terms into normal language. If a technical term is necessary, define it the first time in the same response.
- Explain bugs as observable behavior and consequence, not only class/function/lock names.
- Explain proposed fixes in terms of the product behavior they protect.
- When presenting options, describe practical tradeoffs (speed, reliability, accuracy, cost, future flexibility) rather than assuming engineering background.
- Clearly separate **confirmed facts**, **our interpretation**, **remaining uncertainty**, and **the next action**.
- Do not hide important risk behind jargon or oversimplify away a decision the user needs to understand.
- Technical identifiers (SHA, PR, file/function names, exceptions) should support the explanation, not replace it.
- For status updates, prefer concise plain-English summaries with exact technical evidence available underneath when useful.

The user should be able to understand the issue well enough to give informed product/management feedback without needing to understand the underlying code.

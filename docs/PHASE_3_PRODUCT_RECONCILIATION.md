# FSFFL NEXT — Phase 3 Product Reconciliation

Status: **Phase 3 active — Intrinsic Value productization slice implemented for review**  
Roadmap authority: `docs/FSFFL_NEXT_PRODUCT_PRIORITIES.md`  
Starting `main`: `641378af5b4d9bb99eae5ec3aa4ee8cc70118d5b`  
Starting live Render SHA: `f38e2f029a0d9563986635012336434a3f9beb63`

This document records actual product state against the canonical roadmap. It does not replace or silently rewrite that roadmap.

## Reconciled deployment state

At the start of this workstream, GitHub `main` contained the merged FSFFL Intrinsic Value v1 work from PR #133 (`641378af...`). The private-beta Render service was still serving `f38e2f...`, the prior product build. Therefore three states must remain distinct:

1. **merged to main** — Intrinsic Value v1 is authoritative repository behavior;
2. **available in the current live beta** — not yet true at the start of this slice because Render lagged `main`;
3. **customer-facing/productized** — not true before this slice even on `main`, because the Intrinsic API had no presentation surface.

Open PR overlap at the start:

- PR #131 — research-only multi-year intrinsic work; draft/unmerged; no production authority and no overlap with this UI slice.
- PR #132 — roadmap documentation alignment; open and based on older `main`; no product implementation overlap.
- no open performance PR.

## Phase 3 surface matrix

| Surface | Status before this slice | What exists today | Exact unfinished gap | Gap type | Phase 3 exit impact | Scope |
| --- | --- | --- | --- | --- | --- | --- |
| Home — “What should I care about right now?” | **MOSTLY COMPLETE** | Scan-first league/team attention view, competitive state, expected wins/playoff outlook, opportunity handoff, league comparison | Some older generic Value language remains in the beta and useful beta discoveries are not yet captured as a durable product-learning loop | UX / product explanation | Medium | Small–medium |
| Franchise — “What is actually driving my franchise?” | **PARTIAL** | Strong diagnosis, position strengths/weaknesses, competitive outlook, resilience, roster, picks, core assets | Governed Intrinsic Value existed only in backend; old generic “FSFFL Value” could be mistaken for it; no explanation of Market vs Intrinsic | Product explanation / UX | **High** | Medium |
| League — “How do these teams differ?” | **MOSTLY COMPLETE** | League comparison, team structure, positional map, age/depth/future-capital context | League Market Value is not production-ready; older cardinal/value terminology remains separate from the new Intrinsic coordinate | Backend evidence / UX | Medium | Medium later |
| Opportunities / Trade Finder — “Where is there something worth doing?” | **MOSTLY COMPLETE** | Market Focus, opportunity detail, feasibility, credible package handoff, server-owned search and cached repeated workspace | Cold first workspace remains ~15s; Intrinsic-vs-Market disagreement is not yet used as a discovery lens | Performance / product intelligence | **High** | Medium–large |
| Trade Center — “What happens if I make this deal?” | **MOSTLY COMPLETE** | Bilateral package analysis, main upside/risk/next step, changed-roster simulation, counter/frontier workflow, advanced detail secondary | Cold analyze ~13s and fresh 50k simulation ~85s; League Market remains unavailable | Performance | **High** | Large |
| Behavioral Intelligence — “How should I understand and approach this owner?” | **MOSTLY COMPLETE** | Customer-facing observed owner history, trade shapes, position flows, counterparties, provenance; unavailable inference explicitly gated | Context-controlled owner preference, proposal fit, owner-adjusted value and calibrated acceptance remain blocked on point-in-time evidence | Evidence / backend | Medium | Large, evidence-dependent |
| Team/Owner-Adjusted Value — “What changes contextually without mutating universal truth?” | **BLOCKED** | Team Utility is separate and Decision uses franchise context; Behavioral surface explains the intended boundary | No governed owner-adjusted asset coordinate is production-ready; Behavioral correctly refuses to fabricate one | Evidence / backend | Medium | Large, evidence-dependent |
| Performance / commercial latency | **PARTIAL** | Reuse/caching makes repeated Market workspace ~0.13–0.18s and an exact repeated simulation ~1.2s in observed beta usage | Cold Market ~15s, Trade analysis ~13s, fresh 50k simulation ~85s; historical frontier observation ~331s | Performance | **High** | Large |

## Intrinsic Value productization audit — before this slice

### Where was Intrinsic visible?

Nowhere in the customer-facing UI.

PR #133 added the governed `/api/value/intrinsic-v1` route and production model/runtime integration, but no frontend module consumed the endpoint. The private beta instead showed an older generic **“FSFFL Value”** or cardinal/provisional beta coordinate next to Broad Market evidence. That older coordinate is not FSFFL Intrinsic Value v1.

### Was there a customer-facing explanation?

No. There was no onboarding copy, legend, tooltip or customer-facing comparison explaining:

- Broad Market Value;
- FSFFL Intrinsic Value;
- League Market Value;
- Team Utility.

A product owner could accurately say, “Intrinsic exists, but I do not know where it lives in the UI.” It therefore did **not** satisfy the Phase 3 productization standard.

### Architecture status before this slice

- **Broad Market Value:** production evidence exists and is customer-facing, commonly as market percentile.
- **FSFFL Intrinsic Value:** production backend exists on `main`; not live on the starting Render SHA; not customer-facing.
- **League Market Value:** not production-ready; must remain explicitly unavailable.
- **Team Utility:** governed and customer-facing in Franchise/Trade Center context; conceptually separate from universal value.

No UI should collapse these coordinates into one apparent number.

## Selected next slice

**Productize FSFFL Intrinsic Value as a Franchise “Value Lens.”**

### Why this beat the alternatives

1. It directly closes a Phase 3 exit-gate gap: important governed intelligence already exists but is not understandable or usable by a customer.
2. It fixes a current conceptual risk: the beta already displays an older generic “FSFFL Value,” so adding Intrinsic without clear separation could create false equivalence.
3. Trade Center already has a strong bilateral decision room and progressive disclosure.
4. Behavioral observed-history intelligence is already visibly online and responsibly gates unsupported inference.
5. Performance remains a major blocker, but the cache/reuse layer already makes repeated use dramatically faster; the remaining cold-path problem is a coherent next slice rather than a reason to leave the new authoritative value coordinate invisible.
6. No open PR duplicates this product work.

## What this slice implements

The Franchise workspace gains a fourth tab: **Value Lens**.

The first read teaches the four-coordinate architecture in plain language:

- **Broad Market Value** — what the wider dynasty market prices;
- **FSFFL Intrinsic Value** — what FSFFL’s multi-year football economics imply above lineup replacement;
- **League Market Value** — explicitly unavailable until governed league-specific pricing exists;
- **Team Utility** — separate franchise/context value, with users directed to Franchise Diagnosis and Trade Center.

The Value Lens then:

- lazily requests `/api/value/intrinsic-v1` only when opened;
- shows the governed raw Intrinsic coordinate, not the older beta/cardinal value;
- surfaces confidence and model/provenance details secondarily;
- explains the largest horizon contribution using fields already returned by the authoritative Intrinsic estimate;
- compares Intrinsic and Broad Market only through percentile rank as a **presentation aid** because the raw scales differ;
- labels material disagreement as “FSFFL higher,” “Broad market higher,” or “Roughly aligned”;
- treats disagreement as a reason to investigate, not an automatic buy/sell command;
- explicitly states that League Market and Team Utility still matter before action;
- handles missing/stale/unavailable Intrinsic evidence without substituting another coordinate;
- provides direct handoffs to Market and Trade Center;
- uses mobile-specific single-column coordinate cards and compact player disclosure rows.

The existing generic “FSFFL Value” is explicitly identified inside the explainer as a separate older beta coordinate rather than silently relabeled as Intrinsic.

## Performance impact of this slice

No new API request is added to Home or Franchise first paint.

The Value Lens JS/CSS are small static assets. The governed Intrinsic endpoint is called only after the customer opens the tab. The endpoint uses the versioned Forecast/Value runtime added by PR #133; it performs no request-time raw historical scan and introduces no external provider call.

Observed beta latency that remains outside this slice:

- first Market workspace: ~15 seconds;
- cached repeated Market workspace: ~0.13–0.18 seconds;
- Trade Center analyze: ~13 seconds;
- fresh 50,000-run changed-roster simulation: ~85 seconds;
- exact repeated simulation after durable reuse: ~1.2 seconds.

## Mobile / unavailable-state design

The Value Lens uses a dedicated <=680px layout:

- coordinate cards stack to one column;
- roster comparison rows become two-column scan blocks;
- the signal occupies a full row;
- action buttons become full-width touch targets;
- Franchise tabs remain horizontally scrollable rather than shrinking labels beyond usability.

If Intrinsic cannot be produced, the lens states that it is unavailable and explicitly refuses to substitute Broad Market, the older beta Value, League Market or Team Utility.

## What remains after this slice

Phase 3 is **not** complete.

Highest-impact remaining gaps:

1. **Cold-path commercial latency** — first Market load, Trade analysis and especially fresh 50k Simulation are too slow for repeated voluntary commercial use.
2. **Intrinsic disagreement discovery beyond Franchise** — once the Value Lens is validated in beta, Trade Finder can use governed Market-vs-Intrinsic disagreement as a discovery/explanation dimension without changing Search/Value authority.
3. **League Market Value** — unavailable until a governed league-specific pricing model exists; do not fabricate.
4. **Owner-adjusted value / calibrated proposal fit** — blocked on appropriate point-in-time Behavioral evidence.
5. **Durable beta-learning record** — Phase 3 exit requires documenting useful discoveries from real beta usage, not just shipping screens.

## Recommended following Phase 3 slice

**Commercial cold-path latency: fast useful first response for Market/Trade Center while preserving full-fidelity 50,000-run Simulation and deeper search.**

Focus specifically on the remaining fresh-work paths rather than duplicating the already-merged reuse/cache work:

- first Market workspace (~15s);
- initial Trade analysis (~13s);
- fresh changed-roster Simulation (~85s);
- deeper frontier work only after a useful first answer is visible.

Prefer versioned reusable artifacts, progressive results, stale-while-revalidate where safe, and background completion of expensive evidence. Do not reduce Simulation fidelity merely to make the benchmark faster.

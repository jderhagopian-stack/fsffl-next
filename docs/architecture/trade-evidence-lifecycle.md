# Trade evidence lifecycle

Trade Center presents server-owned bilateral analysis, Simulation and counter search.
A response belongs to the package that requested it, for the selected league,
managed team, canonical State and published generation. Changing any of those
inputs invalidates pending presentation. Editing away and back also invalidates
the earlier request. For repeated requests of the same kind, only the newest may
render results, errors or completion controls. Independent Simulation and counter
requests may still complete independently for the same unchanged draft.

The existing Trade UI state owns these request markers. They do not cancel server
computation, create an economic cache, or alter Decision/Simulation authority.
The progressive Analyze sequence retains its own existing stage checks and uses
the shared context identity. Counter responses now expose `state_id_before`, as
analysis and Simulation already do. The browser requires matching State and team
identities before presenting those results.

Opportunity handoffs retain the exact package and can reuse its completed
Simulation only when its own State and teams match the current context. Trade
Center still checks canonical ownership after its browser load completes. A
pending load is joined for the same context; a response for an earlier context
cannot replace a newer browser. Handoffs await the actual load rather than timing
out a polling loop. An earlier handoff cannot clear a later draft.

Regression evidence:

- `tests/browser/trade_evidence_lifecycle.cjs` executes the production scripts
  against delayed/reordered transports, changed drafts/teams/States/generations,
  wrong-State responses, quick/deep counters, browser-load races, slow handoffs,
  and valid artifact reuse without duplicate Simulation work.
- `tests/test_trade_journey_api.py` exercises real browser, analysis and counter
  routes using a small synthetic canonical State. Missing Simulation evidence
  remains unavailable; all four POST routes reject incorrectly owned assets;
  the canonical State remains unchanged.

Opportunity enhancements install when the lazy Opportunity module loads, rather
than assuming its globals exist at initial page load. The served classic-script
syntax regression covers the shell and Opportunity module, including the corrected
player-stat row builder. A failure of the final Simulation step preserves the
completed roster analysis and explains which stage could not finish.

These bounded tests do not certify an authenticated hosted browser session or
full production economic outcomes. They preserve those existing authorities and
cover the presentation boundary changed here. No scoring, forecasts, intrinsic
values, acceptance models, persistence or service plans change.

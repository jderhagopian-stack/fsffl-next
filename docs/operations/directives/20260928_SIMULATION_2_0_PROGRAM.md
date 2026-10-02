# 2026-09-28 — Simulation 2.0 Program

## Status
**MANAGEMENT ACCEPTED — NEAR-TERM FOUNDATION AFTER RUNTIME STABILIZATION AND IN-SEASON FORECAST**

Simulation 2.0 is a foundational upstream program. It is not a presentation feature and must remain inside the canonical authority chain:

Data -> Point-in-Time State -> Forecast -> **Simulation** -> Value / Team Utility / Decision consumers

Simulation owns competitive outcome distributions. It does not own market prices, utility preferences, trade acceptance, or presentation conclusions.

## Sequence
Do not start implementation until runtime / atomic-publication acceptance closes.

Near-term order:
1. Runtime stabilization terminal acceptance.
2. In-season Forecast: Actual YTD + governed third-party ROS, with PIT capture.
3. **Simulation 2.0.**
4. Origin-aware draft-pick Value.
5. Long-Term Intrinsic.
6. PIT historical market evidence.
7. League Market / Owner Intelligence.
8. Trade Decision.
9. Market / Search optimization.
10. Intelligence-surface exploitation.

Simulation 2.0 should be designed while in-season Forecast is being finalized, but production authority changes wait until that Forecast contract is stable.

## What comes forward from the legacy Simulator
Re-derive the capability; do not blindly port old code.

The prior simulator's high-value behaviors to preserve or re-establish include:
- actual league schedule and division structure;
- weekly player outcome distributions rather than season-total-only math;
- week-specific legal lineup optimization;
- bye-week handling;
- explicit empty-lineup-slot behavior when a roster cannot legally fill a position;
- player availability / missed-game uncertainty with legal bench substitution;
- historical player/position weekly volatility with appropriate shrinkage;
- playoff qualification, seeding, byes and league-specific bracket rules;
- expected wins and expected points;
- finish / seed distributions;
- playoff, first-place, division, bye and championship probabilities where league rules support them;
- deterministic/replayable simulation seeds;
- governed scenario / counterfactual competitive-outcome deltas;
- replayable unusual-outcome / "Multiverse" examples, including rare plausible seasons and notable extremes.

Legacy provisional same-NFL-team correlation behavior should be **re-derived and tested**, not copied as unquestioned truth.

## Simulation 2.0 — current-season canonical engine
The current-season simulation should operate week by week.

Completed NFL/fantasy outcomes are immutable facts. Future weeks are simulated.

Inputs:
- exact PIT League State;
- actual standings / completed matchups;
- actual NFL/fantasy production already completed;
- governed remaining-season Forecast distributions;
- actual remaining fantasy schedule;
- league lineup/scoring/division/playoff rules;
- known byes and governed availability evidence.

Core behavior:
- optimize a legal lineup for each relevant team/week from the available roster;
- sample player outcomes from governed weekly distributions;
- model absence/availability separately from conditional healthy production where authority supports it;
- perform legal bench substitution;
- score weekly fantasy matchups;
- update standings/tiebreakers;
- seed and play the actual league playoff structure;
- preserve the entire simulated season path for diagnostics when useful.

Canonical production output remains **50,000 Monte Carlo seasons** unless a separate convergence study earns a lower/adaptive authority standard.

## Output contract
At minimum:
- expected remaining wins;
- expected final wins;
- expected / median finish;
- full finish-position distribution;
- playoff probability;
- first-place probability;
- division probability where applicable;
- bye probability where applicable;
- championship probability;
- expected points / scoring distribution;
- remaining-schedule strength/effect where defensible;
- uncertainty / Monte Carlo error diagnostics;
- exact State + Forecast + simulation-model identity;
- deterministic replay seed / run identity.

Preseason, current and forward outlook must remain distinct:
- preseason = frozen PIT pre-Week-1 State + Forecast;
- current = actual results to date + governed remaining-season simulation;
- forward = remaining games only from today's State.

## Team-of-origin future pick simulation
Simulation 2.0 also owns the football-outcome distribution needed to value future rookie picks.

For every pick:
- season;
- round;
- origin team;
- current owner;
- actual league draft-order rules.

Near-horizon pick-slot simulation should use governed football evidence about the origin team rather than generic early/mid/late labels.

Outputs should include:
- probability by exact slot where feasible;
- expected slot / percentile;
- early/mid/late probabilities only as summaries;
- uncertainty that widens with horizon;
- origin-team / State / Forecast provenance.

For farther horizons, use a separate calibrated multi-season team-trajectory contract if necessary. Do not force current-season mechanics to pretend they are precise three years forward.

Draft-order simulation must follow FSFFL rules exactly (for example regular-season finish, Max PF, playoff finish or other configured rules) rather than assuming generic NFL draft order.

## Counterfactual / scenario Simulation
Simulation should accept authorized alternate States from downstream Decision/Counterfactual consumers and return **competitive-outcome deltas only**.

Examples:
- trade roster A/B;
- add/drop;
- injury/availability scenario;
- alternate starter/roster composition;
- future draft-capital changes when they alter modeled roster evolution.

Outputs may include delta expected wins, playoff odds, title odds, scoring distribution and future pick-slot distributions.

Simulation must not decide whether the transaction is "good", estimate acceptance probability, or own trade economics.

## Multiverse / explainability
Bring forward the legacy replayable-outcome capability.

Persist or sample representative simulated worlds such as:
- median / expected-like season;
- plausible upside and downside seasons;
- unusual but credible outcomes;
- extreme tails;
- superstar player season/week;
- biggest upset/blowout;
- strong team missing playoffs;
- low-seed / rare champion.

Each example should carry simulation ID/seed and rarity context. This is explanation, not a second probability model.

## Performance architecture — do not rebuild the slow Python engine
The old efficient path demonstrated that 50,000-run simulation does not inherently require minute-long sequential execution. Simulation 2.0 should be designed around batched/vectorized execution from the start.

Required optimization directions:

### 1. Precompile static state
For one published State/Forecast generation, compile once:
- player -> team arrays;
- weekly schedule arrays;
- roster eligibility;
- lineup-slot constraints;
- bye masks;
- league scoring transforms;
- playoff/tiebreaker structure;
- forecast distribution parameters.

Do not rebuild Python objects inside the Monte Carlo inner loop.

### 2. Vectorized / batched worlds
Generate player/team/week outcomes in arrays and process many seasons at once. Use NumPy-style vectorized scoring, batched standings and vectorized playoff progression where possible.

Python loops should orchestrate batches, not own every player x week x season operation.

### 3. Reuse optimized lineups
Cache deterministic or state-conditioned lineup structures where the inputs have not changed. Do not solve the same lineup problem 50,000 times if the legal choice set is identical.

Where availability changes require substitutions, use precomputed depth/eligibility structures and fast substitution rather than rebuilding optimization from scratch.

### 4. Common Monte Carlo worlds for comparisons
For counterfactual A vs B, reuse common random numbers / simulated worlds where mathematically valid. This reduces noise in **deltas** and avoids recomputing unrelated teams.

A trade affecting two teams should not require rebuilding all league inputs from zero.

### 5. Dependency-based selective recomputation
Cache baseline compiled state and recompute only affected teams/weeks/components when an alternate State changes a bounded dependency.

### 6. Persist canonical results
A completed canonical 50,000-run result belongs to the exact State+Forecast+model identity and should be persisted/reused. Ordinary page reads never rerun Simulation.

Prewarm/restore canonical Simulation on startup and preserve last-good published output through reconciliation under the atomic-publication contract.

### 7. Progressive scenario computation
Keep **canonical current-state production** at governed 50,000-run fidelity.

Interactive scenario consumers may use explicitly labeled non-authoritative stages:
- very small screening batch for broad search;
- ~2,500-5,000-run provisional comparison;
- 15,000-50,000 confirmation for finalists / close decisions.

Deeper results replace provisional outputs. Do not present screening probabilities as canonical Simulation authority.

### 8. Convergence study
Run a separate empirical study across roughly 5,000-100,000 simulations to measure convergence of:
- expected wins;
- finish ranks;
- playoff / title probabilities;
- pick-slot distributions;
- scenario deltas;
- decision-sign stability.

The current 50,000-run standard remains authoritative until evidence supports a different adaptive rule.

### 9. Memory discipline
Batch dimensions to stay safely below hosted memory limits. Reuse numeric arrays, avoid retaining all raw worlds when aggregate statistics suffice, and retain only selected replayable Multiverse worlds / diagnostics.

Do not solve performance by uncontrolled parallel process multiplication on the free-tier host.

## Weekly distributions and correlation research
Do not use a generic season-total variance hack.

Re-derive:
- position/player weekly volatility;
- player-history shrinkage;
- role/usage-conditioned variance if supported;
- same-NFL-team / game-environment covariance;
- opponent/matchup effects;
- injury/availability variance.

Only promote correlation or matchup effects that improve PIT calibration. Independence is an explicit fallback, not hidden truth.

## Historical / PIT validation
Validate Simulation 2.0 against archived or reconstructed PIT states where feasible:
- standings calibration;
- scoring distribution calibration;
- playoff/title probability calibration;
- pick-slot probability calibration;
- scenario-delta stability;
- week-by-week probability movement.

Do not evaluate a historical forecast using information unavailable at that date.

## Promotion gates
Before Simulation 2.0 becomes production authority:
1. legacy capabilities required above are represented or explicitly deferred;
2. 50,000-run outputs match contractual invariants;
3. performance is materially better than the current sequential path;
4. deterministic replay works;
5. persistence/restart/publication identity is exact;
6. PIT calibration is documented;
7. Work red-team finds no P1/P2 authority/performance defect;
8. hosted acceptance passes without violating memory/foreground latency;
9. physical product surfaces show one coherent published Simulation generation.

## Non-goals
- no Market prices inside competitive-outcome generation;
- no Team Utility preferences inside Simulation;
- no fabricated trade acceptance probabilities;
- no arbitrary future-team strength weights;
- no reduction of current 50,000-run authority merely for speed;
- no port of legacy code without revalidation.

## Management clarification — league-governed postseason authority (2026-10-01)

The generic 2/4/6/8-team bracket path is an interim capability only. Final Simulation 2.0 postseason outputs must derive from each exact League State's governed postseason rules; the FSFFL league's weeks, round count, bye structure, seed behavior, or bracket shape are never global defaults.

Canonical League State / LeagueRules must retain, or explicitly mark unknown/unsupported, regular-season end and playoff start, qualifying-team count, playoff round count and week map, bye count and seeds, seeding/tiebreak and reseeding policy, matchup graph, championship matchup timing, and any league-specific scoring/tiebreak behavior that materially changes advancement. Normalize provider data into this provider-neutral contract; the Simulation kernel consumes only canonical rules. A missing/unsupported material rule makes bracket/championship probabilities unavailable with a reason. It must never make stale or assumed output look ready.

Championship probability is the ordinary Simulation estimate when either the exact provider bracket is observed or governed league settings plus a well-supported standard bracket rule defensibly determine the graph. Preserve those two authorities as internal provenance (`provider_observed_exact` or `settings_derived_standard`); do not create a separately labeled or visually downgraded “provisional” product metric. Keep playoff qualification independently available whenever its rules are known. Withhold championship probability only when material ambiguity or unsupported/custom structure prevents a defensible bracket.

Fixtures must prove materially different league structures, including different qualifier counts, start weeks, bye structures, and a non-FSFFL bracket. A configured structure is executable only when every material rule is supported; otherwise preserve it as known configuration and fail closed for affected outputs. This clarifies, and does not reorder, the accepted capability sequence in this directive.

## 2026-10-02 management correction — item 5 draft-order fallback

For team-of-origin future-pick distributions, use explicit governed league draft-order rules first. When no explicit league rule evidence is available for the target draft season, do **not** fail closed solely because the league-specific bylaw is unavailable; use the governed standard fallback below and retain derived provenance.

Standard fallback:
- non-playoff order: worse regular-season record, then resolvable head-to-head among tied teams, then lower regular-season Points For;
- playoff order: round eliminated first; within the same elimination round use the same regular-season tiebreak sequence;
- championship runner-up drafts immediately before the champion, with the champion last;
- placement/consolation games affect draft order only when explicit league rule evidence says they do;
- if the governed sequence still leaves an exact tie, preserve uncertainty across unresolved tied slots rather than inventing a hidden final tiebreak.

An explicit but unsupported custom rule remains explicit/unavailable and must not be silently replaced by the fallback. Preserve `explicit_league_rule` versus `derived_standard_fallback` provenance. Remove FSFFL-specific Max-PF and placement-game assumptions from generic Simulation authority.


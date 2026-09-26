# FSFFL NEXT — Product Roadmap

## Current parallel critical paths

### Foundation / league-agnostic path
1. K/DST architecture + evidence-independent implementation: **COMPLETE / MERGED**.
2. 2026 K/DST late-start/provisional exception work: **SEPARATE ACTIVE/EXTERNAL-EVIDENCE TRACK** under its persisted contracts.
3. Cross-league scoring-rule / Forecast-input audit: **DIRECTIVE COMPLETE — RESEARCH**.
   - 89-coordinate/rule-semantic registry;
   - 48-row platform coverage matrix;
   - primary-source ledger;
   - provider/historical/scoring-engine gap analysis;
   - deterministic fixtures;
   - implementation-ready handoff.
4. Scoring Coverage Stage 0 + Stage 1: **MANAGEMENT GATE — PLAN READY, NOT AUTHORIZED**.
   - canonical registry/rule/capability contracts;
   - compatibility compilation for existing scoring;
   - raw provider superset preservation;
   - zero new production authority.
5. Later scoring expansion, each separately gated:
   - direct 2PT/returns/common event coordinates;
   - nonlinear per-game milestone distributions;
   - attempts/completions/carries/first downs/targets/returns;
   - IDP subject/Forecast family;
   - advanced long-play/punter/head-coach/conditional rules.
6. League-agnostic validation must prove materially different scoring families without weakening evidence authority before the product claims broad league-agnostic scoring support.

### Product / Market path
1. Prior physical-iPhone Market acceptance: **FAILED / NOT ACCEPTED** as a product gate.
2. Market / Trade Discovery Architecture Review: **COMPLETE**. Handoff: `artifacts/architecture/market_trade_discovery_20260924/IMPLEMENTATION_HANDOFF.md`.
3. Management acceptance of revised Opportunity + Market contract: **COMPLETE**.
4. Bounded Market/Search/North Star implementation: **IMPLEMENTATION ACCEPTANCE COMPLETE — PR #220**. Handoff: `artifacts/implementation/market_discovery_north_star_20260925/IMPLEMENTATION_HANDOFF.md`.
5. Merge/deploy PR #220 and repeat physical-iPhone/Safari Market acceptance: **NEXT GATE**.
6. Home × Franchise redundancy/information-hierarchy audit.
7. Trade Center expansion only after discovery/search order of operations is settled.

## Forecast authority boundary
Implemented contracts and research harnesses do not themselves create production K/DST forecasts. No one-source calibration, offensive-position fallback coefficient, aggregate-source double counting, guessed D/ST bucket math, or current/post-opener data backdated as preseason is permitted.

## Why Market architecture moved forward
The shipped Market shell established useful concepts, but physical-iPhone evidence showed:
- a supposedly high-signal For You feed can contain repeated target neighborhoods and packages still requiring substantial evaluation;
- discovery is spending user attention before enough cheap economic/bilateral screening and diversity control;
- Player Board and Free Agents can be unavailable while global readiness reports 7/7;
- Market is denser and less immediately readable/navigable than the accepted North Star surfaces.

This is not treated as presentation polish alone.

## Trade Discovery principle
Simulation should evaluate shortlisted trades, not perform broad discovery.

Working sequence:
`League State → strategic needs/opportunity hypotheses → candidate assets/counterparties → broad cheap package generation → economic screening → bilateral plausibility → clustering/diversity → high-signal opportunity frontier → targeted Decision/Simulation → deeper analysis`

Simulation is a microscope, not the searchlight.

## Product principle
For You should surface a deliberately small number of genuinely distinct strategic opportunities, not merely raw packages Search can construct. The product must be able to explain why each item deserves scarce user attention before asking the user to enter a deep evaluation.

## League-agnostic validation
“League-agnostic” remains a target, not a fully proven property. Forecast implementation and later lifecycle validation must exercise configurations unlike the original FSFFL league without weakening evidence authority.


## Accepted-for-review Market architecture
The completed review proposes:
- strategic hypotheses before targets/packages;
- Opportunity as the scarce-attention object;
- Candidate Paths as concrete acquisition routes;
- raw package neighborhoods as subordinate variants;
- cheap Decision-owned economic screening and a bounded pre-Simulation bilateral screen;
- family clustering/dominance pruning before feed ranking;
- deterministic diversity selection instead of package-row lane diversity;
- maximum four For You opportunities in the private beta, with no duplicate exact target;
- zero broad changed-state Simulation calls;
- Core 7/7 readiness separated from Market consumer readiness;
- opportunity-first For You, progressive Trade Finder, read-only Player Board, and roster-fit-first Free Agents.

Management accepted these policies on 2026-09-25; PR #220 implements them and has satisfied implementation-level automated acceptance.

## Near-term infrastructure/performance priority — Simulation kernel efficiency
Following completion of current reliability acceptance and the immediate Market foreground-latency corrective, prioritize a dedicated general Simulation efficiency program before lower-priority product breadth.

The product already benefits from persistent exact Simulation reuse, coalescing and progressive delivery, but fresh canonical 50,000-run Simulation remains a core latency dependency for intelligence refresh and deep scenario/trade analysis. The next phase should optimize the engine itself under the existing authority contract, beginning with exact-output-preserving software improvements and only escalating to statistically equivalent/non-bit-identical numerical architecture under a separate Management gate.

## Simulation Multiverse / alternative-futures product
Recover the original FSFFL Multiverse concept after the core Simulation engine is modernized.

Purpose: preserve the richness that disappears when thousands of modeled seasons are reduced to expected wins and probabilities. Surface auditable, model-consistent alternative futures such as surprise breakouts, dominant/collapse seasons, unlikely playoff paths, high-seed champions and historically interesting scoring outcomes.

Product rule: clearly separate **expected outcome** from **interesting possible universe**. Extreme-of-N values are sample-size dependent, so pair them with rarity/percentile/frequency context and avoid presenting them as forecasts.

Prefer deriving the Multiverse catalog from the same canonical Simulation pass with replayable simulation IDs/provenance. Potential surfaces include preseason Reports, Home, League Atlas, team pages and shareable league-story cards.

## Legacy FSFFL capability harvest — preserve proven primitives, not legacy authority
A structured review of `jderhagopian-stack/sleeper-league-data` identified several predecessor capabilities worth preserving as reference implementations or future infrastructure. Do not port legacy authority wholesale; recover concepts only under NEXT's current Data → State → Forecast → Value → Decision → Search/Optimization → Analytics/API → Presentation chain.

High-value harvest targets:

1. **Vectorized Simulator reference.** The predecessor NumPy-based Simulator performed 50,000 preseason universes with batched player draws, scoring, matchup outcomes and playoff evaluation. One archived 2026 snapshot records 50k in 6.286s in its environment. Use this as evidence that NEXT's sequential Python kernel has substantial software-efficiency headroom, not as an apples-to-apples hosted benchmark.
2. **Point-in-time historical state provider.** The old system could reconstruct exact pre-transaction rosters, taxi/reserve, pick ownership and FAAB by reversing completed Sleeper transactions. Preserve the principle of historical FACT reconstruction separately from hindsight or decision models.
3. **Historical analysis with hindsight isolation.** At-the-time trade evaluation and later realized outcomes were explicitly separate layers. Retain this boundary for future historical trade grading/backtesting.
4. **Asset lineage graph.** The predecessor retained a 774-node / 1,434-edge player-and-pick lineage graph, including pick-to-player draft conversions and explicit "mixed inputs / attribution unknowable" labels for multi-asset trades. This is strong infrastructure for trade genealogy, pick conversion history and shareable league stories.
5. **Player franchise history.** The predecessor retained 393 player-history records with acquisition events, reacquisitions and unique FSFFL-team counts. Preserve/migrate this historical identity for Record Book and player-history products rather than recomputing ad hoc.
6. **Simulation snapshot archive.** The predecessor archived dated Simulator outputs with model/input/runtime provenance. NEXT should preserve time-series intelligence snapshots so users can compare preseason/current/weekly beliefs and replay how the league outlook changed.
7. **Simulation-sensitivity gating.** The old Opportunity Engine could rerun candidate utility across multiple seeds and withhold sign-unstable trades from headline actionability rather than hiding uncertainty. Consider this after current latency work, using NEXT Decision authority and without fabricating acceptance probability.
8. **Context-normalized Owner Intelligence.** Behavioral Intelligence research adjusted observed owner choices for roster need and league opportunity environment, used leave-one-manager-out priors, and shrank sparse samples toward neutral. Reuse methodological ideas only as descriptive Owner Intelligence; do not convert them into unsupported acceptance probabilities or Forecast inputs.
9. **Validated position-specific matchup signal.** Old opponent-adjustment research retained small RB/TE effects after holdout but neutralized QB/WR when evidence failed. The lesson is methodological: plausible football features should be position-specific and promoted only after chronological holdout evidence.
10. **Multiverse / media-guide / Record Book storytelling.** The predecessor turned governed analytics into league-specific stories and publications without giving Presentation new decision authority. NEXT should recover this after core reliability/performance, using current North Star interaction patterns rather than legacy report-first UX.

Explicit non-goals:
- do not restore legacy GM/Value/Trade authority;
- do not port hand-set heuristics merely because they were once production;
- do not let historical realized outcomes leak into point-in-time evaluation;
- do not let owner behavior or market behavior enter universal Forecast;
- do not prioritize Record Book/media-guide breadth ahead of current reliability, Market responsiveness and Simulation performance.

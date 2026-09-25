# FSFFL NEXT — Acceptance Gates

## Performance / intelligence lifecycle
Not complete until evidence demonstrates:
- durable last-good restoration;
- intentional mid-refresh restart behavior;
- stale-job reconciliation;
- truthful readiness state;
- no inappropriate automatic heavy refresh after restart;
- fresh 7/7 completion;
- atomic promotion;
- another restart surviving with the promoted last-good bundle intact;
- acceptable foreground latency during compute;
- Home, Franchise, and Market populated with governed evidence for the correct active league;
- no cross-league intelligence contamination.

Current status: **MANAGEMENT GATE / blocked upstream by unimplemented Forecast authority for the newly connected K/DST league.**

## Forecast K/DST research
**Status: COMPLETE — RESEARCH.**

Research acceptance is satisfied by the persisted contract and evidence in:
- `docs/operations/workstreams/RESEARCH.md`
- `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`

The completed research provides:
- K as a distinct Forecast problem;
- D/ST as a team-unit fantasy asset;
- provider/raw-data inventory and provenance constraints;
- historical evidence availability and gaps;
- league scoring translation requirements;
- uncertainty/calibration approach;
- fail-closed behavior when evidence is insufficient;
- compatibility with existing Forecast authority and two-source governance;
- synthetic fixtures for no K/DST, K-only, D/ST-only, K+D/ST, and evidence-deficient cases;
- explicit separation of K/DST modeling from new-league bootstrap;
- Forecast → Value → Simulation → Decision/Search migration boundaries;
- implementation sequence and acceptance tests.

No K/DST production coefficient or model authority is promoted merely by this research completion.

## New-league Forecast bootstrap research
**Status: COMPLETE — RESEARCH.**

The contract defines governed behavior for a league first connected after preseason:
- use an immutable league-agnostic annual raw Forecast snapshot when it exists;
- otherwise permit only an evidence-preserving migration of genuinely retained point-in-time raw Forecast evidence;
- preserve original timestamps, source identity, hashes, and lineage;
- do not refetch current pages and backdate them as preseason;
- fail closed on target scoring rules not supported by the retained raw evidence;
- when qualifying preseason evidence does not exist, surface preseason evidence as unavailable while permitting separately authoritative current-forward Forecast where valid.

## Forecast K/DST implementation gate
**Status: ACTIVE — PR #215 UNDER ACCEPTANCE VALIDATION.**

Management has authorized the bounded implementation. Stage 1 contracts/scoring and a non-promoting Stage 2 research harness are implemented in PR #215, but production K/DST authority is not yet accepted.

Implementation is not fully accepted until evidence demonstrates:
- canonical K and D/ST subject identity; **implemented in PR #215, pending merge acceptance**;
- active-rule-complete league scoring; **implemented for the governed contract in PR #215, with active missing `fum_lost` fail-closed**;
- no silent missing-metric zero substitution, including `fum_lost`;
- source health and independence at the relevant metric/rule coordinate;
- separate promoted K/DST season-error and weekly-volatility evidence;
- distributional treatment for D/ST scoring bands; **contract/scoring implementation present; empirical provider evidence still gated**;
- annual snapshot/bootstrap migration behavior;
- downstream compatibility without Value/Simulation/Decision inventing Forecast truth;
- regression-clean behavior for the original no-K/DST league;
- successful lifecycle acceptance for the newly connected league.

## Product principle
Do not make a red gate green by weakening model authority, fabricating projections, backdating evidence, or hiding unsupported assets in Presentation.


## Market / Trade Discovery architecture review
**Status: MANAGEMENT GATE — ARCHITECTURE REVIEW COMPLETE.**

Implementation-ready handoff:
- `docs/operations/workstreams/MARKET_DISCOVERY.md`
- `artifacts/architecture/market_trade_discovery_20260924/IMPLEMENTATION_HANDOFF.md`

Architecture review evidence demonstrates:
- the repeated-neighborhood failure mechanism in the current package-row-first Search;
- why additive Cardinal closeness is insufficient before Decision-owned package economics;
- why current sparse bilateral enrichment cannot support a multi-card high-signal feed;
- how OpportunityHypothesis → MarketOpportunity → CandidatePath separates strategic attention from package variants;
- how existing Decision primitives can supply bounded pre-Simulation screening without fabricated acceptance probability;
- how family clustering, dominance pruning, and diversity selection prevent repeated target neighborhoods from crowding For You;
- why exact changed-state Simulation remains downstream of a selected transaction;
- why global 7/7 and lazy all-player Intrinsic readiness are different contracts;
- how Player Board / Free Agents can render partial governed evidence without weakening fail-closed authority;
- a deterministic fixture/test matrix including repeated Gibbs neighborhoods and extreme Superflex package shapes;
- a bounded implementation/migration sequence.

Management acceptance is required before broad Market implementation.

## Market implementation acceptance gate
**Status: NOT STARTED / NOT AUTHORIZED pending architecture acceptance.**

After authorization, implementation is not accepted until evidence demonstrates:
- every For You card is a distinct `worth_attention` Opportunity, not a raw package row;
- every For You Opportunity has at least one bounded pre-Simulation Decision-screened representative path;
- counterparty-dominated, focal-dominated, stale, and critically incomplete paths cannot qualify for For You;
- repeated exact targets cannot occupy multiple For You cards;
- diversity rules and any relaxations are deterministic and observable;
- no Market-generated acceptance probability;
- Owner Intelligence never mutates universal Value;
- package premium evidence is not added to Value or Team Utility;
- mandatory cut cost is charged exactly once;
- broad Market discovery performs zero exact changed-state Simulation calls;
- Core 7/7 copy is scoped truthfully and each Market surface exposes independent readiness;
- Broad Market rows remain usable while optional Intrinsic is building;
- physical-iPhone/Safari Market presentation meets the accepted North Star scanability/navigation standard.

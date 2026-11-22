# Historical circumstances for Owner Intelligence

This increment connects existing draft-aware roster history to recorded player
production and team results. It is descriptive context for past choices, not a
new owner-preference score, forecast, competitive-state classifier or trade grade.

## Shared inputs, no second reconstruction engine

`build_sleeper_historical_context()` returns the native histories it already
built, alongside field coverage and pick lineage. The new circumstance join
consumes those histories and the existing explicit season/franchise crosswalk.
It does not replay the archive again, create canonical State, fetch providers,
write persistence, or add runtime jobs/caches. The adapter normalizes supplied
retained player-season production and Sleeper matchup scores once. League-scored
points retain their source season and scoring fingerprint; they are not rescored.

For each completed trade and participant, the output retains:

- Exact before-completion roster membership where supported, with both the trade
  creation and completion clocks. This is not a creation-time context.
- Prior-completed-season observed player production/positions and explicit
  unobserved-player counts. No games or unknown position is not evidence of poor
  quality; a prior-season position never becomes a current historical position.
- Separate season records over the specific included weeks: wins, losses, ties,
  points for and against. Missing scores are not zero. Custom score overrides,
  incomplete pairings and changed provider roster numbers retain their semantics.
- Source receipts and payload/scoring hashes. Unlinked or mismatched sources and
  duplicate weekly revisions are rejected. Future/equal-cutoff results and full
  trade-season annual production are excluded.

Past franchise results do not prove the current owner's tenure. No owner identity
is inferred from a team name, matching roster number or franchise crosswalk.
Existing independent owner-identity admission remains necessary.

## Model readiness and historical timing

The accepted v2 model's partial-input projection is reused unchanged. Evidenced
lineup requirements/FLEX/Superflex and roster size supply at most seven of its
21 inputs here. Historical active placement, complete pick counts and current
historical position counts remain unknown. This does not admit a model-training
row or authorize stronger live preference weights. Membership uncertainty can
block roster facts without discarding independently supported team results.

A caller must provide completion receipts. A week number or season label does
not generate a date. Receipt `effective_at` is the supplied completed-period
boundary; source `available_at` remains independent and may be unknown. The
retrospective roster path never certifies full contemporaneous source availability.

The disposable real-source fixture also checks an independently pinned NFL
calendar from the existing nflverse evidence family: `nflverse/nfldata` commit
`b925cb83ec90782ae4bbfc06a4f8288fe7ac33c0`, `data/games.csv`, SHA-256
`05dd485f7418350cd6fcbbc7790286b319276353c3261dcde592ff72dc5aeda8`.
For its completed 2022–25 regular-season games, it uses a conservative date bound
of two UTC days after the final game date of each week. This is a research-fixture
completion upper bound, not an invented exact game-end, original statistics
publication time or proof that subsequent stat corrections were knowable then.
Availability remains unknown and training eligibility remains false. Earlier
results cannot pass a cutoff inside that conservative window. The production
adapter contains no guessed calendar formula.

## Real-source proof and limits

The existing public pinned archive and eight retained player-production/matchup
blobs are verified by Git hash before normalization. Existing separately accepted
2023 supplemental evidence remains independent; it does not patch the original
provider audit. Only counts are printed; disposable sources are deleted by CI.

The bounded join produces 144 trade dossiers / 291 participant sides. Recorded
completed regular-season results are present for 287 sides. Supported prior-season
roster observations include 4,013 production records and 472 unknowns across 4,485
rostered observations. These are repeated observations, not unique players or
training samples. There are 257 participant contexts with seven known v2 inputs
and 34 with six; none has all 21. Historical roster membership remains supported
at 127/144 trade boundaries with the accepted supplement, not universally complete.

No new football computation, external paid API, service, database write or live
refresh is involved. One local focused run including real sources used roughly
109 MiB peak RSS for the entire test process and completed 85 tests in 4.85s;
this is not a measurement of the hosted service.

## Next acceptance

Use these factual dossiers to evaluate supported positional quality/strength and
competitive circumstances without importing legacy fixed thresholds. Reconcile
owner tenure and creation/completion semantics before training. The unchanged
full v2 model still requires its missing inputs; any reduced/expanded feature
alternative needs explicitly versioned chronological research. Group all sides of
a trade into one held-out fold, fit priors/scaling on earlier choices, and compare
pooled/context-only baselines before promoting owner residual information.

The end-user milestone remains a useful explanation of an owner's choices in
comparable circumstances and what that suggests for a particular package. This
backend increment does not complete that milestone or change live trade ordering.

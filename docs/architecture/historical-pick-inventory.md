# Historical draft-right inventory

This offline State capability extends the accepted roster/pick replay; it does
not value picks, publish owner preferences or relax canonical State gates.

## Scope and authority

`state/historical_pick_inventory.py` records immutable, source-referenced rights,
completed transfers and selections/expiry. A right keeps its original team,
draft season and round while ownership changes. Explicit allotments include
untraded rights. `enumerate_round_pick_allotment()` supports ordinary round-based
allotments for caller-specified seasons/teams/rounds; exceptions and other draft
mechanisms can supply individual rights. No next-three-year convention applies.

Transfers reuse `reverse_draft_pick_transfer_batch()` on inverse edges to apply
forward changes atomically. Same-time conflicting movements do not acquire an
invented ordering. Contradictions are scoped to affected rights. A partial
season ledger can expose an ownership gap without erasing an independently
recorded draft selection; conditional post-transfer ownership is not certified.

Issuance and use support date bounds. A draft start/last-pick pair bounds a
selection, not its exact timestamp. Queries inside that interval remain unknown;
before/after boundaries are explicit when the timestamp is exact. A recorded
transfer proves existence no later than its timestamp, without inventing the
original issuance date. Used picks are removed from outstanding ownership.

## Coverage is explicit

The inventory distinguishes:

- a complete allotment for the declared draft seasons;
- a complete transfer ledger for those rights, including earlier-season trades;
- a complete use/expiry ledger;
- the timestamp through which the source covers events.

Each completeness declaration defaults to false and is part of identity.
`complete_for_declared_seasons` additionally requires resolved lifecycle states
and no issues. It never certifies unrelated draft seasons. Querying beyond
ledger coverage does not extrapolate outstanding ownership. Merely listing
traded picks or supplying a receipt name cannot establish a complete universe.

Snapshot rows may contain explicitly conditional ownership when a transfer
ledger is incomplete. `known_outstanding_owners` withholds such rows. Missing use
history does not imply that a right is still outstanding. Uncertain selection
coverage remains unknown, rather than leaving a completed draft's missing picks
available to trade.

Identity binds normalized facts, source references, scope, date bounds,
completeness declarations and source coverage cutoff. The Sleeper adapter also
binds the original source revision/content hash even for an untraded/unconsumed
inventory. This prevents different source cohorts from sharing an identity just
because their enumerated rights happen to look alike.

The output is retrospective inventory only and remains ineligible for a PIT
Decision grade. Missing owner tenure, active roster placement, balances, source
availability or Forecast evidence is not filled by this module. Existing
canonical roster State materialization still requires its established receipts
and full evidence; this inventory is not automatically admitted as `LeagueState`.

## Sleeper source adapter

`providers/sleeper_historical_pick_inventory.py` reads already collected source
objects; it does not fetch a provider or write persistence.

`sleeper_linear_draft_allotment()` accepts explicitly identified ordinary rookie
drafts and historical roster mapping evidence. It uses archived rounds/team
settings and draft order to bind every original round/slot to a right. It does
not guess rookie purpose from year, shape or a five-round limit. Other mechanisms
need explicit allotments and bindings. An incomplete original-owner mapping is
an error, not a guess from today's owners.

`normalize_sleeper_historical_pick_inventory()` maps completed transfers using
`status_updated`, preserving the established completion clock. It uses retained
selection `round`, `draft_slot` and receiving `roster_id` plus the explicit original
bindings. It never treats a current three-year pick window as historical issuance.
Draft start/last-pick timestamps bound use; when the last-pick timestamp is absent,
source observation supplies only an upper bound. Malformed, duplicate, unbound or
missing completed selections are coverage issues.

A single season's transactions need not include earlier-season trades of that
season's picks. Do not set transfer completeness merely because the season scan
finished. The shared inventory accepts verified, normalized multi-season events;
cross-season team identity must come from existing lineage/crosswalk evidence,
not similar team names or equal raw roster numbers. Source normalization and
inventory completeness remain separate acceptance layers.

## Validation and source acceptance

Focused tests cover untraded/future allotments, transfers across years, exact and
bounded selection clocks, expiry, conflicting atomic batches, incomplete
transfer/use/allotment evidence, stale coverage and source identity. Synthetic
drafts vary team/round counts, including six rookie rounds.

The existing disposable pinned-archive workflow runs the adapter against its
known 2023–2026 rookie fixtures and keeps the 2022 startup separate. A sanitized
probe has measured 36 selection records in each of 2023–2026 and 240 startup
records in 2022; all have round/slot/roster fields, and all five drafts expose
start/last-pick bounds. Counts are not independently certified at-time ownership
or a validated owner-preference training sample. Real allotment/use mapping
acceptance is recorded with the exact run/head in the workstream checkpoint.

Pinned-source [run 43997893198](https://github.com/jderhagopian-stack/fsffl-next/actions/runs/43997893198)
at code head `e03d8d36b187649dee5ef1b4e1fd7735131f3e34` passed the focused
contracts and four non-skipped source tests. The new source test maps all 36
original rights to 36 consumed selections for each known 2023–2026 rookie
fixture (144 total). It explicitly leaves complete inter-season ownership and
PIT Decision eligibility uncertified. Subsequent documentation updates do not
change those executable contracts.

No raw archive is committed or printed. `scripts/audit_historical_pick_inventory.py`
requires the exact Git blob digest and prints season counts only. The existing
CI acquisition/deletion path is reused; no production State export is involved.

## Resource and rollout boundary

This is offline, one-cohort normalization and immutable inventory construction.
Queries allocate bounded rights/event maps and return small pick rows, not copied
football State graphs or simulations. No web-request work, new database reads,
connections, background service, cache or persisted artifact family is introduced.

Next integration should reconcile the verified multi-season transfer ledger and
dated allotment/use coverage, then consume supported inventory facts through
existing historical State/behavioral evidence boundaries. Current live pick
valuation, trade search, manual priorities and source rules are unchanged.

The [cross-season context integration](historical-cross-season-context.md) now
joins these normalized facts through admitted franchise crosswalks and measures
per-trade field coverage. It keeps conditional ownership and incomplete model
inputs separate from supported roster and selection facts.

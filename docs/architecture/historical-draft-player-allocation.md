# Historical draft-player allocation

## Purpose and authority

Historical Owner Intelligence needs the roster an owner held when acting.
Transaction-only reverse replay carries later draft selections into earlier
rosters. Removing every later-selected player is also wrong: a veteran may have
been held earlier, released and then drafted again.

The existing Sleeper historical-context adapter now normalizes admitted draft
selections into `PlayerTransfer` acquisitions and consumes the existing reverse
batch helper. It reuses the draft purpose, roster identity and selection keys
already admitted for historical pick lineage. It does not infer rookie-only
eligibility, build another replay engine, or introduce historical forecasts.

## Bounds and missing evidence

Draft start and last selection define a bounded interval, not individual pick
times. If the last-selection clock is absent, the retained source-observation
clock is an upper bound; a missing start remains unknown. The upper bound is an
internal reverse-sweep boundary, never a synthetic provider transaction.

Before a known start, safe acquisitions are reversed. Inside the interval,
selected-player membership remains uncertain. Overlapping selected-player
transactions, drafts or supplemental movements leave ordering unknown in
affected earlier contexts. Incomplete selection details block earlier membership
certification but do not discard later known rosters or unrelated pick rights.
Explicit keeper rows are retention, not acquisitions. Unstarted future drafts
create no player allocation; their pick rights remain available separately.

A bare archive caller without admitted draft semantics retains facts but cannot
certify affected pre-draft membership. Both field coverage and historical State
materialization honor snapshot-level uncertainty reasons, including uncertainty
that has no individually identified player. The older single-trade retrospective
diagnostic is not this integrated owner-context path and must not be used as a
draft-aware membership certificate or point-in-time Decision grade.

## Identity and evidence

Allocations require exact season/league/source hash, source references, aware
clocks and unique player identities. Draft-aware histories use
`historical-roster-context-v4:draft-allocations`; their identities include admitted
bounds, selections, completeness and receipts. Legacy v3 identities remain
unchanged when no draft evidence exists. Provider transaction counts and original
supplemental-source audit status remain independent.

Generic tests cover source fences, veteran retention, keeper handling, incomplete
selections, timing/ordering uncertainty and unchanged post-draft ownership. The
existing pinned-source workflow verifies the public archive Git blob, executes
the real integration and deletes its temporary source; raw rosters are not
committed or published as CI artifacts.

The pinned archive has 144 trade boundaries. Draft-aware membership coverage is
89, versus the earlier transaction-only 96: 15 boundaries fall inside draft
intervals, eight already in a known incomplete season and seven newly recognized
as partial. All transaction facts remain. Three sampled pre-draft seasons each
correct 36 later allocations while preserving evidenced earlier veteran holdings;
the sampled ordinary post-draft roster is unchanged. These are membership
results, not complete historical States, admitted model samples or forecast
validation. The known missing historical movement remains separately scoped.

## Continuation

This is offline contextual-input work: no runtime orchestration, persistence,
deployment, behavioral weighting or accepted valuation mathematics changes.
Next connect supported prior production and completed-week team circumstances
to historical choices, preserve field/source uncertainty, then chronologically
validate the existing contextual model before stronger search influence.

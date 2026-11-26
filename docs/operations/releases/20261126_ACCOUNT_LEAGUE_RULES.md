## Released — Personal League Rules & Settings — 2026-11-26

[PR607](https://github.com/jderhagopian-stack/fsffl-next/pull/607) is merged and
live. More → League Rules & Settings imports provider settings, saves personal
league/season overrides, preserves them across refresh/reconnect/restart, offers
reset and provider-conflict review, and supports an unsaved lineup What-If.
Personal changes do not replace provider facts or shared factual history. Capacity
reductions that overfill active/IR/taxi rosters need explicit roster moves.

Validation:3,474 passed /19 skipped on the exact application release head; local
phone-width and desktop journeys passed, including a twelve-team provisional
What-If, save/reopen/reset and roster integrity. Actual league inputs, screenshots
and runtime receipts remain private. Physical iPhone/authenticated settings-save
acceptance is still pending. The existing league analysis restored completely.
No new infrastructure, schema migration, valuation math or recurring expense.

Remaining: Max PF/custom draft rules can be saved, but unsupported slot forecasts
stay unavailable; current-season scoring/season-length What-If needs fresh governed
forecast evidence. Specific imported playoff graphs are retained. These limits do
not claim a new Max PF method or confirmed FSFFL bylaw.

This checkpoint changes documentation only. Public release/check/deployment links
are inPR607. GitHub's active main rules require both `test` and `full-suite` even
for documentation PRs; run those checks without changing protections or redeploying
the application. The procedural documentation-only exception does not waive them.


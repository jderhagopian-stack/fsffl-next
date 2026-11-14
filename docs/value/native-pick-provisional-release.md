# Initial provisional native pick release

## Later-year provisional extension

Future available picks in the released rounds can now use an explicitly neutral
draft-position prior. Forecast supplies equal probability across the league's
possible slots for each later draft, labeled `bounded_provisional_exchangeability`.
These are not Simulation trials or an origin team's predicted finish. Current
next-draft values continue to require the existing published Simulation evidence;
missing next-draft evidence is not silently filled with this later-year prior.

Value applies that prior to the same frozen annual slot statistics, assuming no
known draft-class strength adjustment. No annual table is refitted or replaced,
and no market value, named-prospect forecast or additional historical computation
is introduced. Equal-slot calculations are reused across origins within the read.
All available later years can use this policy where the release's actual rules
and round coverage apply; unsupported formats/rounds still remain unavailable.

Each later pick carries a central reference and the minimum/maximum of its
possible slot references. This shows uncertainty about draft position. It is not
a calibrated confidence interval, a bound on actual player outcomes, or an
estimate of all draft-class/model uncertainty. No package range or covariance is
invented by adding individual ranges. Explore labels the slot uncertain and offers
a compact “Value by draft slot” expansion with explicitly raw Intrinsic units.

The existing horizon calendar is preserved. A 2028 pick contributes its first
post-draft season at the existing Y3 discount in the 2026–2028 window. A 2029 pick
contributes zero in that window, while retaining an undiscounted Career reference.
With no new class-strength evidence and no accepted Career time discount, later
years can have the same neutral Career center; increased uncertainty is not an
arbitrary reduction to that center.

The projection policy has its own version and availability date, pinned in the
existing publication manifest alongside the unchanged annual release. Restored
older manifests without this policy retain their original behavior. This prevents
a new deployment from rewriting previously published future-pick estimates. Later
priors can be used without current Simulation when the publication and player
evidence are otherwise valid; they do not claim Simulation authority. No new
database queries, tables, model-payload writes or workers are introduced.

The sections below document the original first rollout and its fixed evidence.

The first production prior is a bounded provisional estimate, not a claim of
validated full-Career accuracy. The user authorized production integration after
review of the multi-class candidate and mixed validation findings. The evidence
and generic fitting implementation remain in research PR552 at
`378c9d0f0da4f96b41a7b6699d075cca677bca55`.

## Economic authority and scope

The private `native_pick_prior_release` artifact is an immutable release of compact sufficient
statistics from that candidate: the same empirical first-three-year means for
both horizons and the complete Career reference envelope. The original joint
paths remain research evidence; no variance or cumulative uncertainty is invented
when serving the compact table. The public package contains only its exact release
reference, never the derived value table. Model/source fingerprints and attributed backoff
mass remain attached to every slot. No Market values, display anchors or player
repricing enter the table.

The evidence comprises 222 qualifying actual Superflex drafts across 2019–2021.
Each class receives equal weight, then each draft within its class receives equal
weight. The long component transports mature within-position outcomes from five
classes and uses the unchanged accepted terminal authority. First3 is counted
once. Missing source mass uses identified empirical forecast backoff, not a
fabricated historical label. Source-format transport and attributed inactive-season
training assumptions remain qualifications. Empirical slot reversals remain; this
estimates observed selection behavior rather than perfect exercise of an earlier
pick's choice. Career is an undiscounted model reference, not a predictive interval.

Initial coverage is deliberately bounded to the supported 2026 evaluation economy,
2027 draft and first three rounds. The canonical scoring and lineup-capacity
signatures must match. No league/user ID is part of shared economics. Different
formats, season rollover, unsupported rounds or later-draft probability gaps stay
unavailable. A 1-QB league never silently receives the Superflex table.

The 3-Year calendar remains evaluation Y1–Y3 with the accepted 0.85 discount:
the 2027 pick has zero current-season production and includes only its first two
post-draft seasons in the current 3-Year window. Career uses the complete released
reference. Slot probabilities follow the original franchise, while ownership and
roster consequences follow the current owner.

## Lifecycle and persistence

The controlled release operation persists the supported private release before
runtime publication. The existing publication sequence selects that exact persisted
release before its manifest becomes reachable. The manifest pins the exact content identity
and the published Simulation result fingerprint. Old manifests without the new
reference retain unavailable pick Intrinsic; no historical snapshot is rewritten.
A release cannot be applied before its release time. A fresh published State is
therefore required after initial deployment if the existing State predates release.

The existing bounded `PersistenceStore` gains a first-writer-only operation using
`ON CONFLICT DO NOTHING`, then reads the existing identity even if invalidated.
The annual baseline lock is independent of model version. A second baseline for
the same year/economy, or a revoked release, cannot be overwritten/reactivated by
refresh. Future class updates require a separate explicit correction/stage design;
this initial implementation does not add an automatic correction path.

Initial controlled release adds two shared rows: the small annual identity lock
and the 17.6 KB release. Runtime publications make one exact pooled release read,
with no additional release writes. They do not fit, score
historical seasons, run Shapley or add Simulation worlds. The existing manifest
grows only by the small release reference and Simulation identity. Warm release
retention is bounded to four shared compact objects. Requests read the already
restored exact-generation reference from memory, with zero database reads, fits
or slot-mixture recomputation per package.

## Trade and discovery use

The existing raw horizon reader attaches pick values once per read, reusing the
published 50,000-world Simulation origin probabilities. Missing or mismatched
State/generation/rules/probabilities withhold the pick channel without zero-filling
or borrowing Market units. Both Trade Center and discovery consume this same
reader and existing mandatory-cut accounting. A mixed package is labeled with
the frozen-prior reference-append comparison policy; it is not an exact joint-game
allocation. Career covariance and package outcome intervals remain unavailable.

Native horizon search lanes can now include supported picks. The existing
both-team objective assessments and changed-state competition evaluation remain
responsible for usefulness. A positive raw Intrinsic balance alone grants neither
mutual-benefit nor recommendation authority. UI wording is simply “Preliminary
pick estimate”; detailed source qualifications remain in evidence metadata.

Directed priorities, young players (26 and under), positions and picks can be
combined through the already implemented search controls. Find More retains those
instructions and remains bound to the source publication and release identity.

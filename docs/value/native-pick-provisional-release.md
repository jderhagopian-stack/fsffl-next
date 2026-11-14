# Initial provisional native pick release

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

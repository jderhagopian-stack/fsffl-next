# Simulation 35k vs 50k stress-test closeout — 2026-10-02

**Status:** COMPLETE — retain 50,000 production authority.

## Study identity
- Workflow run: `37011239970`
- Final artifact: `simulation-35k-stress-final`
- Artifact ID: `11227844607`
- Artifact digest: `sha256:377d6400b082817aa8348e56461fa0d784d1a9a960614ecc8b21a7ab96a34153`
- Candidate: 35,000
- Production: 50,000
- Research reference: same-root 100,000 only
- Roots: 12
- Governed stress fixtures: 4
- RNG: numpy-pcg64-batched-gauss-v1, batch 500

## Management result
`retain_50000_candidate_failed_meaningful_boundary`

35k saved about **29.9%** median runtime in this stress harness (35.153s vs 50.172s), but it failed the required product-boundary gate.

Product divergence counts versus the same-root 100k reference:
- 35k diverged where 50k matched: **71**
- 50k diverged where 35k matched: **24**
- both diverged: **55**

Selected stability comparisons:
- close-team ranking agreement: **45/48 at 35k** vs **47/48 at 50k**;
- future-pick boundary-summary agreement: **10/12 at 35k** vs **11/12 at 50k**;
- near-zero scenario-delta signs: 100% agreement with 100k at both counts;
- material scenario-delta signs and governed materiality classification: 100% agreement with 100k at both counts.

The candidate therefore was not catastrophically unstable; rather, its extra noise crossed user-visible / downstream-relevant boundaries more often than 50k. The ~30% harness speed gain is not free enough to justify reducing canonical authority.

## Authority decision
- Production Simulation remains **50,000 canonical runs**.
- 35,000 is not promoted as a canonical authority count.
- No adaptive-count rule is introduced.
- Stop count hunting under this directive.
- 35k may remain useful for explicitly non-authoritative research/internal experimentation, but final governed answers continue to use the existing preview/provisional/50k-confirmation contract.

## Review / validation
The study harness:
- uses the production NumPy/PCG64 batched protocol;
- pairs candidate and reference by the same root;
- uses 12 registered independent roots;
- exercises supported four- and six-team postseason structures;
- reuses existing product rounding, competitive-state classification, future-pick summaries, common-world counterfactual comparison and materiality thresholds;
- does not fabricate trade economics or negotiation evidence;
- hard-fails if production authority is changed by the research path.

Workflow result: dedicated stress workflow PASS; ordinary CI PASS; PR164 focused corrective regression PASS.

Bounded P1/P2 methodology/aggregation review found no remaining issue requiring correction. Research/evidence only; no Render deployment or physical acceptance is required.

The complete aggregate JSON is committed alongside this note.

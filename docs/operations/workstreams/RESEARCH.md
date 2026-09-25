# Workstream — Forecast Research: K/DST Empirical Evidence & Source Gates

## State
**DIRECTIVE COMPLETE — RESEARCH**

Authorized: 2026-09-25  
Completed: 2026-09-25  
Completion artifact: `artifacts/research/k_dst_evidence_gate_20260925/RESEARCH_CLOSEOUT.md`  
Evidence ledger: `artifacts/research/k_dst_evidence_gate_20260925/RESEARCH_LEDGER.md`

## Objective
Determine whether the remaining empirical/source gates blocking governed K/DST Forecast authority can be cleared with legitimate evidence, without reopening the completed K/DST architecture and without implementing or promoting production Forecast/model changes.

**Outcome:** complete. Research materially decomposed the gate, recovered additional historical and 2026 PIT evidence, corrected the 2026 kickoff/preseason cutoff, narrowed Sleeper scoring truth, and identified the remaining dependencies as external licensing/data-access or later bounded Implementation work.

No production Forecast/model implementation, authority promotion, persistence mutation, merge, or deployment was performed by Research.

## Authoritative starting state retained
- The K/DST architecture directive remains complete at `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`.
- Forecast implementation PR #215 completed evidence-independent contracts/scoring work and the non-promoting calibration harness.
- Existing two-independent-source governance, fail-closed scoring semantics, source-independence rules, and no-backdating rules remain binding.

## Final research determinations

### Historical PIT evidence
- A genuine pre-opener 2024 source-specific K/DST corpus was recovered from FantasySharks, ESPN and CBS.
- This disproves the prior assumption that an independent historical K/DST source #2 could not be recovered.
- The historical-source gate is **PARTIALLY CLEARED**, not fully promoted: rule coverage, rights, and production-grade uncertainty validation remain outstanding.

### 2026 K evidence
- Authentic pre-opener 2026 FFToday and CBS K snapshots were recovered with provider identity, timestamps and retained hashes.
- 2026 K PIT existence/provenance is **CLEARED**.
- Hodor K authority remains **STILL BLOCKED** because its 50-59 and 60+ rules are not exactly supported by the recovered two-source coordinates and public-use rights are unresolved.

### 2026 D/ST evidence
- Authentic pre-opener RotoWire-via-Sleeper component evidence was recovered.
- Authentic pre-opener FantasyPros aggregate D/ST evidence was recovered.
- FantasyPros cannot automatically count as an independent second provider because its projections are aggregated from multiple underlying sources.
- A second provenance-clean independent component D/ST source was not recovered.
- 2026 D/ST PIT recovery is **PARTIALLY CLEARED**.

### Sleeper scoring truth
Official Sleeper documentation now establishes:
- blocked FG/PAT counts as a kicker miss;
- K distance categories include separate 50-59 and 60+;
- Team Defense includes 2-point conversion returns;
- Special Teams Defense includes team ST TD / forced-fumble / fumble-recovery;
- Special Teams Player remains separate;
- PA/YA are mutually exclusive bucket outcomes with documented accounting;
- scoring categories stack when the underlying NFL play truthfully earns each stat.

Remaining work is exact official-stat/gamebook truth-fixture implementation for rare combined events, not guesswork about category ownership.

### Correct 2026 preseason cutoff
Official NFL scheduling establishes the season began **2026-09-09 at 8:20 p.m. ET** (`2026-09-10T00:20:00Z`).

Therefore:
- artifact 145 is post-opener and must not be described as preseason PIT evidence;
- artifact 63 is the last recovered authentic FSFFL pre-kickoff offense Forecast evidence;
- artifact 63 contains QB/RB/WR/TE only and no K/DST or `fumbles_lost`.

This correction must be reconciled into canonical Management state before annual-preseason migration work.

### Production rights
Current candidate providers remain externally rights-gated:
- FantasyPros offers an explicit commercial licensing path;
- Sleeper requires commercial licensing;
- RotoWire requires written authorization for the proposed automated/storage/derived use;
- CBS/Razzball remain permission/license gated;
- ESPN's undocumented endpoint does not establish production rights;
- FFToday/FantasySharks public accessibility does not establish commercial ingestion/storage rights.

Private beta status does not create permission.

## Final gate disposition

- Historical independent PIT discovery: **PARTIALLY CLEARED**
- 2026 K PIT existence/provenance: **CLEARED**
- 2026 D/ST PIT existence/provenance: **PARTIALLY CLEARED**
- Sleeper semantic definition: **PARTIALLY CLEARED**, with major prior ambiguities resolved
- Empirical K/DST uncertainty promotion: **PARTIALLY CLEARED / NOT PROMOTED**
- Current-forward K/DST Forecast: **STILL BLOCKED**
- Hodor K preseason comparison: **STILL BLOCKED**
- Hodor D/ST preseason comparison: **STILL BLOCKED**
- Weekly K/DST volatility promotion: **PARTIALLY CLEARED / NOT PROMOTED**
- Provider rights for private beta/commercial production: **STILL BLOCKED**
- Simulation/Value/Decision/Search downstream authority: **STILL BLOCKED** pending Forecast promotion
- New-league 7/7 acceptance: **STILL BLOCKED** pending governed K/DST Forecast authority

## External dependencies / Management actions

The remaining gates cannot be resolved by further undirected public Research. Resolution requires one or more of:

1. obtain written provider permission / commercial data licenses covering ingestion, storage, historical use, derived outputs, private beta and commercial production;
2. if using Sleeper-hosted RotoWire data, establish whether commercial Sleeper rights actually sublicense the underlying RotoWire content;
3. obtain a rights-cleared second independent component-level D/ST source or licensed source decomposition proving independence;
4. obtain exact K 50-59 vs 60+ projection evidence for Hodor-like rules;
5. authorize later bounded Implementation to add the now-documented Sleeper truth fixtures, fit/validate calibration, and promote authority only if evidence passes.

Durable license/permission evidence must be retained before production promotion.

## Operating-protocol closure

Research exhausted materially distinct available paths across governed persistence, Git history, public retained snapshots, historical source-specific files, provider/API rights documentation, official Sleeper documentation, and independent provenance implementations.

No further authorized Research action presently available can materially resolve the remaining external dependencies.

**DIRECTIVE COMPLETE — RESEARCH**

## Original prohibitions remain binding
- no production Forecast/model implementation or promotion under this Research directive;
- no fabricated projections;
- no one-source evidence presented as independent calibration;
- no aggregate consensus double-counting;
- no mutable current page relabeled as PIT evidence;
- no guessed D/ST semantics;
- no weakening the two-source or uncertainty authority requirements;
- no synthetic 2026 preseason evidence.

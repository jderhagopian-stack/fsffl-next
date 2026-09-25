# FSFFL NEXT — Decision Log

## 2026-09-24 — Repo-backed operating workflow
Decision: use repository Markdown as the primary durable Management ↔ worker coordination mechanism. PDFs remain optional human-facing artifacts.

Reason: reduce context loss, giant handoffs, and repeated reconstruction while preserving explicit authority and acceptance gates.

## 2026-09-24 — Outcome ownership with bounded authority
Decision: workstreams own assigned outcomes through acceptance and should exhaust authorized actions in each turn. PRs, CI, deploys, and intermediate findings are evidence rather than automatic completion.

## 2026-09-24 — Performance boundary at Forecast authority
Decision: Performance must not weaken Forecast governance to make the new league reach 7/7. The K/DST/new-league Forecast blocker transfers to Research/Forecast authority.

## 2026-09-24 — K/DST modeling is not a UI patch
Decision: research K and D/ST as potentially distinct fantasy asset/forecast families. Do not simply force them through the existing offensive-player model.

## 2026-09-24 — Separate K/DST from new-league bootstrap
Decision: a newly connected league lacking a preserved preseason baseline is a general bootstrap problem and must be solved separately from K/DST modeling.

## 2026-09-24 — K and D/ST Forecast subject model
Decision: K is a distinct Forecast family but remains an individual-player subject. D/ST is a canonical NFL team-season unit and must not be modeled as an ordinary human player.

Reason: the evidence and scoring semantics differ materially from QB/RB/WR/TE, while D/ST identity is inherently a team unit.

## 2026-09-24 — Rule-level Forecast evidence completeness
Decision: production fantasy-point promotion must be complete for every active non-zero scoring rule relevant to the subject. Missing raw evidence cannot silently become zero.

Reason: the research identified that the current material-domain guard can omit an active `fum_lost` rule when `FUMBLES_LOST` evidence is absent.

## 2026-09-24 — D/ST scoring bands require distributions
Decision: points-allowed and yards-allowed bucket scoring cannot be reconstructed from a season total or average alone. Forecast must carry game-level/distributional evidence capable of integrating the configured buckets.

## 2026-09-24 — Preserve existing source authority
Decision: the two-independent-source Forecast rule is not weakened for K/DST. Source eligibility becomes rule/metric specific, and aggregate sources do not automatically count as independent votes.

## 2026-09-24 — K/DST uncertainty is separate
Decision: K and D/ST require distinct empirical season-error and weekly-volatility calibration. Offensive position coefficients are not fallback authority.

## 2026-09-24 — Late-connect preseason bootstrap
Decision: annual preseason authority remains a league-agnostic immutable raw-stat artifact. A late-connected league may use an existing season artifact or a provenance-preserving migration of authentic retained PIT raw evidence; current pages may not be refetched and backdated.

If qualifying preseason evidence does not exist, preseason comparison is explicitly unavailable. Separately authoritative current-forward Forecast may still operate.

## 2026-09-24 — Research completion does not equal production resolution
Decision: the K/DST + new-league Forecast research directive is complete, but the production blocker remains until Management authorizes and accepts governed implementation, empirical evidence promotion, downstream compatibility, and lifecycle validation.

Completion artifact: `artifacts/research/forecast_k_dst_bootstrap_20260924/RESEARCH_HANDOFF.md`.

## 2026-09-24 — Bounded K/DST implementation authorized
Decision: Management accepts the completed K/DST + late-connect Research contract and authorizes the staged implementation sequence in the persisted handoff.

PR #215 may implement contracts, scoring completeness, deterministic fixtures, and non-promoting calibration/outcome harnesses, but must not promote live K/DST provider authority, K/DST uncertainty coefficients, a fabricated 2026 preseason baseline, or downstream K/DST economics before their separate evidence gates pass.

## 2026-09-24 — Synthetic fixture zero is not production evidence
Decision: deterministic tests may include an explicit zero fumble-loss observation when the fixture itself defines a complete synthetic stat line. Provider/runtime code may not convert an absent fumble-loss field into zero. Missing active production evidence remains fail-closed.

## 2026-09-24 — Market North Star not product-accepted
Decision: physical-iPhone acceptance does not close the current Market implementation. The four-surface shell is useful, but opportunity quality, readiness truth, and mobile information hierarchy remain below the product acceptance bar.

## 2026-09-24 — Trade Discovery architecture moves ahead of Market acceptance
Decision: move the Trade Discovery Architecture Review forward as a dependency of Market acceptance rather than treating it as later Trade Center work.

Reason: a small high-signal feed must establish strategic relevance, cheap economic coherence, bilateral plausibility, and diversity before deep Decision/Simulation. Raw package generation plus a “needs full evaluation” label is not sufficient to earn scarce For You attention.

## 2026-09-24 — Opportunity before package
Decision: the Market review will define an Opportunity as a governed strategic object distinct from a generated trade package. Package variants are candidate implementations of an opportunity and must be clustered/deduplicated before presentation.

## 2026-09-24 — Market mobile simplification
Decision: Market must be recomposed around SEE → UNDERSTAND → INTERACT → DRILL DEEPER, with progressive disclosure and distinct jobs for For You, Trade Finder, Player Board, and Free Agents. Market-vs-Intrinsic remains a discovery lens rather than mandatory repeated top-level chrome on every surface.

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

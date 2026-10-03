# Multi-Year Intrinsic Historical Evidence Audit Results

**Status:** Research-only.  
**Canonical workstream:** Draft PR #131 — multi-year intrinsic franchise value study.  
**Production authority:** None.  
**Purpose:** Preserve the historical-evidence audit that determines what can and cannot support empirical calibration of multi-year intrinsic franchise value without hindsight leakage, market-target contamination, or production promotion.

## Guardrails preserved

This audit does **not** change production behavior, coefficients, model authority, or promotion status. It preserves the existing PR #131 research constraints:

- Forecast owns career trajectory, development/decline, survival/attrition, and football uncertainty.
- Value owns multi-year intrinsic franchise economics.
- Decision consumes intrinsic value exactly once alongside separate competitive, roster, and market dimensions.
- Market value and intrinsic value must remain meaningfully independent.
- Team-specific roster need remains downstream in Team Utility / Decision.
- Replacement definition remains a model-selection problem.
- Time preference is not treated as identified until relevant confounders are addressed.
- Intrinsic value must not be trained to reproduce market consensus.
- Simple Model A is allowed to outperform or supersede richer challengers.
- Economic-usefulness checks matter in addition to aggregate error.
- Uncertainty remains first-class.
- No double counting.
- No production promotion without strict chronological, point-in-time-safe evidence.

---

## Executive conclusion

The historical evidence base is **sufficient to run a credible research benchmark of transparent multi-year replacement-adjusted surplus Model A against the existing affine control**, provided historical Forecast inputs are reconstructed correctly inside chronological folds.

It is **not** sufficient to justify fitting or promoting the richer hybrid structural + empirical Model B yet.

The key historical constraint is not a total lack of evidence. It is that different evidence classes have different usable windows and different point-in-time properties. Realized NFL outcomes, career-transition panels, Sleeper league history, historical trade facts, and historical pick reconstruction reach materially farther back than NEXT's hosted projection-history tables. The hosted projection archive is currently empty for historical calibration purposes, and hosted state-history begins only in 2026.

Accordingly, there is no single fully observed 2015–2025 calibration panel in which every desired IntrinsicCalibrationRow field is contemporaneously available. The defensible study must use overlapping evidence windows and chronological fold-specific reconstruction.

Most importantly, the present through-2025 career calibration **must not be applied backward as if it were contemporaneous**. Historical Forecast must be recalibrated within each fold using only transition evidence available before that fold.

---

## Source-by-source historical evidence matrix

| Source | Years covered | Raw evidence retrievable? | Point-in-time / hindsight-free reconstruction possible? | IntrinsicCalibrationRow fields supported | Unresolved / missing fields | Defensible usable window |
|---|---|---|---|---|---|---|
| **2015–2025 career-transition / career-trajectory calibration evidence** | 2015–2025 transition evidence is represented in the research/calibration work | **Yes, for underlying historical player seasons/transitions.** The final through-2025 fitted calibration is only a later summary and is not itself historical point-in-time evidence. | **Yes, conditionally.** Historical Forecast must be re-estimated separately inside each chronological fold using only seasons/transitions observable before that fold. | Position; age/career state; prior production/history; realized future production; survival/attrition outcomes; trajectory targets; uncertainty-calibration inputs. | Contemporaneous projection priors for many older seasons; thin prehistory in earliest folds; current full-panel parameters cannot be reused backward as if known then. | Not simply "2015–2025 using today's calibration." Evaluation should begin only after enough pre-fold history exists to estimate the required career model. Later folds are stronger than the earliest years. |
| **Historical Trade Grader / trade persistence** | Historical FSFFL transaction era across multiple prior seasons | **Yes for timestamped transactions and reconstructable league context.** Some grader outputs are later summaries. | **Yes for raw trade facts and timestamped historical state. No for treating today's historical grade as contemporaneous evidence.** | As-of date; assets exchanged; transaction context; pick/player identities; subsequent asset persistence/outcomes; reconstructable roster/league state. | Complete contemporaneous player-value/projection state for every historical trade; exact separation of then-known facts from later grader features. Trade acceptance itself cannot become the intrinsic target. | Sleeper-era transactions for which transaction timestamps and underlying state can be recovered and validated. |
| **Historical Pick Coordinate** | Historical draft/pick evidence spanning prior league seasons | **Yes for reconstructed pick/draft evidence governed by that workstream.** | **Yes when the point-in-time reconstruction contract is followed.** The workstream was explicitly designed to avoid substituting current pick values for historical values. | Pick season/round/slot where known; historical pick state; later player realization as an outcome; uncertainty around historical pick coordinate. | Pre-resolution picks remain less precise; eventual selected player cannot be used to infer information unavailable before selection; startup/nomination artifacts must remain excluded where applicable. | Historical seasons whose pick-coordinate reconstruction satisfies its provenance and point-in-time rules. |
| **Sleeper historical league / roster / transaction state** | FSFFL Sleeper history | **Yes, substantially.** Transactions, rosters, draft information, settings, and season-specific state are recoverable independently of NEXT's newer hosted history tables. | **Yes for facts recorded at the relevant time or deterministically reconstructable from timestamped events.** | League settings; roster state; rostered assets; transaction timing; draft/pick ownership; lineup requirements; some contemporaneous team context and player metadata. | Sleeper does not supply historical expert projection archives or a historical intrinsic value target. Later roster developments cannot leak backward. | Sleeper league-history era, subject to per-source timestamp validation. Particularly useful for context, state reconstruction, and external validation. |
| **NEXT-3 historical market / research artifacts** | Prior NEXT/FSFFL research period, generally more recent than the full league history | **Mixed.** Some raw or timestamped artifacts exist; other documents are later research summaries. | **Artifact-by-artifact only.** A contemporaneously dated raw market observation can be used; a later document discussing an old season is not automatically point-in-time evidence. | Historical market coordinate where independently timestamped; research provenance; candidate validation comparisons; possibly dated forecast/value observations. | Historical depth is sparse; observation date must be separated from season discussed; later summaries may contain hindsight. | Only explicitly dated raw observations/workflow outputs whose creation/effective time is contemporaneous. No blanket historical window for later NEXT-3 summaries. |
| **Historical NFL realized production / outcomes** | Broad multi-season NFL history, including the career-transition study period | **Yes.** | **Yes as future outcome/label evidence, not as an as-of feature.** Future realization may score an earlier prediction but cannot inform it. | Realized fantasy/NFL production; games/seasons survived; subsequent role/availability; career continuation/attrition; realized multi-year surplus components once replacement is defined. | Does not indicate what a forecaster or market participant knew at the historical cutoff. Future injuries, role changes, and results must remain outcomes. | Broadest evidence window in the study. Suitable for chronological holdout outcomes wherever corresponding pre-cutoff features can be reconstructed. |
| **Provider projection snapshots / workflow artifacts outside hosted history tables** | Primarily recent NEXT-era evidence; older coverage is incomplete | **Mixed / incomplete.** | **Yes where an actual dated provider observation or preserved workflow artifact exists. No where only a later value survives.** | Baseline projected production; provider identity; effective date; potentially source dispersion when multiple independent observations survive. | No demonstrated continuous annual archive across 2015–2025; older vintages are incomplete; vintage dating must be verified individually. | Individually verified dated snapshots only. Cannot currently be treated as a continuous historical projection series. |
| **Hosted `fsffl.projection_snapshot`** | Schema intended for multi-season projection history | **Table exists, but currently contains zero historical rows usable for this audit.** | Not applicable for older seasons at present. | Could eventually support season/effective-time/provider projection evidence if populated historically. | Actual historical observations. | **None currently for retrospective calibration.** |
| **Hosted `fsffl.projection_observation`** | Schema intended for provider-level projection observations | **Table exists, but currently contains zero rows usable for historical calibration.** | Not applicable at present. | Could eventually support point-in-time provider observations and multi-source projection evidence. | All historical observations. | **None currently.** |
| **Hosted projection latest-snapshot layer** | Current architecture | No meaningful historical population identified | Not a historical calibration source | Current/latest projection state where populated | Historical vintages | Not usable as the retrospective historical backbone. |
| **Hosted `fsffl.state_snapshot_history`** | 2026 onward | **Yes.** | **Yes for recorded 2026+ snapshots.** | As-of league/player/system state depending on stored payload. | Does not reconstruct older FSFFL seasons by itself. | **2026+ only.** |

---

## Critical interpretation of the 2015–2025 career evidence

The existence of a 2015–2025 career-transition panel does **not** authorize use of the present through-2025 calibrated career model in historical folds.

A historically valid workflow must use rolling-origin reconstruction. Conceptually:

- for a historical fold with cutoff year **Y**, only transition evidence observable before the cutoff may be used to estimate the career/Forecast model;
- seasons after the cutoff can be used only as future outcomes for evaluation;
- the model may be re-estimated in each fold as the evidence base grows;
- current full-panel coefficients may be retained as a modern research reference, but not as historical inputs.

Example: a 2021 evaluation fold may use only career evidence available before the 2021 cutoff. 2021-and-later realizations may then score the prediction, but they cannot inform the historical Forecast that generated it.

This requirement is central because otherwise the study would appear point-in-time-safe while quietly importing future career-transition knowledge through the Forecast layer.

---

## True reconstructable historical window

There is **no single universal 2015–2025 window** in which every desired intrinsic-calibration field is contemporaneously observable.

Instead, the study has overlapping evidence windows:

1. **Historical NFL realized outcomes** provide the broadest future-outcome window.
2. **Career-transition evidence** can support historical Forecast reconstruction, but only after enough pre-fold data exist to estimate the model without using future transitions.
3. **Sleeper historical league, roster, transaction, and draft state** can reconstruct many league-context facts over the Sleeper-era history.
4. **Historical Trade Grader raw transaction evidence** can support timestamped behavioral/context diagnostics, but later grades cannot be treated as historical truth.
5. **Historical Pick Coordinate** can support point-in-time pick reconstruction over historical seasons that satisfy its provenance contract.
6. **Provider projection snapshots and market artifacts** have a materially shorter, patchier historical window and must be validated individually.
7. **Hosted projection-history tables** currently provide no retrospective historical evidence.
8. **Hosted state snapshot history** becomes useful in 2026 onward.

Therefore the correct historical study design is an **overlapping-window, rolling chronological panel**, not a claim that all fields are observed uniformly from 2015 onward.

The earliest credible evaluation fold should be selected by a **minimum-prehistory sufficiency rule** for the career/Forecast model. The earliest years of the 2015–2025 transition panel are more defensible as model-training history than as high-confidence out-of-sample evaluation periods. Later folds will have stronger pre-cutoff evidence.

---

## What can be reconstructed hindsight-free

The following evidence can be reconstructed or used without hindsight when governed correctly:

### Historical Forecast trajectory

Yes, by recalibrating the career model within each chronological fold using only evidence available before the fold cutoff. This provides a defensible point-in-time internal Forecast even when a third-party projection vintage does not survive.

### League settings and roster context

Yes, where Sleeper historical state or timestamped events preserve the relevant facts. These can reconstruct starting-lineup structure, roster composition, draft/pick ownership, and transaction context.

### Historical trades

Yes for the trade event itself, participants/assets, timestamp, and reconstructable surrounding state. No later trade grade or subsequent success metric may leak backward into the decision-date features.

### Historical pick state

Yes when the Historical Pick Coordinate's point-in-time reconstruction rules are satisfied. Future draft resolution can be an outcome, not an input.

### Realized NFL outcomes

Yes as future labels/realizations for scoring historical predictions. They cannot be included in the historical feature set.

### Dated provider/market evidence

Yes only where a genuine contemporaneous observation or workflow artifact survives with defensible dating and provenance.

---

## What cannot currently be reconstructed safely

### A continuous 2015–2025 archive of third-party projections

The hosted projection-history tables do not contain this archive, and other provider/workflow artifacts are not currently sufficient to declare a continuous annual historical series.

### Historical intrinsic value itself

There is no authoritative historical intrinsic-value target. That is the construct being researched. It must not be backfilled from today's intrinsic model or inferred from market prices.

### A clean historical time-preference coefficient from observed market behavior

Historical trade prices combine time preference with uncertainty, scarcity, positional context, owner strategy, roster need, competitive timing, behavioral effects, and market inefficiency. Market behavior cannot simply be inverted into a universal intrinsic discount rate.

### A uniquely identified replacement definition

The available evidence can compare replacement definitions, but it does not establish one replacement policy as self-evidently correct before model comparison.

### Rich Model B interactions without substantial identification risk

The present evidence does not yet reliably separate all richer structural/empirical interactions from missing projection vintages, replacement choice, time preference, career uncertainty, and market/context effects.

---

## What parts of the study are empirically supportable now

The current evidence supports a substantial, disciplined research study now.

Specifically, it supports:

- chronological comparison of the existing affine control against transparent multi-year replacement-adjusted surplus Model A;
- fold-specific historical Forecast reconstruction;
- use of realized future production, survival, and career outcomes as holdout labels;
- candidate replacement-policy comparison rather than presupposing a single answer;
- uncertainty-aware evaluation;
- economic-usefulness checks in addition to aggregate error;
- external diagnostics using historical trades and market observations without making market consensus the intrinsic target;
- inspection of whether intrinsic estimates retain meaningful independence from market values.

The study should therefore ask whether Model A produces a more defensible and economically useful intrinsic coordinate than the affine control, **not** whether it can imitate historical market prices.

---

## What remains underidentified

### Time preference

Time preference remains underidentified because historical asset prices and trade behavior entangle several forces:

- expected future production;
- uncertainty and career risk;
- liquidity and marketability;
- positional scarcity;
- roster construction;
- contender/rebuilder timing;
- owner preference and behavioral bias;
- pick uncertainty;
- replacement environment;
- market mispricing.

A discount parameter should therefore remain a research object unless and until the study can separate these confounders sufficiently.

### Replacement value

Replacement remains a model-selection problem. Candidate definitions can be compared empirically and economically, but no single definition should be hardcoded as "truth" merely because it is conventional or convenient.

### Historical external expectation baseline

A complete historical provider-projection archive is not available. Where dated external projections do not survive, the study must rely on the chronologically reconstructed internal Forecast rather than pretending a historical external baseline exists.

### Rich hybrid interactions

The added flexibility envisioned for Model B risks fitting missingness, hindsight-contaminated summaries, replacement-choice artifacts, or market/context confounders rather than true intrinsic economics.

---

## Can Model A be benchmarked credibly now?

**Yes, with strict chronological reconstruction.**

Model A can be benchmarked credibly against the existing affine control because its core requirements are supportable from the current evidence base:

- a point-in-time Forecast reconstructed within each fold;
- realized future outcomes;
- multi-year horizon structure;
- candidate replacement definitions;
- uncertainty;
- chronological holdout evaluation.

This does **not** mean Model A is ready for production. It means the research benchmark can be run without fabricating historical information or leaking future transition evidence backward.

The benchmark must include both predictive/statistical measures and economic-usefulness tests. A model that marginally reduces aggregate error but produces implausible franchise economics should not be considered superior merely on error metrics.

---

## Should Model B remain blocked?

**Yes.**

Model B should remain blocked from substantive fitting until Model A has been evaluated and until the residual evidence demonstrates that richer structure is both identifiable and economically useful.

At present, Model B has enough flexibility to absorb:

- missing historical provider projections;
- replacement-definition uncertainty;
- time-preference confounding;
- historical market/context effects;
- career-model uncertainty;
- later-summary hindsight contamination.

Fitting it now would create a high risk of false precision.

The correct research sequence remains:

> **Existing affine control → chronologically reconstructed Model A → inspect statistical and economic usefulness → only then determine whether residual evidence justifies Model B.**

Simple Model A is explicitly allowed to win.

---

## Implications for market-independence testing

Intrinsic value and market value must remain independently meaningful coordinates.

Historical market observations and trade behavior are useful for **diagnostics**, including questions such as:

- Does the intrinsic estimate merely shadow market consensus?
- Where does intrinsic diverge from market, and do later outcomes provide evidence that the divergence was informative?
- Is market information entering the intrinsic pathway indirectly through a supposedly structural feature?
- Do model improvements persist when market-related evidence is withheld from intrinsic construction?

They should **not** be used as the supervised target for intrinsic value.

A model trained to reproduce historical market consensus would collapse the distinction PR #131 is explicitly trying to preserve.

---

## Implications for replacement-value calibration

Replacement should be treated as a candidate family of defensible structural definitions and selected through research comparison.

The next benchmark should therefore evaluate plausible replacement constructions under the same chronological folds and ask both:

1. which definition improves historical holdout performance; and
2. which definition produces economically sensible franchise-value behavior across positions, ages, horizons, and asset types.

Selection should not be based on aggregate error alone.

---

## Implications for time-preference research

The study should **not** attempt to identify time preference by directly fitting intrinsic values to historical market prices or trade exchange rates.

If time preference is investigated empirically, the research must first control or explicitly model material confounders such as career uncertainty, pick uncertainty, replacement environment, competitive timing, position, age, and marketability.

Until that standard is met, discounting should remain a bounded structural research choice or sensitivity analysis rather than an empirically "identified" production coefficient.

---

## Recommended next research step

Proceed with **Model A benchmark design only**. Do not expand Model B yet.

The next research slice should:

1. define the rolling chronological folds and the minimum-prehistory sufficiency rule;
2. rebuild the career/Forecast calibration independently inside each fold using only pre-cutoff evidence;
3. construct the point-in-time Model A rows from admissible historical evidence;
4. define a small candidate set of replacement policies as model-selection alternatives;
5. carry uncertainty and evidence provenance through every historical row;
6. compare Model A with the existing affine control using both predictive metrics and economic-usefulness checks;
7. run explicit market-independence diagnostics without training intrinsic value to market consensus;
8. document missingness and narrower evidence windows rather than silently imputing unavailable historical information;
9. stop again before Model B fitting and determine whether Model A leaves a defensible, empirically identifiable residual problem that actually requires richer structure.

No production promotion should occur as part of that work.

---

## Research decision summary

1. **True reconstructable historical window:** overlapping rather than uniform. Broad NFL outcomes and historical league data extend farther back; historically valid Forecast requires fold-specific pre-cutoff recalibration; external provider/market vintages are shorter and patchier; hosted projection history currently contributes no retrospective rows and hosted state history starts in 2026.
2. **Empirically supportable now:** affine-control vs Model A benchmarking, chronological Forecast reconstruction, replacement-policy comparison, uncertainty-aware holdout scoring, economic-usefulness testing, and market-independence diagnostics.
3. **Underidentified:** universal time preference, a uniquely correct replacement definition, a continuous historical external-projection baseline, and richer Model B interactions.
4. **Model A:** can be benchmarked credibly now under strict chronological reconstruction, but remains research-only.
5. **Model B:** should remain blocked until Model A results and residual identification evidence justify additional complexity.

**No production behavior or model authority is changed by this document.**

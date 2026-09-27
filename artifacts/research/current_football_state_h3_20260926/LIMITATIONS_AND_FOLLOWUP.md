# Current Football-State H3 — Limitations and Follow-up

## Limitations

1. **No historical provider-revision series.** The projection snapshot table contains zero retained revisions, so this study cannot estimate how much provider ROS revisions historically absorbed an injury/transaction shock.
2. **Current ROS is not deployment authority.** Exact two-source standard scoring covers only 54 current players and CBS/Razzball rights are not cleared for production model use.
3. **Episode ratios are descriptive.** Injury post-return PPG/opportunity and recurrence cohorts are not causal counterfactual estimates.
4. **Age/experience-specific injury penalties are not established.** The current episode output does not support a governed age-specific injury multiplier, and no such penalty is recommended.
5. **Structural-event sparsity.** Suspension/exempt and retirement are too sparse for fitted coefficients; release/cut H3 is only coarse because no position subgroup reaches 30 OOT rows.
6. **Promotion/demotion are observed-role events.** They demonstrate current role change but not a separate future causal effect after current production/role evidence is already known.
7. **The preseason remaining comparator is structural.** Current provider comparison uses `preseason Y1 * (18-completed_week)/18`, not an exact team-specific remaining schedule.

## Justified follow-up

### A. Prospective provider-revision archive
Persist every governed current ROS snapshot with:
- capture/effective timestamp;
- provider/source version;
- exact scoring coordinate coverage;
- event state at capture;
- current role/availability evidence.

This is the highest-leverage follow-up because it will allow future Research to measure provider reaction and avoid double counting empirically.

### B. Injury availability model
Use the 4,793 historical episodes to build a separate chronological model for:
- probability of active participation by remaining week;
- expected games available / time-to-return distribution.

Do not include healthy-production loss in this target.

Only after this model beats simple severity/status baselines should it become an H1 availability fallback when provider ROS is unavailable.

### C. Post-return role model
Separately test opportunity after return. It should be incremental to pre-event role, age/experience, injury class and current provider/role evidence. Do not infer role loss from the same availability model.

### D. Release/cut H3 confirmation
The narrow H3 persistence signal merits a dedicated attachment/survival study with more historical support and pooled/coarse semantics. Do not fit position-specific cardinal penalties from the present 62 OOT rows.

### E. Recurrence/durable injury
Only pursue if recurrence state adds OOT information beyond injury class, role, age/experience and provider/current availability. No generic recurrence penalty is justified today.

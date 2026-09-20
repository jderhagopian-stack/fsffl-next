# Pre-fit residual-library eligibility clarification

Persisted before challenger fitting/performance evaluation.

Exact D1 replay across the canonical 2014-2022 evaluation origins passes. While constructing the earlier prior-origin prospective residual library, three pre-primary rows have a frozen D1 depth/usable tie at zero:
- source 2011: one developmental-RB active row;
- source 2012: two developmental-RB active rows.

The gap-aware successor cannot preserve *strict* within-lower-group ordering for a row whose frozen D1 depth and usable means are tied, because both states receive the same lower-group log1p correction. The directive requires final state ordering to be verified numerically for every training and evaluation row.

Therefore residual-library eligibility is resolved mechanically, before fitting and without inspecting challenger performance:
- include an earlier prospective residual row only when its frozen prior-origin D1 positive-state means are strictly ordered depth < usable < starter < premium < elite;
- record every excluded row and reason;
- do not otherwise alter the residual target, penalties, amplitude, state grouping, optimizer, gates, or canonical 2014-2022 evaluation set.

This removes exactly three pre-primary residual rows. It does not remove or alter any canonical evaluation row and is not based on target performance, source magnitude, player identity, or challenger outcome.

# Historical Y1–Y3 coverage and executable gate

Five distinct starting-season cohorts from the recovered historical outcome panel were checked. This verifies which Shapley computations can be executed **without fabricated retirements/zeroes**.

|Start|Player pool|Y2 missing|Y3 missing|
|---|---:|---:|---:|
|2003|559|133|196|
|2006|554|134|210|
|2009|546|135|212|
|2012|574|156|238|
|2015|578|163|244|

Y1 has complete observed source-year coverage for each cohort. Thus the repo runner `scripts/replay_historical_shapley_hindsight.py` can compute the **actual frozen Shapley algorithm** over each Y1 observed cohort using an explicit 12-team Superflex fixture. It does **not** equate hindsight observations with contemporaneous forecasts. It emits a blocking coverage result instead of claiming a full Y2–Y3 value when seasons are missing.

This is not a completed historical Career reconstruction. To derive Career, we additionally need valid Y2–Y7 forward projections and a governed Y8+ terminal model, with historical-scoring/league-rule normalization. Observed nonappearance/retirement needs explicit handling and a full year-specific active pool.

The unmodified source historical package is retained outside this repository. Executing the full-scale Y1 runner requires making those exact authorized historical inputs available to the execution environment. Test CI on synthetic fixture is verification of runner behavior, **not** execution against the 559–578 row historical datasets.

Research-only, no cap change / merge / production changes.

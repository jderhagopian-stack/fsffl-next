# Observable Collapse-Risk Stage B — First Structural Control Result

Date: 2026-09-18

## Execution
Temporary draft PR #151 was opened only to expose the bounded research workflow to the connector's PR-run interface. It is DO-NOT-MERGE and carries no production authority.

Workflow run: 35404601164
Artifact: 10571592164
Result: SUCCESS after adding the explicit pandas runtime dependency.

## Frozen evidence
Source population: Phase-2 artifact 10486530017, source seasons 2014–2020.
Structural evidence: nflverse weekly rosters, source season only. Snapshot SHA-256 values are persisted separately.

No model fitting.

## Control discrimination
Source-season roster non-active share >=25% versus <25%:

Y1:
- lower-risk control: 18.87% role-loss rate (n=2,933)
- structural-warning group: 28.43% (n=1,164)
- absolute lift +9.56 percentage points; relative risk ~1.51x
- target-present rate 81.11% vs 55.50%

Y2:
- control: 20.51%
- warning: 31.74%
- absolute lift +11.23pp; relative risk ~1.55x
- target-present 67.64% vs 42.10%

Y3:
- control: 22.00%
- warning: 36.05%
- absolute lift +14.04pp; relative risk ~1.64x
- target-present 55.61% vs 30.58%

End-of-source-season non-active status is directionally weaker:
- Y1 19.54% -> 25.81%
- Y2 21.49% -> 26.73%
- Y3 23.21% -> 28.74%

## Interpretation boundary
This is the first clean matched-population evidence that a source-time observable structural signal discriminates later governed role-loss. It does NOT by itself establish a Stage-C eligible feature or justify candidate fitting. The leverage-first causal reconstruction and additional controls must continue, including distinguishing temporary availability from durable role/security deterioration.

No S1/S2 fitting; no holdout/current-board selection; no main/PR147/production/Shapley changes.

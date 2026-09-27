# Joint Injury-Availability Follow-up Reproducibility

Date: 2026-09-27

## Branch

`research/joint-injury-availability-20260927`

Base durable Research head:
`99d2ad1292b389c2187a8cdbf0ee578bc5b89796`

Frozen protocol commit:
`490252cd473c10fa3119db4554b6c23898cf25c0`

Frozen gates commit:
`970070e7489957e1c30a9dc19050aa3a954ea77d`

Joint scoring implementation commit:
`7122ab45ff3ea847fa8f88d0619c9ecbdfef5382`

Workflow trigger commit:
`277f2a00a40c4c97f09a70e8830a3c4d4bc0acc2`

## Source evidence

Governed injury episode source:
- workflow artifact: `10921183161`
- digest: `sha256:154ef6c7d35d5c04ac01cfbaedd47b8a654c43dd521e4251718277a10e929ea1`
- governed episodes: **4,793**

Exact separate-model benchmark:
- prior workflow run: `36323231951`
- prior artifact: `10933510516`
- digest: `sha256:a531a75b9c8b7878dc7aca4c193b5081ca0f29ec6b132d01ccf509ff240afee1`

## Joint execution

Workflow:
- name: `Joint Injury Availability Follow-up Research`
- run: `36328926750`
- trigger head: `277f2a00a40c4c97f09a70e8830a3c4d4bc0acc2`
- result: **success**

Complete evidence artifact:
- artifact id: `10934946877`
- digest: `sha256:60b368b3ffc772b5b74e4615776aab79f5a291f213d1910f063addd77b926934`
- retention expiry: 2026-10-27

## Frozen-before-scoring records

- `JOINT_INJURY_AVAILABILITY_PROTOCOL.md`
- `JOINT_INJURY_AVAILABILITY_GATES.md`

Both were committed before the scoring workflow existed and before any joint score was produced.

## Persisted compact outputs

- `JOINT_INJURY_AVAILABILITY_FOLD_METRICS.csv`
- `JOINT_INJURY_RETURN_POOLED_METRICS.csv`
- `JOINT_INJURY_AVAILABILITY_POOLED_METRICS.csv`
- `JOINT_INJURY_RETURN_POSITION_SAFETY.csv`
- `JOINT_INJURY_AVAILABILITY_POSITION_SAFETY.csv`
- `JOINT_INJURY_AVAILABILITY_CONFORMAL_SUMMARY.csv`
- `JOINT_INJURY_AVAILABILITY_RESULT.json`

The complete workflow artifact additionally retains:
- joint return OOT predictions;
- joint availability OOT predictions;
- conformal prediction rows.

## Frozen result

- minimum support: pass;
- original remaining-availability gate: pass;
- non-inferiority to separate accepted availability model: pass;
- original return-timing gate: pass;
- direct return comparison to separate HistGB challenger: **fail**;
- all frozen gates: **fail**.

Failure reason:
the joint integrated Brier score is ~1.28% worse than the separate HistGB return challenger, exceeding the frozen 1% direct-comparison non-inferiority limit.

## Authority guards

- conditional healthy production changed: no;
- post-return role changed: no;
- recurrence/durable H2/H3 changed: no;
- production H3 changed: no;
- Intrinsic changed: no;
- provider ROS authority changed: no;
- no-double-counting rule changed: no.

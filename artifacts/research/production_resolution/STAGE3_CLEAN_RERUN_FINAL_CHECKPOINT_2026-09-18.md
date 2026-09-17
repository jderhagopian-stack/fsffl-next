# FSFFL NEXT - Stage 3 Clean Reproducibility Rerun Final Checkpoint

Status: **CLEAN_RERUN_COMPLETE_ACCEPTANCE_RULE_SATISFIED - STOPPED BEFORE HOLDOUT**

## Literal sequence verified

1. M2-only clean run completed from frozen M1a.
2. M2 standalone artifact/checkpoint persisted.
3. Research ref re-fetched at `caf289d1021d789942ee633d553b1ab57d0c4bf1`.
4. M3a-only clean run completed; no M3b object was computed.
5. M3a standalone artifact/checkpoint persisted.
6. Research ref re-fetched at `60761d103b7124e41c904e90ada2fd4a21ce8ab3`.
7. M3b-only clean run completed from the persisted M3a state.
8. M3b standalone artifact persisted.
9. Final holdout was never accessed. No named current player was used.

The clean runner control path therefore satisfies the directive's literal M2 -> persist -> re-fetch -> M3a -> persist -> re-fetch -> M3b -> persist sequence.

## Reproducibility comparison

| Test | Comparator | Prior Y2 MAE delta | Clean Y2 | Prior Y3 MAE delta | Clean Y3 | Classification |
|---|---|---:|---:|---:|---:|---|
| M2 career stage | M1a | +0.003540 | +0.003540 | -0.006476 | -0.006476 | No clear replicated signal |
| M3a production trajectory | M1a + M2 | +0.035059 | +0.035059 | +0.013257 | +0.013257 | Do not advance |
| M3b opportunity trajectory | M1a + M2 + M3a | +0.009158 | +0.009158 | -0.000328 | -0.000328 | No general advancement |

All key conclusions reproduce without classification change.

### M2
- Core validation metrics and fitted coefficients reproduce exactly.
- Y2 CI: [-0.010052, +0.025315].
- Y3 CI: [-0.018163, +0.000343].
- Conclusion unchanged: career stage does not add clear replicated signal beyond M1a.

### M3a
- All common row-level forecast/audit fields reproduce exactly.
- Every official validation source-season remains numerically worse.
- Y2 non-persistence harm remains +0.101243 MAE, CI [+0.051026, +0.143720].
- Y2 realized role-loss harm remains +0.316304, CI [+0.110395, +0.548063].
- Y3 non-persistence harm remains +0.055228, CI [+0.036407, +0.076740].
- Conclusion unchanged: production trajectory does not advance.

### M3b
- Validation, paired uncertainty, chronological, era-stability and common row-level outputs reproduce exactly.
- Full row-audit SHA-256 is identical to the prior run: `22ba1638fb7e86146ad228c6d803c9ff1693d19f9dd36744bdefe0de37204767`.
- Y2 role-loss harm remains +0.070380 MAE, CI [+0.019209, +0.135080].
- Y3 aggregate improvement remains statistically detectable but practically negligible at -0.000328 MAE.
- Conclusion unchanged: opportunity trajectory does not earn general advancement.

## Acceptance-rule result

**PASS - CLEAN RERUN REPRODUCES THE SAME QUALITATIVE CONCLUSIONS WITH ONLY OUTPUT-STRUCTURE/HASH DIFFERENCES CAUSED BY THE STRICT STAGE-SPECIFIC RUNNER.**

No challenger changes classification. No key lower-tail conclusion reverses. No reproducibility defect was identified.

Under the management directive's acceptance rule, Stage 3 can now be treated as procedurally clean:
- M1a remains the only supported new mechanism.
- M2 does not advance.
- M3a does not advance.
- M3b does not advance.
- The two-or-more-standalone-dimensions condition for M4/M5 is not met.

## Hashes

Clean strict runner:
`15802aebd41bcb3468162799777643309e3701a09a4318597c57a9871f2d622e`

Clean outputs:
- M2 result: `0a7cbb737b8c062a1841e82ec52a053a3474c056b489f7fdfc4050a163b816a5`
- M2 audit: `250d19ae2e391b7039611d61feb03fba17132a6e42f5e9092c1b2019ef6bedca`
- M3a result: `d916f15c7ed6453b2ee4f61e2f237caa6b3e3577b82bb0bc4cecb5cd11857b57`
- M3a audit: `1f0043e5fa1ed583442c4287f4376d20cb65493800fc8c2fd1a5f41c1a0b0973`
- M3b result: `eec39930fbb90ddf22b0c0075721749f3bb5e420ea74c40aed1fbc60dd1c5971`
- M3b audit: `22ba1638fb7e86146ad228c6d803c9ff1693d19f9dd36744bdefe0de37204767`

The M2/M3a audit hashes differ from the prior combined audit because the strict runner writes only columns computed by that stage; their shared row-level values match the prior run exactly. M3b contains the full stage stack and reproduces the prior audit byte-for-byte.

## Stop boundary

**STOP.** Do not run M4/M5, consume the final holdout, run current-player sentinels, implement, promote, merge, or deploy. Return this clean reproducibility result to management.

# Broad Market vs Shapley Intrinsic — real-player evidence

Date: 2026-09-20  
Workflow: `35539340259`  
Artifact: `value-authority-comparison-audit` / `10613972386`

## Runtime population and authority

- frozen/reconciled player population: 335
- current Broad Market players: 329
- Shapley Intrinsic players: 335
- comparison uses percentile/rank presentation only
- raw Market and Intrinsic quantities are not subtracted
- no team value is created
- no League Market Value is created
- no Team Utility is created
- current successful market sources: Dynasty Dealer, FantasyCalc, Stats Guy
- current Shapley model: `intrinsic-shapley-i1-v1`

## Named examples

| Player | Pos | Broad Market | Shapley Intrinsic raw | Intrinsic rank | Gap (Intrinsic − Market) | Cardinal Market Value |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Josh Allen | QB | 100.0th pct | 659.41 | 99.85th pct | -0.15 pct pts | 9,069 |
| Dak Prescott | QB | 86.08th pct | 523.91 | 97.46th pct | +11.38 pct pts | 2,424 |
| Jahmyr Gibbs | RB | 99.70th pct | 493.79 | 95.67th pct | -4.02 pct pts | 10,000 |
| Tony Pollard | RB | 53.05th pct | 219.93 | 72.99th pct | +19.94 pct pts | 326 |
| Tyjae Spears | RB | 40.78th pct | 127.20 | 56.27th pct | +15.49 pct pts | 176 |
| Puka Nacua | WR | 98.34th pct | 436.24 | 92.99th pct | -5.36 pct pts | 7,089 |
| CeeDee Lamb | WR | 94.50th pct | 321.31 | 85.52th pct | -8.98 pct pts | 4,972 |
| Matthew Golden | WR | 71.84th pct | 141.91 | 58.96th pct | -12.89 pct pts | 927 |
| Brock Bowers | TE | 97.26th pct | 279.63 | 80.15th pct | -17.11 pct pts | 6,348 |
| Kyle Pitts | TE | 71.85th pct | 200.42 | 69.10th pct | -2.75 pct pts | 1,187 |
| Dallas Goedert | TE | 60.84th pct | 143.59 | 59.25th pct | -1.59 pct pts | 409 |

## Interpretation

The examples prove the two lenses are independently populated and can materially disagree without either replacing the other. Tony Pollard and Tyjae Spears rank materially higher on Shapley football economics than in the current Broad Market distribution, while Brock Bowers and Matthew Golden rank materially higher in Broad Market than on Shapley Intrinsic.

Cardinal values are shown here only to demonstrate the third coordinate remains separate. The size/order of Cardinal is not used to calculate the Market-vs-Intrinsic gap.

## Atlas consequence

The safe player-level Atlas contract remains:

`Broad Market | FSFFL Intrinsic (Shapley) | Difference`

Difference is a presentation percentile gap only. It is diagnostic and does not create a buy/sell instruction, acceptance probability, team Intrinsic total, League Market Value, or Team Utility score.

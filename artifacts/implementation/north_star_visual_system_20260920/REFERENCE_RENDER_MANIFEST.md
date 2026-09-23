# Reference Render Manifest — 2026-09-20

The visual-system candidate was rendered in headless Chromium using repository-governed fixture fields.

Primary bilateral numeric source:
`tests/test_trade_decision_evaluation.py::test_bilateral_evaluation_preserves_each_side_separately`

Action-language source:
the existing governed `support` disposition path exercised in `tests/test_trade_decision_disposition.py`, translated by current Presentation code to `Pursue this trade`.

The render does not infer the action from visualized deltas.

These are component/browser renders, not authenticated private-beta screenshots.

| Render | Viewport/render size | SHA-256 |
| --- | --- | --- |
| desktop baseline | 1200 × 900 | `1cdc65bf8f6bf28eea5dec8a98eda84c6bc10e15fc6230c8bae65fb681542419` |
| desktop candidate | 1200 × 1229 full-page | `36e9d03fc69c72a93272356d9a29dea7d6cff3862ea165eee152ba7fe1a31739` |
| mobile baseline | 390 × 979 full-page | `c2eb05f3373b0d9a8115765dbe10679a2c2ca681a262a08a0183e9279e71048a` |
| mobile candidate | 390 × 1973 full-page | `8954a2c3cea9af8f234cd826f215e596373c75fb68b3e2bdbe46867bf6f0995b` |

Fixture values:
- Team A: +1.00 expected wins, +10.0 pp playoff probability, +5.0 pp first-place probability;
- Team B: -0.50 expected wins, -7.0 pp playoff probability, -4.0 pp first-place probability;
- 50,000 simulations in the bilateral fixture;
- package identity: Team A sends `p1`, Team B sends `p2`.

The management PDF embeds the four renders directly for visual review.

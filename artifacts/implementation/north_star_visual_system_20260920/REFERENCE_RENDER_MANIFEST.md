# Reference Render Manifest — 2026-09-20

The visual-system candidate was rendered in headless Chromium using repository-governed fixture fields from `tests/test_trade_decision_evaluation.py::test_bilateral_evaluation_preserves_each_side_separately`.

These are component/browser renders, not authenticated private-beta screenshots.

| Render | Viewport/render size | SHA-256 |
| --- | --- | --- |
| desktop baseline | 1200 × 900 | `b0685e228dd9a9b3952a0633505e280dcc653180d9efedca6bedfce14e58e813` |
| desktop candidate | 1200 × 1315 full-page | `d648452b07324a03cf005f4c6bfd1fa35b09f8ca78c28f8ec07580bd451a2f82` |
| mobile baseline | 390 × 912 full-page | `c0f590f55a5c0234d1cce20b296d4f39b0362363826e12c26ea959553a10b22b` |
| mobile candidate | 390 × 2010 full-page | `13425c5e90625aa7fa29bbec6c8c10fe6b05cc3ea665ecbb5b1d6292cb2a9cb0` |

Fixture values:
- Team A: +1.00 expected wins, +10.0 pp playoff probability, +5.0 pp first-place probability;
- Team B: -0.50 expected wins, -7.0 pp playoff probability, -4.0 pp first-place probability;
- 50,000 simulations in the fixture;
- package identity: Team A sends `p1`, Team B sends `p2`.

The management PDF embeds the four renders directly for visual review.

# Approved Hybrid Reference Render Manifest

Date: 2026-09-20

These images are browser/component evidence, not authenticated private-beta screenshots.

## Current-beta / merged #159 baseline

- desktop: prior validated #159 component baseline
- SHA-256: `1cdc65bf8f6bf28eea5dec8a98eda84c6bc10e15fc6230c8bae65fb681542419`
- mobile: prior validated #159 component baseline
- SHA-256: `c2eb05f3373b0d9a8115765dbe10679a2c2ca681a262a08a0183e9279e71048a`

## Approved-hybrid candidate

- desktop render: 1200 px wide, full component page
- SHA-256: `cdb505c1d95ebd5c3e1b10d109212d15a3e359c21e8611490cc0965651eb00bf`
- mobile first-viewport render: 390 × 844
- SHA-256: `dc79b4573f2ddf89d222f819f3074e954b48909b08e45c9f3b42545a35f9db13`

## Approved eight-screen visual benchmark

- user-supplied visual reference
- SHA-256: `18a4f5880751e2168f62b568d8566fead406bbf58eab16a52158440e7efb57aa`

## Governed fixture used for candidate comparison

Primary bilateral numeric fixture:
`tests/test_trade_decision_evaluation.py::test_bilateral_evaluation_preserves_each_side_separately`

- Team A: +1.00 expected wins, +10.0 pp playoffs, +5.0 pp first place
- Team B: -0.50 expected wins, -7.0 pp playoffs, -4.0 pp first place
- fixture Simulation count: 50,000
- package identity remains the fixture package, not invented NFL-player branding

Action language remains sourced from the existing governed Decision path rather than inferred from the visual bars.

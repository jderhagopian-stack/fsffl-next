# FSFFL NEXT — Bounded K/DST Empirical Uncertainty Check

Date: 2026-09-25  
Directive: 2026 late-start K/DST Management exception  
State: **RESEARCH EVIDENCE — NON-PROMOTING**

This artifact executes the bounded empirical checks requested by Management. It does **not** promote a K or D/ST production uncertainty coefficient.

## Governing rule

A measured coefficient is authoritative only for the exact scoring fingerprint represented by both:

1. >=2 genuinely independent PIT projection sources; and
2. realized outcomes reconstructed under the identical scoring fingerprint.

A reduced-fingerprint measurement must not be silently applied to a broader Hodor K/DST total.

---

## 1. K season-error check

### Projection evidence

Repository:
`ashishkab0b/fantasy_football_2024`

Ref:
`d02f24161e7c08b4e99faacc2481b688b8487704`

File:
`data/projections/K_projections.csv`

Blob:
`85026bfa652b56a7d675ac42ac818716f6531c88`

Qualifying provider candidates:
- FantasySharks
- CBS
- ESPN

The repository commit predates the 2024 NFL regular-season opener and preserves provider-specific raw K projections.

### Realized evidence

Repository:
`cdemurjian/uconn-gn-ffl`

Ref:
`7749bf32bf45208117ea5705d344637bcfdb2f4b`

File:
`assets/data/player-stats-2024.json`

Blob:
`093d6aa50022e31044813c2465f7182df2985812`

Realized K fields:
- FGM
- FGA
- XPM

### Calibration fingerprint

`3 * FGM - (FGA - FGM) + XPM`

This fingerprint deliberately excludes:
- distance-tier premiums;
- the Hodor 50–59 / 60+ distinction;
- XP miss penalty;
- any other unsupported coordinate.

Projection sample construction:
- equal-weight the qualifying provider values per kicker;
- require >=2 distinct provider sources;
- compare to realized 2024 fingerprint.

### Result

- sample size: **34 kickers**
- 30 kicker samples have 3 sources
- 4 kicker samples have 2 sources
- mean projection: **92.1872656667**
- RMSE: **35.4172854106**
- relative RMSE: **0.3841884793**
- MAE: **30.8973251384**
- mean error (realized − projected): **+8.0480284509**

### Disposition

**BOUNDED EMPIRICAL K SEASON-ERROR EVIDENCE EXISTS.**

The measured relative RMSE `0.3841884793` is valid only for this reduced K fingerprint.

It is **not** a promoted Hodor K uncertainty floor because Hodor separately scores 40–49, 50–59, 60+, XP misses, and other active coordinates not all represented by the calibration fingerprint.

---

## 2. D/ST season-error check

### Projection evidence

Repository:
`ashishkab0b/fantasy_football_2024`

Ref:
`d02f24161e7c08b4e99faacc2481b688b8487704`

File:
`data/projections/DEF_projections.csv`

Blob:
`ea903795364225b3c4d34a76104035766419f084`

Qualifying provider candidates:
- FantasySharks
- CBS
- ESPN

### Realized evidence

Repository:
`csj606/nfl-predictor`

Ref:
`0157590392c09be2bb9f38a4c493d9f6470f8797`

File:
`ML_Model/annual_2024.csv`

Blob:
`059f53d37b6eded83c6df84e54265816f225c2e9`

The retained annual team file contains nflverse-derived 2024 REG raw defensive event totals.

### Calibration fingerprint

`1 * DST_SACK + 2 * DST_INTERCEPTION`

These coefficients match Hodor for the two included coordinates.

The fingerprint deliberately excludes:
- fumble recoveries;
- forced fumbles;
- safety;
- blocked kicks;
- defensive TDs;
- defensive two-point returns;
- team special-teams TD/FF/FR;
- nonlinear points-allowed buckets.

Projection sample construction:
- equal-weight provider projections per team;
- require >=2 independent provider rows;
- compare to realized 2024 REG sacks + interceptions score.

### Result

- sample size: **30 D/ST units**
- 20 samples have 2 sources
- 10 samples have 3 sources
- mean projection: **72.1942609610**
- RMSE: **15.4516171923**
- relative RMSE: **0.2140283312**
- MAE: **12.1608169043**
- mean error (realized − projected): **−6.6275942943**

### Disposition

**BOUNDED EMPIRICAL D/ST SEASON-ERROR EVIDENCE EXISTS.**

The measured relative RMSE `0.2140283312` is valid only for the sacks + interceptions fingerprint.

It is **not** a promoted Hodor D/ST uncertainty floor.

---

## 3. K weekly realized volatility

### Realized evidence

Repository:
`jameslyman7/NFL`

Ref:
`53de8e4559930eb626adb5d1698684e488b52238`

File:
`archive/2024/special_teams/2024_special_teams_combined.csv`

Blob:
`f4fec961bbd91b5c505f3900ae50f330b48616da`

The retained file is player-level weekly special-teams boxscore evidence.

### Weekly fingerprint

`3 * FGM - (FGA - FGM) + XPM`

Using the same reduced K coordinate as the season-error study.

The PR #215 volatility method is followed:
- group by kicker;
- require at least two games;
- center scores within kicker;
- pool centered residuals;
- divide pooled residual RMS by mean absolute subject score.

### Result

- K subjects: **42**
- weekly observations: **542**
- pooled absolute subject mean: **7.0301560407**
- pooled within-subject centered stddev: **3.6720435609**
- pooled coefficient of variation: **0.5223274618**

### Disposition

**BOUNDED EMPIRICAL K WEEKLY VOLATILITY EVIDENCE EXISTS** for the reduced K fingerprint.

It is not a Hodor-total weekly CV.

---

## 4. D/ST weekly realized volatility

### Realized evidence

Repository:
`csj606/nfl-predictor`

Ref:
`0157590392c09be2bb9f38a4c493d9f6470f8797`

File:
`ML_Model/weekly_2024.csv`

Blob:
`79e0460401afead83cd9ecccf92c209335f191b8`

### Weekly fingerprint

`1 * DST_SACK + 2 * DST_INTERCEPTION`

Using the same reduced D/ST coordinate as the season-error study.

### Result

- D/ST subjects: **32**
- weekly observations: **544**
- each team contributes 17 regular-season games
- pooled absolute subject mean: **3.8198529412**
- pooled within-subject centered stddev: **2.4378077394**
- pooled coefficient of variation: **0.6381941339**

### Disposition

**BOUNDED EMPIRICAL D/ST WEEKLY VOLATILITY EVIDENCE EXISTS** for sacks + interceptions.

It is not a Hodor-total weekly CV.

---

## 5. Authority implication

The historical evidence gate must no longer be described as “no empirical K/DST uncertainty evidence.”

The correct statement is:

> Historical evidence is sufficient to estimate bounded empirical K and D/ST uncertainty on explicitly supported common scoring fingerprints. Existing evidence does not yet support direct promotion of a full Hodor-total uncertainty coefficient.

### Production-safe next step

Implementation may:
1. encode `CalibrationScoringFingerprint`;
2. reproduce these measurements from retained source evidence;
3. add replay/holdout diagnostics;
4. measure additional fingerprints when enough independent PIT projection coordinates exist;
5. promote uncertainty only when the target league scoring fingerprint is proven compatible or a separately governed residual decomposition covers every excluded active coordinate.

Implementation must **not**:
- copy `0.3841884793` into Hodor K uncertainty;
- copy `0.2140283312` into Hodor D/ST uncertainty;
- use `0.5223274618` or `0.6381941339` as whole-score weekly CVs;
- borrow QB/RB/WR/TE uncertainty;
- treat provider disagreement as a substitute for an empirical floor.

## Final empirical gate status

- bounded K season-error evidence: **CLEARED FOR RESEARCH**
- bounded D/ST season-error evidence: **CLEARED FOR RESEARCH**
- bounded K weekly volatility evidence: **CLEARED FOR RESEARCH**
- bounded D/ST weekly volatility evidence: **CLEARED FOR RESEARCH**
- full Hodor K uncertainty promotion: **STILL BLOCKED**
- full Hodor D/ST uncertainty promotion: **STILL BLOCKED**

The remaining uncertainty blocker is **target-scoring compatibility / uncovered-coordinate treatment**, not absence of measurable empirical K/DST error.

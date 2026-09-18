# FSFFL NEXT — Governed exact-age completion: source-conflict stop boundary

Date: 2026-09-18

Authority: Management Authorization — Governed Exact-Age Completion.

## Protected state at start

- research branch: `a6c4831f0351e4ff5b7812ed28fbb1c1185c377b`
- main: `53ff3a3c2e79a59d1e4d8bbdfbb293b10f978b76`
- PR #147: open/unmerged; head `3e63cd61602d0832acf0a30dcc5bee0b13ceeb63`

No protected ref was modified.

## Step 1 — settled exact-age convention recovered

The frozen Phase 2 player-season panel is the authoritative historical input consumed by the surviving A2/age-state machinery. It contains 15,492 player-season rows with `birth_date`, `season`, and full-precision `age_years`.

The age convention is mechanically recoverable from the frozen bytes without choosing among conventions:

`age_years = (date(season, 9, 1) - birth_date).days / 365.2425`

Recovered properties:

- A2 reference date: **September 1 of the evaluation/source season**.
- Decimal-age calculation: integer calendar-day difference divided by **365.2425**.
- Rounding: **none** before the stored full-precision float.
- Leap-year treatment: calendar date subtraction determines elapsed days; the denominator is the fixed mean Gregorian year **365.2425 days**.
- Position-specific handling: **none** in exact-age calculation. Position enters downstream age-band/A2 feature behavior, not the age arithmetic.

Full frozen-panel verification:
- rows checked: **15,492 / 15,492**;
- maximum absolute difference between recomputed and persisted `age_years`: **4.973799150320701e-14**;
- rows exceeding `1e-12`: **0**.

This is a recovery from frozen artifacts, not a new age convention.

As an independent downstream sanity check, the governed Year-1 horizon begins `2026-09-01T00:00:00Z`, consistent with the recovered 2026 A2 reference date.

## Step 2 — governed DOB/source recovery

The frozen NFLverse identity asset used by the replacement coordinate was checked first through its persisted provenance. The replacement package records:
- NFLverse `players.csv` release asset id `572597132`;
- SHA-256 `801d5fec2fc21c54ad585415e8e551ae9d1de7c601a8c3768504b7ce59b579b6`.

The replacement snapshot intentionally retained identity aliases/IDs rather than birth dates, and the exact source bytes were not available in the durable research package. A byte-identical reacquisition was not established in this execution, so it was not silently substituted with a refreshed provider asset.

Management authorized a new governed completion coordinate only where identity is deterministic and DOB evidence is verifiable. Pro-Football-Reference was used as the preferred canonical football identity source for drafted/current NFL players because PFR identifiers are already part of the NFLverse identity system used by FSFFL. For Jalon Daniels, whose PFR record did not expose DOB in the retrieved record, the already-used FSFFL Year-1 provider FF Today and corroborating nflverse-backed evidence report the exact DOB.

## Row-level recovery status

33 of the 35 missing-age rows have deterministic identity and mutually coherent exact-DOB evidence in the bounded recovery.

Two rows encounter explicit conflicting DOB evidence and therefore fail the management row-level acceptance rule.

### Conflict 1 — KC Concepcion

Frozen Year-1 identity:
- player: KC Concepcion
- position: WR
- Year-1 player id: `diag:sleeper:13298`
- team: CLE
- PFR id: `ConcKC00`

Evidence:
- Pro-Football-Reference: **2004-09-23**.
- A retrieved secondary player record is internally inconsistent: its structured birth-date field says **2004-09-23**, while its biography text says **2004-09-24**.

Because management explicitly requires any row with conflicting birth-date evidence to remain unresolved, no date is selected.

### Conflict 2 — Jadarian Price

Frozen Year-1 identity:
- player: Jadarian Price
- position: RB
- Year-1 player id: `diag:sleeper:13286`
- team: SEA
- PFR id: `PricJa02`

Evidence:
- Pro-Football-Reference: **2003-10-09**.
- The current structured player encyclopedia record also says **2003-10-09**.
- A separate retrieved football-card database record says **2003-10-29**.

The higher-authority sources agree, but management's acceptance rule does not authorize adjudicating conflicting birth-date evidence by source weighting. No date is selected.

## Deterministically sourced rows not implicated by a conflict

The following 33 rows have exact DOB evidence recovered without a detected conflict in the bounded source check:

Fernando Mendoza; Carson Beck; Germie Bernard; Ty Simpson; Omar Cooper; Carnell Tate; Jordyn Tyson; Malachi Fields; Jeremiyah Love; Nicholas Singleton; Ja'Kobi Lane; Makai Lemon; Caleb Douglas; Antonio Williams; Cade Klubnik; Mike Washington; Chris Bell; Ted Hurst; Zachariah Branch; Malik Benson; Kenyon Sadiq; Emmett Johnson; Jonah Coleman; Denzel Boston; Demond Claiborne; Eli Stowers; Kaytron Allen; Cyrus Allen; Kaelon Black; De'Zhaun Stribling; Seth McGowan; Jalon Daniels; Will Kacmarek.

No row-complete 35-player completion artifact is declared because two required rows remain unresolved.

## Exact stop boundary

Management section 4 requires that if **any** row has ambiguous or conflicting birth-date evidence, that row remain unresolved and execution stop before Gate A.

Therefore:

- exact-age convention recovery: **PASS**;
- deterministic DOB recovery: **33/35**;
- unresolved due conflicting DOB evidence: **KC Concepcion, Jadarian Price**;
- row-complete 35-player exact-age completion artifact: **NOT CREATED**;
- 335-player Gate A Y2/Y3 board: **NOT RUN**;
- replacement-coordinate sentinel parity Gate B: **NOT RUN**;
- Intrinsic/Shapley Gate C: **NOT RUN**;
- rankings: **NOT PRODUCED OR INSPECTED**.

No age was estimated, defaulted, borrowed from the obsolete sentinel, or chosen by outcome/ranking behavior.

## Management decision required

The remaining question is now source-governance only. Management must either:

1. authorize a deterministic source-priority/adjudication rule for conflicting DOB evidence (for example, a named canonical source hierarchy), or
2. provide/authorize a specific primary/canonical DOB source for KC Concepcion and Jadarian Price.

Until then the downstream diagnostic remains correctly stopped before Gate A.

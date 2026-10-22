# WP5: Cape Town Special Rating Area (SRA) onset compile (E3)

**Date:** 2026-09-30
**Code:** `scripts/cleaning/e3/` (00–05, `manual/` evidence files, `tests/test_sra_onsets.py`, 9/9 pass)
**Outputs:** `data/cleaned/e3/` — `sra_onsets.parquet` (one row per SRA; codebook `codebook_sra_onsets.csv`), `sra_polygons.gpkg`, `sra_events.parquet`, `sra_levy_panel.parquet`, `sra_security_budget.parquet`, `sra_onset_candidates.parquet`
**Scope:** descriptive only; nothing is merged with crime data.
**Authorship:** the data-engineer built the pipeline. After a usage-limit interruption, the orchestrator re-ran step 05, wrote the tests and wrote this report.

## Coverage
- **60 SRAs/CIDs** are compiled: 58 current polygons, plus historical ones without a polygon (e.g. Athlone, dissolved FY2022/23).
- **Classification:** 24 residential, 28 commercial, 4 mixed, 1 non-service CID, 3 UNVERIFIED. The basis for each class is recorded in `sra_class_basis`: the business-plan residential/non-residential property shares and the residential levy share.
- **Events:** 81 renewals, 6 boundary extensions, 1 residential category added, 1 dissolution, 1 levy end.

## Onsets (memo §5 hierarchy)
- **Primary source:** the first City financial year with an SRA additional-rate line in the budget annexures. Council approvals, application records and business-plan start dates are used to corroborate it. Every candidate date and its source ID is kept in `sra_onset_candidates.parquet`.
- **Precision:** 44 onsets are exact to the financial year; 12 are ±1 FY (a mid-year start can't be excluded); 4 are left-censored (already levied in the first covered year, FY2006/07).
- **Window status (A3):** 28 in window, 22 pre-window, 8 post-window, 2 straddling.
- **City FY → SAPS FY mapping** and the re-timed G̃ are computed as in memo §5.4 (`G_saps_fy`, `G_tilde_saps_fy`).

## G3 feasibility
**12 residential SRAs** have pre-specified fy_exact onsets in FY2011/12-2023/24 and a documented security-budget first stage within [G_min, G_max + 2] (16 had any documented security spend in any budget FY; the four dropped by the onset-window rule are Mount Rhodes, Northpine, Overkloof and Penzance). The G3 threshold is >= 10, so G3 is attainable only narrowly, and before the control-pool check.

| Onset FY | 2014 | 2016 | 2019 | 2020 | 2023 |
|---|---|---|---|---|---|
| Residential G3 candidates with first stage | 2 | 1 | 1 | 4 | 4 |

**Sensitivity (residential levy-share cut 0.7 instead of 0.5, `sra_class_alt07`):** 22 residential SRAs (24 at 0.5); 15 G3 candidates, 11 with first stage. Still >= 10, but the margin is 1.

**Caveats:**
- The **four FY2023 cohorts** (Clifton, Park Island, Pinelands, Upper Kenilworth) have at most about two post-onset years of SAPS data. The effective J_T for dynamic effects is closer to 12.
- The G3 control-pool requirement (J_C ≥ 10 on support) is **not yet checked**. It needs the WP2 precinct clusters × SRA overlay and the Census SAL covariates, which are blocked on the user's download.
- The `dwellings_wp2` field is still empty for the same reason.

## Not verified / open
- **Athlone:** one quote ("Tariff Rates & Cids Including Athlone", archived FY2007/08 budget page) failed automatic verification. The book it refers to is not archived. The onset is kept, flagged UNVERIFIED; Athlone is commercial and dissolved, so this doesn't affect G3.
- **Three SRAs have UNVERIFIED class.** Their business plans weren't found.
- **Failed or withdrawn SRA proposals** (the memo's applicant-type controls): only one pending approval was found in the City documents. Failed proposals are not systematically published, so this control arm needs a City records request, or it drops to robustness.
- **Pre-existing voluntary patrols** (first-stage increment, memo §5): evidence was hand-coded for only 4 SRAs (`manual/pre_existing_provision.csv`). The rest are unknown.

## Review round-1 fixes (2026-09-30)
- A covered FY with no parsed rows is now `not_parsed`, not an absence (`n_rows_parsed_fy`); all 14 covered FYs parse, so no onset changed.
- Levy-bound tightening uses `max` for the lower bound, with `assert lmin <= lmax`. Athlone's quote is still unverified, so its interval stays [2007, 2008] (pm1).
- The business-plan parse skips missing text files (NaN share).

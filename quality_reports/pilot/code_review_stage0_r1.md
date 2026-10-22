# Code review, Stage-0 pilot cleaning (coder-critic, single round, MEDIUM), 2026-09-30

**Scores:**
| Work package | Score | Status |
|---|---|---|
| WP1 gazette | 74 | FAIL |
| WP2 units | 81 | PASS |
| WP5 E3 SRAs | 77 | FAIL |

## Blocking / important fixes
- **WP1-H1 (validation covers precision only).** The validation sample measures parse precision, not recall. Add low/unflagged notices and strata for `sar_confidence`, window and municipality. (`03_parse_notices.py:539,567`)
- **WP1-H2 (W2 2022 coverage).** The W2 2022 gaps (79 missing numbers in contiguous runs, mainly extraordinary issues) look like archive gaps, and the tail gap is hidden. The W2 rate is therefore a lower bound; flag it and check against the GPW listing. (`04_pilot_report.py:103-107`)
- **WP1-M1 (header segmentation).** Missed headers merge notices into one segment, contents parsing stops too early, and the recall check is too narrow. Flag segments with more than one "Act 10 of 1998" block. (`02:246-264,299`)
- **WP1-M2 (stage precedence).** "renewal" is tested before "intent" in the first 1,500 characters, and 0 removals were found. Verify both. (`03:95-113,135-146`)
- **WP1-M3 (dedup key).** Dedup on (kind, number, year) misses re-numbered republications, so the Poisson CI is too narrow. Say so in the report. (`03:571-581`)
- **WP2-H1 (silent column drop).** `_sal.R` silently drops unmatched columns. Add `stopifnot` on the columns found and a ≥99% SAL code match; replace the silent `dwellings := 0`. (`_sal.R:99,129`; `02:72-74`)
- **WP2-M (clustering checks).** Add a direct 2014→2025 overlay check. Fix the E1 share wording/code mismatch. Add an "E3 off" sensitivity scenario (Bekkersdal–Lenasia). (`01_precinct_clusters.R`)
- **WP5-MH1 (parse failure read as absence).** A covered FY with 0 parsed rows is treated as an absence. Require `n_rows_parsed > 0`. (`05:141-144`)
- **WP5-M1 (G3 first stage).** Use `fs_documented_within_onset_plus2` for G3 and recount. (`05:396,426`)
- **WP5-M2 (residential rule).** Test the residential-classification rule's sensitivity (threshold 0.7). Make the business-plan parse robust to missing files. (`05:211-224,200`)
- **WP5-LM (levy bound and Athlone).** Levy-bound `min` should be `max`; assert `g_lo <= g_hi`; clarify Athlone's onset. (`05:270-276`)

## Low (optional)
- WP1 effort extrapolation caveat.
- `dwltyp_13` handling.
- Document crosswalk "outside" rows.
- A synthetic SAL fixture test.
- A CID ±2 FY flag (memo §5.6) or a recorded decision.
- Synthetic tests for `levy_interval`, `classify` and FY mapping.

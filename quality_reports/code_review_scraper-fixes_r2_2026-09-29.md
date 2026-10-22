# Code Audit, Round 2: PSC Exposure, Workstream B (scraper fixes)

**Date:** 2026-09-29 · **Reviewer:** coder-critic · **Severity:** MEDIUM
**Score:** 93/100, a **PASS** (round 1 scored 68).

## Summary
- All twelve round-1 items (B1–B12) are checked as fixed against the code. No regressions.
- The main PSC flag is back to the keyword list in the plan, with a fully accounted change from the old version: 5 rows gained a flag (the fingerprint fix) and 149 lost one (124 intercom, 19 walls, 5 bare "guarded").
- Counts: 18,332 rows and 17,406 unique listings. Every row maps to a metro; 2,779 Durbanville rows were moved to Cape Town and 1 Roodepoort row to Johannesburg.
- The engineer's five flagged decisions are all accepted:
  - walls removed from the main flag
  - access control counted as hardening by default
  - "security complex"-type candidate phrases only in the broad enclave flag
  - `city` redefined as the study metro
  - `?ListingNumber=` pages kept as stubs

## New issues (−7)
| # | Issue | File | Severity | Deduction | Fix |
|---|---|---|---|---|---|
| N1 | `property_use` inherits substring bugs: `"erf" in t` is tested before `"house"`, so a house in "Waterfall" becomes land; a "Warehouse" becomes house; `flat` is a bare substring. | `utils/html_parser.py:330-344,407-422`; `03:109-117` | LOW-MED | -2 | Use `\b` regexes; add tests for Waterfall/Warehouse; add a property_use × property_type crosstab to the audit. |
| N2 | The enclave coding rule is lenient: it counts secure *apartment blocks* as enclaves, which inflates enclave precision (sample F, 95%). | audit; precision_labels CSV | LOW-MED | -2 | Split the enclave code into horizontal (estates, complexes) and vertical (apartment blocks); report enclave rates by property type. |
| N3 | Stub locations are not repaired (they can still say Durban for Durbanville). | `03:120-135` | LOW | -1 | Apply the `label_location` fallback to the stubs. |
| N4 | The block on 05 is only a header comment; 03 validates locations with `assert`. | `05:13-19`; `03:164-171` | LOW | -1 | Make 05 exit at runtime if the new location fields are missing; use `ValueError` instead of `assert`. |
| N5 | Style: leftovers in the 00/05 headers, a `samples`/`sample` column mismatch, implicit tie-breaking in `suburb_canonical`. | various | LOW | -1 | Clean up. |

## Recommendations (not deducted)
- The 53-case fixture is a regression spec, not a validation: the same agent wrote the patterns and the labels.
- Enclave recall hasn't been measured. Add `cand_named_estate` (golf/eco/wildlife/country/equestrian estate) as a candidate column.
- Add a `cand_access_controlled_complex` candidate phrase.
- A 0 means "not advertised", not "absent". Condition on `word_count`.
- Fetching the 4,827 stub listings that appear nowhere else would add about 28% to the listing universe.
- The enclave signal is concentrated in Cape Town (62% of enclave flags). Durban is thin (44.8% of rows have no description; only 10 enclave flags).

## Before the strategy memo relies on these data
1. The user confirms or overturns the model-coded precision labels, especially the enclave rule (N2).
2. Fix N1 before any "residential only" figure is used.
3. Keep 05 blocked until N4 is done and the query uses suburb_canonical + city_url + province_url.

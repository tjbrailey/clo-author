# Code Audit: PSC Exposure, Workstream B (scraper fixes, 03/04), Round 1

**Date:** 2026-09-29 · **Reviewer:** coder-critic · **Severity:** MEDIUM
**Score:** 68/100, which is **FAIL** (the bar is 80). It goes back to the data-engineer for round 2 of 3.

## Summary
The mechanical fixes are correct:
- URL normalisation
- `p24_id`
- dropping pages that aren't listings
- dedup
- the panel fields
- `fingerprints?`
- word-boundary matching for company names
- NA for missing descriptions

Five problems are blocking:
1. `psc_flag_any` brings back NA-as-0.
2. The dictionary was widened beyond the plan, and inconsistently.
3. The pooled flag mixes different constructs, and commercial listings are included.
4. The deterministic `city` fix was deferred.
5. The precision check was not carried out.

## Issue table
| # | Issue | File:line | Severity | Deduction | Recommended fix |
|---|---|---|---|---|---|
| B1 | `psc_flag_any` gives 0 when the description is NA and the title is 0. Titles are templated and never flagged, so the column is just `psc_flag` with NA set to 0. The audit headline reports this biased rate. | `04_classify_psc.py:141-147,161`; `tests/test_classify.py:104-120` | HIGH | -8 | Return 1 if either source is 1, 0 only if the description is observed and 0, and NA otherwise. Or drop the column. Add a test. Take it out of the audit headline. |
| B2 | The 24h variants and `electric fencing` were added (+415 flags). "security complex" (269 rows) and "secure(d) complex" (262) were deferred. | `config.py:83-97,132-139,148-150` | MEDIUM | -4 | Keep the plan-scope `psc_flag`. Store the widened set as a versioned alternative, or record each candidate phrase as its own 0/1 column. |
| B3 | The pooled flag mixes enclave, guard-service and hardening constructs. Commercial and office listings get flagged. `boundary wall` says nothing about security. | `config.py:100-156,190-197`; `04_classify_psc.py:111-125` | MEDIUM | -4 | Output `enclave_flag`, `guard_service_flag` and `hardening_flag`, with `psc_flag` as a documented union. Add `is_commercial`. Move wall phrases to the weak indicators. |
| B4 | The precision check was not done: the `ok?` column is empty. | `audit_classification.py:325-345` | MEDIUM | -2 | Code the samples and report precision by construct with a Wilson CI. |
| B5 | `city` is wrong for 2,798 "Durban" rows, which are Durbanville / D'Urbanvale in the Western Cape. **Hard blocker for 05**: geocoding would fall back to the Durban centroid. | Root cause `00_archive_discovery.py:153-156`; fix in 03 | MEDIUM | -3 | In 03, derive `city_url` from the URL slug and province, keep the old label as `city_target`, assert consistency with province, and log the corrections. Fix 00 before any new discovery run. Also review `html_parser._city_from_url`. |
| B6 | 03 and 04 define "missing description" differently (placeholders). `_n_nonnull` counts empty strings. | `03:116-118`; `04:80-95` | LOW-MED | -2 | Put one shared `is_missing_text` in `utils/`. |
| B7 | The 5,005 dropped `?ListingNumber=` rows were not checked. | `03:17-22,85-112` | LOW-MED | -2 | Sample 10 of them. Report the share of their embedded ids already in `p24_id`, and recover them if they turn out to be listings. |
| B8 | Test gaps: `psc_flag_any` with NA; dedup tie-breaks; placeholders; ALL-CAPS company names; idempotence; negative cases for the 24h pattern; no labelled fixture. | `tests/test_classify.py` | LOW-MED | -2 | Add the cases and a labelled fixture of about 50 snippets. |
| B9 | Pre-fix backups have no recorded provenance. Dependencies are unpinned. The Python version is not stated. | `audit_classification.py:45-46`; `requirements.txt` | LOW | -2 | Record provenance, pin a lockfile, state Python ≥ 3.10. |
| B10 | Case-sensitive company names miss ALL-CAPS text. "Fidelity ADT" is counted as 2 companies. | `config.py:171-188` | LOW | -1 | Document the trade-off or match with context. Merge the brand. |
| B11 | `first_seen` / `last_seen` are capture dates, not listing dates. | `03:31-33,133-135` | LOW | -1 | Rename to `first_captured` / `last_captured`. |
| B12 | Style: `logger` and `print` are mixed, Usage lines are inconsistent, some lines exceed 100 characters. | various | LOW | -1 | Make them consistent. |

## Critic's precision coding by eye (25 flagged rows, §6a)
- As a measure of a **gated enclave**, about 13/25 (~52%) are right.
- As a measure of **residential private-security presence**, about 22/25 (~88%) are right.
- Three are commercial listings.
- Among the unflagged rows there is a clear missed enclave ("Security Complex", row 22), a likely one (Golf View Estate, row 13), and a missed PSC case (row 21).

## Other notes
- 95% of listings are captured once, so in practice this is a cross-section.
- 94 listings appear under more than one suburb slug; pick one canonical suburb before geocoding.
- A flag of 0 means "not advertised", not "absent". The flag rate depends on description length and on the portal's templates.

## Minimum fixes to pass
B1, B5, B2 and B3 (handled the same way throughout), B6, and B4 and B7 in the audit. B8–B12 if convenient.

## Escalation
None. This is round 1 of 3. The construct choice in B2/B3 goes to the strategist at the `/strategize` checkpoint.

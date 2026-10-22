# Plan: Data feasibility round + scraper fixes (PSC Exposure)

**Status:** COMPLETED · **Date:** 2026-09-29 · **Phase:** Discovery (data)

## Context

The Property24 scrape (Wayback only) yields ~17,500 unique listings and 1,592 PSC-flagged ones. The data covers only 80 suburbs, some of which are city-wide buckets. 83% of rows have no street address, and 85% of the data falls in 2011–2016. It can't locate estate boundaries, so the planned spatial RD isn't feasible with it, and the post-2016 sample is too thin to time new estates for the DiD. The audit also found pipeline bugs:
- The dedup step lets through 3,948 search/index pages and repeat captures.
- `\bfingerprin\b` never matches.
- Missing descriptions are coded as non-PSC (0) instead of NA.
- Company names match as substrings (e.g. "Enforce" matches "enforcement").

The user chose to assess better treatment and outcome sources before investing more in scraping, and to fix the scraper in the same round. **Outcome:** a ranked, critic-scored data assessment that says which designs each data combination can support. That puts us in a position to decide on strategy.

## Workstream A: Data feasibility (explorer → explorer-critic)

Dispatch the **explorer** with the requirements below. It writes `quality_reports/data_exploration_psc-exposure.md`.

**Treatment: where gated/PSC enclaves are and when they appeared.** The explorer grades each candidate on resolution, timing, coverage and access:
- OpenStreetMap: residential polygons with `access=private`, `barrier=gate`, or `gated=yes`; its history is available for timing
- Municipal security access restriction / road-closure registers (Johannesburg/JRA, Tshwane, eThekwini, Cape Town), which may carry approval dates
- Academic gated-community inventories (e.g. CSIR / Landman's enclosed neighbourhood mapping)
- Deeds Office sectional-title and HOA/estate registers; Lightstone (proprietary)
- PSIRA statistics on the security industry by area
- Remote sensing (Open Buildings, imagery-based wall and gate detection), noted only as a fallback
- The existing Property24 scrape, graded as a suburb-level intensity measure

**Outcomes: state attitudes and violence.**
- Afrobarometer South Africa: the AidData geocoded rounds (R1–R6) and restricted EA coordinates for later rounds
- GCRO Quality of Life Survey (Gauteng, ward-level, large n; check for items on security measures and trust)
- HSRC SASAS
- StatsSA Victims of Crime Survey
- ACLED
- SAPS precinct crime statistics plus precinct boundaries

**Joint feasibility, the key deliverable.** For each treatment × outcome pairing, the explorer reports:
- the spatial unit where they overlap
- the likely number of respondents or events within 1, 2 and 5 km of treated areas
- whether time coverage overlaps well enough for a DiD
- which designs the pairing supports: spatial RD, DiD, or area-level cross-section

It assigns each source a grade from A to D and ranks the sources.

**explorer-critic** scores it using the 5-point assessment (measurement validity, sample selection, external validity, identification compatibility, known issues) at **SEVERITY: LOW (Discovery)**. The pass bar is 80. If it falls short, run up to 3 rounds; if it still fails, escalate to the user with a specific question. The critic's rejection table is included in the report.

## Workstream B: Scraper fixes (data-engineer → coder-critic), in parallel with A

1. [03_merge_deduplicate.py](scripts/scraping/03_merge_deduplicate.py):
   - Pull `p24_id` (a numeric ID of 7 or more digits) out of the URL
   - Drop pages that aren't listings
   - Dedup on `(p24_id, snapshot_date)`
   - Add `first_seen` and `last_seen`
   - Normalise URLs by dropping the `:80` port and treating http and https as the same
2. [04_classify_psc.py](scripts/scraping/04_classify_psc.py) and [config.py](scripts/scraping/config.py):
   - Change `fingerprin` to `fingerprints?`
   - Tighten the bare `guarded` and `intercom` patterns: drop them or require security context
   - Match company names on word boundaries
   - When there's no description, set the flags to NA instead of 0
   - Add a separate flag for matches found only in the title
3. Re-run 03 and then 04, which needs no network. **Don't run geocoding (05)**; that waits until the design is settled.
4. Write `quality_reports/scrape_audit_2026-09-29.md`:
   - before/after counts
   - flags by group, city and year
   - a random sample of 25 flagged and 25 unflagged descriptions for a precision check by eye
5. **coder-critic** reviews at **SEVERITY: MEDIUM**, with a pass bar of 80 and up to 3 rounds.

## Workstream C: Logging

- Create `quality_reports/research_journal.md` with one entry for each agent run, and append to `SESSION_REPORT.md`.
- Update the project memory with the status as of 2026-09-29.
- **No commits.** The user said not yet.

## Checkpoint (end of round)

Present the ranked sources, the recommended data architecture and what it means for the design. The next step is `/strategize`. The user decides that design question, for example: Gauteng-only using GCRO + a municipal register, or national using Afrobarometer + OSM.

## Out of scope

- Downloading restricted data or submitting data applications (they are listed with how to apply)
- New scraping
- Geocoding
- The strategy memo
- Literature review (it can run later with `/discover lit`)

## Verification

- 03 and 04 exit 0.
- The output has 0 non-listing rows and about 17.5k unique `p24_id`.
- `fingerprint` and `fingerprints` match a test string.
- Rows with no description have NA flags.
- coder-critic scores ≥ 80.
- `data_exploration_psc-exposure.md` exists and explorer-critic scores it ≥ 80.
- Every source has a grade and an access route; the joint-feasibility table is filled in.
- The journal has entries for all four agent runs.

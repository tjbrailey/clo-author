# Plan: Execution Stage 0: pilot and data foundations (PSC Exposure)

**Status:** APPROVED · **Date:** 2026-09-30 · **Phase:** Execution (pilot)

## Context

The strategy memo (`quality_reports/strategy_memo_psc-exposure.md`, strategist-critic score 94/100) is approved. Before any treatment effect is estimated, it requires a pilot (P-A to P-E) and a set of recorded go/no-go gates (G0–G4, §9.3).

This round builds the parts of the pilot that do not depend on the pending data requests (JRA register, GCRO respondent locations, SAPS incident data). It also builds the analysis units and the power simulation, so the gates can be evaluated once the pilot data are in.

**No treatment effects are estimated in this round.** The memo requires gate decisions to be logged, with user sign-off, before any real closure onset is merged with outcomes. P-E therefore uses placebo onsets only.

**User decisions this round (2026-09-30):**
- The user will download QoL III–7 from DataFirst into `data/raw/qol/`.
- Installing R packages (arrow, DIDmultiplegtDYN, pdftools) and Tesseract OCR (via winget) is approved.

## Work packages (each is a worker → critic pair, max 3 rounds; run in parallel where independent)

### WP0: Environment (orchestrator)
- Install the R packages `arrow`, `DIDmultiplegtDYN` and `pdftools` from CRAN into R 4.6.1.
- Install Tesseract with `winget install UB-Mannheim.TesseractOCR`.
- Verify that each one loads.
- Append the new packages to `scripts/scraping/requirements-lock.txt` and to an R session-info file.

### WP1: P-B, JHB gazette pilot (data-engineer → coder-critic)
- New `scripts/cleaning/gazette/`:
  - `01_fetch_gazettes.py`: the Gauteng Provincial Gazette index and PDFs for W1 (2017–18) and W2 (Jul 2021–Jun 2022), from Gazettes.Africa or gpwonline. Polite rate limiting reuses `scripts/scraping/utils/rate_limiter.py`, and PDFs are cached to `data/raw/gazettes/`.
  - `02_extract_sar_notices.py`: reads the text layer with pdfplumber, falls back to Tesseract OCR, and records an `ocr_used` flag.
  - `03_parse_notices.py`: builds one structured row per notice with: date, gazette/notice no., municipality, ref no., stage (intent / final / extension / renewal / removal), restriction type, suburb, streets, applicant, s.4.7 count if stated, and PSC provider if stated.
- Outputs:
  - `data/cleaned/gazette/sar_notices_jhb_pilot.parquet`
  - a 30-notice manual-validation CSV for the user
  - `quality_reports/pilot/P-B_gazette_pilot.md`, reporting volume per window with an exact Poisson CI, type mix, reference-number chronology, OCR share, and time per gazette (to cost the full compile)
- Follow the conventions of `scripts/scraping/` (header blocks, config module, `utils/text_utils.py`).

### WP2: Units and common-support covariates (data-engineer → coder-critic)
- New `scripts/cleaning/units/` (R, `sf`):
  - SAPS station boundaries plus station opening dates → **time-invariant precinct clusters** (parent/child merges, §7).
  - Municipal Demarcation Board ward boundaries for 2011, 2016 and 2021, and a Census-2011 SAL-weighted crosswalk → **stable ward units (SWU)** based on 2021 (§7).
  - Census 2011 SAL attributes (dwellings, dwelling type, race, income band) → the common-support predictors (§3.2) and the calibration target (§6.3).
- Scope: JHB, Tshwane, Ekurhuleni and Cape Town.
- Outputs go to `data/cleaned/units/` (gpkg + parquet), with a unit-count report in `quality_reports/pilot/units_report.md`.
- If a source needs a login, the script stops with a clear message saying where to download the file.

### WP3: P-E power simulation (coder → coder-critic)
- New `scripts/analysis/power/` (R):
  - `01_saps_panel.R`: public SAPS station-year counts, FY2005/06–2025/26, aggregated to WP2 clusters, covering the V0 murder, V1 targeted-index and contact/property families (§11).
  - `02_placebo_power.R`: implements the §9.2 P-E protocol:
    - never-switchers on common support
    - pseudo `(G̃, G)` pairs with lag bins
    - stock bins {0, >0}
    - the ≥5-controls cell rule
    - BJS (`didimputation`) aggregated by t − G, plus CS for E3
    - 500–1,000 draws per δ
    - a size check at δ = 0
  - `03_qol_panel_power.R`: the same for A1 on QoL ward means. It runs once the user has downloaded QoL, and stops cleanly until then.
- The cohort, lag and dose distributions are parameterised and **ASSUMED** until P-B/P-D, so the simulation reruns automatically when pilot values arrive.
- Actual SAR onsets are never merged in.
- Outputs:
  - an MDE table in `quality_reports/pilot/P-E_power.md`
  - publication-ready power-curve figures in `paper/figures/` (serif, colourblind-safe, no in-plot titles, PDF)
- The critic checks the implementation against memo §9.2 and §14.1 (coder hand-off notes: lag-bin control frames, exact-L splits, dip weights).

### WP4: QoL questionnaire lock (data-engineer → coder-critic), starts after the user's QoL download
- Build an item × wave harmonisation map for QoL III–7, mapped to the dimensions in memo §11: performance / procedural / normative legitimacy / trust / reliance / safety / victimisation, plus years at address and dwelling type.
- Close the open "?" cells, including whether trust in government appears before QoL7 (R1).
- Outputs: `data/cleaned/qol/item_map.csv` and `quality_reports/pilot/qol_item_harmonisation.md`.
- Any change to outcome definitions goes back to the strategist for the PAP lock and is logged in the journal.

### WP5: E3 Cape Town SRA onset compile (data-engineer → coder-critic)
- Download the City of Cape Town SRA polygons and the SRA budget spreadsheet.
- Compile onset dates using the memo's §5 onset hierarchy, and flag residential SRAs.
- Outputs: `data/cleaned/e3/sra_onsets.parquet` and `quality_reports/pilot/E3_sra_compile.md`, including a G3 feasibility count.

## Deferred (need data from pending requests or later pilot steps)
- P-A: the JRA register.
- P-C: perimeters for ≥30 closures. This needs WP1 output to geocode streets; it is the next round.
- P-D: imagery dating and first-time classification (manual/semi-manual; next round).
- A1-I and A2-X: need GCRO respondent locations and SAPS incident data.
- All gate decisions (G0–G4) and all estimation.

## Logging and conventions
- One research-journal entry per agent run. Append to `SESSION_REPORT.md`.
- `explorations/` is not used: these are production pipelines under the memo.
- No commits unless the user asks.
- Data stay gitignored.

## Checkpoint
Present the following, and ask for the user's sign-off on whether the pilot has passed:
- the P-B volume and type-mix results
- unit counts, including the effective J_C recount
- SAPS-arm MDEs
- the QoL harmonisation status
- the E3 feasibility count

The next round then covers P-C/P-D and costs the full gazette compile.

## Verification
- Each script runs end to end, exits 0 and writes its outputs. Tests exist for parsers and crosswalks: parsing the notice fixture, and checking that crosswalk weights sum to 1.
- WP1: validation-CSV agreement between parsed rows and the PDFs is reported.
- WP2: unit counts reconcile with the memo's §3.2 recount, or the difference is explained.
- WP3:
  - empirical size at δ = 0 is within [0.03, 0.08];
  - MDEs are reproducible given the seed;
  - the formula-based MDEs from §8 are reproduced as a sanity check.
- Each coder-critic score is ≥ 80.
- Figures follow `.claude/rules/content-standards.md` §2.

# Session Report — PSC Exposure

## 2026-09-29 — Status audit + data-feasibility round

**Operations:**
- Audited the existing Property24 Wayback scrape (data/raw/scraping/); backed up pre-fix parquets to data/raw/scraping/.cache/
- Workstream A (explorer → explorer-critic, 2 rounds): quality_reports/data_exploration_psc-exposure.md
- Workstream B (data-engineer → coder-critic, 2 rounds): fixed scripts/scraping/03, 04, config, 00 (code only), utils/{text_utils,url_utils,html_parser}.py; added tests (18) + fixtures, audit_classification.py, requirements-lock.txt; regenerated quality_reports/scrape_audit_2026-09-29.md
- Created quality_reports/research_journal.md; reviews saved under quality_reports/

**Decisions:**
- Data feasibility before more scraping — scrape can't locate estate boundaries (80 suburbs, mostly 2011–16)
- No commits yet — user instruction
- Geocoding (05) not run — blocked until design settled and location fields adopted

**Results:**
- Scrape: 18,332 rows / 17,406 listings; psc_flag 12.0% of described rows; construct flags (enclave 3.4%, guard service 9.3%, hardening 5.6%); Durbanville mislabel fixed
- Top architecture: Gauteng — gazetted security-access-restriction (road closure) register + OSM estates × GCRO QoL wards + SAPS precincts; spatial RD not feasible with public data
- JHB SAR policy: crime evidence required (endogenous timing); mandatory PSIRA-guarded gate

**Commits:**
- none (user asked to hold)

**Status:**
- Done: Discovery (data) — explorer-critic 89/100, coder-critic 93/100
- Pending: user decisions (construct, data requests, pilot, scope, precision labels); /strategize; carry-forward items N1–N6, R1 (data) and N1–N5 (code)

## 2026-09-30 — Strategy phase

**Operations:**
- /strategize: strategist → strategist-critic, 3 rounds (64 → 84 conditional → 94 unconditional)
- Memo: quality_reports/strategy_memo_psc-exposure.md; review: quality_reports/strategy_memo_psc-exposure_review.md
- Data request drafts: quality_reports/data_requests/2026-09-29_request_drafts.md (GCRO, JRA incl. renewal files + pre-2012 policy, SAPS incl. Cape Town)

**Decisions:**
- Headline = gazetted security access restrictions; pooled 3-metro estimate framed as "enclosure"; mandated-guarding claims only from JHB post-policy / SAPS incident data / A6 renewal design — user
- Scope Gauteng + Cape Town SRA module; JHB pilot first — user
- MDE thresholds 0.25 SD / 0.40 log / 0.25 log accepted as benchmark ratios — user
- Fund gazette + imagery compile if JRA refuses register; pursue A6 — user
- Ward (A1-W) and precinct (A2-P) arms are area-level ITT only; exposed-resident effects require GCRO SAL/GPS or SAPS incidents — strategist + critic
- Primary estimators: BJS imputation (A1, A2-P, indexed from onset with dip window re-timed out), CS for Cape Town SRAs, dCDH by lag bin as robustness/HonestDiD source

**Results:**
- Power: ward-level MDE on exposed residents ~1.4 SD at best (infeasible); A1-I needs ~155k newly enclosed dwellings for 0.25 SD; Cape Town SRA best-powered area design (~0.35 log)

**Commits:**
- none (user asked to hold)

**Status:**
- Done: Discovery (data 89, code 93), Strategy (94)
- Pending: strategist clean-up (r1, r2, r4, r5, record §18.7); user sends data requests; user confirms scrape precision labels; plan Execution (JHB gazette pilot, P-E power simulation, unit construction, questionnaire lock)

## 2026-10-01 — Execution Stage 0 (pilot): HANDOFF for next session

**Done (see quality_reports/research_journal.md for detail):**
- WP0 env: R pkgs + Tesseract (scripts/analysis/R-packages-lock.txt)
- WP1 gazette pilot: quality_reports/pilot/P-B_gazette_pilot.md (accepted after fix round)
- WP2 units: precinct clusters final; SWUs provisional pending Census SAL (quality_reports/pilot/units_report.md)
- WP5 Cape Town SRAs: 12 G3 candidates (quality_reports/pilot/E3_sra_compile.md)
- WP3 power sim: ran, but coder-critic 68/100 — results PROVISIONAL (quality_reports/pilot/code_review_power_r1.md)

**Next step (resume here):** WP3 power fix round — follow code_review_power_r1.md:
1. realistic treated share (cap J_T ≤ ~25% of pool; not-yet-treated as controls), 2. δ=0 size diagnostics,
3. randomisation inference inside the loop (gate-usable MDEs), 4. ≥500 draws for priority scenarios
(E1 pooled Low/Mid, E1 JHB Low, E3_all), 5. checkpoint key hash. Limits: ≤4 workers (14 exhausted RAM), ≤3h compute, run in background.
The previous fix agent hit the usage limit before changing any file.

**Blocked on user:** DataFirst downloads (QoL III–7 → data/raw/qol/; Census 2011 Community Profiles study 517 + SAL GIS → data/raw/units/census2011_saccp/); send data requests (quality_reports/data_requests/); check data/cleaned/gazette/validation_sample.csv and scrape precision labels.
**Then:** WP4 QoL harmonisation; pilot checkpoint (gate discussion). Nothing committed (user's choice).

## 2026-10-01 — WP3 P-E power fix round (done)

**Operations:**
- Rewrote `scripts/analysis/power/_power_functions.R`, `02_placebo_power.R`, `03_power_report.R` and `README.md`.
- Ran 02: 16 scenarios × 1,000 draws, 999 RI permutations per draw, 32 minutes on 4 workers.
- Ran 03, which writes the tables and figures in `paper/{tables,figures}/03_power_report/`. New outputs: `size_by_jc.tex` and `power_ri_vs_analytic_mid.pdf`.
- Updated `quality_reports/pilot/P-E_power.md` and saved `code_review_power_r2.md`.
- Removed the stale 200-draw checkpoints.

**Decisions:**
- RI is the simulated primary inference. WCR was not simulated, because no implementation works with BJS/CS.
- Treated share capped at 25% of in-scope clusters. This is ASSUMED, from critic r1; P-C replaces it.
- E3 is uncapped: its J_T is the real count of 12 candidates.

**Results:**
- RI size is 0.036–0.059 in every scenario. The analytic SE over-rejects at 0.10–0.30.
- RI MDEs (V1 area, asinh points):
  - E1 pooled: 0.18–0.19 (no cap: 0.157);
  - JHB-only: 0.46–0.48 (0.35 on feasible draws);
  - E3: 0.29 with 12 treated, 0.33 with 9.
- E3 exposure-scaled MDE is about 1.0, against the 0.25 threshold.
- Coder-critic r2 scored 84/100 (PASS).

**Commits:**
- none (user's choice)

**Status:**
- Done: WP3 (P-E SAPS arm) accepted.
- Pending, strategist: is RI primary for A2-P (memo §13.4); RI strata metro × bin; P-E deviations noted in §5.
- Pending, user: DataFirst downloads (QoL, Census SAL); send data requests; check the gazette validation sample and the scrape precision labels.
- Next: WP4 QoL harmonisation (after the QoL download); then the pilot checkpoint (gate discussion).

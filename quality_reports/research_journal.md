# Research Journal — PSC Exposure

### 2026-09-29 — Orchestrator
**Phase:** Discovery (data)
**Target:** Property24 scrape audit + phase transition
**Score:** N/A
**Verdict:** Scrape (~17.5k unique listings, 80 suburbs, 85% from 2011–16) can't locate estate boundaries; spatial RD not feasible with it. User chose data-feasibility round before further scraping.
**Report:** quality_reports/plans/2026-09-29_data-feasibility.md

### 2026-09-29 18:15 — data-engineer
**Phase:** Discovery (data), Workstream B
**Target:** scripts/scraping/03_merge_deduplicate.py, 04_classify_psc.py, config.py (+ tests/test_classify.py, audit_classification.py)
**Score:** N/A (awaiting coder-critic)
**Verdict:** 18,427 rows / 17,494 unique p24_id, 0 non-listing rows; psc_flag NA for 30.1% (no description), 15.6% flagged among described rows. Also found: titles are templated (psc_flag_title = 0 everywhere) and 2,798 "Durban" rows are Durbanville (Western Cape).
**Report:** quality_reports/scrape_audit_2026-09-29.md

### 2026-09-29 — coder-critic
**Phase:** Discovery (data) — Workstream B, round 1
**Target:** scripts/scraping/03_merge_deduplicate.py, 04_classify_psc.py, config.py, tests, audit
**Score:** 68/100 (FAIL)
**Verdict:** Mechanical fixes correct; blocking: psc_flag_any reintroduces NA-as-0, city mislabel (Durbanville→Durban) blocks geocoding, inconsistent dictionary widening/mixed constructs, precision check undone. Returned to data-engineer (round 2/3).
**Report:** quality_reports/code_review_scraper-fixes_r1_2026-09-29.md

### 2026-09-29 — explorer
**Phase:** Discovery (data) — Workstream A
**Target:** Treatment/outcome data sources for PSC exposure
**Score:** pending explorer-critic
**Verdict:** Top-ranked: Gauteng panel — gazetted road-closure register + OSM-reconstructed estates (treatment) × GCRO QoL wards + SAPS precincts (outcomes); supports staggered DiD / ward-precinct cross-section. Boundary RD infeasible with public data.
**Report:** quality_reports/data_exploration_psc-exposure.md

### 2026-09-29 — explorer-critic
**Phase:** Discovery (data) — Workstream A, round 1
**Target:** quality_reports/data_exploration_psc-exposure.md
**Score:** 70/100 (FAIL)
**Verdict:** Arch 1 (Gauteng SAR + OSM × GCRO QoL + SAPS) directionally right but SAR-timing DiD asserted not shown — no first-approval counts, reverse causality absent, treatment-induced QoL non-response. Returned to explorer (round 2/3).
**Report:** quality_reports/data_review_explorer-critic_r1_2026-09-29.md

### 2026-09-29 19:40 — data-engineer (round 2)
**Phase:** Discovery (data), Workstream B
**Target:** 03/04/config + utils/{text_utils,url_utils}.py, 00 + html_parser city logic, 05 header note, tests (18 + 53-snippet fixture), audit_classification.py, requirements-lock.txt
**Score:** N/A (awaiting coder-critic round 2)
**Verdict:** Addresses B1-B12. 18,332 rows / 17,406 listings. `city` repaired for 2,780 rows (Durbanville → Cape Town). psc_flag (plan scope) 12.0% of described rows, 13.5% residential; construct flags added; 4,967 ?ListingNumber= ids saved as stubs. Model-coded precision (not blind): psc_flag 25/25 any construct, 10/25 enclave, 3/25 commercial.
**Report:** quality_reports/scrape_audit_2026-09-29.md

### 2026-09-29 — coder-critic (round 2)
**Phase:** Discovery (data) — Workstream B, round 2
**Target:** scripts/scraping/ (03, 04, config, utils, tests, audit)
**Score:** 93/100 (PASS)
**Verdict:** B1–B12 fixed, no regressions. Minor open items N1 (property_use substring bugs), N2 (lenient enclave coding), N3–N5 — non-blocking; N1/N4 to fix before scrape feeds strategy or geocoding.
**Report:** quality_reports/code_review_scraper-fixes_r2_2026-09-29.md

### 2026-09-29 — explorer (round 2)
**Phase:** Discovery (data) — Workstream A, round 2
**Target:** quality_reports/data_exploration_psc-exposure.md
**Score:** pending explorer-critic round 2
**Verdict:** All 11 items addressed. JHB SAR policy verified: crime evidence required (timing endogenous by design) and PSIRA-guarded gate mandatory (enclosure bundles PSC). First-approval count in 2009–24 still unknown; go/no-go threshold + JHB pilot proposed. Three treatment arms separated (SAR / estates / CT SRA).
**Report:** quality_reports/data_exploration_psc-exposure.md

### 2026-09-29 — explorer-critic (round 2)
**Phase:** Discovery (data) — Workstream A, round 2
**Target:** quality_reports/data_exploration_psc-exposure.md
**Score:** 89/100 (PASS)
**Verdict:** All 11 R1 items addressed; Arch 1 sound as a conditional design. Carry forward to /strategize: go/no-go & pilot inconsistencies (onset window, uncalibrated E≥0.10, pilot can't identify first-time closures), gazette rate ~50–240/yr, T9 stale, QoL pre-wave items unchecked.
**Report:** quality_reports/data_review_explorer-critic_r2_2026-09-29.md

### 2026-09-29 — Orchestrator
**Phase:** Discovery → Strategy (checkpoint)
**Target:** Data-feasibility round
**Score:** Data quality component 89 (explorer-critic); scrape code 93 (coder-critic)
**Verdict:** Both workstreams pass. Awaiting user decisions on construct, data requests, pilot, scope, and scrape precision labels before /strategize.
**Report:** quality_reports/plans/2026-09-29_data-feasibility.md

### 2026-09-29 — User decisions (Discovery → Strategy checkpoint)
**Phase:** Strategy (entry)
**Target:** Design scope
**Score:** N/A
**Verdict:** (1) Headline construct = gazetted road closures with mandated private guarding (E1), conditional on pilot; (2) send GCRO respondent-location, JRA register, and SAPS incident-data requests now; defer Afrobarometer geocodes; (3) scope = Gauteng core + Cape Town SRA module, AB national later; (4) JHB gazette pilot before full register compile.
**Report:** quality_reports/data_review_explorer-critic_r2_2026-09-29.md

### 2026-09-29 — strategist
**Phase:** Strategy
**Target:** quality_reports/strategy_memo_psc-exposure.md
**Score:** pending strategist-critic
**Verdict:** Power analysis: RQ1 ward-ITT cannot credibly identify effects on exposed residents (MDE_exposed ~2 SD mid scenario); GCRO SAL/GPS + SAPS incidents are the binding upgrades; CT SRA (E3) likely best-powered RQ2 design. Estimators: BJS imputation (RQ1), dCDH continuous/non-absorbing (RQ2), CS (E3). Pilot redesigned (JHB continuous windows, SAR size, first-time audit); MDE-based go/no-go per arm.
**Report:** quality_reports/strategy_memo_psc-exposure.md

### 2026-09-29 — strategist-critic
**Phase:** Strategy — round 1
**Target:** quality_reports/strategy_memo_psc-exposure.md
**Score:** 64/100 (REVISE)
**Verdict:** All §7 arithmetic reproduces; CRITICAL C1 — primary dCDH anchors on the dip window (mean-reversion bias toward "SARs work"). Major: stock-unit treatment definition, control-pool comparability, gate logic vs exposed-effect claims, overstated A2-P power, E3 under-designed, no directional hypotheses. Returned to strategist (round 2/3).
**Report:** quality_reports/strategy_memo_psc-exposure_review.md

### 2026-09-29 — strategist (round 2)
**Phase:** Strategy — round 2
**Target:** quality_reports/strategy_memo_psc-exposure.md
**Score:** pending strategist-critic round 2
**Verdict:** C1 fixed (re-timed onset: min(application−12m, onset−24m); re-timed dCDH primary). A1-W/A2-P now ITT-only by design; A1-I/A2-X (restricted data) are the only exposed-effect routes; E3 fully designed; directional hypotheses + interpretation matrix; new conditional A6 guard-onset-at-renewal design.
**Report:** quality_reports/strategy_memo_psc-exposure.md

### 2026-09-29 — strategist-critic (round 2)
**Phase:** Strategy — round 2
**Target:** quality_reports/strategy_memo_psc-exposure.md
**Score:** 84/100 (APPROVE, conditional)
**Verdict:** C1, M1–M9 resolved; power arithmetic reproduces. Conditional on patching N-M1 (event-time indexing when G−G̃ varies) and N-M2 (pre-window in-panel switchers) before A1-W/A2-P estimation code; N-M3 cell sparsity and N-M4 A6 exogeneity to fix in same pass. Pilot, P-E, unit construction may start now.
**Report:** quality_reports/strategy_memo_psc-exposure_review.md

### 2026-09-30 — User decisions (Strategy)
**Phase:** Strategy
**Target:** strategy_memo_psc-exposure.md §18
**Score:** N/A
**Verdict:** (1) MDE thresholds accepted as proposed (0.25 SD attitudes / 0.40 log SAR crime / 0.25 log CT SRA), reported as benchmark ratios; nulls interpreted via TOST. (2) Pooled 3-metro headline framed as "enclosure"; "mandated guarding" only from JHB post-policy subset, A2-X, A6. (3) If JRA refuses register: fund continuous gazette + imagery compile. (4) Pursue A6: renewal histories + pre-2012 policy added to JRA request. Also adopted (strategist rec., critic agreed, user did not object): A1-W as secondary appendix ITT; comparable common-support controls; no reframing before gate; Cape Town in SAPS inquiry.
**Report:** quality_reports/data_requests/2026-09-29_request_drafts.md (JRA draft updated)

### 2026-09-30 — strategist (round 3, targeted patch)
**Phase:** Strategy
**Target:** quality_reports/strategy_memo_psc-exposure.md
**Score:** pending strategist-critic targeted check
**Verdict:** N-M1: post effects indexed from G, BJS-by-(t−G) primary for A2-P, re-timed dCDH by lag bin as robustness/HonestDiD. N-M2: cohort classes, pre-window cohorts kept as treated/never controls. N-M3/N-M4, n1–n8, §18 ratios addressed.
**Report:** quality_reports/strategy_memo_psc-exposure.md

### 2026-09-30 — strategist-critic (round 3, targeted)
**Phase:** Strategy — final
**Target:** quality_reports/strategy_memo_psc-exposure.md
**Score:** 94/100 (APPROVE, unconditional) — Identification validity component
**Verdict:** N-M1/N-M2 resolved in text and code; BJS-primary for A2-P appropriate for the absorbing first-switch ITT. Minor: r1 A6 sample rule/Wald assumptions, r2 BJS long-PT robustness, r3 code defects (coder hand-off), r4 restore §6/§7 detail dropped in rewrite, r5 cosmetic. Strategy phase passes; execution may begin.
**Report:** quality_reports/strategy_memo_psc-exposure_review.md

### 2026-09-30 — strategist (round 4 clean-up) + Orchestrator
**Phase:** Strategy → Execution (transition)
**Target:** quality_reports/strategy_memo_psc-exposure.md
**Score:** 94/100 stands (clean-up of minor items; orchestrator verified r4 restorations, §18 decisions recorded, section structure intact)
**Verdict:** Strategy phase complete. Execution may begin: pilot P-A..P-E, unit construction, questionnaire lock; estimation code later gated on G0–G4.
**Report:** quality_reports/strategy_memo_psc-exposure.md

### 2026-09-30 — Orchestrator
**Phase:** Execution (Stage 0: pilot + data foundations)
**Target:** quality_reports/plans/2026-09-30_execution-stage0.md
**Score:** N/A
**Verdict:** Plan approved. WP0 done (R: arrow 25.0.1, DIDmultiplegtDYN 2.4.0, pdftools 3.9.1 installed; Tesseract 5.5.0 already present, off PATH; lock files written). WP1 (gazette pilot), WP2 (units), WP5 (CT SRA onsets) dispatched in parallel; WP3 (power sim) waits on WP2; WP4 (QoL harmonisation) waits on user's DataFirst download.
**Report:** scripts/analysis/R-packages-lock.txt

### 2026-09-30 15:40 — data-engineer (WP2 units)
**Phase:** Execution (Stage 0 pilot, data foundations)
**Target:** scripts/cleaning/units/ (00-04, helpers, tests); data/cleaned/units/
**Score:** N/A (pending coder-critic)
**Verdict:** Precinct clusters final: 84 in-scope clusters in 3 GP metros (JHB 34, TSH 25, EKU 25) + CPT 55; 65 GP never-split. SWUs only PROVISIONAL (GHSL weights): memo rule collapses to 94 GP SWUs (vs ~310 assumed) because the 2011->2016 redelimitation chains wards -- strategist decision needed. SAL covariates blocked on manual DataFirst 517 download.
**Report:** quality_reports/pilot/units_report.md

### 2026-09-30 — data-engineer + Orchestrator (WP1 gazette pilot, P-B)
**Phase:** Execution (pilot)
**Target:** scripts/cleaning/gazette/, data/cleaned/gazette/
**Score:** pending coder-critic (single round, simplified mode)
**Verdict:** 1,199 issues / 40k pages, 0 fetch failures; 215 SAR notices (144 intent, 41 final, 12 renewal); Gauteng ~63 (W1) / ~86 (W2) notices/yr, JHB ~43/69. JHB refs not chronological (ρ≈0.14); s.4.7 counts in 4 notices, PSC provider in 1 → size/provider must come from perimeters/JRA. Full compile ~11.9k issues, ~40% notices need manual reading. G0(b) not attainable from gazettes alone. Orchestrator finished after rate-limit: wrote report_template.md and regression tests (3 pass).
**Report:** quality_reports/pilot/P-B_gazette_pilot.md

### 2026-09-30 — data-engineer (WP2 units)
**Phase:** Execution (pilot)
**Target:** scripts/cleaning/units/, data/cleaned/units/
**Score:** pending coder-critic (single round)
**Verdict:** Precinct clusters final: 84 Gauteng (JHB 34, TSH 25, EKU 25) + 55 CPT, all active FY2005/06–2025/26. Ward counts match memo. SWUs provisional (GHSL) and SAL covariates blocked on user download of Census 2011 Community Profiles (DataFirst study 517). Tests pass (2 skipped pending SAL).
**Report:** quality_reports/pilot/units_report.md

### 2026-09-30 — data-engineer + Orchestrator (WP5 Cape Town SRA onsets)
**Phase:** Execution (pilot)
**Target:** scripts/cleaning/e3/, data/cleaned/e3/
**Score:** pending coder-critic (single round)
**Verdict:** 60 SRAs (24 residential); onsets from budget-annexure levy lines, 44 FY-exact; 16 residential G3 candidates with first stage (≥10 threshold) — G3 plausible on counts, J_C check pending SAL/WP2 overlay; failed-SRA controls largely unavailable publicly. Orchestrator re-ran 05, wrote tests (5 pass) and report after rate-limit interruption.
**Report:** quality_reports/pilot/E3_sra_compile.md

### 2026-09-30 — coder-critic (Stage-0 pilot, single round)
**Phase:** Execution (pilot)
**Target:** scripts/cleaning/{gazette,units,e3}/
**Score:** WP1 74 FAIL · WP2 81 PASS · WP5 77 FAIL
**Verdict:** No crashes; silent-failure and recall gaps: gazette validation measures precision only, W2 volume a lower bound (archive gaps); SRA parse failures read as absences, G3 first stage too loose. Fix round dispatched (sonnet).
**Report:** quality_reports/pilot/code_review_stage0_r1.md

### 2026-09-30 — data-engineer (Stage-0 fix round 1)
**Phase:** Execution (pilot)
**Target:** scripts/cleaning/{gazette,units,e3}/ (all blocking items from code_review_stage0_r1)
**Score:** N/A (awaiting coder-critic re-review)
**Verdict:** Gazette: recall strata added, stage precedence fixed (5 intent -> final), W2 2022 gaps revised from 79 to 17-21 real ones; units: SAL schema guards + fixture test, E3-off and 2014-2025 checks (clusters unchanged); E3: G3 candidates 16 -> 12 with first stage within onset+2 (11 at 0.7 threshold). All three test suites pass.
**Report:** quality_reports/pilot/P-B_gazette_pilot.md, units_report.md, E3_sra_compile.md

### 2026-09-30 — Orchestrator (Stage-0 fix round accepted)
**Phase:** Execution (pilot)
**Target:** scripts/cleaning/{gazette,units,e3}/
**Score:** accepted without second critic round (lean mode, user-approved 2026-09-30); all blocking items addressed, tests re-run by orchestrator: gazette 3/3, E3 9/9, units 42 pass / 2 skip (SAL)
**Verdict:** Gazette: stages 139 intent / 46 final; W2 coverage 95.4% (gaps overstated before); volumes flagged as lower bounds. E3: G3 candidates with first stage within onset+2 = 12 (11 at 0.7 residential cut) — narrow margin over ≥10. Units: clusters unchanged; E3-off sensitivity added.
**Report:** quality_reports/pilot/code_review_stage0_r1.md

### 2026-09-30 — coder + Orchestrator (WP3 P-E SAPS power simulation)
**Phase:** Execution (pilot)
**Target:** scripts/analysis/power/, quality_reports/pilot/P-E_power.md
**Score:** pending coder-critic (single round)
**Verdict:** Cluster-robust SEs over-reject (size 0.08–0.23 at nominal 0.05) → WCR/RI must be primary inference for SAPS arms. Size-adjusted area MDEs (V1): E1 pooled 0.18–0.30 log, JHB-only 0.32–0.39, E3 0.28; exposure-scaled E3 ≈1.06 (fails user's 0.25 threshold; memo formula had 0.36). Simulated MDEs ~2–3× memo formulas (σ_V1 0.19, ρ 0.70 vs assumed 0.12/0.3–0.5). Control pool binds: cell rule drops 60% of switchers in High scenarios. Agent stalled; orchestrator killed thrashing 14-worker run, added per-scenario checkpointing, reran (4 workers, 200 draws).
**Report:** quality_reports/pilot/P-E_power.md

### 2026-09-30 — coder-critic (WP3 power simulation, round 1)
**Phase:** Execution (pilot)
**Target:** scripts/analysis/power/
**Score:** 68/100 (FAIL)
**Verdict:** No leakage; design mostly faithful. But treated share of pool ~60% (unrealistic) makes Mid/High J_C and cell-rule results artifacts; size-adjusted MDEs use an oracle critical value; actual inference (RI/WCR) not simulated; only 200 draws. P-E MDEs reported earlier are PROVISIONAL — not for gate decisions. Fix round dispatched.
**Report:** quality_reports/pilot/code_review_power_r1.md

### 2026-10-01 — Orchestrator (WP3 P-E power fix round, inline)
**Phase:** Execution (pilot)
**Target:** scripts/analysis/power/ (_power_functions.R, 02_placebo_power.R, 03_power_report.R, README.md)
**Score:** N/A (scored by coder-critic r2 below)
**Verdict:**
- Changes: treated-share cap 25%; per-draw range rule; fixed-point cell rule that counts not-yet-treated controls; BJS and CS rewritten as linear weight vectors, checked against the packages on every draw (max gap 4.4e-7); placebo-unit RI with 999 permutations inside the loop; 1,000 draws for all 16 scenarios; checkpoints keyed on a hash; per-scenario seeds.
- RI size is 0.036–0.059 everywhere. The analytic SE over-rejects at 0.10–0.30: the excess tracks J_T, and neither the bin FE nor the cell rule drives it.
- RI MDEs (V1 area): E1 pooled 0.18–0.19; JHB-only 0.46–0.48 (0.35 on feasible draws); E3 0.29.
- E3 exposure-scaled MDE is about 1.0, against the 0.25 threshold.
- Run time: 32 minutes on 4 workers.
**Report:** quality_reports/pilot/P-E_power.md

### 2026-10-01 — coder-critic (WP3 power simulation, round 2)
**Phase:** Execution (pilot)
**Target:** scripts/analysis/power/
**Score:** 84/100 (PASS)
**Verdict:**
- All H1–H4 items are fixed. The linear-weight BJS/CS and the RI construction are verified correct.
- Remaining items were addressed by the orchestrator: an MDE conditional on feasible draws, the documented §9.2 pool deviation, NA handling, the non-estimable share, print calls and figure font.
- Open (strategist): whether RI is primary for A2-P, since WCR was not simulated; RI strata (metro × bin).
- Deferred: package versions in the checkpoint key.
**Report:** quality_reports/pilot/code_review_power_r2.md

### 2026-10-28 22:45 — Orchestrator (scope lock + D1 timing check)
**Phase:** Strategy / Execution
**Target:** quality_reports/plans/2026-10-28_closure-timing-scope-lock.md; scripts/analysis/closure_timing/01_timing_check.R
**Score:** D1 = INCONCLUSIVE (pre-specified rule)
**Verdict:** Scope locked to the closure-timing design (data on disk only; other designs parked). D1, 44 applicant precincts x FY2014-2023, 379 intent notices: IRR per within-precinct SD of lagged log residential burglary 1.06 [0.90, 1.26]; burglary spike 1.09 [0.94, 1.26]. No detectable crime-driven timing at precinct level; large effects ruled out, moderate ones not. D2 (local pre-onset victimisation test) is now binding.
**Report:** scripts/analysis/closure_timing/output/01_timing_check.csv

### 2026-10-28 23:15 — Orchestrator (closure-timing exposure + main estimates)
**Phase:** Execution
**Target:** scripts/analysis/closure_timing/02_build_exposure.R, 03_main_estimates.R
**Score:** D2 = PASS (pre-onset victimisation +1.2 pp [-4.5, 6.9]); no kill triggered
**Verdict:** 575 notices -> 376 sites (194 street-level). Sample 6,133 respondents (inside 595, neighbours 2,739, suburb-level 986, comparison 1,813), 135 wards. Main: crime victim inside -3.7 pp (p=.10), neighbours -3.0 pp (p=.07); safe at night inside +0.16 (p=.08); satisfaction with govt security negative, n.s.; secondary outcomes null. Nothing significant at 5%. Event time vs 2+ yrs before onset: victimisation and night safety flat; satisfaction with govt security already -0.27 [-0.47,-0.06] in the 2 years before onset and -0.29 [-0.47,-0.11] 2-5 years after -> dissatisfaction precedes closures (selection), so the attitudinal outcome is not causally identified. Balance: comparison areas more Black African (67.5% vs 44.7% inside). Interview dates added to QoL harmonisation (V/6/7). Known pipeline bug: QoL 7 ward codes are 2021 demarcation but treated as 2016 in the merge pipeline (this analysis uses EA-derived 2016 wards instead).
**Report:** scripts/analysis/closure_timing/output/; paper/tables/estimation/reg_closure_timing_{primary,secondary}.tex; paper/tables/descriptive/balance_closure_timing.tex; paper/figures/closure_timing_event_time.pdf

### 2026-10-29 — Main session (data cleaning)
**Phase:** Discovery (data)
**Target:** WC police personnel panel; Redpath & Nagia-Luddy (2015) tables
**Score:** N/A
**Verdict:** New WC station panel 2018-2022 (officers, vehicles; WCPP Q9) parsed, 151/151 stations matched to SAPS; Redpath Table 4 re-transcribed (old CSV was corrupt). With Redpath 2013 this gives WC officer counts for 2013 + 2018-2022.
**Report:** data/raw/wcpp_q9_2022/README.md; data/raw/redpath_nagia-luddy_2015/README.md

### 2026-10-29 — Main session (design screen)
**Phase:** Strategy (screen only; no estimation)
**Target:** Natural experiments on repo data, security/legitimacy angle
**Score:** N/A
**Verdict:** Recommended: load shedding x QoL interview dates (waves 6-7), needs Eskom hourly load-reduction series. Viable on disk: Zuma-resignation UESD in wave V (balance holds). Dropped: close ward elections, July 2021 unrest (GPSJS undated), alcohol ban, 67% consent RD, SRA-officer DiD, informal-housing cap.
**Report:** memory/project_natural_experiment_screen.md

### 2026-10-29 — Main session (data: load shedding)
**Phase:** Discovery (data)
**Target:** Load-shedding exposure for QoL wave 7
**Score:** N/A
**Verdict:** eskom-calendar HF dataset pulled (CC BY-NC-SA); exposure built for all 13,795 wave-7 respondents (national) and 57% (block). Feasibility: national hours keep 44% of variance after ward+month FE; block evening hours keep 64% after day FE. Balance: block design clean with day+ward FE; national design shows older respondents on heavy days (t~2.5) and fieldwork volume rises with load shedding (r=+0.24). Wave 6 not covered.
**Report:** data/raw/loadshedding/README.md

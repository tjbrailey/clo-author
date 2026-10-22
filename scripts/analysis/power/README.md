# scripts/analysis/power/ -- P-E placebo power simulation (SAPS arm)

Run these from the project root with R 4.6.1 (package versions in `scripts/analysis/R-packages-lock.txt`), in this order:

| Step | Script | Inputs | Outputs |
|---|---|---|---|
| 1 | `01_saps_panel.R` | `data/raw/units/saps/*` (WP2 downloads; the Q1-Q3 2025/26 workbooks are fetched if missing), `data/cleaned/units/station_to_cluster.parquet`, `precinct_clusters.gpkg` | `data/cleaned/power/saps_cluster_panel.parquet` (139 in-scope clusters x FY2005-2025) |
| 2 | `02_placebo_power.R` | the panel, `precinct_clusters.gpkg`, `data/cleaned/e3/sra_onsets.parquet` (timing only), `sra_polygons.gpkg` (used to exclude SRA clusters) | `data/cleaned/power/pe_draws.parquet` (RI and analytic rejections on the delta grid), `pe_diag_draws.parquet` (delta = 0 diagnostics), `pe_design_draws.parquet`, `pe_inputs.rds` |
| 3 | `03_power_report.R` | the step-2 outputs | `paper/tables/03_power_report/*.tex`, `paper/figures/03_power_report/*.pdf`, `data/cleaned/power/pe_mde_summary.rds` |

`_power_functions.R` contains:
- the design draw (treated-share cap, per-draw range rule, fixed-point cell rule counting not-yet-treated controls);
- the BJS and CS estimators, written as linear weight vectors;
- placebo-unit randomisation inference within metro;
- the package wrappers (`didimputation`, `did`, `fixest` TWFE) used at delta = 0;
- the memo S8 formula.

**Inference.** Both primary estimators are linear in the outcome, theta = sum(V * Y), so each draw builds V once. The injected-effect grid and the 999-permutation RI are then exact and cheap. The in-house estimate is checked against `didimputation` / `did` on every draw: `max_abs_diff_pkg` in `pe_mde_summary.rds` reports the agreement, and BJS differs only at fixest's demeaning tolerance, about 1e-7. MDEs use RI power. Analytic cluster-robust MDEs are shown for comparison only.

**Settings.**
- `PE_NDRAWS` (default 1000) and `PE_WORKERS` (default 4) are environment variables. Do not use more than about 4 workers: 14 exhausted RAM.
- All ASSUMED inputs (lag distribution, stock share, contiguity loss, treated-share cap, cohort sizes, dose) are in the `CFG` and `SC` lists at the top of `02_placebo_power.R`. Replace them with the P-B / P-C / P-D numbers and re-run.

**RNG.** Each scenario's seed comes from `CFG$seed` plus a hash of the scenario id, with an L'Ecuyer stream for each draw. A scenario's results therefore do not depend on which other scenarios run, on their order, or on scheduling.

**Checkpoints.** Checkpoints in `data/cleaned/power/intermediate/checkpoints/` are keyed on a hash of CFG, the scenario, the pool, the panel, the function source and the seed. Any change to these triggers a re-run.

**Deviation from memo §9.2 step 1:** the real switchers are not yet known, so the pools are all in-scope clusters, not "never-switchers on common support". The range rule is applied per draw. See `quality_reports/pilot/P-E_power.md` §5.

**Rule:** no real treatment onset is merged with outcomes. The E3 arm uses the 12 residential G3 onset years as a timing structure only, on Cape Town clusters that do not overlap any SRA polygon.

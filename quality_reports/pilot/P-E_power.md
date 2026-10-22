# P-E: Placebo power simulation, SAPS arm (E1 Gauteng, E3 Cape Town)

**Date:** 2026-10-01. This is the fix round after coder-critic r1 scored 68/100 (`code_review_power_r1.md`). It replaces the provisional 2026-09-30 run. **Coder-critic r2: 84/100, PASS** (`code_review_power_r2.md`); the r2 documentation and low-cost items are applied below.

**Code:** `scripts/analysis/power/`:
- `01_saps_panel.R`
- `02_placebo_power.R`
- `03_power_report.R`
- `_power_functions.R`

**Outputs:**
- Tables in `paper/tables/03_power_report/`:
  - `mde_main.tex`
  - `mde_sensitivity.tex`
  - `size_check.tex`
  - `size_by_jc.tex`
- Figures in `paper/figures/03_power_report/`:
  - three power-curve figures (area V1, murder, exposure-scaled V1);
  - a sensitivity figure;
  - `power_ri_vs_analytic_mid.pdf`.
- Summary data: `data/cleaned/power/pe_mde_summary.rds`.

**Run:**
- 16 scenarios × 1,000 draws.
- Placebo-unit randomisation inference (RI): 999 permutations within metro, on every draw.
- Each scenario has its own seed (`CFG$seed` + a hash of the scenario id).
- 32 minutes on 4 workers (R 4.6.1).

**Rule held:** placebo onsets only. No real SAR or SRA onset was merged with outcomes. E3 uses the 12 G3 onset years as a timing structure on non-SRA Cape Town clusters.

## What changed (critic r1 → fix)

| Critic item | Fix |
|---|---|
| **H1** Treated share was about 60% of the pool | Pools are now all in-scope clusters (E1P 84, E1J 34, E3 35). Reported switchers are capped at 25% of the pool (`cap_share`, ASSUMED; the P-C recount replaces it). The range rule is applied **per draw** to the overlap of switchers and controls. A no-cap sensitivity (memo J_T = 40) is reported. Realised J_C is shown next to the memo's J_C. |
| **H2** Only 200 draws | 1,000 draws for every scenario. MDE bootstrap CIs are now about ±0.005–0.04. |
| **H3** Oracle size-adjusted critical value | Removed. MDEs now use **RI power**, which real inference also has. |
| **H4** Analytic SE instead of the memo's inference | Placebo-unit RI is simulated inside the loop (memo §13.2: primary for A3 and whenever J_T < 20, which holds for every capped scenario). Analytic MDEs are kept for comparison only. WCR was not simulated: §13.2 makes RI primary at these J_T. |
| MED: not-yet-treated units not counted as controls | The cell rule counts every unit with G̃ > t as an eligible control. It is iterated to a fixed point, because a dropped switcher stops being a control. Mean not-yet-treated controls are reported. |
| MED: outcome is asinh of counts | Kept. All effects are labelled "asinh points". For counts of the size in this panel they approximate log points; they are not the memo's index or rates. |
| MED: CS for E3 | CS is unconditional with not-yet-treated controls and universal base G̃−1. The aggregation weights by ℓ are as in `did::aggte`, with equal weight across ℓ. With one metro and no stock bins, this has the same FE structure as E1 (unit + year). |
| MED: labels and checkpoint key | Tables use "$>$grid" (not reached) and "n.r." (not run). The checkpoint file name is a hash of CFG, the scenario, the pool, the panel, the function source and the seed. A label change re-ran only that scenario. |
| LOW items | `tryCatch(finally = stopCluster)` replaces the top-level `on.exit`. Bootstrap NA shares are kept (`frac_na_boot` ≤ 0.008). `cat` is gone. |

**Implementation note.** BJS imputation and unconditional CS are both linear in the outcome: θ̂ = Σ V·Y, with V fixed by the design. So each draw builds V once, and the δ grid and RI are exact (`bjs_V`, `cs_V`). On every draw the in-house estimate is checked against `didimputation::did_imputation` and `did::att_gt`. The largest gap is 4.4e-7 for BJS, which is fixest's demeaning tolerance, and 2e-15 for CS.

## 1. Size: RI is valid; the analytic SE is not

Rejection rate at δ = 0, nominal 5%. The Monte Carlo SE is about 0.007. Full tables: `size_check.tex` and `size_by_jc.tex`.

| Scenario | RI | Analytic SE (BJS/CS) | BJS without bin×FY FE | Static TWFE | SD(θ̂)/mean SE |
|---|---|---|---|---|---|
| E1 pooled (Low/Mid/High) | **0.043–0.045** | 0.135–0.160 | 0.145–0.164 | 0.053–0.064 | 1.35–1.39 |
| E1 JHB-only (Low/Mid/High) | **0.041–0.052** | 0.291–0.303 | 0.291–0.310 | 0.083–0.100 | 1.75–1.76 |
| E3 (12 / 9 / 5 treated) | **0.044–0.055** | 0.084–0.163 | n.r. | 0.075–0.114 | 1.06–1.27 |
| Cell rule off (Mid) | 0.054 | 0.161 | 0.166 | 0.057 | 1.39 |
| No treated-share cap (J_T kept 32) | 0.046 | 0.097 | 0.102 | 0.058 | 1.20 |

**Diagnostics (critic's list):**
- Over-rejection is **not** caused by the bin×FY FE: removing it changes nothing.
- Nor is it caused by the cell rule: turning the rule off gives 0.161.
- It tracks **J_T, not J_C**. By J_C bin, analytic size is 0.28–0.30 where mean J_T ≈ 5 (JHB-only draws) and 0.12–0.15 where J_T ≈ 18–27, for any J_C.
- The static TWFE cluster-robust test is close to nominal when pooled, so the problem is the BJS (and CS) analytic variance with few treated clusters.
- RI holds size in **every** scenario, inside the plan's [0.03, 0.08] criterion.

**Implication (unchanged from the provisional run, now confirmed):**
- Analytic SEs must not be used for inference in the SAPS arms.
- Placebo-unit RI should be the **primary** inference for A2-P, not only when J_T < 20. This is a memo §13.4 change for the strategist: today the reporting rule makes "cluster SE + WCR" primary for A2-P.

## 2. Minimum detectable effects (80% RI power, 1,000 draws)

Columns:
- Area MDEs are in asinh points; the area V1 value has a bootstrap 95% CI.
- Exposure-scaled MDEs are per unit of exposure.
- "Formula" is the memo §8.4 value.

| Scenario | J_T drawn → kept | J_C (memo) | Area V1 | Formula | Expo V1 | Formula | Murder | Formula |
|---|---|---|---|---|---|---|---|---|
| E1 pooled Low | 20 → 18.0 | 36 (30) | **0.191** [0.187, 0.196] | 0.084 | 74 | 29 | 0.262 | 0.209 |
| E1 pooled Mid | 21 → 18.8 | 36 (30) | **0.184** [0.178, 0.190] | 0.075 | 15.5 | 5.8 | 0.252 | 0.187 |
| E1 pooled High | 21 → 18.8 | 36 (30) | **0.184** [0.179, 0.190] | 0.070 | 5.8 | 2.0 | 0.258 | 0.175 |
| E1 pooled High+ | 21 → 18.7 | 36 (30) | n.r. | 0.070 | 3.6 | 1.2 | n.r. | 0.175 |
| E1 JHB-only Low | 8 → 4.5 | 11 (10) | **0.482** [0.446, 0.526] | 0.137 | 273 | 48 | 0.692 | 0.344 |
| E1 JHB-only Mid | 8 → 4.5 | 11 (10) | **0.468** [0.434, 0.521] | 0.122 | 59 | 9.5 | 0.707 | 0.305 |
| E1 JHB-only High | 8 → 4.6 | 11 (10) | **0.457** [0.426, 0.520] | 0.115 | 22 | 3.4 | 0.662 | 0.289 |
| E3, 12 treated (ΔE = 0.3) | 12 → 9.6 | 13 (18) | **0.287** [0.277, 0.296] | 0.108 | **1.01** | 0.36 | 0.487 | 0.270 |
| E3, 9 treated | 9 → 7.4 | 13 (18) | **0.334** [0.325, 0.344] | 0.118 | 1.20 | 0.39 | n.r. | 0.296 |
| E3 high-dose, 5 treated (ΔE = 0.6) | 5 → 3.8 | 11 (18) | **0.517** [0.490, 0.550] | 0.146 | 1.04 | 0.24 | n.r. | 0.366 |

**Feasible draws:**
- E1 pooled: 100%.
- E1 JHB-only: 84–85%, because the cell rule and the range rule leave fewer than 3 switchers in 15% of draws.
- E3: 99–100%; high-dose 86%.

Infeasible draws count as non-rejections in the headline MDE, which caps power at the feasible share. **Conditional on feasible draws**, the MDEs (`mde_main.tex`, "RI, feasible draws" column) are:
- JHB-only: area 0.35, exposure-scaled 14–163;
- E3 high-dose: area 0.42, exposure-scaled 0.77;
- unchanged elsewhere.

Feasibility should therefore be treated as a separate gate metric: G2 and G3 count J_T after the rules. No draw was non-estimable.

**Analytic MDEs** (`mde_main.tex`) are 7–30% smaller than the RI MDEs (E3 7%, E1 pooled about 19%, JHB-only about 29%). That gap is the false power of an over-rejecting test, so they must not be used.

**Sensitivities** (E1 pooled, area V1, RI; `mde_sensitivity.tex`):

| Variant | Area MDE |
|---|---|
| Baseline (Mid) | 0.184 |
| No stock bins | 0.179 |
| No contiguity loss (J_C 48) | 0.169 |
| Cell rule off | 0.187 |
| All L = 2 | 0.175 |
| **No treated-share cap (J_T 40 → 32 kept, J_C 26)** | **0.157** |

## 3. What this means for the gates (for the user's checkpoint; nothing decided here)

1. **The noise is worse than the memo assumed, and the simulated MDEs are about 2.2–2.6× the memo formula (pooled) and 3.5–4× (JHB).**
   - Residual SD is 0.19 against an assumed 0.12, and AR(1) ρ is 0.70 against 0.3–0.5.
   - The memo formulas themselves reproduce to within 0.001.
2. **The E1 pooled design (A2-P / G2) clears G2's count conditions in simulation.**
   - J_T kept is about 19 (≥ 15), J_C about 36 (≥ 15), with at least 4 clean pre-years by construction.
   - It detects area effects of about **0.18 asinh points (≈ 17%) or more on the targeted index**, and about 0.25 on murder.
   - At a 25% treated share, Mid and High are capped at 21 of 84 and give the same area MDE (0.184). Low (20 drawn, uncapped) gives 0.191. More gazetted closures help only if the real treated share is higher. The no-cap run (J_T 32) gives 0.157.
   - Whether 17% is a plausible *precinct-level* net effect is the substantive question. Alley-gating's ≈ −40% applies to the gated area itself, so it would be diluted at precinct level.
3. **E1 JHB-only fails G2** (J_T kept about 4.5, 15% of draws infeasible). This confirms the memo: A2-P must pool the three metros.
4. **Exposure-scaled E1 effects are unidentifiable at precinct level** (MDE ≥ 3.6 per unit of exposure). Exposed-resident crime effects need incident data (A2-X / G2′).
5. **E3 (G3).**
   - The area MDE is about 0.29 with 12 candidates and 0.33 with 9.
   - The **exposure-scaled MDE is about 1.0**, against the E3 exposure-scaled threshold (0.25 log). So G3 would license the area effect θ^P_E3 only, not the exposure-scaled claim.
   - The high-dose subset does not rescue it: 1.04 per unit of exposure (0.77 conditional on feasible draws), area MDE 0.52 (0.42). Both are well above 0.25.
   - Caveats:
     - simulated E3 draws its treated clusters *from* the non-SRA pool, so J_C (11–13) understates the real J_C (up to 35 non-SRA clusters minus contiguity);
     - the range rule drops about 2.3 of 12 switchers. The E3 MDEs are therefore conservative.
6. **Inference decisions for the strategist (before any gate uses these MDEs):**
   - (a) Should placebo-unit RI be the primary inference for A2-P (§13.4), not only for A3 and J_T < 20? WCR was not simulated: there is no BJS/CS-compatible implementation, so its size here is unknown.
   - (b) Should RI stratify by metro × stock bin in the real analysis? Bin is noise in the simulation, so metro-only strata are harmless here, but not with real data.

## 4. Open items

- Rerun when the P-B/P-D lag distribution, the P-C stock share, dose and **treated share** (replacing `cap_share` = 0.25), and the Census common-support covariates arrive. Config is at the top of `02_placebo_power.R`; checkpoints re-run only what changed.
- The QoL arm (A1) needs the user's QoL download (`03_qol_panel_power.R` not yet written).
- Not simulated:
  - WCR (no BJS/CS-compatible implementation; RI is primary at these J_T);
  - the E3 timing-permutation test;
  - the dynamic contiguity rule (a static 25% loss stands in).
- The outcome is asinh of counts, not the memo's §11 indices or rates. Rates would change σ and need the population denominators.

## 5. Deviations from the memo §9.2 protocol (documented)

1. **Pool.** Step 1 says "never-switchers on common support". The real switchers are not yet known (the register is pending), so the pool is all in-scope clusters, and real switchers' actual effects enter the placebo noise. This is probably conservative.
   - The range rule is applied per draw, to the overlap of switchers and controls.
2. **Common support** uses pre-period level and trend only. The Census covariates are pending.
3. **Contiguity** is a static 25% random loss of controls, not the dynamic rule.
4. **Inference** is RI only. WCR is not simulated (see §3.6).
5. **Outcome** is asinh of counts, not the §11 indices or rates.

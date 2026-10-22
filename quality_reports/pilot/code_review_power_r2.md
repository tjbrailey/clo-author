# Code review: P-E power simulation (coder-critic, round 2, MEDIUM-HIGH), 2026-10-01

**Score: 84/100 (PASS).** All round-1 HIGH items (H1–H4) are fixed, as are the MED and LOW items. Nothing was re-run; the critic read the code and the output tables only.

## Verified correct
- **BJS weights:** `bjs_V` is algebraically right. The pivoted-QR solve and the estimability check (`a` against Z0'Z0x) are correct.
- **CS weights:** `cs_V` matches `att_gt` (notyettreated, universal base) plus `aggte` dynamic aggregation, given L = 2. E3 asserts L = 2.
- **RI under each δ:** permuting the rows of Y0 + δD gives p0_r + δq_r, so `ri_grid` is the exact permutation statistic. Size of 0.041–0.055 confirms it.
- **Analytic SE shift-invariance** holds for BJS (every obs with w ≠ 0 shifts by δ) and for CS (the treated influence function is demeaned).
- **Cell rule:** applies the §3.2 rule-6 margins literally, counts only on-support kept units, and iterates to a fixed point.
- **Seeds and checkpoints:** the seed and stream design is sound; the checkpoint key covers CFG, SC, pool, BASE, function source and `run_draw`.

## Remaining issues and disposition (orchestrator, 2026-10-01)
| Sev | Issue | Disposition |
|---|---|---|
| MED | Infeasible draws count as non-rejections, so the JHB and E3 high-dose MDEs partly measure feasibility | **Fixed:** an MDE conditional on feasible draws is added (`mde_feasible`, a column in `mde_main.tex`), with feasibility reported as a separate metric. |
| MED | Pools are all in-scope clusters, not §9.2 "never-switchers on common support"; this deviation was not flagged | **Fixed (documented):** listed in P-E_power.md §5 and the README. |
| MED | RI stratified by metro only; bin is a real covariate in real data | **Open:** strategist decision (P-E §3.6b). |
| MED | WCR not simulated, yet RI is proposed as primary for A2-P | **Open:** strategist decision (P-E §3.6a). |
| LOW | `sum(rej_an)` has no `na.rm` | **Fixed:** `na.rm = TRUE`, and the failed-call count is reported (0). |
| LOW | Non-estimable share not reported | **Fixed:** `non_estimable` added to `design_sum` (0 in every scenario). |
| LOW | Shift-invariance not asserted in code | Not done. It is verified analytically by the critic and only affects the comparison-only analytic MDEs. |
| LOW | `print()` used for console output | **Fixed** in 03 and 02. |
| LOW | Figure `base_size` 11 | **Fixed:** 14. |
| LOW | Lines over 100 characters | Not done (style). |
| LOW | Checkpoint key leaves out package versions and includes `label` | Not done. Changing the key would force a full 32-minute re-run; it is deferred to the next substantive rerun (P-B/P-C/P-D inputs). |
| LOW | Write-up said Low/Mid/High were identical | **Fixed:** reworded (Low is uncapped, 0.191 vs 0.184). |

## Deductions
- Starting score: 100.
- Feasibility conflated with power: −5.
- Undocumented §9.2 deviation: −3.
- RI strata specification: −2.
- Console `print()`: −3.
- Style and figure size: −2.
- Minor robustness: −1.
- **Final: 84.**

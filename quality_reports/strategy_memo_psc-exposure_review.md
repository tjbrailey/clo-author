# Strategy Review, Round 1: strategy_memo_psc-exposure.md

**Date:** 2026-09-29 · **Reviewer:** strategist-critic · **Severity:** MEDIUM (Strategy)
**Score:** 64/100, so **REVISE**. There is 1 CRITICAL issue, 9 MAJOR and 11 MINOR. Fixing C1, M1–M3 and M8 alone recovers about 19 points.

## Headline assessment
- **The design concept is honest and strong.** Power is reported both for the area ITT and for exposed residents. The mean-reversion defence is layered: dip exclusion, an applicant stack, and F8/F11. QoL post-treatment selection is handled with Lee/Manski bounds and a reachable-population estimand. Gates are logged before outcomes are merged.
- **All §7 power arithmetic re-computes exactly.** The problems lie in the inputs and in which adjustments are carried through, not in the arithmetic.
- **About 45 citations were spot-checked** and all are correct. The items marked UNVERIFIED are flagged appropriately.

## Issue table
| # | Issue | Section | Severity | Deduction | Recommendation |
|---|---|---|---|---|---|
| C1 | The primary A2-P dCDH estimate anchors on F−1, which is inside the dip window. Exclusion appears only in robustness; "reference ℓ=−3" is unachievable; the code passes raw treatment. As written, the RQ2 estimate is measured from the dip trough, which biases it toward "SARs work". | §3.2, §4.2(1), §13 step 5 | CRITICAL | −6 | Make re-timed dCDH (switch at G−A, or at the application date) the primary. Report dip periods separately. Fix the table and the code. |
| M1 | Setting G_u = first-ever FT SAR drops wards with pre-existing stock from A1-W. This is inconsistent with the stock-bin switchers in A2-P, and it isn't reflected in power or the pilot. | §2.3, §2.6(i), §3.2, §7.2, §8.2 | MAJOR | −3 | Define in-window switchers the same way across arms, or accept the restriction and measure the zero-stock share in P-C. |
| M2 | The control pool: J_C = 350/80 can't be reached under a JHB-primary scope with stock and contiguity exclusions. The never-treated units that survive are probably townships and peri-urban areas, where parallel trends aren't credible. | §2.3, §6.3, §7.1, §7.4 | MAJOR | −4 | Recount J_C under the real rules. Impose common support on Census 2011 predictors. Make not-yet-treated units within stock bins the primary control. Report control composition. |
| M3 | Gate logic: a GO on G1/G2 licenses exposure-scaled claims that §1.2(b) forbids. G1 fails even at High+ (0.31 > 0.30), before applying π (×1.43), JHB D_w (×1.53) and estimator inflation. G1′ needs about 94k dwellings at JHB ward size, not 61k. | §7.2, §7.3, §8.3 | MAJOR | −3 | Redefine GO as an "exposure-scaled ITT" with τ_far/τ_ring bounds, or make A1-W ITT-only. Recompute with JHB D_w, π and inflation. |
| M4 | A2-P power is overstated. It uses the cumulative rather than the first-switch dose, P=Q=5 clean years is infeasible at the window edges, and serial correlation is ignored (Burlig, Preonas & Woerman 2020). | §7.4 | MAJOR | −2 | Use the first-switch 24-month dose and cohort-specific P/Q. Use serial-correlation-robust power, or placebo-simulation power in P-E. |
| M5 | The applicant design is under-specified. Approval is selected on spike severity (s.5.3); delayed controls become treated; withdrawals are endogenous; adjacent units are contaminated; rejected applicants remain in the never-treated pool. | §4.2(2), §14.1 | MAJOR | −2 | Specify window truncation, a decision rule for balance tests, withdrawal handling and a ring-distance rule. Drop failed applicants from the never-treated pool. |
| M6 | HonestDiD is fed BJS pre-trend coefficients, which don't share a reference period. Cohort 6 has only one clean pre-difference. | §4.2(4–5), §13 step 7 | MAJOR | −2 | Use CS `base_period="universal"` or Sun–Abraham for A1, and re-timed dCDH or CS-universal for A2. State how many pre-coefficients each bound uses. |
| M7 | A1-I uses SAL fixed effects in a repeated cross-section. This produces singletons, BJS drops treated observations, and it doesn't match the MDE counts. | §1.2(d), §3.2, §13 step 4 | MAJOR | −2 | Use perimeter-zone × SAR-group FE. Verify with GCRO whether sampling points are reused. |
| M8 | E3 is the causal core under NO-GO but is under-designed. There is nothing on consent-vote selection, pre-existing patrols, onset source, boundary misalignment, renewal/dissolution, failed-SRA controls, or overlap with about 12 treated units. | §2.7, §3.2 A3, §9 | MAJOR | −3 | Write an E3 subsection mirroring §4. Pre-specify the onset source. Report unconditional CS alongside DR. |
| M9 | There are no directional hypotheses, and the primary RQ1 item has an ambiguous sign (misattribution vs substitution). | §10.1 | MAJOR | −2 | Give expected signs per RQ and arm, plus an interpretation matrix conditioned on the safety first stage. Consider a municipal- or police-referent item as co-primary. |
| m1 | "Ward-mean SD" is mislabelled; the units are individual SD. | §7.2 | MINOR | −0.5 | Relabel. |
| m2 | ε_W ignores π; "most of Mid" contradicts the homogeneous scenario. | §2.6(ii), §7.2 | MINOR | −0.5 | Set ε_W = 1/(π·n̄_post) and fix the text. |
| m3 | The 19× illustration omits the ring term (R/ΔE ≈ 3–8) and the amplification of any ward-level bias. ΔE and R are collinear. | §1.2(b), §6.6 | MINOR | −1 | Extend the algebra and note that R is weakly identified in A1-W. |
| m4 | SAPS cohorts FY2010–12 predate the 2012 JHB guard mandate. | §2.1, §8.4 | MINOR | −1 | Restrict PSC claims to onsets after 2012, or verify the earlier policy. |
| m5 | The projection uses 6 years but the window is 5. | §8.1 | MINOR | −0.5 | Correct the range to 6–144. |
| m6 | Code plumbing: the G0 denominator; undefined `onset_precision_months`; horizon re-indexing; `wildrwolf` works with fixest only; Conley is applied only to TWFE; "largest SE" is used alongside WCR. | §12, §13 | MINOR | −1 | Fix. Use BJS weights for the spatial-HAC. |
| m7 | Several tests per RQ are labelled "primary", with no headline estimate or cross-arm rule. | §12.4 | MINOR | −0.5 | Pre-specify one headline estimate per RQ, conditional on the gate. |
| m8 | RI exchangeability is undercut by crime-driven timing. | §12.2 | MINOR | −0.5 | Interpret RI as a sharp-null test only; add placebo-unit RI. |
| m9 | A1 doesn't condition on the SAPS crime trajectory, which is the actual selection variable. | §4.2(3) | MINOR | −0.5 | Add the precinct pre-trajectory, mapped to SWU, to A1's CS-DR and matching. |
| m10 | E2 rate denominators create a mechanical composition effect. | §3.2 A4 | MINOR | −0.5 | Use counts in pre-existing areas. |
| m11 | The bibliography lacks all the methods references; the Sidebottom magnitude and the dCDH volume are pending. | §3, §7.4 | MINOR | −0.5 | Populate the bibliography before the writer phase. |

## Constructive alternatives
1. Make re-timed dCDH the primary for A2-P.
2. Use perimeter-zone FE for A1-I.
3. Restrict controls to common support, with not-yet-treated units within stock bins as the primary comparison.
4. **A "guard onset, walls constant" contrast:** renewals of pre-2012 closures under the 2012/2018 policy. This depends on the renewal files and compliance evidence.
5. Simulation-based power in P-E, using real panels and placebo onsets.

## Carry-forward resolution
N1, N2(a), N2(d), N3, N4, N5 and N6 are resolved. N2(b) and N2(c) are mostly resolved (gaps: π, JHB D_w, serial correlation). R1 is resolved procedurally; the questionnaire pull is still open.

## Decisions that belong to the user
1. The MDE thresholds (0.30/0.25 SD for attitudes; 0.40 log points for crime).
2. Whether A1-W is reported as a stand-alone area ITT or folded into a descriptive section.
3. Control comparability vs sample size (M2).
4. JHB-only vs pooled Gauteng for the E1 headline. This can wait until the Tshwane/Ekurhuleni policy read.
5. Paper framing under NO-GO: proceed now with E3/E2 as the causal core, or wait for the GCRO/SAPS requests.

---

# Round 2: 84/100, APPROVED (conditional)

**Date:** 2026-09-29. Every item was checked against the memo text and the code, not against the revision log.

- **Round-1 items:**
  - C1 and M1–M9 are resolved.
  - m1–m9 and m11 are resolved.
  - m10 is partly resolved; see n8.
  - The 55 BibTeX entries were spot-checked and are correct.
- **§8 power:** all recomputed and all reproduce. That includes the AR(1) factors ×1.677 (ρ=0.3) and ×2.378 (ρ=0.5), A1-I 98.5/√NS, 155k NS for 0.25 SD, and E3 0.354. P-E placebo simulation is the binding calculation.
- **Condition:** N-M1 and N-M2 must be patched before any A1-W/A2-P estimation code is written. A targeted check is enough; a full round 3 isn't needed. The pilot, P-E, unit/common-support construction and the questionnaire lock can start now.

| # | Issue | Severity | Deduction | Fix |
|---|---|---|---|---|
| N-M1 | G − G̃ = max(24m, L+12m) varies across units, but dCDH/CS/SA index effects from G̃. For long-lag units, "ℓ=0,1" are pre-installation processing years, so reversion enters the headline. The §3.4 BJS row contradicts the (correct) A1 code. | MAJOR (blocks A2-P code) | −4 | Anchor the baseline at G̃−1 and index post effects relative to G. BJS aggregated by t−G is a strong candidate for A2-P co-primary. For dCDH/CS/SA, use lag-bin estimation or restrict to G−G̃ ≤ 2 FY. Require ≥2 clean pre-waves per unit. |
| N-M2 | FT switches inside the panel but before the window (A1: 2013–mid-2018; A2: FY2006–09) aren't handled, and B_u is defined inconsistently. This contaminates the controls. | MAJOR (blocks code) | −3 | G_u = first FT switch after panel start. Keep pre-window cohorts as treated (never used as controls; not reported). B_u = closures active at panel start. Add a flag and count in P-C. |
| N-M3 | Metro × bin × wave cells hold about 2–7 controls. dCDH/BJS silently drop switchers that have none. | MAJOR | −2 | Bins {0,>0}, or additive FE. A minimum-controls-per-cell rule. Report switchers dropped. Mirror the cell structure in P-E. |
| N-M4 | A6's exogeneity is overclaimed. Only the scheduled expiry is mechanical: renewal is chosen and may need fresh crime evidence, timing is compressed to about 2012–14, and there may be anticipation. Walls aren't verified to be unchanged. | MAJOR | −2 | Switch at the scheduled first post-policy expiry (ITT). Keep lapsed closures in the sample. Treat renewal and guards as the first stage. Code physical changes from imagery. Add a timing-spread condition to G4. Soften objection 1. Label F12 a weak test. |
| n1 | TOST re-test after entropy balancing is vacuous. | MINOR | −1 | Use held-out moments and a floor on effective sample size. |
| n2 | HonestDiD `numPostPeriods=6` vs 8 dCDH effects. | MINOR | −1 | Pass all 8 and target ℓ=0..3 via `l_vec`. |
| n3 | Windows disagree (SAPS FY2010 vs g=2012; E3 FY2008 has 1 clean pre-year). | MINOR | −0.5 | One window per arm; cohorts that don't meet it go to sensitivity. |
| n4 | §8.2 J_T scenarios don't match the §3.2 recount. | MINOR | −0.5 | Relabel, or cap J_T. |
| n5 | A1-I zones overlap between SAR groups. | MINOR | −0.5 | Precedence in > ring > outer; exclude cross-exposed outer respondents. |
| n6 | G0 is in effect a register-or-imagery gate. | MINOR | −0.5 | State this explicitly (it drives the NO-GO probability if JRA refuses). |
| n7 | A3 placebo-unit RI is coarse. | MINOR | −0.5 | Report the number of distinct assignments; pair it with the timing test. |
| n8 | A4 fixed offset biases toward "estates raise crime". | MINOR | −0.5 | Label it as a bundle; bracket with the time-varying denominator. |

**Comments on §18:**
- Thresholds should be stated as ratios to their benchmarks: E1 0.40 is about 0.8× gating; E3 0.25 is about 2.5× the BID effect; A1-I 0.25 SD is too coarse for legitimacy effects (about 0.05–0.15 SD).
- Agree with A1-W as a secondary appendix ITT; common support with not-yet-treated units within bin; not reframing now; adding Cape Town to the SAPS inquiry.
- Pooling the 3 metros is necessary, but the pooled headline then measures "enclosure". "Mandated guarding" is carried only by the JHB post-policy subset, A2-X or A6.

**User decisions:**
(1) Thresholds as ratios to benchmark, and accepting that legitimacy is underpowered.
(2) Headline construct vs the pooled estimate.
(3) If JRA refuses: fund the gazette + imagery compile (6–12 weeks), or accept E1 as stock-only.
(4) Whether to pursue A6, which needs an extra JRA file request.

---

# Round 3 (targeted check): 94/100, APPROVED (unconditional)

**Date:** 2026-09-30. Checked against the text and §14 code.

- **N-M1 is resolved.** L_u = max(24m, L^app+12m). The baseline is set at G̃−1, effects are indexed by ℓ = t−G, and the dip is reported separately. The index mappings were verified for every estimator (BJS `wtr`, dCDH k→ℓ=k−1−L, CS e→ℓ=e−L, SA p→ℓ=p−L). The per-unit clean-pre rule is in place. HonestDiD takes 8 effects with `l_vec` selecting ℓ = 0..3.
- **N-M2 is resolved.** B_u counts only closures active at panel start; G_u is the first FT switch after panel start. `cohort_class` is one of {reported, pre_window, insufficient_pre, post_window, never}. Control eligibility is correct in the code.
- **N-M3, N-M4 and n1–n8 are resolved.** The recomputed MDEs check out (0.307 average; E1 0.083/0.075/0.070; JHB J_T cap 30 → 0.23).
- **BJS as the A2-P primary is appropriate** for the absorbing first-switch ITT, with dose as heterogeneity and non-absorbing robustness covered by current-status dCDH.
- **The whole-file rewrite dropped some content from §6/§7:** the trait list, the Lee trimming share and monotonicity, the calibration target, the refusal evidence and the 1 km displacement trigger.

| # | Issue | Deduction | Fix |
|---|---|---|---|
| r1 | The A6 primary drops closures with physical change, which conditions post-assignment. The Wald exclusion and monotonicity assumptions are unstated. | −1 | Keep all closures in the ITT; treat physical change as a first-stage or bundle component; use the no-change sample as robustness; state the assumptions. |
| r2 | BJS imputes Y(0) from the full pre-history, so it needs long-run parallel trends. The "only estimator" wording is overstated. | −1.5 | Add restricted-window (≥ G̃−6) and unit-trend BJS as mandatory robustness; match an L=2 BJS estimate against dCDH; soften the wording. |
| r3 | Code: lag-bin dCDH frames exclude the controls; `L` is undefined in the lambda and the ≥4 bin is heterogeneous; A1 builds only the ℓ=−1 dip weight. | −1.5 | Frame each bin as its switchers plus the shared controls; split by exact L; generate w for ℓ ∈ [−L_max, −1]. (Hand-off to the coder.) |
| r4 | §6/§7 detail lost in the rewrite. | −1 | Restore it. |
| r5 | The E3 row isn't rescaled to 0.307; the header date is stale. | −0.5 | Update. |

**The user's §18.7 decision (fund the compile) is not yet recorded in the memo.** A continuous gazette compile satisfies G0(a) but not G0(b), so the funded fallback must include imagery *dating* of installation for events that have only a final notice.

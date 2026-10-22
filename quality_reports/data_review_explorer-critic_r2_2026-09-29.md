# Data Assessment Review: explorer-critic, round 2

**Date:** 2026-09-29 · **Severity:** LOW (Discovery)
**Score:** 89/100, a **PASS** (round 1 scored 70).

## Verdict
All 11 round-1 items were checked against the revised text. They are all addressed, and 10 are fully resolved. Architecture 1 (the Gauteng SAR road-closure design) is **sound as a conditional design**: each of its conditions can now be tested.

Its main unaddressed risk is **scale**. SAR perimeters are small relative to Gauteng wards, so the ward-level QoL arm may be underpowered. The SAPS precinct arm is probably the stronger causal leg. A GCRO request for GPS or small-area locations matters more than the report's ranking suggests.

## Carry-forward items for /strategize (−11)
| # | Issue | Deduction |
|---|---|---|
| N1 | The gazette rate estimate is over-precise. 7 notices in 3 issues gives about **50–240/yr**, not 100–120. 3 of the 7 notices are unclassified. JHB reference numbers aren't chronological (the 2024 intent notice is No. 250, while the 2021 notice is Ref 438), so the "renewal" inference is weakened. The 2007 zero may be a missing contents page. | −2 |
| N2 | The go/no-go rule and the pilot are inconsistent. (a) The ≥2 pre-wave rule needs onset from about 2016, not 2014. (b) E ≥ 0.10 hasn't been calibrated: a ward has about 9–10k dwellings, so it needs about 1,000 enclosed dwellings; calibrate from s.4.7 affected-persons counts. (c) Power has to be stated in *exposed* respondents (roughly a tenfold dilution). (d) Non-consecutive pilot years can't identify first-time closures; that needs the JRA register or a continuous series. The pilot should instead estimate notice volume, type mix and SAR size. | −4 |
| N3 | "E1 = PSC exposure" is verified only de jure, for JHB under the 2012/2018 policy. Tshwane and Ekurhuleni are unverified, and SAHRC reports non-compliance. | −1 |
| N4 | The reasoning in the per-wave table for ward use is inconsistent (QoL II vs 6/7). QoL6 under COVID should be marked conditional. | −1 |
| N5 | T9/§10 are stale against the passed Workstream B. Figures should be 18,332/17,406 rows/listings and 40% enclave precision, the Durban label is now fixed, and the Gauteng enclave signal is thin. Use `guard_service_flag` as the Gauteng covariate. | −1 |
| N6 | Under a NO-GO, the fallback (E2+E3) is mainly a violence design; RQ1 falls back to a cross-section. | −1 |
| R1 | Trust in government is verified only in QoL7. Pull the public QoL III–6 questionnaires before /strategize. | −1 |

## Critic's view on the explorer's recommendations
1. Make E1 the headline construct: agree, but conditional on the pilot, since the guarding mandate is de jure and JHB-only.
2. Send the GCRO and JRA requests now and defer AB: agree. Also send a low-cost SAPS incident-data inquiry now, because it is the only route to a boundary design for RQ2.
3. Pilot first: agree, but redesign it as in N2.
4. Gauteng core plus the Cape Town SRA module, with AB later: agree. The CT module only helps with violence outcomes.
5. Freeze the scrape: agree, conditional on the user confirming the precision labels and on using `guard_service_flag` as the covariate.

## Rejection table: see the round-1 review. Added this round: gazette notice dates used as onset dates without first-seen coding (a deal-breaker unless coded against a continuous series or the JRA register).

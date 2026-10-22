# Strategy Memo: PSC Exposure — Enclosure with Mandated Private Guarding, State Attitudes and Violence (South Africa)

**Agent:** strategist. I created this memo and do not score it; review is by strategist-critic at SEVERITY: MEDIUM.

**Round:** 4, a clean-up before the PAP lock.

| Round | Score | Outcome |
|---|---|---|
| 1 | 64/100 | Revise |
| 2 | 84/100 | Conditional |
| 3 | 94/100 | Approved unconditionally |

Reviews are in `quality_reports/strategy_memo_psc-exposure_review.md`. Revision logs for rounds 2–4 are at the end.

**Date:** 2026-09-30 · **Phase:** Strategy

**Inputs:**
- `quality_reports/data_exploration_psc-exposure.md` (explorer r2, 89/100)
- `quality_reports/data_review_explorer-critic_r2_2026-09-29.md` (carry-forward items N1–N6, R1)
- `quality_reports/scrape_audit_2026-09-29.md`
- `quality_reports/code_review_scraper-fixes_r2_2026-09-29.md`
- `quality_reports/research_journal.md` (user decisions)
- `quality_reports/strategy_memo_psc-exposure_review.md` (rounds 1–3)
- `.claude/references/domain-profile.md`

**Fixed user decisions (not re-opened):**
1. Headline treatment is E1: gazetted Gauteng security access restrictions (SARs) with mandated guarding by PSIRA-registered providers, conditional on the pilot. The guarding mandate is verified de jure only for JHB.
2. Data requests are out now to GCRO (GPS/SAL, refusal metadata, gated layer), JRA (SAR register) and SAPS (incident data). Afrobarometer (AB) geocodes are deferred.
3. Scope: Gauteng core plus a Cape Town Special Rating Area (SRA) module (E3, violence outcomes only). AB national coverage comes later.
4. The JHB gazette pilot runs before the full register compile.

User decisions taken on 2026-09-30 are recorded in §18.

**Evidence labels:** as in the data assessment (VERIFIED, VERIFIED\*, SECONDARY, SNIPPET, UNVERIFIED, ESTIMATE), plus:
- **ASSUMED:** a modelling parameter I chose. It will be replaced by pilot or data values before any go/no-go decision.
- **UNVERIFIED** in a citation: the venue, volume or effect size is not confirmed.

**Notation** (per the domain profile):

| Symbol | Meaning |
|---|---|
| $u$ | Unit: stable ward unit (SWU) $w$, or precinct cluster $c$ |
| $t$ | Period: QoL wave, or SAPS financial year (FY) |
| $B_u$ | Baseline stock: closures active at panel start |
| $E_{ut}$ | SAR dwelling-share intensity |
| $\Delta E_u$ | First-switch dose: the first-time (FT) increment within 24 months of $G_u$ |
| $R_{ut}$ | Share of dwellings in the 0–500 m ring |
| $G_u$ | Onset: first FT switch after panel start |
| $\tilde G_u$ | Re-timed switch: start of the dip/processing window |
| $L_u=G_u-\tilde G_u$ | Lag between re-timed switch and onset |
| $\ell=t-G_u$ | Event time relative to **onset** |
| $D_i$ | Respondent inside a perimeter |
| $r_i$ | Signed distance to the perimeter (m) |
| $\tau$ | Effect on exposed residents |
| $\theta$ | Area-level ITT |
| $\gamma$ | Cross-unit spillover |
| $W$ | Row-normalised spatial weights (queen contiguity; 2 km inverse distance as the alternative) |
| $\pi$ | Survey retention of exposed dwellings after onset |

---

## 0. Bottom line

1. **Ideal experiment.** Randomise SAR authorisation among neighbourhoods that apply. Then run a panel survey of residents inside, next to and far from each perimeter, and collect geocoded incidents by zone, before and after authorisation.

2. **How far the data are from that ideal:**
   - Assignment is selected on recent crime (s.4.4) and on cohesion (the 67% consent rule, s.4.8).
   - Onset is not yet observed.
   - Outcomes are observed only for areas one to two orders of magnitude larger than a SAR: JHB wards hold about 14.5k dwellings and precincts about 35k (ASSUMED).
   - Legitimacy items are sparse across survey waves.
   - Few comparable control units exist (§3.2).

3. **Design.**
   - **Treatment and comparison.** Heterogeneity-robust staggered designs on the first FT switch after panel start, defined the same way in every E1 arm. Comparisons are made within coarse stock bins {0, >0}, among units on common support, with not-yet-treated units as the primary comparison. Pre-window cohorts stay in the data as treated but never serve as controls (§2.3).
   - **Baseline and indexing.** Every design anchors its baseline at $\tilde G-1$, outside the dip window, and indexes post-onset effects by $\ell=t-G$. The dip/processing periods $[\tilde G,G)$ are reported separately. This matters because $L_u$ varies across units (§2.2).
   - **RQ1:** BJS imputation (A1-W). Upgraded to a perimeter-zone design (A1-I) if GCRO SAL/GPS data arrive.
   - **RQ2:** the primary estimator is **BJS imputation aggregated by onset-relative time** (A2-P). The principal robustness check is **re-timed dCDH estimated by lag bin** $L\in\{2,3,\ge4\}$ FY, which is also the HonestDiD source (§3.4).
   - **Other arms:**
     - Cape Town SRAs (A3) are the patrol-only contrast.
     - A2-X is the incident-level upgrade.
     - A6 is a guard-onset design built on scheduled renewal expiries (conditional).

4. **Honest power verdict (§8).**
   - **A1-W and A2-P (area-level E1 arms):** they cannot support claims about exposed residents, so they are ITT-only by design.
   - **A1-I:** needs roughly 110–180k newly enclosed dwellings to detect 0.25 SD, and **even then it is underpowered for legitimacy-sized effects (0.05–0.15 SD).**
   - **A2-X:** the only E1 route to exposed-level crime effects of the size gating produces (about 0.30 log points with roughly 30 SARs; ESTIMATE).
   - **E3:** the best-powered area design (exposure-scaled MDE about 0.36 log points), but still coarse relative to effects the size of those found for business improvement districts (BIDs).
   - **Binding calculation:** the P-E placebo simulation.

5. **Gates never license a claim that §1.2(b) forbids.** User decisions and recommendations are in §18.

---

## 1. Design overview, estimands, hypotheses

### 1.1 Arms

| Arm | Treatment | Outcome data | Unit × period | Status | Estimand licensed |
|---|---|---|---|---|---|
| **A1-W** | E1 first FT switch | QoL III–7 (public ward IDs) | SWU × wave (repeated cross-section) | **ITT-only by design** | $\theta^W$ in area units, for the reachable population |
| **A1-I** | E1 in / ring / outer zone | QoL + GCRO SAL/GPS | Respondent in zone × SAR-group × wave | Conditional on the data request and gate G1′ | $\tau_{in}-\tau_{outer}$ |
| **A1-I-CS** | E1 *stock* zones | As A1-I | Cross-section | Descriptive | Selection-on-observables contrast |
| **A2-P** | E1 first FT switch | SAPS FY2005/06–2025/26 | Precinct cluster × FY | **ITT-only by design** | $\theta^P$ (net of within-precinct displacement); $\gamma$ |
| **A2-X** | E1 zones | SAPS incident points | Zone × month | Conditional on the data request and gate G2′ | $\tau_{in}$, $\tau_{ring}$, WDQ |
| **A3** | E3 residential SRA onset | SAPS, Cape Town | Cluster × FY | Conditional on gate G3 | $\theta^P_{E3}$; exposure-scaled with bounds where $\Delta E\ge0.3$ |
| **A4** | E2 new estates (2016–2023) | SAPS; QoL (incumbents) | Cluster/SWU × period | Secondary | Development bundle (bracketed, §3.3) |
| **A5** | OSM/E1 stock + AB EA-SEC-E | Afrobarometer | Place × round | Later | Associational; normative legitimacy |
| **A6** | "Guard onset, walls constant": **scheduled** first post-policy expiry of pre-policy closures | SAPS (A2-P/A2-X) | Cluster/zone × FY | Conditional on gate G4; **pursued (user decision 2026-09-30)** | ITT of intention-to-renew under the guard mandate (a bundle); fuzzy Wald for guards under stated assumptions (§2.8) |

### 1.2 Estimands and what they identify

**(a) Area ITT (A1-W, A2-P).**

$$\theta_\ell=\mathbb E\big[\bar Y_{u,G_u+\ell}(G_u)-\bar Y_{u,G_u+\ell}(\infty)\mid u\ \text{reported switcher},\ b(u)\big],\quad \ell\ge0$$

- **Indexing:** effects are indexed by time since **onset** $G_u$.
- **Counterfactual:** $\bar Y(\infty)$ is identified from untreated observations: never-switchers, and not-yet-switchers observed before their own $\tilde G$.
- **Assumptions:**
  - parallel trends (PT) within stock bin and common support, from $\tilde G-1$;
  - no anticipation before $\tilde G$;
  - neighbour interference captured by $WE$ (§7).
- **What the ITT includes:** it is the ITT of the first switch, so it bundles guards, CPF, renewals, lapses, further SARs and sorting. For QoL, $\bar Y$ is the mean over the **reachable** population.
- **Dip window:** estimates for $\ell\in[-L_u,-1]$ are reported separately as dip/processing estimates. They are not treatment effects.

**(b) Why area ITTs are not rescaled to exposed residents.**

$$\theta=\pi\Delta E\,\tau_{in}+R\,\tau_{ring}+(1-\pi\Delta E-R)\,\tau_{far}+b_u$$

so

$$\frac{\theta}{\pi\Delta E}=\tau_{in}+\tfrac{R}{\pi\Delta E}\tau_{ring}+\tfrac{1-\pi\Delta E-R}{\pi\Delta E}\tau_{far}+\tfrac{b_u}{\pi\Delta E}$$

- The ring multiplier $R/\pi\Delta E$ is about 3–8 (ASSUMED; measured in P-C). The far-field multiplier is about 10–100.
- At $\pi\Delta E=0.03$, any one of the following becomes an apparent "$\tau_{in}$" of 0.15–0.5 SD:
  - a ring effect of 0.05 SD;
  - a far-field spillover of 0.005 SD;
  - a residual PT bias of the same size.
- $\Delta E$ and $R$ are nearly collinear, so $\tau_{ring}$ is weakly identified in A1-W.

**Rule.**
- A1-W and A2-P report $\theta$ only.
- An exposure-scaled ITT appears only as a descriptive interval, under spillover bounds $b_r\in\{0,0.05\}$ and $b_f\in\{0,0.005,0.01\}$:
$$\Big[\tfrac{\theta-Rb_r-(1-\pi\Delta E-R)b_f}{\pi\Delta E},\ \tfrac{\theta+Rb_r+(1-\pi\Delta E-R)b_f}{\pi\Delta E}\Big]$$
- **E3 exception:** point statements are allowed only where $(1-\Delta E-R)/\Delta E\le2.5$ (roughly $\Delta E\gtrsim0.3$), and always together with the interval.

**(c) Dose.** Report terciles of $ATT(d\mid d)$. The average causal response (ACRT) is reported only as "under strong parallel trends" (Callaway, Goodman-Bacon & Sant'Anna 2024).

**(d) A1-I.**

$$Y_i=\lambda_{g(i)z(i)}+\alpha_{g(i)t}+\tau\,\mathbb 1[z=\text{in}]\text{Post}_{gt}+\rho\,\mathbb 1[z=\text{ring}]\text{Post}_{gt}+\varepsilon_i$$

- **Groups and zones:** $g$ is a SAR-group. Zones are in, ring (0–500 m) and outer (500–1,500 m).
- **Zone precedence (n5):** each respondent takes the highest-precedence zone across **all** perimeters (in > ring > outer) and is assigned to that perimeter's group. Outer-zone respondents who are also within 1,500 m of a *different* group that has switched are cross-exposed and excluded.
- **Fixed effects:** zone × group and group × wave.
- **Identification:** $\tau$ comes from the same group's outer-zone respondents and from in-zones of not-yet-switched groups. It equals $\tau_{in}-\tau_{outer}$.
- **Check:** whether GCRO reuses sampling points across waves.
- **With GPS:** a descriptive boundary comparison on $r_i$ at 200/500/1,000 m (Keele & Titiunik 2015).

**(e) A2-P.**
- $\theta^P$: effect on **recorded** crime, net of within-precinct displacement.
- $\gamma$: the neighbour-switch effect.
- Regional net effect: $\theta^P+\bar k\gamma$.

**(f) A2-X.** Monthly counts by zone:
- 0–250, 250–500 and 500–1,000 m rings;
- a 1–2 km control ring;
- perimeter roads.

Targets: $\tau_{in}$, $\tau_{ring}$ and the WDQ (Bowers & Johnson 2003).

### 1.3 Directional hypotheses and interpretation

Tests are two-sided wherever the sign is ambiguous. Readings of mechanism are exploratory.

| RQ × arm | Outcome | Inside | Ring / neighbours | Competing mechanisms |
|---|---|---|---|---|
| RQ1 E1 | **Safety (first stage)** | **+** | − or 0 | Salience: booms signal danger (−) |
| RQ1 E1 | **Performance, security referent (F1a anchor)** | **±** | − or 0 | Credit/co-production (+): state-authorised, SAPS meeting (s.5.3), CPF (s.7.4.1). Substitution/exit (−): Hirschman 1970; Caldeira 2000 |
| RQ1 E1 | **Performance, police or municipal referent (F1b, co-primary if harmonisable)** | ± | − or 0 | Police: + via CPF; − via contrast with guards |
| RQ1 E1 | Trust in government (QoL7 cross-section; AB) | − under exit | − | — |
| RQ1 E1 | CPF attendance | + | 0 | Co-production vs exit |
| RQ1 E1 | Private-security use (if the item exists) | + | + | First stage for PSC exposure |
| RQ1 (AB) | Normative legitimacy | − under exit | — | — |
| RQ2 E1 | V1 targeted crimes | **−** | ± | Displacement vs diffusion |
| RQ2 E1 | Net precinct V1 | − (small) or 0 | — | — |
| RQ2 E1 | Perimeter-road robbery and carjacking | + | — | Traffic diversion (s.6.1.3(b)) |
| RQ2 E1 | V0 murder | 0 or − | 0 | — |
| RQ2 E1 | V3 police-detected | + | 0 | Detection |
| RQ2 E1 | V2 / V4 | 0 | 0 | Falsification |
| RQ2 E3 | V1 | − (smaller than E1) | ± | Patrols without walls |
| RQ2 E3 | V3 | + | 0 | — |
| RQ2 E2 | V1 in pre-existing areas | ± | ± | — |
| RQ2 A6 | V1 | − (increment over walls) | ± | Null → walls do the work, or guards pre-existed |

**Interpretation matrix (RQ1).** Rows cross the safety first stage (F4) with F1a.

| Safety | F1a | Reading | Corroboration |
|---|---|---|---|
| + | + | Credit / co-production | CPF +; police referent + |
| + | − | Substitution / exit | Private security +; trust − (QoL7) |
| + | 0 | Attribution to the private provider | F1b ≈ 0 |
| 0 | ≠ 0 | Not via safety: salience, JRA contact, composition | §6 diagnostics; ring |
| − | − | Salience plus blame | Victimisation unchanged |
| 0 | 0 | Null, or weak/non-compliant treatment | Compliance audit; MDE |
| (ring) | ring − | Exclusion / relative deprivation | A1-I only |

### 1.4 Headline estimate rule

- **RQ1**, taking the first gate that passes:
  1. A1-I $\tau$ on F1a (G1′);
  2. A1-W $\theta^W$ on F1a, in area units (G1);
  3. otherwise no causal headline.

  F1a and F1b are co-primary under Holm (1979) if F1b is eligible.
- **RQ2**, taking the first that applies:
  1. A2-X $\tau_{in}$ on V1 (G2′);
  2. A2-P $\theta^P$ on V1;
  3. A3 if G0 fails.
- **E3 sub-question:** pre-specified separately as A3 $\theta^P_{E3}$ on V1. It is never pooled with E1.

---

## 2. Treatment definition and intensity

### 2.1 E1 construct and the guard mandate
- **What E1 is:** an authorisation under Act 10 of 1998 Ch. 7.
- **JHB guarding mandate:** at least one access point manned 24 hours by a PSIRA-registered provider (s.7.1.2, s.7.1.8), with the provider named (s.4.10.1). This is an **intention-to-guard**; SAHRC reports non-compliance.
- **Where "mandated guarding" language applies:** only to **JHB onsets after the guard-mandating policy took effect**. The adoption date of the 2012 base text is to be verified.
- **Other onsets are labelled:**
  - JHB SAPS cohorts that switched before that date: "enclosure (guard condition unverified)";
  - Tshwane and Ekurhuleni: "enclosure (mandate UNVERIFIED)" until their policies are read.
- **Compliance measures:** the provider named in JRA files, and an imagery audit of guardhouses (feasibility ASSUMED).
- **Consequence:** **the pooled 3-metro estimate measures "enclosure"** (user decision, 2026-09-30). "Mandated guarding" is carried only by the JHB post-policy subset, A2-X and A6 (§18.4).

### 2.2 Onset, re-timed switch, and a varying lag (C1, N-M1)

**Onset $G$**, in order of preference:
1. installation date (register or imagery);
2. interim approval;
3. first final gazette notice.

**Re-timed switch:** $\tilde G=\min(\text{application}-12\text{m},\ G-A)$, with $A=24$ months (ASSUMED; recalibrated in P-D).

**The lag varies by unit.**
- $L_u=G_u-\tilde G_u=\max(24\text{m},\ L^{app}_u+12\text{m})$, where $L^{app}_u$ is the time from application to installation.
- Gazette-only units have $L=24$ m (2 FY).
- Units with long processing times have $L$ of 3, 4 or more FYs.

**Anchoring and indexing rule (every estimator):**
- **Baseline:** anchored at $\tilde G_u-1$. All observations with $t\ge\tilde G_u$ are excluded from the $Y(0)$ fit and from the reference period.
- **Post-onset effects:** indexed by $\ell=t-G_u\ge0$.
- **Dip/processing window:** $\ell\in[-L_u,-1]$, reported separately and never part of the headline.

Indexing from $\tilde G$ is **not** allowed. For long-lag units it would put pre-installation processing years into "$\ell=0,1$" and let mean reversion leak into the headline. See §3.4 for how each estimator implements this.

**Onset precision** (`onset_precision_months`):

| Source | Precision (months) |
|---|---|
| Register installation date | 1 |
| Imagery | Width of the bracketing interval |
| Interim approval only | 12 |
| Final gazette notice only | 24 |

Installation before approval is dated from imagery.

### 2.3 Switchers, pre-window cohorts and stock bins (M1, N-M2, N-M3)

- **Panel start:**
  - A1: start of QoL III fieldwork (2013);
  - A2, A3, A6: FY2005/06.
- **$B_u$:** the intensity of closures **physically active at panel start**, whatever their vintage. Nothing that starts after panel start enters $B_u$.
- **$G_u$:** the date of the **first FT switch after panel start**, anywhere in the panel. Later FT increments are part of the ITT path.
- **Cohort classes** (flag `cohort_class`):

| Class | Definition | Role |
|---|---|---|
| `reported` | $G_u$ inside the arm's onset window (§9.4), and the unit meets the per-unit clean-pre rule | Treated; effects reported |
| `pre_window` | $G_u$ after panel start but before the window (A1: 2013 to mid-2018; A2: $\tilde G<$ FY2009/10) | **Kept in the data as treated.** Observations from $\tilde G$ onward are excluded from $Y(0)$; observations before $\tilde G$ help estimate FE. **Never a control. Not reported** (appendix count only) |
| `insufficient_pre` | $G_u$ inside the window, but the clean-pre rule fails | Handled like `pre_window`; used in sensitivity |
| `post_window` | $G_u$ after the window | Not yet treated until $\tilde G_u$; excluded from $Y(0)$ from then on |
| `never` | No FT switch in the panel | Control, subject to common support and the cell rule |

- **Failed applicants** (§2.4) are dropped from the `never` pool.
- **Stock bins (N-M3):** coarse **{0, >0}** on $B_u$. The finer {0, low, high} split is used in robustness only, and only where cells pass the minimum-controls rule (§3.2 rule 6).
- **Comparisons within bin, through additive FE:**
  - A1: `swu + metro^wave + bin^wave`;
  - A2: `pcl + metro^fy + bin^fy`;
  - dCDH: `trends_nonparam = bin`. Metro × bin is used in robustness only, where cells allow.
- **Robustness:** restrict to zero-stock units.
- **P-C reports** counts by `cohort_class` and bin, and the share of reported switches with $B_u>0$.

### 2.4 First-time vs renewal classification
- **Sources**, in order of preference:
  1. JRA or municipal register;
  2. a continuous gazette series (verified back to 1999; "probable" if ≥5 continuous years precede the event);
  3. dated street-level imagery.
- **Samples:** primary = FT-verified ∪ FT-probable; robustness = FT-verified only.
- **Renewals** are never counted as switches.
- **Failed applicants** are dropped from the never-treated pools. They are used only in the applicant design (§4.3) and in F8.

### 2.5 Status history
- **States:** none / applied / interim / final-active / legally lapsed / withdrawn / physically removed.
- **Primary treatment:** the absorbing ITT of the first switch.
- **Secondary treatment:** current-status dose (dCDH).
- **Robustness:** drop units with lapses.
- **Lapses are outcomes** (s.9.1.4) and are never conditioned on.

### 2.6 Intensity

$$E_{ut}=\frac{\sum_{s\in u}\text{dw}_{st}\,\mathbb 1[s\ \text{inside an active perimeter at }t]}{\sum_{s\in u}\text{dw}_{st}}$$

- **Dwellings:** Census 2011 SAL dwellings plus Open Buildings growth. SALs that straddle a perimeter are split by building footprints.
- **Rings:** $R$ at 500 m (250 m and 1 km in sensitivity).
- **Perimeters:** s.4.3 plans, or constructed from road data. Cross-checked against the s.4.7 affected-persons count divided by 3.0 (ASSUMED persons per dwelling).
- **Units:**
  - SWU: ≥95% population overlap, otherwise the smallest nesting union. The merged share is reported.
  - Robustness: 2021 wards, and never-changed wards.
  - Precinct clusters are time-invariant.

### 2.7 Threshold calibration
- The $E\ge0.10$ threshold is dropped.
- **Ward-level minimum dose:** $\varepsilon_W=1/(\pi\bar n_{post})\approx0.055$, about 800 dwellings in a JHB ward.
  - Units below it are excluded from the A1-W treated and control groups, but kept in A1-I.
  - In the homogeneous scenarios, Low and Mid fall entirely below $\varepsilon_W$.
- **Dose terciles** are locked before outcomes are seen.
- **Precinct level:** the binarised robustness drops $\Delta E_c<0.005$.

### 2.8 Other arms

**E2**
- OSM private-road component with at least one gate, at least 200 m of internal road, and either ≥10 footprints or ≥1 ha.
- Build year taken from Open Buildings.
- E2c enters only as a covariate.
- Validated against GCRO, Lightstone and the gazetteer.

**E3:** see §5.

**A6, guard onset with walls constant** (conditional; revised under N-M4 and r1; **pursued, user decision 2026-09-30**)
- **Idea.** Closures authorised before the guard-mandating policy meet its conditions at their first renewal afterwards.
- **What is mechanical.** Only the **scheduled expiry date** of the prior authorisation: 2-year validity, extendable to 6 (s.3.2.4, s.8.1).
- **What is not.** Renewal is a choice and may need fresh evidence. Whether a subsequent application (s.10–12) requires new crime statistics is **UNVERIFIED**; the policy text names a simplified traffic study and a fee of about 30%.
- **Switch:** the **scheduled first post-policy expiry**, $\tilde G^{A6}_u$. This is an ITT on the *intention-to-renew under the mandate*.
- **Sample (r1): all closures stay in the ITT.** This includes lapsed and non-renewed closures, and closures that change physically at renewal.
- **The ITT is a bundle.** Scheduled expiry sets off the renewal process itself: re-application, public notice, fees, possible SAPS and CPF contact, possible lapse and removal of booms, and possible physical upgrades. It also sets off the guard requirement. The ITT therefore estimates the effect of that bundle.
- **Anticipation:** the FY before scheduled expiry is a separate anticipation window, since residents may contract guards early.
- **First stage, reported component by component** from files and imagery:
  - (i) renewal together with installation of a **new guard post**;
  - (ii) **physical change** (new or relocated booms, extended fencing or walls, cameras, extra closure points);
  - (iii) lapse or physical removal.

  Physical change is treated as a first-stage/bundle component, not a reason to drop a closure.
- **Guard effect (fuzzy Wald):** ITT divided by first stage (i) (de Chaisemartin & D'Haultfœuille 2018), with CIs robust to a weak first stage. It is valid only under these stated assumptions:
  - **Exclusion:** scheduled expiry affects V1 only through the new guard post. Channels (ii) and (iii), and process effects (renewed residents' association or CPF activity), must have no effect on V1. This is plausible only if (ii) and (iii) are rare (G4 condition 4) and are reported as first-stage shares. Otherwise the Wald ratio is labelled "bundle per guard installed".
  - **Monotonicity:** no defiers, i.e. expiry never removes a guard post that would otherwise have stayed. This is threatened by closures with *pre-existing voluntary guards* that lapse at expiry and drop their guards. Test: the share of closures with pre-existing guards that lapse or remove guards, reported against the complier share.
- **Robustness only, not primary:** the no-physical-change sample. It conditions on behaviour after assignment.
- **Gate G4** (all conditions required):
  1. the earlier policy has no guard condition;
  2. at least 30% of scheduled renewals add a *new* guard post (ASSUMED floor);
  3. extension length is not crime-responsive, tested on the pre-authorisation crime trajectory;
  4. **physical change (ii) at renewal in no more than 20% of closures**, so that the bundle is mostly a guard bundle;
  5. **timing spread:** scheduled expiries span at least 4 FYs, with at least 3 clusters in each of at least 3 of those FYs (this guards against compression into 2012–14);
  6. at least 15 clusters, each with at least 4 pre-years.
- **Scope:** RQ2 only.
- **Dilution** is as severe as in E1, so the design is informative mainly through A2-X.
- **Data:** the JRA request now covers pre-policy authorisations, renewal files and the pre-2012 policy text (user decision, 2026-09-30).

---

## 3. Comparison groups and estimators

### 3.1 Why not TWFE
- Staggered, heterogeneous effects bias TWFE (Goodman-Bacon 2021; de Chaisemartin & D'Haultfœuille 2020; Sun & Abraham 2021; Roth et al. 2023).
- Further complications here:
  - treatment is non-absorbing;
  - dose is continuous;
  - stock is left-censored;
  - $L_u$ varies;
  - QoL has five uneven waves observed as repeated cross-sections.
- TWFE and the Bacon decomposition are reported as diagnostics only.

### 3.2 Control pools, recount and common support (M2, N-M3)

**Planning counts** (ASSUMED; the GIS recount happens in P-C):

| Step | A1-W JHB | A1-W 3 metros | A2-P JHB | A2-P 3 metros |
|---|---|---|---|---|
| Units | ~115 SWU | ~310 SWU | ~35 clusters | ~100 clusters |
| Ever-enclosed | 45–60 | 100–140 | 20–25 | 45–60 |
| Never-enclosed | 55–70 | 170–210 | 10–15 | 40–55 |
| … not contiguous to a switcher (dynamic) | 40–55 | 130–170 | 6–10 | 30–40 |
| … on common support | **5–15** | **20–45** | **2–5** | **10–20** |
| Not-yet-treated within bin | 5–15 | 15–40 | 3–8 | 10–25 |
| **Effective $J_C$** | **~20** | **~60** | **≤10** | **~30** |

Ward counts (JHB 135, Tshwane 107, Ekurhuleni 112) and station counts are ASSUMED.

**Rules:**
1. **Common support.** A logit of ever-enclosed on Census 2011 income, freestanding share, race composition, density, distance to the CBD, and the pre-window SAPS trajectory (FY2005–09, mapped to SWUs for A1). The range rule is primary; the Crump et al. (2009) 0.1–0.9 rule is robustness.
2. **Comparison priority.**
   - Primary: not-yet-treated units within bin.
   - Secondary: never-enclosed units on support.
   - Full never-treated pool: robustness only ("comparability not assumed").
3. **Dynamic clean controls.** A control drops out from the period in which a contiguous unit switches.
4. **Composition report.** Standardised differences, with equivalence at ±0.25 SD, by metro and bin.
5. **Timing variation among adopters carries identification.** JHB-only A2-P is infeasible, so A2-P pools the three metros (§2.1).
6. **Minimum controls per cell (N-M3).**
   - Every stock bin × period cell, and every metro × period cell, used to impute or compare a switcher must contain **at least 5 eligible control units**: never- or not-yet-treated, on support, and clean (ASSUMED floor).
   - Switchers in cells that fail are **dropped before estimation**, not silently by the estimator. Their number, cohort, bin, metro and $\Delta E$ are **reported**.
   - $J_T$ in all gates is counted **after** this rule.
   - P-E mirrors the same cells, FE and drop rule.

### 3.3 Per-arm specification

**A1-W**
- **Primary:** **BJS imputation** (Borusyak, Jaravel & Spiess 2024) on respondents.
  - `gname` = wave index of $\tilde G$.
  - First stage: `~0 | swu + metro^wave + bin^wave`.
  - Aggregation by $\ell=t-G$ uses treated-observation weights (`wtr`); dip waves and post waves are reported separately.
- **Why:** efficient with five waves; uses all clean untreated observations; handles the repeated cross-section; separates the definition of untreated observations from the aggregation index.
- **Robustness:**
  - CS: `base_period="universal"`, not-yet-treated, `panel=FALSE`, DR **and** unconditional, groups = wave of $\tilde G$, post waves relabelled by $t-G$ (the HonestDiD source);
  - Sun–Abraham;
  - dCDH on SWU-wave means.
- **Windows:** at least **2 clean pre-waves per unit** (fieldwork ended before $\tilde G_u$) (N-M1), and $G$ from mid-2018 to mid-2023.

**A1-I**
- **Primary:** BJS at respondent level, with FE `sargroup^zone + sargroup^wave`. Two runs: in vs outer, and ring vs outer. Zone precedence as in §1.2(d).
- **Why:** avoids singletons and absorbs local shocks.
- **Robustness:** CS by group; `fixest` triple difference; A1-I-CS.
- **Windows:** as A1-W, per group.

**A2-P**
- **Primary: BJS imputation aggregated by onset-relative time.**
  - All observations with $t\ge\tilde G_u$ are excluded from the $Y(0)$ fit.
  - First stage: `~0 | pcl + metro^fy + bin^fy`.
  - `wtr` weights put $\ell=0..5$ into post-onset effects (headline = mean of $\ell=0..3$), and $\ell\in[-L_u,-1]$ into a separate dip panel.
- **Why BJS (N-M1; wording softened under r2).** It anchors each unit's baseline at its own $\tilde G_u$ and aggregates by $t-G_u$ across units with different lags, all in a single estimation. It is chosen for **efficiency, simplicity and consistency with A1**. Lag-bin versions of dCDH, CS and Sun–Abraham identify the same object, but split $J_T\approx20$–40 into three bins of about 7–15 each.
- **Costs of BJS and how they are handled:**
  - **Long-run PT.** BJS imputes $Y(0)$ from the full untreated pre-history, so it needs PT over long horizons (r2). Two robustness checks are **mandatory** (§15.1 #3a–3b):
    - restricted-untreated-window BJS, which uses only switcher observations with $t\ge\tilde G_u-6$ in the $Y(0)$ fit;
    - BJS with unit-specific linear trends.
  - **No common reference in BJS pre-coefficients.** HonestDiD therefore uses lag-bin dCDH/CS (§4.2). **BJS on the $L=2$ subsample is reported next to the dCDH $L=2$ HonestDiD source.**
- **Principal robustness: re-timed dCDH by lag bin** $L\in\{2,3,\ge4\}$ FY (`DIDmultiplegtDYN`; de Chaisemartin & D'Haultfœuille, *REStat* 2024, venue and volume UNVERIFIED).
  - Treatment $S=\mathbb 1[t\ge\tilde G]$; `trends_nonparam = bin`.
  - Within bin, effect $k$ maps to $\ell=k-1-L$.
  - Estimates are re-aggregated by $\ell$ with $J_T$ weights.
- **Other robustness:**
  - CS universal and Sun–Abraham by lag bin;
  - **primary sample restricted to $L=2$ FY**, which holds all gazette-only units;
  - Poisson ETWFE (Wooldridge 2023);
  - stacked DiD (Cengiz et al. 2019; Wing, Freedman & Hollingsworth 2024);
  - SDID (Arkhangelsky et al. 2021);
  - current-status continuous dCDH.
- **Windows:** $\tilde G\ge$ FY2009/10 (at least 4 clean pre-years) and $G\le$ FY2023/24. The PSC subset is JHB post-policy.

**A2-X**
- **Primary:** Poisson imputation by zone × month, with the same anchoring and indexing rule. FE: group × zone and month × metro.
- **Why:** no dilution.
- **Robustness:** WDQ; CS on zone panels.
- **Windows:** $\ell$ from −36 to +36 months.

**A3**
- **Primary:** CS on $\tilde G=G-2$ FY, not-yet-treated, **reported both unconditional and DR** (§5).
  - Here $L$ is constant, so indexing from $\tilde G$ and from $G$ coincide up to a shift.
  - BJS as a check.
- **Why:** few, large events.
- **Robustness:** SDID; entropy-balanced CS; dCDH; placebo-unit RI.
- **Windows:** $\tilde G\ge$ FY2009/10 and $G\le$ FY2023/24 (n3).

**A4**
- **Primary:** dCDH on the continuous estate share. **Counts are bracketed (n8):**
  - (a) a fixed pre-construction offset. Crimes against new residents count as increases, so this is the upper bracket on "estates raise crime".
  - (b) a time-varying denominator (lower bracket).

  Labelled as the development bundle. The pre-existing-area version needs A2-X.
- **Why:** growth is continuous.
- **Robustness:** CS on the first large estate; neighbour exposure.

**A6**
- **Primary:** CS/BJS on the scheduled first post-policy expiry (ITT, **all closures**). The anticipation FY is reported separately. Fuzzy Wald for guards under the assumptions stated in §2.8.
- **Why:** the timing of scheduled expiry is not selected on current crime.
- **Robustness:**
  - stacked by expiry FY;
  - **no-physical-change sample (robustness only; conditions on behaviour after assignment)**;
  - Wald ratio with the combined first stage (i)+(ii) as a "bundle per change" check.
- **Windows:** at least 4 pre-years (§2.8).

### 3.4 Implementing "baseline at $\tilde G-1$, effects by $t-G$" (N-M1)

| Estimator | Untreated definition / reference | Aggregation | Dip output | Post-onset output |
|---|---|---|---|---|
| **BJS (A1-W, A1-I, A2-P, A2-X)** | `gname` $=\tilde G$: all observations with $t\ge\tilde G$ excluded from the $Y(0)$ fit | `wtr` columns $w_\ell=\mathbb 1[t-G=\ell]/n_\ell$ | $\ell\in[-L_u,-1]$ via `wtr` (negative $\ell$) | $\ell=0..5$ (A2), post-waves 1–2 (A1) |
| dCDH by lag bin (A2-P robustness; HonestDiD source) | $S=\mathbb 1[t\ge\tilde G]$; reference $\tilde G-1$ | Within bin $L$, effect $k$ ↔ $\ell=k-1-L$; re-aggregated over bins by $\ell$ | Effects $1..L$ | Effects $L+1..L+6$ |
| CS by lag bin | `gname` $=\tilde G$, `base_period="universal"`, `anticipation=0` | Event time $e$ → $\ell=e-L$ per bin | $e=0..L-1$ | $e=L..L+5$ |
| Sun–Abraham by lag bin | `sunab(G_tilde, period, ref.p=-1)` | Relative period $p$ → $\ell=p-L$ | $p=0..L-1$ | $p\ge L$ |
| CS (A3, A6) | Constant $L$ | $e\to\ell=e-L$ | $e<L$ | $e\ge L$ |

Dip panels are labelled "dip/processing window, not treatment effects". The expected pattern is a rise followed by partial reversion (F11).

---

## 4. Crime-driven timing (E1)

### 4.1 The bias
- **Mean reversion.** Applicants must show crime over the six months before applying (s.4.4). Transitory spikes then produce spurious falls in crime and spurious rises in perceived safety (Ashenfelter 1978; Heckman & Smith 1999).
- **Severity selection.** SAPS's view (s.5.3) deepens the reversion.
- **Aggregation.** Area aggregates dilute street-level spikes, but precinct crime waves can cluster applications.

### 4.2 Layered responses
1. **Re-timing with onset-relative indexing** (§2.2, §3.4); $A\in\{12,24,36\}$ months; restriction to $L=2$ as a robustness check.
2. **Applicant stack** (§4.3).
3. **Pre-trajectory conditioning:** CS-DR with the SAPS trajectory (A2, and A1 via SWU mapping); matched stacks; SDID weights.
4. **Pre-trend power** (Roth 2022; `pretrends`). Inference is never conditioned on passing.
5. **HonestDiD** (Rambachan & Roth 2023), using common-reference event studies only (M6, n2):

| Arm | Source | Reference | Pre-coefficients | Post vector passed | Target (`l_vec`) | Restrictions |
|---|---|---|---|---|---|---|
| A1 | CS `base_period="universal"` (primary); Sun–Abraham (check) | Last clean pre-wave per unit | **2** in total: $r=-2$ (all reported units) and $r=-3$ (units with 3 clean pre-waves). A unit with exactly 2 clean pre-waves contributes 1 | Dip wave(s) + post-waves 1–2 | ½ on each post-onset wave, 0 on dip waves | Relative magnitudes (RM) only, $\bar M\in\{0,.5,1,1.5,2\}$ |
| A2-P | Re-timed dCDH, **lag bin $L=2$ FY** (the largest bin; primary); CS universal $L=2$ (check); other bins reported separately. **BJS on the $L=2$ subsample reported alongside (r2)** | $\tilde G-1$ | **4** placebos | **All 8** effects: 2 dip + 6 post | $(0,0,\tfrac14,\tfrac14,\tfrac14,\tfrac14,0,0)$, i.e. the mean of $\ell=0..3$ | RM $\bar M\in\{0,.5,1,1.5,2\}$ and smoothness $M\in\{0,.01,.02,.03\}$; breakdown values reported |
| A3 | CS universal ($L=2$) | $\tilde G-1$ | 4 | 2 dip + 4–6 post | Mean of $\ell=0..3$ | RM + smoothness |

   The dCDH–HonestDiD hook-up is either a built-in option (UNVERIFIED) or manual, using the bootstrap variance matrix.

6. **Placebo onsets** at $\tilde G-3$ and $\tilde G-4$ years (SAPS) and $\tilde G$ − 1 wave (QoL); placebo-unit RI (§13.2).
7. **Monthly dip shape** for the 2020–2025 cohorts.
8. **V2/V4:** expect no dip and no effect.

### 4.3 Applicant-based stacked design (requires the register; M5, n1)
1. **Stacks** by application half-year $a$.
   - Treated: installed within 18 months.
   - Controls: installed at least 36 months later, or rejected on **non-crime** grounds.
2. **Window:** from $a-5$ years to $\min(a+3\text{y},\ \text{earliest control installation}-12\text{m})$. Stacks with fewer than 2 post-installation years are dropped.
3. **Exclusions:**
   - withdrawals are excluded (they are added back in robustness);
   - rejections on crime or SAPS grounds are excluded;
   - if rejection reasons are unrecorded, all rejections are included, with a sensitivity check that excludes rejections.
4. **Severity balance with a held-out decision rule (n1):**
   - **Balancing moments** (used for entropy balancing, Hainmueller 2012, only if needed): (a) levels in FY $a-5$ and $a-4$; (c) spike size, i.e. the 12 months before application relative to the $a-5$…$a-4$ mean.
   - **Held-out test moments** (never balanced on): (b) levels in FY $a-3$ and $a-2$; (d) the trend over $a-5$…$a-2$.
   - **TOST bounds:** ±0.10 log points for levels and spike; ±0.02 log points per year for trend.
   - **Decision rule:**
     - Unweighted equivalence on all moments → run as specified.
     - Otherwise, entropy-balance on (a) and (c), then run TOST on the **held-out** (b) and (d). The Kish effective sample size of controls must be at least 50% of the control count and at least 10 units.
     - If either condition fails, the design is descriptive only.
5. **Contamination:**
   - treated and control units must be different units;
   - controls must be more than 1 km from a treated perimeter (A2-X/A1-I) and not contiguous to one (area arms).
6. **Estimand:** the effect of prompt installation among applicants who applied at the same time. It is local to applicants.

### 4.4 The 67% consent rule
- **Trends threat** — tested via:
  - pre-period equivalence in social trust (`X6_40`) and CPF attendance (`X6_4_7`, `Q6_4_7`);
  - cohesion × wave terms in robustness;
  - failed-consent applicants as controls where recorded.
- **Post-onset cohesion is an outcome**, never a control.

### 4.5 Concurrent shocks
- **Shocks:** CIDs and patrols (bundle), FY2020/21 COVID, load-shedding, metro policing.
- **Controls:** metro × period FE; income tercile × period FE; robustness drops of FY2020/21 and QoL6.

---

## 5. E3 Cape Town SRA design (M8)

**Role:** the patrol-only contrast, and the RQ2 causal core if E1 is a NO-GO. RQ1 is out of scope.

### 5.1 Institutions (to verify)
- **Process:** owners apply; public participation; council approval; an additional rate funds a non-profit company's business plan.
- **Unverified rules:** consent threshold, term, renewal and dissolution (City SRA By-law and Policy).
- **Available data:** 58 polygons (VERIFIED\*); budgets by category (VERIFIED\* listed).

### 5.2 Selection: consent vote and crime-and-grime timing
- **Re-timing:** $\tilde G=G-2$ FY (campaign plus approval), calibrated from business-plan timelines.
- **Checks:** pre-trend power, HonestDiD, pre-trajectory matching.
- **Failed-SRA applicant-type controls** where City records exist, handled as in §4.3, including the held-out balance rule.

### 5.3 Pre-existing patrols and the first stage
- **Treatment:** the increment from voluntary to levy-funded patrols.
- **First stage:** security spend per dwelling and patrol resources.
- **Pre-existing provision:**
  - coded from business-plan histories;
  - the scrape's `guard_service_flag` (Cape Town: 819 flagged rows, 16.4%) serves as a pre-switch proxy for onsets from 2017 onward (conditions in §12).
- **Heterogeneity:** by spend increment and by pre-existing guarding.
- **A null first stage** makes E3 uninformative.

### 5.4 Onset source (pre-specified)
- **Priority:**
  1. first City FY with an SRA additional-rate budget line;
  2. council approval;
  3. business-plan start.
- **Mapping to SAPS FY:** the SAPS FY that contains at least 9 months of the first levy year.
- **Patrol start:** recorded; if known, $G$ = patrol start.

### 5.5 Boundary misalignment
- **Dose:** the share of the cluster's residential dwellings that fall inside the SRA.
- **High-dose subset:** $\Delta E\ge0.3$; bounded exposure-scaled statements are allowed only here.
- **Cape Town incident data** would resolve the misalignment (§18.6).

### 5.6 Renewal, dissolution, expansion
- **Primary:** ITT of the first onset.
- **Dissolution** is a switch-off (robustness).
- **Extensions** are dose increments.
- **CID onsets within ±2 FYs** are flagged and dropped in robustness.

### 5.7 Overlap and estimation with about 12 treated clusters
- **Controls:** not-yet-SRA and never-SRA residential clusters on support, about 15–20 of about 60 (ASSUMED). Contiguous clusters are excluded.
- **Estimators:**
  - CS, unconditional and DR (at most 4 covariates);
  - entropy-balanced CS;
  - SDID;
  - dCDH.
- **Inference:**
  - placebo-unit RI, **reporting the number of distinct assignments (n7)**, with the exact p-value grid if there are fewer than 1,000;
  - a **timing test** alongside it (onset FYs permuted among treated units; sharp null);
  - WCR as a complement.
- **Window:** $\tilde G\ge$ FY2009/10, i.e. $G\ge$ FY2011/12 (n3). Earlier SRAs are sensitivity only. $J_T$ may fall to about 8–10 (ASSUMED; counted in P-C).

### 5.8 E3 power
- MDE$_\theta$ ≈ 0.11 log points; exposure-scaled ≈ 0.36 at $\Delta E=0.3$ (§8.4).
- BID evaluations suggest area effects of about 10% (Brooks 2008; Cook & MacDonald 2011; magnitudes UNVERIFIED).
- **E3 can only detect effects about 3.6× that benchmark.**

---

## 6. Post-treatment sample selection (QoL)

### 6.1 Channels
- **(a) Access denial.**
  - Guards may not demand ID (s.7.1.7), but compliance gaps are documented by the SAHRC.
  - Gated areas have the highest access refusal, and one QoL II Midvaal ward was inaccessible (VERIFIED\*).
- **(b) Substitution within the ward** toward non-enclosed SALs. The substitution procedure is UNVERIFIED.
- **(c) Sorting:** E1 later, via prices; dominant in E2.
- **(d) Item non-response.**

Retention $\pi$ enters the estimand (§1.2(b)).

### 6.2 Diagnostics
Run in the event-study framework:
1. **Achieved $n$** per ward-wave against the design target.
2. **Composition on predetermined traits** used as outcomes: race, age, sex, home language, education, dwelling type, tenure, and years at address (if the item exists). Summarised by an Anderson index, with equivalence tested at ±0.1 SD.
3. **With SAL:** interviews achieved in treated SALs against the expected number (Census dwellings × wave sampling fraction), before vs after onset. This yields $\hat\pi$.
4. **GCRO metadata:** refusals, access-denied counts and substitutions by ward/SAL and wave, regressed on onset.

### 6.3 Corrections and bounds
1. **Calibration reweighting** of each SWU-wave sample to **Census 2011 SAL composition** (dwelling type × race × income band). Unweighted and reweighted estimates are compared. Survey weights are used in robustness only (Solon, Haider & Wooldridge 2015).
2. **Lee (2009) bounds with SAL:**
   - trimming share $p=(\pi_C-\pi_T)/\pi_C$, from response rates in treated vs comparison SALs;
   - **monotonicity:** enclosure never *raises* response;
   - tightened by stratifying on dwelling type.
3. **Ward-level Manski-type bounds without SAL:**
   - lost interviews $M_{ut}=n_{ut}\Delta E_u(1-\pi)$, with $\pi\in\{0.5,0.7,0.9\}$;
   - lost interviews imputed at the 5th and 95th percentiles of the treated units' outcome distribution.
4. **If bounds straddle zero,** the estimand is the ITT on the reachable population.

### 6.4 Sorting
- **E1:** long-term residents (years at address > years since onset), if that item exists. Otherwise, test for shifts in tenure and age composition.
- **E2:** incumbent neighbours only (ring × pre-construction residence). Needs SAL plus years at address.

---

## 7. Spillovers and displacement

1. **SUTVA violations:**
   - within units (ring; traffic diversion, s.6.1.3(b));
   - across units (displacement);
   - diffusion of benefits (Clarke & Weisburd 1994; Weisburd et al. 2006; Guerette & Bowers 2009).

   The evidence on private precautions cuts both ways: positive externalities in Ayres & Levitt (1998), negative in Gonzalez-Navarro (2013).
2. **Exposure mapping** (Aronow & Samii 2017):
   - own switch or dose;
   - ring $R$ (A1-I and A2-X only; weakly identified in the area arms, §1.2(b));
   - neighbour exposure $(WE)$.

   Related spatial DiD: Butts 2021 (venue UNVERIFIED); Delgado & Florax 2015.
3. **Dynamic clean controls** (§3.2 rule 3). Robustness: static exclusion; $(WE)$ entered as its own treatment.
4. **Displacement event study (A2-P).**
   - Sample: never-switched clusters.
   - Switch: $\tilde G$ of the first contiguous neighbour to switch, **or of the first FT onset within 1 km of the cluster boundary**, whichever comes first. Same anchoring and indexing rule.
   - Outcome: V1.
   - Regional net effect: $\theta^P+\bar k\gamma$.
5. **A2-X:** rings, WDQ and perimeter roads.
6. **RQ1:** ring effects are estimated only in A1-I.
7. **Inference and diagnostics:** see §13; Moran's I; spatial lag/error panels (`splm`) reported side by side.

---

## 8. Power and minimum detectable effects

### 8.1 Set-up
- **Planning MDE** $=2.8\times f\times SE$, with $f=1.2$ (range 1.1–1.3, ASSUMED).
- **Defaults:** JHB $D_w=14{,}500$; $\pi=0.7$.
- **The P-E simulation is binding** (§9.2) and uses the §3.2 cells and drop rule.

| Parameter | Value | Label |
|---|---|---|
| $\sigma^2_e$ / $\sigma^2_{ww}$ | 0.9 / 0.02 (range 0.01–0.04) | ASSUMED |
| $n_t$ per ward-wave | III 54, IV 59, V 49, 6 26, 7 26 | ESTIMATE |
| $V_w$ | 0.055 | Derived |
| $J_C$ (A1-W) | 20 (JHB) / 60 (3 metros) | §3.2 |
| $S$; $k$ | 100–1,000; 1–3 | P-C |
| DEFF; outer/in ratio (A1-I) | 1.3; 5 | ASSUMED |
| $D_c$; $J_C$ (A2-P) | 35,000; 30 | ASSUMED |
| $\sigma_c$: V1 / murder | 0.12 / 0.30 | ASSUMED |
| AR(1) $\rho$ | 0.3 (range 0–0.5) | ASSUMED |

### 8.2 A1-W
- **Area MDE:** MDE$_\theta=2.8\cdot1.2\sqrt{V_w(1/J_T+1/J_C)}$, in individual-level SD units (the effect on the ward mean).
- **Exposure-scaled:** MDE$_\theta/(\pi\Delta E)$ with $b=0$. Descriptive only.
- **$J_T$ cap (n4):** JHB $J_T$ is **capped at 30**. The §3.2 recount allows about 45–60 ever-enclosed SWUs, minus stock units without a new switch and pre-window cohorts. The 3-metro column keeps $J_T=N/k$ as a lower bound on its precision.

| Scenario | $N$ (JHB FT, window) | $S$ | $k$ | $\Delta E$ | vs $\varepsilon_W$ | $J_T$ JHB (cap 30) | MDE$_\theta$ JHB ($J_C$=20) | Exposure-scaled JHB | $J_T$ 3 metros | MDE$_\theta$ 3 metros ($J_C$=60) |
|---|---|---|---|---|---|---|---|---|---|---|
| Low | 20 | 100 | 1 | 0.007 | below | 20 | 0.25 | 52 | 20 | 0.20 |
| Mid | 60 | 300 | 2 | 0.041 | below | 30 | 0.23 | 7.9 | 30 | 0.18 |
| High | 150 | 600 | 3 | 0.124 | above | 30 | 0.23 | 2.6 | 50 | 0.15 |
| High+ | 150 | 1,000 | 3 | 0.207 | above | 30 | 0.23 | 1.6 | 50 | 0.15 |

- **Sensitivity:** $\sigma^2_{ww}$ = 0.01 gives ×0.90; 0.04 gives ×1.20.
- **Verdict:** ITT-only by design.

### 8.3 A1-I
- **In-zone sample sizes:** pre $0.00931\,NS$; post $0.00188\,NS$. Outer zone ×5.
- **MDE:** MDE$_{in}\approx98.5/\sqrt{NS}$ at $f=1.2$.

| $NS$ | 2,000 | 18,000 | 90,000 | 150,000 |
|---|---|---|---|---|
| MDE$_{in}$ (SD) | 2.20 | 0.73 | 0.33 | 0.25 |

- **Dwellings needed for 0.25 SD:** about 108k, 155k or 182k at $f$ = 1.0, 1.2 or 1.3. For 0.40 SD: about 61k.
- **Legitimacy-sized effects (0.05–0.15 SD)** would need about 0.4–3.9 million newly enclosed dwellings: $(98.5/0.15)^2\approx431$k and $(98.5/0.05)^2\approx3.9$M.
- **A1-I is underpowered for legitimacy-sized effects in every scenario.** Only the safety first stage and large shifts in performance evaluations are detectable.
- **A1-I-CS (descriptive):** about 0.11 SD.

### 8.4 A2-P and A3
- **Windows:** $P_g=g-2007$ and $Q_g=\min(6,2026-g)$ for $g$ = FY2011/12–2023/24 (the n3 window). Mean of $1/P+1/Q$ = 0.307.
- **Serial correlation:** AR(1) with ρ = 0.3 inflates variance ×1.68 (Burlig, Preonas & Woerman 2020); ρ = 0.5 gives ×2.38.
- **First-switch dose:** $\Delta E_c=k_1S/35{,}000$, with $\kappa$ = 1.
- **$J_T$** is at most the number of ever-enclosed clusters on support after the cell rule (about 35–50). "High" uses 40.

| Arm / scenario | $N$ | $S$ | $k_1$ | $J_T$ | $\Delta E_c$ | MDE$_\theta$ V1 (log) | Exposure-scaled V1 | MDE$_\theta$ murder |
|---|---|---|---|---|---|---|---|---|
| E1 Low | 40 | 100 | 1 | 20 | 0.003 | 0.083 | 29 | 0.21 |
| E1 Mid | 120 | 300 | 1.5 | 30 | 0.013 | 0.075 | 5.8 | 0.19 |
| E1 High | 300 | 600 | 2 | 40 | 0.034 | 0.070 | 2.0 | 0.18 |
| E1 High+ | 300 | 1,000 | 2 | 40 | 0.057 | 0.070 | 1.2 | 0.18 |
| **E3** | ~12 (8–10 in the n3 window) | suburb-scale | — | 12 ($J_C$=18) | 0.30 | 0.108 | **0.36** | 0.27 |
| E3 high-dose subset | ~5 | — | — | 5 | 0.60 | 0.146 | 0.24 | — |
| **A2-X (rough)** | 30 SARs, $S$=300 | — | — | 30 zones | 1 | — | **≈0.30** | — |

- **Sensitivities:**
  - $\sigma_c$ = 0.08: ×0.67;
  - ρ = 0: ×0.77; ρ = 0.5: ×1.19;
  - $\kappa$ = 2 halves the exposure-scaled values.
- **E3 with $J_T$ = 9:** MDE$_\theta$ ≈ 0.119; exposure-scaled ≈ 0.40.
- **Benchmarks:**
  - alley-gating, burglary ≈ −40% (≈0.5 log; Sidebottom et al. 2018, magnitude UNVERIFIED);
  - private police: large effects (MacDonald, Klick & Grunwald 2016);
  - BIDs ≈ −10% (UNVERIFIED).
- **Verdicts:**
  - A2-P is ITT-only by design; it detects net precinct changes of about 7–8%.
  - E1 exposed-level effects need A2-X.
  - E3 is exposure-scalable only in high-dose clusters, with bounds, and is underpowered for BID-sized effects.

### 8.5 Implications
1. **Two currencies:**
   - area $\theta$ with TOST (Hartman & Hidalgo 2018; Lakens 2017);
   - exposed-unit effects only from A1-I, A2-X, or E3 high-dose with bounds.
2. **Data priority:** SAL/GPS and incident data (Cape Town included) come before the full gazette compile.
3. **P-E replaces** every ASSUMED variance.

---

## 9. Pilot and go/no-go

### 9.1 Current evidence (N1)
- **Rate:** about 50–240 notices a year across Gauteng, all types. 3 of the 7 notices are unclassified; reference numbers are not chronological; the 2007 zero may reflect a missing contents page.
- **Illustrative projection (ASSUMED):** 12–58 JHB decisions a year × 0.1–0.5 first-time share × 5 years = **6–144 FT SARs**.

### 9.2 Pilot components

| Component | Content | Output | Effort (ESTIMATE) |
|---|---|---|---|
| **P-A** | JRA register and files (sent). **The request now includes (user decision 2026-09-30):** pre-policy authorisations, renewal files and the pre-2012 policy text, including whether subsequent applications require crime evidence | Closure histories, rejection reasons, s.4.3, s.4.7, providers; A6 inputs | 1–3 months |
| **P-B** | Continuous read of JHB gazettes, W1 = 2017–18 and W2 = Jul 2021–Jun 2022 | Volume (Poisson CI); type mix; reference-number chronology | 4–8 days |
| **P-C** | Perimeters for at least 30 closures; GIS recount (§3.2) | $S$, $k$, $k_1$, $R/\Delta E$. **Counts by `cohort_class` (including `pre_window`) and bin; share of reported switches with $B_u>0$; cell counts; switchers dropped under rule 6.** $\Delta E$ vs $\varepsilon_W$; effective $J_C$; E3 $J_T$ in the n3 window | 4–6 days |
| **P-D** | FT feasibility for 30 W1 closures (register, imagery, backward read). **Distribution of $L^{app}$ (hence lag-bin shares).** A6: 10 legacy closures coded for guard post, physical change and lapse around scheduled expiry, plus pre-existing voluntary guards (monotonicity check) | $\hat\pi_{FT}$; recalibrated $A$; lag-bin shares; A6 first-stage component shares | 3–5 days |
| **P-E** | Placebo-simulation power on the real SAPS panels (3 metros + Cape Town) and the QoL panels | Definitive MDEs | 3–5 days |

**P-E protocol:**
1. Restrict to never-switchers on common support, and to switcher periods before $\tilde G$.
2. Draw pseudo-$(\tilde G, G)$ pairs that reproduce the projected cohort sizes, **the P-D lag distribution**, stock bins, contiguity, and the §3.2 **cells, FE and drop rule**. Draw doses from P-C.
3. Inject an effect of $\delta\Delta E$ (or $\delta$) starting at $G$.
4. Run the **actual primary estimator** (A2-P: BJS aggregated by $t-G$; A1: BJS; A3: CS) with the actual inference, using 500–1,000 draws per $\delta$.
5. MDE = the smallest $\delta$ with power of at least 0.80. Check size at $\delta=0$.

**Projection:** $\hat N_{FT}$ = volume × final share × $\hat\pi_{FT}$ × 5 (JHB). Gates use the lower 80% bound.

### 9.3 Gates

| Gate | Arm | GO if | Licenses | Otherwise |
|---|---|---|---|---|
| **G0** | All E1 | (a) at least 80% of in-window closures classified; (b) at least 80% of FT onsets precise to within 12 months. Denominator = all closures with any in-window notice or approval | Dated E1 | Stock-only E1 (§10) |
| **G1** | A1-W | G0; $J_T\ge15$ after the per-unit clean-pre rule, $\varepsilon_W$ and the cell rule; $J_C\ge15$ on support; selection diagnostics pass or bounds reported | Causal area ITT $\theta^W$ only | Descriptive |
| **G1′** | A1-I | G0; SAL/GPS available; P-E MDE$_{in}\le$ 0.25 SD; at least 15 SAR-groups with pre-period in-zone respondents | $\tau_{in}-\tau_{outer}$ | 0.25–0.40: exploratory (F1a + safety). Above 0.40: A1-I-CS |
| **G2** | A2-P | G0; $J_T\ge15$ after the cell rule; $J_C\ge15$ on support; at least 4 clean pre-years per reported unit | Causal area $\theta^P$ and $\gamma$ only | Descriptive |
| **G2′** | A2-X | Incident data with at least 2 years before and 2 after, for at least 30 FT SARs; P-E MDE$_{in}\le$ 0.40 log | $\tau_{in}$, $\tau_{ring}$, WDQ | E1 exposed effects unidentified |
| **G3** | A3 | At least 10 residential-SRA clusters with pre-specified onsets and $G$ in FY2011/12–2023/24; $J_C\ge10$ on support; first stage documented for at least 80% | Area $\theta^P_{E3}$; exposure-scaled with bounds for $\Delta E\ge0.3$ only if P-E exposure-scaled MDE ≤ the E3 threshold | Descriptive |
| **G4** | A6 | §2.8 conditions 1–6: first stage ≥30%; physical change ≤20%; timing spread ≥4 FYs; ≥15 clusters | ITT of intention-to-renew (bundle); fuzzy Wald guard effect under the stated exclusion and monotonicity assumptions (area-level; exposed-level only via A2-X) | Not run |

**G0 is in practice a register-or-imagery gate (n6).** Gazette notices rarely state their type, and non-consecutive sample years cannot classify closures. G0 can pass only through one of:
- (i) the JRA register;
- (ii) a continuous gazette compile back to 1999;
- (iii) imagery.

**User decision (2026-09-30): if JRA refuses, the user will fund the continuous gazette compile plus imagery** (§18.7). The funded fallback must include **imagery dating of installation for events known only from a final notice**, not just classification:
- the compile satisfies G0(a);
- final-notice-only onsets have 24-month precision and would fail G0(b) without imagery dating.

Gates are recorded before any outcome merge, with user sign-off.

### 9.4 Onset windows (one per arm; n3)

| Arm | Clean-pre rule | Onset window | Outside the window |
|---|---|---|---|
| A1-W / A1-I | At least 2 waves fielded before $\tilde G_u$, **per unit** | $G$ from mid-2018 to mid-2023 | `insufficient_pre`/`pre_window` → sensitivity ($A$ = 12 months; QoL II pre-wave if ward-representative) |
| A2-P / A2-X | $\tilde G\ge$ FY2009/10 (at least 4 clean pre-years) | $G\le$ FY2023/24 | $\tilde G$ in FY2006/07–2008/09 → sensitivity |
| A3 | $\tilde G\ge$ FY2009/10 | $G$ in FY2011/12–2023/24 | Earlier SRAs → sensitivity |
| A6 | At least 4 pre-years before scheduled expiry | Scheduled expiries FY2009/10–2023/24 | — |

**Wave reliability:** II marginal; III–V usable; 6 conditional (dropped in robustness); 7 usable.

---

## 10. NO-GO fallback (N6)

- **If G0 fails:**
  - E1 is used as stock only.
  - RQ1 is descriptive: a ward cross-section with Cinelli & Hazlett (2020) sensitivity analysis; A1-I-CS if SAL arrives; possibly E2 incumbents.
  - RQ2's causal core is E3 (A3) plus E2 (A4, bracketed), plus A2-X if incident data arrive.
- **If G0 passes but the power gates fail:** A1-W and A2-P remain causal *area* ITTs, reported with equivalence bounds.
- **Framing:**
  - E3's causal language does not transfer to E1.
  - The pooled E1 estimate is "enclosure" (§2.1).
- **Always survives:** the dated, geocoded E1 register.

---

## 11. Outcome mapping (R1, M9)

### 11.1 QoL items × waves

| Dimension | Item | III | IV | V | 6 | 7 | DiD-eligible | Role |
|---|---|---|---|---|---|---|---|---|
| Performance (security) | Satisfaction with government safety & security | ✓ `X9_12` | ✓ `Q9_6` | ? | ? | ✓ `q11_6_gov_security` | Yes (pre III, IV; post 7) | **F1a anchor** |
| Performance (police) | Satisfaction with metro/traffic police | ? | ✓ `Q1_31` | ? | ? | ? | Pending | **F1b candidate** |
| Performance (municipal) | Satisfaction with local government | ? | Municipal item to find (`Q6_6`/`Q6_7` are national/provincial) | ? | ? | ? | Pending | **F1b candidate** |
| Procedural | Judiciary; officials | ? | ✓ `Q6_35`, `Q6_23` | ? | ? | ? | No | Cross-section; AB R9 Q44 |
| Trust | Trust in government leaders | ? | ? | ? | ? | ✓ `q7_11_gov_trust` | **No (QoL7 only)** | Cross-section; AB |
| Normative | — | — | — | ? | ? | — | **AB only** | A5 |
| Reliance | CPF attendance | ✓ `X6_4_7` | ✓ `Q6_4_7` | ? | ? | ? | Pre only | Covariate / outcome |
| Reliance | Uses private security | ? | ? | ? | ? | — | No | First stage if found |
| Safety | Safe at home / after dark | ? | ? | ? | ? | ✓ `q11_3–5` | Pending (II ✓) | **F4** |
| Victimisation | Victim in past 12 months | ? | ✓ `Q9_2` | ? | ? | ✓ `q11_2` | Pending | RQ2 complement |
| Collective action | Crime protest | ? | ✓ `Q10_3_8` | ? | ? | ✓ `q12_4–5` | Pending | Secondary |
| Social trust | Community trust | ✓ `X6_40` | ? | ? | ? | ? | Pre only | Consent balance |
| Negative control | Satisfaction with water/electricity/refuse | ? | ? | ? | ? | ? | Pending | F7 |

**F1b rule.** F1b is co-primary under Holm if it has the same referent and scale in at least 2 clean pre-waves per primary unit and at least 1 post-wave, and passes the wording check. The police referent is preferred.

**Questionnaire checks** (waves II–7, before any merge):
1. Wording, referent, scale, position in the questionnaire, skips, translation.
2. Search for:
   - trust in police, courts and government;
   - municipal satisfaction;
   - first contact about crime;
   - private-security payment;
   - **years at address**;
   - dwelling type;
   - neighbourhood watch;
   - being denied access at booms;
   - corruption;
   - service satisfaction (F7).
3. Mode, delimitation, interview-date variable, weights, sampling design, and **reuse of sampling points**.
4. A locked eligibility table.

**Families:**
- F1 performance (F1a; F1b if eligible);
- F2 trust and procedural (cross-sections; AB);
- F3 reliance;
- F4 safety and victimisation;
- normative legitimacy: AB only.

### 11.2 RQ2 outcomes

| Family | Outcomes | Role |
|---|---|---|
| V0 | Murder, attempted murder | Anchor robust to reporting; underpowered |
| **V1** | Residential burglary, residential robbery, carjacking, motor-vehicle theft | **Primary** (Anderson index + components) |
| V2 | Assault GBH, common assault, sexual offences | Expected 0; weak falsification |
| V3 | Drugs, firearms, DUI | Policing intensity |
| V4 | Commercial crime, shoplifting, stock theft | Falsification |
| V5 | Neighbour V1; perimeter-road robbery | Displacement |
| ACLED | Inter 8 / 5 | Descriptive only |

- **Specification:** rates per 1,000 dwellings, and Poisson with an offset.
- **QoL victimisation** (A1-I) is a complement that does not depend on reporting.

---

## 12. Role of the Property24 scrape (N5)

- **State of the scrape:**
  - 18,332 rows, 17,406 listings; 29.8% of descriptions missing;
  - Gauteng coverage: JHB 1,231 rows, Pretoria 4,208, no Ekurhuleni;
  - the enclave signal is thin (11 / 72); enclave precision 40% (non-blind);
  - `guard_service_flag`: JHB 133 (16.1%), Pretoria 144 (4.7%), Cape Town 819 (16.4%).
- **Roles:**
  - suburb-level covariate for advertised guarding (empirical-Bayes shrunk; conditioned on description length; pre-treatment only for switches from 2017 onward);
  - heterogeneity (substitution vs complementarity);
  - E3 first-stage proxy;
  - E2 gazetteer.
- **Never a treatment.**
- **Conditions:**
  - the user confirms the labels;
  - the `property_use` bug is fixed first;
  - script 05 stays blocked until N4 is resolved;
  - no new scraping.

---

## 13. Inference

### 13.1 Clustering
- Cluster at the level of assignment (Abadie et al. 2023): SWU (A1), cluster (A2, A3).
- A1-I: SWU × SAR-group in robustness.

### 13.2 Few clusters and randomisation inference
- **Wild cluster bootstrap (WCR):** Webb weights, $B$ = 9,999 (Cameron, Gelbach & Miller 2008; MacKinnon & Webb 2017, 2018; Roodman et al. 2019). `fwildclusterboot` availability UNVERIFIED.
- **Timing RI:** tests only the sharp null. Exchangeability of timing is not claimed.
- **Placebo-unit RI:** primary for A3 and whenever $J_T<20$. Reports the number of distinct assignments, with the exact p-value grid if fewer than 1,000 (n7).

### 13.3 Spatial correlation
- **Conley HAC on the primary estimators:**
  - BJS is re-implemented in-house to get the weights $v_{it}$; the variance is then $\sum\sum v_iv_j\hat\varepsilon_i\hat\varepsilon_jK(d_{ij})$;
  - dCDH and CS use a spatial block bootstrap.
- **Bandwidths:** 2/5/10 km (A1); 5/10/20 km (A2, A3).
- **Moran's I.**

### 13.4 Reporting rule
- **Primary:** cluster SE with WCR p-value and CI (placebo-unit RI for A3).
- **"Robust"** means also significant under the spatial HAC or block bootstrap **and** under placebo-unit RI. All are reported.

### 13.5 Multiple testing
- **One headline per RQ** (§1.4); F1a/F1b under Holm.
- **Within families:** Romano–Wolf, via `wildrwolf` on the `fixest` SA/stacked versions, or computed manually from bootstrap draws.
- **Across secondary families:** Benjamini–Hochberg and sharpened q-values.
- **Exempt:** leads, dip panels, falsification tests, heterogeneity.

### 13.6 Functional form
- **A1:** LPM plus logit AMEs.
- **A2/A3:** Poisson PML plus linear rates; no log(1+y) (Chen & Roth 2024).
- **Spatial lag/error** models side by side.

---

## 14. Pseudo-code (R; specification level)

```r
## ---------- 0. Setup ----------
library(data.table); library(sf); library(fixest); library(did); library(didimputation)
library(DIDmultiplegtDYN); library(etwfe); library(HonestDiD); library(pretrends)
library(synthdid); library(spdep); library(wildrwolf); library(WeightIt)
set.seed(20260929)

## ---------- 1. Histories, dates, lag, G0 ----------
sar <- load_sar_register()
sar[, onset := fcoalesce(install_date, interim_date, final_date)]
sar[, onset_precision_months := fcase(
        !is.na(install_date) & install_src == "register", 1,
        !is.na(install_date) & install_src == "imagery",  imagery_bracket_months,
        !is.na(interim_date), 12, default = 24)]
sar[, G_tilde := pmin(app_date %m-% months(12), onset %m-% months(A_months), na.rm = TRUE)]
sar[, L_fy := fy(onset) - fy(G_tilde)]                 # 2, 3, >=4
sar[, lag_bin := fifelse(L_fy >= 4, "4+", as.character(L_fy))]
inwin <- sar[any_notice_or_approval_date %between% window]
G0 <- inwin[, mean(ft_status != "unknown")] >= .80 &
      inwin[ft_status %like% "^FT", mean(onset_precision_months <= 12)] >= .80
failed <- sar[status %in% c("rejected", "withdrawn", "failed_consent")]

## ---------- 2. Units: B (active at panel start), G (first FT after start), classes ----------
U <- unit_panel(list(swu, pcl), perims = sar, dw = dw, ring_m = c(250, 500, 1000))
U[, B   := stock_active_at(panel_start)]               # closures physically active at panel start only
U[, bin := fifelse(B > 0, ">0", "0")]                  # coarse bins (N-M3)
U[, G   := first_ft_switch_after(panel_start)]          # any time in panel
U[, `:=`(G_tilde = G_tilde_of_first_switch, L_fy = L_of_first_switch, dE1 = ft_increment_24m)]
U[, n_clean_pre := clean_pre_periods(G_tilde)]          # waves fielded / FYs before G_tilde
U[, cohort_class := fcase(
      is.na(G), "never",
      G < window_start, "pre_window",
      G > window_end, "post_window",
      n_clean_pre < min_clean_pre, "insufficient_pre",   # A1: 2 waves; A2: 4 FYs
      default = "reported")]
U <- U[!(cohort_class == "never" & unit %in% units_of(failed))]
ps <- glm(ever_enclosed ~ inc11 + fh_share11 + race11 + dens11 + dist_cbd + crime_lvl0507 + crime_gr0509,
          family = binomial, data = U)
U[, on_support := between(ps_hat, min(ps_hat[cohort_class == "reported"]), max(ps_hat[cohort_class == "reported"]))]
# eligibility as control at t: cohort_class %in% c("never","post_window") & t < G_tilde & on_support & !contig_switched(t)
dropped <- apply_min_controls_rule(U, cells = list(c("bin", "period"), c("metro", "period")), min_ctrl = 5)
report(dropped); report_counts(U, by = c("cohort_class", "bin", "metro")); report_control_composition(U)

## ---------- 3. A1-W: BJS, baseline at G_tilde-1, aggregation by t - G ----------
a1 <- merge(harmonise_qol(locked_item_table), U_swu_wave, by = c("swu", "wave"))
a1 <- a1[(cohort_class %in% c("reported", "pre_window", "insufficient_pre") |
          (control_eligible & on_support)) & !sub_threshold_W & !dropped_switcher]
a1[, g_imp := ifelse(is.na(G_tilde), 0, wave_index_of(G_tilde))]     # obs from G_tilde on excluded from Y(0)
a1[, ell := wave_index(t) - wave_index_after(G)]                     # onset-relative (waves)
for (k in c(-1, 0, 1)) {                                             # -1 = dip wave(s); 0,1 = post-waves 1,2
  a1[, (paste0("w", k)) := as.numeric(cohort_class == "reported" & ell == k & wave_num >= g_imp)]
  a1[, (paste0("w", k)) := get(paste0("w", k)) / sum(get(paste0("w", k)))]
}
m_a1w <- did_imputation(a1, yname = "F1a", gname = "g_imp", tname = "wave_num", idname = "resp_id",
                        first_stage = ~ 0 | swu + metro^wave_num + bin^wave_num,
                        wtr = c("w-1", "w0", "w1"), pretrends = TRUE, cluster_var = "swu")  # `wtr` interface: verify
# pre_window / insufficient_pre units: treated in the Y(0) exclusion, zero weight in every w-column (never reported)
cs_a1 <- att_gt(yname = "F1a", tname = "wave_num", gname = "g_imp", data = a1_cs_sample, panel = FALSE,
                control_group = "notyettreated", base_period = "universal", anticipation = 0,
                xformla = ~ bin + inc11 + crime_lvl0507, est_method = "dr", clustervars = "swu")
# relabel CS event time e → ell = e - L_waves(unit); HonestDiD input: 2 pre-coefficients

## ---------- 4. A1-I: zone precedence, zone × group FE ----------
qi <- attach_location(qol, gcro_sal_or_gps)
qi <- assign_zone_precedence(qi, perims, order = c("in", "ring", "outer"))       # n5
qi <- qi[!(zone == "outer" & within_1500m_of_other_switched_group)]
run_zone <- function(tr) {
  d <- qi[zone %in% c(tr, "outer")]
  d[, g := fifelse(zone == tr, wave_index_of(G_tilde_group), 0)]
  build_wtr_by_ell(d)          # as in step 3
  did_imputation(d, yname = "F1a", gname = "g", tname = "wave_num", idname = "resp_id",
                 first_stage = ~ 0 | sargroup^zone + sargroup^wave_num,
                 wtr = wtr_cols, cluster_var = "swu")
}
m_in <- run_zone("in"); m_ring <- run_zone("ring")

## ---------- 5. A2-P: PRIMARY = BJS aggregated by t - G ----------
sp <- merge(build_saps_panel(2005:2025, pcl), U_pcl_fy, by = c("pcl", "fy"))
sp <- sp[(cohort_class %in% c("reported", "pre_window", "insufficient_pre") | control_eligible) & !dropped_switcher]
sp[, rate_V1 := 1000 * V1 / dwellings]
sp[, g_imp := fifelse(is.na(G_tilde_fy), 0, G_tilde_fy)]
sp[, ell := fy - G_fy]
for (k in -4:5) {   # negative ell within [-L, -1] = dip panel; 0..5 = post-onset
  nm <- paste0("w_", k)
  sp[, (nm) := as.numeric(cohort_class == "reported" & ell == k & fy >= g_imp)]
  sp[, (nm) := get(nm) / sum(get(nm))]
}
m_a2p <- did_imputation(sp, yname = "rate_V1", gname = "g_imp", tname = "fy", idname = "pcl",
                        first_stage = ~ 0 | pcl + metro^fy + bin^fy,
                        wtr = paste0("w_", -4:5), pretrends = 1:4, cluster_var = "pcl")
headline <- mean_of(m_a2p, paste0("w_", 0:3))          # mean of ell = 0..3 (or a single w column)
# Mandatory BJS robustness (r2):
#  (3a) restricted untreated window: drop switcher obs with fy < G_tilde_fy - 6 from the estimation sample
m_a2p_rw <- did_imputation(sp[is.na(G_tilde_fy) | fy >= G_tilde_fy - 6], yname = "rate_V1", gname = "g_imp",
                           tname = "fy", idname = "pcl", first_stage = ~ 0 | pcl + metro^fy + bin^fy,
                           wtr = paste0("w_", -4:5), cluster_var = "pcl")   # weights re-normalised on subsample
#  (3b) unit-specific linear trends in the Y(0) model (fixest varying-slope syntax; pass-through to verify)
m_a2p_tr <- did_imputation(sp, yname = "rate_V1", gname = "g_imp", tname = "fy", idname = "pcl",
                           first_stage = ~ 0 | pcl[fy] + metro^fy + bin^fy,
                           wtr = paste0("w_", -4:5), cluster_var = "pcl")
#  BJS on the L = 2 subsample, reported next to the dCDH L = 2 HonestDiD source
m_a2p_L2 <- did_imputation(sp[is.na(L_fy) | L_fy == 2], yname = "rate_V1", gname = "g_imp", tname = "fy",
                           idname = "pcl", first_stage = ~ 0 | pcl + metro^fy + bin^fy,
                           wtr = paste0("w_", -2:5), cluster_var = "pcl")
# Principal robustness: re-timed dCDH by lag bin, re-aggregated by ell
dcdh <- lapply(split(sp, by = "lag_bin_or_control"), function(d)
  did_multiplegt_dyn(df = d, outcome = "rate_V1", group = "pcl", time = "fy",
                     treatment = "S_rt", effects = L + 6, placebo = 4,
                     trends_nonparam = "bin", cluster = "pcl"))   # effect k ↔ ell = k - 1 - L
dcdh_by_ell <- reaggregate_by_ell(dcdh, weights = "n_switchers")
# CS / Sun-Abraham by lag bin analogously; primary-sample sensitivity: L_fy == 2 only
# Applicant stack (§4.3): balance on (a),(c); TOST on held-out (b),(d); ESS >= max(10, .5 * n_ctrl)

## ---------- 6. A3 (E3) and A6 ----------
ct <- merge(saps_ct, sra_onsets(priority = c("levy_fy", "council", "bizplan")), by = "pcl")
ct <- ct[G_fy >= 2011 & on_support_ct]
a3_dr  <- att_gt(yname = "rate_V1", tname = "fy", idname = "pcl", gname = "G_tilde_fy", data = ct,
                 control_group = "notyettreated", base_period = "universal",
                 xformla = ~ crime_lvl0507 + crime_gr0509 + inc11 + fh_share11, est_method = "dr")
a3_unc <- update(a3_dr, xformla = ~ 1)
ri <- placebo_unit_ri(a3_unc, pool = never_sra_on_support, B = 2000); report(ri$n_distinct_assignments)
# A6: switch = scheduled first post-policy expiry (ITT); ALL closures kept (lapsed, physically changed); anticipation FY separate
a6 <- att_gt(yname = "rate_V1", tname = "fy", idname = "pcl", gname = "sched_expiry_fy", data = a6_sample_all,
             control_group = "notyettreated", base_period = "universal", anticipation = 1)
fs6_guard  <- att_gt(yname = "new_guard_post", ...)     # first-stage component (i)
fs6_phys   <- att_gt(yname = "physical_change", ...)    # component (ii): reported, bundle
fs6_lapse  <- att_gt(yname = "lapse_or_removal", ...)   # component (iii): reported; monotonicity check
wald_guard <- ratio_with_weakIV_ci(a6, fs6_guard)       # fuzzy DiD; valid under exclusion + monotonicity (§2.8)
# robustness only: no-physical-change sample; Wald with combined first stage (i)+(ii)

## ---------- 7. Sensitivity and inference ----------
b <- extract_event_study(dcdh$`2`)                    # lag bin L = 2: 4 placebos, 8 effects (2 dip + 6 post)
lvec <- c(0, 0, .25, .25, .25, .25, 0, 0)
HonestDiD::createSensitivityResults_relativeMagnitudes(betahat = b$coef, sigma = b$vcov,
        numPrePeriods = 4, numPostPeriods = 8, l_vec = lvec, Mbarvec = c(0, .5, 1, 1.5, 2))
HonestDiD::createSensitivityResults(betahat = b$coef, sigma = b$vcov,
        numPrePeriods = 4, numPostPeriods = 8, l_vec = lvec, Mvec = c(0, .01, .02, .03))
pretrends::slope_for_power(sigma = b$vcov_pre, targetPower = 0.8)
spatial_hac_bjs(m_a2p_inhouse, coords, cutoff_km = c(5, 10, 20))
placebo_unit_ri(primary, cohorts = real_cohorts, pool = never_on_support, B = 2000)
rwolf(models = sunab_components_V1, param = "ATT", B = 9999)
moran.test(resid_primary, W)
## P-E: simulate (G_tilde, G) with the P-D lag distribution; same cells/FE/drop rule; BJS by t - G; MDE at power .8
```

### 14.1 Coder hand-off notes

These are known defects in the pseudo-code above. Strategist-critic flagged them as r3 (items 1–3); I noted items 4–7. They are left for the coder to fix, and do not change the specification.

1. **Lag-bin dCDH frames exclude the controls.** `split(sp, by = "lag_bin_or_control")` puts controls in a frame of their own. Each bin's frame must contain **that bin's switchers plus the shared pool of eligible controls** (never and post-window units before their $\tilde G$, on support, clean).
2. **`L` is undefined inside the `lapply` lambda, and the "4+" bin mixes lags.** The mapping from effect $k$ to $\ell=k-1-L$ needs one $L$ per frame. Split by **exact** $L$ (2, 3, 4, 5, …), pass `L` into the function, and re-aggregate by $\ell$.
3. **A1 builds only the ℓ = −1 dip weight.** Generate `wtr` columns for every $\ell\in[-L^{\max}_{waves},-1]$ plus the post-waves. Likewise in A2, the loop `-4:5` must span $[-L^{\max},5]$ from the data.
4. `wtr` column names such as `"w-1"` are not syntactic in R. Use `w_m1` or similar.
5. Guard every weight normalisation against a zero sum: an $\ell$ with no treated observations must be dropped, not divided by 0.
6. Check that `didimputation` passes fixest varying-slope syntax (`pcl[fy]`) through `first_stage`. If it does not, implement the unit-trend BJS in-house (a `fixest` first stage on untreated observations, then impute).
7. The restricted-window run (3a) must re-normalise the `wtr` weights on its own subsample.

---

## 15. Robustness plan and falsification tests

### 15.1 Robustness
Items 1–10, including 3a and 3b, are mandatory for any headline.

| # | Check | Threat |
|---|---|---|
| 1 | Applicant stack (§4.3), with the held-out TOST rule | Crime-driven timing |
| 2 | $A\in\{12,24,36\}$ months; switch at application − 12 months vs $G-A$ | Where the dip falls |
| 3 | **Lag-bin dCDH/CS/SA re-aggregated by $\ell$; primary sample restricted to $L=2$ FY; BJS on the $L=2$ subsample reported next to the dCDH $L=2$ HonestDiD source** | Varying lag (N-M1) |
| 3a | **BJS with a restricted untreated window:** only switcher observations with $t\ge\tilde G_u-6$ enter the $Y(0)$ fit (r2) | Long-run PT built into BJS |
| 3b | **BJS with unit-specific linear trends** in the $Y(0)$ model (r2) | Differential long-run trends |
| 4 | HonestDiD (§4.2); power of pre-trend tests | PT violations |
| 5 | FT-verified only | Misclassification |
| 6 | Estimator set: BJS ↔ dCDH ↔ CS (DR + unconditional) ↔ SA ↔ stacked ↔ Poisson ETWFE ↔ SDID | Estimator dependence |
| 7 | Zero-stock only; three-level bins where cells pass; metro × bin trends where cells pass | Legacy SAR dynamics; cell structure |
| 8 | Support: range rule vs Crump rule vs full pool; minimum-controls floor of 3, 5 or 10 | Comparability; drop rule |
| 9 | Selection diagnostics; Lee/Manski bounds; reweighting | QoL selection |
| 10 | JHB post-policy vs pooled; by metro | Guard mandate |
| 11 | Dynamic vs static clean controls; $(WE)$ as a treatment | SUTVA |
| 12 | Income tercile × period FE; drop FY2020/21 and QoL6 | Shocks |
| 13 | Alternative units | Unit instability |
| 14 | Current-status dose; drop lapsed units | Non-absorbing treatment |
| 15 | Dose terciles vs ACRT vs binary; variants of $\varepsilon_W$ | Dose |
| 16 | Rings; s.4.3 vs constructed perimeters | Perimeters |
| 17 | Drop controls with OSM lift gates on public roads | Undocumented closures |
| 18 | Survey weights; logit | Functional form |
| 19 | E2/E2c as a control | Concurrent development |
| 20 | Spatial lag/error; Conley cut-offs; block bootstrap | Spatial dependence |
| 21 | Add back `insufficient_pre` units ($A$ = 12 months; QoL II) | Relaxed windows |
| 22 | E3: drop clusters with CID overlap and dissolved SRAs; high-dose subset; SRAs before FY2011 | E3-specific |
| 23 | A4: fixed vs time-varying denominator bracket | Composition (n8) |
| 24 | A6: **no-physical-change sample (robustness only; primary keeps all closures)**; exclude the anticipation FY; stack by expiry FY; Wald with combined first stage (i)+(ii) | A6-specific (r1) |

### 15.2 Falsification and placebo tests

| # | Test | Expected |
|---|---|---|
| F1 | Placebo switches at $\tilde G-3$/$-4$ years; $\tilde G$ − 1 wave | 0 |
| F2 | Placebo-unit assignment | Null distribution |
| F3 | Future adopters (first FT after 2024) | 0 |
| F4 | V4 | 0 |
| F5 | V2 | ≈0 (weak) |
| F6 | Predetermined traits | 0 |
| F7 | Satisfaction with water/electricity/refuse | ≈0 under a security-specific channel; read alongside F1–F3 |
| F8 | Non-crime rejections and failed-consent applicants coded at application | A dip and reversion, but no sustained effect |
| F9 | Streets in the application area but outside the perimeter | Displacement or diffusion only |
| F10 | Commercial CIDs on residential burglary | ≈0 |
| F11 | Dip-panel estimates | A rise before $G$ |
| F12 | A6: renewals with no new guard post. **A weak test:** these closures may differ (guards already present, or lapsing), so a non-zero result is not decisive | ≈0 |

---

## 16. Top five referee objections

1. **Mean reversion.** Responses:
   - a re-timed baseline with onset-relative indexing, so no processing years enter the headline;
   - lag-bin, restricted-window and unit-trend robustness;
   - the applicant stack with a held-out balance rule;
   - F8 and F11;
   - HonestDiD from common-reference event studies;
   - placebo-unit RI.

   **A6 may add a design whose timing is plausibly less driven by crime** (scheduled expiries), subject to gate G4 and to the unverified question of whether renewals need fresh crime evidence. It is not a clean solution.
2. **Tiny exposure, uninformative nulls.** Responses:
   - area arms that are ITT-only;
   - the §1.2(b) algebra;
   - exposure claims only from A1-I, A2-X, or E3 high-dose with bounds;
   - TOST in area units;
   - MDEs from the P-E simulation;
   - an explicit statement that A1-I cannot detect legitimacy-sized effects.
3. **Mismeasured treatment.** Responses:
   - the onset hierarchy and G0 (register or imagery, with imagery dating in the funded fallback);
   - FT-verified robustness;
   - OSM lift gates;
   - the s.4.7 cross-check.
4. **Walls vs guards; mechanism.** Responses:
   - E1 is treated as a bundle, and the pooled estimate is labelled "enclosure";
   - E3 (guards without walls) and A6 (guards added to walls; a bundle ITT, plus a fuzzy Wald under stated assumptions);
   - the directional hypotheses and interpretation matrix;
   - the police-referent co-primary;
   - the compliance audit.
5. **QoL limitations.** Responses:
   - selection diagnostics and bounds, with the reachable-population estimand;
   - locked harmonisation;
   - dropping QoL6 in robustness;
   - trust and procedural items used only as cross-sections.

**Also addressed:** controls that differ from treated units; SAPS reporting; external validity (Brazil, Delhi, Nairobi, BIDs); cohort timing.

---

## 17. Open items, ASSUMED list and dependencies

### 17.1 ASSUMED parameters

| Item | Value | Replaced by |
|---|---|---|
| $S$, $k$, $k_1$, $R/\Delta E$, positive-stock share, `cohort_class` counts | §8; unknown | P-C |
| $\pi_{FT}$; $N$ | 0.1–0.5; 6–144 | P-A, P-D |
| $A$; distribution of $L^{app}$ | 24 months; unknown | P-D |
| Variances, $\rho$, $f$, $V_w$ | §8.1 | **P-E** |
| $D_w$, $D_c$; unit counts | 14.5k, 35k; 135/107/112 wards, ~110 stations | Census, MDB, SAPS |
| $J_C$ | 20 / 60 / ≤10 / 30 / 18 | P-C |
| Minimum controls per cell | 5 | Fixed pre-specification; robustness at 3/10 |
| $\pi$ | 0.7 | GCRO metadata; A1-I |
| DEFF; outer/in ratio | 1.3; 5 | A1-I |
| Burglary base rate | 20–40 per 1,000 per year | SAPS incidents |
| A6 first-stage floor; physical-change ceiling | 30%; 20% | Pre-specification; P-D |
| Thresholds | 0.25 SD (A1-I); 0.40 log (E1); 0.25 log (E3) | **Accepted by the user, 2026-09-30** (§18.1) |

### 17.2 Verification items
1. QoL questionnaires II–7, including whether sampling points are reused.
2. JHB policy history:
   - the adoption date of the 2012 base text;
   - whether pre-2012 authorisations carried a guard condition;
   - **whether subsequent applications (s.10–12) require fresh crime evidence** (A6).

   All three are now covered by the JRA request.
3. Tshwane and Ekurhuleni policies.
4. Moratoria and backlogs.
5. Imagery coverage **and dating precision** (needed for G0(b) in the funded fallback).
6. The Cape Town SRA by-law; records of failed SRAs.
7. Package details:
   - `didimputation`: the `wtr` interface and whether varying-slope `first_stage` is passed through;
   - `DIDmultiplegtDYN`: effect indexing and the HonestDiD hook;
   - `etwfe`: offset handling;
   - availability of `contdid` and `fwildclusterboot`.
8. Citation details marked UNVERIFIED (Appendix B).

### 17.3 Data requests and what they unlock

| Request | Unlocks | If refused |
|---|---|---|
| **JRA register and files** (sent) | G0; $\tilde G$ and $L$; applicant stack; perimeters; providers | **User decision 2026-09-30: fund the continuous gazette compile to 1999 plus imagery classification *and dating* of installation for events known only from a final notice** (G0(a) + G0(b)); 6–12 weeks |
| **JRA A6 files** (added to the request; user decision 2026-09-30) | Pre-policy authorisations; renewal files; pre-2012 policy text; whether renewals require crime evidence | No A6 |
| **GCRO SAL/GPS** (sent) | A1-I; A1-I-CS; Lee bounds | RQ1 = A1-W ITT + descriptive |
| **GCRO metadata / gated layer** (sent) | $\pi$; E2 validation | ASSUMED $\pi$; OSM + gazetteer |
| **SAPS incident data** (sent; Cape Town scope §18.6) | A2-X; E3 without misalignment; A6 at zone level | No E1 exposed-level effects |
| Census SAL; MDB; Open Buildings; SRA business plans; QoL questionnaires | Denominators, units, E2 timing, E3 onsets, the outcome lock | Required |
| AB geocodes (deferred) | A5 | Province-level AB |

### 17.4 Sequencing
1. **Now:**
   - P-B, P-C, P-D;
   - P-E, first with ASSUMED cohorts;
   - questionnaire check;
   - units and common support;
   - policy reads;
   - E3 onset compilation.

   No A1-W/A2-P estimation code until the patch is accepted (critic's condition, now met: round 3 approved).
2. **When P-A arrives, or at 8 weeks:** re-run P-E and apply G0–G4, with user sign-off, and log it. If JRA refuses, start the funded compile plus imagery dating (§18.7).
3. **Before any outcome merge:** lock the outcomes, families, bins, $\varepsilon_W$, support, cell rule and headline rule, then register the PAP.

---

## 18. Decisions that belong to the user

Decisions the user took on 2026-09-30 are marked **DECIDED**. The rest remain recommendations.

### 18.1 MDE thresholds, as ratios to benchmarks: **DECIDED, accepted as proposed**

| Arm | Threshold | Ratio to benchmark |
|---|---|---|
| E1 crime (A2-X, A6) | 0.40 log points | ≈0.8× the gating benchmark (≈0.5 log) |
| E3 | 0.25 log points | ≈2.5× the BID benchmark (≈0.10) |
| A1-I | 0.25 SD | 1.7–5× plausible legitimacy effects (0.05–0.15 SD) |

- The E3 threshold is itself coarse. At the planning MDE of 0.36 (≈3.6×), exposure-scaled statements for E3 will probably fail.
- **Stated plainly: A1-I is underpowered for legitimacy-sized effects.** It can detect the safety first stage, or unusually large performance shifts.
- **What accepting these thresholds means:** they are feasibility gates, and null legitimacy results will not be informative about small effects. The paper will say so.

### 18.2 A1-W framing
- **Recommendation (not yet decided):** a secondary area ITT in the appendix, with TOST.
- It moves to the main text only if A1-I is unavailable, labelled as an area ITT on the reachable population.

### 18.3 Control comparability vs size
- **Recommendation (not yet decided):** common support with not-yet-treated units within bin, the minimum-controls rule, WCR and placebo-unit RI, even if $J_C$ is only about 10–30.
- The full never-treated pool is robustness only.

### 18.4 Headline construct vs pooled estimate: **DECIDED, pooled "enclosure" headline**
- Estimation pools the three metros.
- **The pooled headline is labelled "enclosure".**
- "Mandated guarding" is carried only by:
  - the JHB post-policy subset;
  - A2-X;
  - A6.
- Pooling the guarding language waits for the Tshwane and Ekurhuleni policy read.

### 18.5 When to adopt the NO-GO framing
- **Recommendation (not yet decided):** decide at the gate (P-A arrival or 8 weeks).
- Start E3 onset compilation and P-E now.

### 18.6 Scope of the SAPS incident request
- **Recommendation (not yet decided):** include Cape Town precincts.

### 18.7 If JRA refuses the register: **DECIDED, the user will fund the continuous gazette plus imagery compile**
- **Scope requirement:**
  - the continuous compile back to 1999 satisfies G0(a), the classification half;
  - events known only from a final notice have 24-month onset precision. The fallback must therefore include **imagery dating of physical installation** (the bracketing captures) for those events so that G0(b) can pass. Classification alone is not enough.
- **Order of work:** JHB first; Tshwane and Ekurhuleni only after their policies are read.
- **Timing:** 6–12 weeks.
- **Budget cue:** if imagery cannot date at least 80% of FT onsets to within 12 months (tested on the P-D sample), G0 fails regardless. E1 then becomes stock-only (§10), even though the compile is funded.

### 18.8 A6: **DECIDED, pursued**
- The JRA request now includes renewal files and the pre-2012 policy text (plus pre-policy authorisations).
- Analysis effort is committed only if G4 passes.

---

## Appendix A: Carry-forward items (explorer-critic)

| Item | Resolution | Where |
|---|---|---|
| N1 | 50–240 notices a year; 6–144 FT SARs | §9.1 |
| N2(a) | Per-unit clean pre-waves relative to $\tilde G_u$ | §3.3, §9.4 |
| N2(b) | First-switch dose; $\varepsilon_W=1/(\pi\bar n)$; terciles locked | §2.7 |
| N2(c) | Recomputed MDEs; P-E simulation | §8, §9.2 |
| N2(d) | Register → continuous series → imagery | §2.4, §9.3 |
| N3 | PSC claims limited to JHB post-policy; pooled estimate = "enclosure" | §2.1, §18.4 |
| N4 | Wave-reliability criterion | §9.4 |
| N5 | Scrape facts and roles | §12 |
| N6 | NO-GO fallback | §10 |
| R1 | Eligibility table; questionnaire checks | §11.1 |

## Appendix B: BibTeX entries needed (not added to `Bibliography_base.bib`)

Check any field marked `note = {UNVERIFIED ...}` before the writer phase.

```bibtex
@article{callaway2021did, author={Callaway, Brantly and Sant'Anna, Pedro H. C.}, title={Difference-in-Differences with Multiple Time Periods}, journal={Journal of Econometrics}, volume={225}, number={2}, pages={200--230}, year={2021}}
@article{sun2021event, author={Sun, Liyang and Abraham, Sarah}, title={Estimating Dynamic Treatment Effects in Event Studies with Heterogeneous Treatment Effects}, journal={Journal of Econometrics}, volume={225}, number={2}, pages={175--199}, year={2021}}
@article{borusyak2024revisiting, author={Borusyak, Kirill and Jaravel, Xavier and Spiess, Jann}, title={Revisiting Event-Study Designs: Robust and Efficient Estimation}, journal={Review of Economic Studies}, volume={91}, number={6}, pages={3253--3285}, year={2024}}
@article{dechaisemartin2020twfe, author={de Chaisemartin, Cl{\'e}ment and D'Haultf{\oe}uille, Xavier}, title={Two-Way Fixed Effects Estimators with Heterogeneous Treatment Effects}, journal={American Economic Review}, volume={110}, number={9}, pages={2964--2996}, year={2020}}
@article{dechaisemartin2018fuzzy, author={de Chaisemartin, Cl{\'e}ment and D'Haultf{\oe}uille, Xavier}, title={Fuzzy Differences-in-Differences}, journal={Review of Economic Studies}, volume={85}, number={2}, pages={999--1028}, year={2018}}
@article{dechaisemartin2024intertemporal, author={de Chaisemartin, Cl{\'e}ment and D'Haultf{\oe}uille, Xavier}, title={Difference-in-Differences Estimators of Intertemporal Treatment Effects}, journal={Review of Economics and Statistics}, year={2024}, note={UNVERIFIED volume/pages; possibly forthcoming}}
@article{dechaisemartin2023survey, author={de Chaisemartin, Cl{\'e}ment and D'Haultf{\oe}uille, Xavier}, title={Two-Way Fixed Effects and Differences-in-Differences with Heterogeneous Treatment Effects: A Survey}, journal={Econometrics Journal}, volume={26}, number={3}, pages={C1--C30}, year={2023}}
@techreport{callaway2024continuous, author={Callaway, Brantly and Goodman-Bacon, Andrew and Sant'Anna, Pedro H. C.}, title={Difference-in-Differences with a Continuous Treatment}, institution={National Bureau of Economic Research}, type={Working Paper}, number={32117}, year={2024}}
@article{goodmanbacon2021, author={Goodman-Bacon, Andrew}, title={Difference-in-Differences with Variation in Treatment Timing}, journal={Journal of Econometrics}, volume={225}, number={2}, pages={254--277}, year={2021}}
@article{roth2022pretest, author={Roth, Jonathan}, title={Pretest with Caution: Event-Study Estimates after Testing for Parallel Trends}, journal={American Economic Review: Insights}, volume={4}, number={3}, pages={305--322}, year={2022}}
@article{rambachan2023more, author={Rambachan, Ashesh and Roth, Jonathan}, title={A More Credible Approach to Parallel Trends}, journal={Review of Economic Studies}, volume={90}, number={5}, pages={2555--2591}, year={2023}}
@article{roth2023trending, author={Roth, Jonathan and Sant'Anna, Pedro H. C. and Bilinski, Alyssa and Poe, John}, title={What's Trending in Difference-in-Differences? A Synthesis of the Recent Econometrics Literature}, journal={Journal of Econometrics}, volume={235}, number={2}, pages={2218--2244}, year={2023}}
@article{ashenfelter1978, author={Ashenfelter, Orley}, title={Estimating the Effect of Training Programs on Earnings}, journal={Review of Economics and Statistics}, volume={60}, number={1}, pages={47--57}, year={1978}}
@article{heckman1999dip, author={Heckman, James J. and Smith, Jeffrey A.}, title={The Pre-Programme Earnings Dip and the Determinants of Participation in a Social Programme}, journal={Economic Journal}, volume={109}, number={457}, pages={313--348}, year={1999}}
@article{lee2009bounds, author={Lee, David S.}, title={Training, Wages, and Sample Selection: Estimating Sharp Bounds on Treatment Effects}, journal={Review of Economic Studies}, volume={76}, number={3}, pages={1071--1102}, year={2009}}
@article{wooldridge2023nonlinear, author={Wooldridge, Jeffrey M.}, title={Simple Approaches to Nonlinear Difference-in-Differences with Panel Data}, journal={Econometrics Journal}, volume={26}, number={3}, pages={C31--C66}, year={2023}}
@article{chen2024logs, author={Chen, Jiafeng and Roth, Jonathan}, title={Logs with Zeros? Some Problems and Solutions}, journal={Quarterly Journal of Economics}, volume={139}, number={2}, pages={891--936}, year={2024}}
@article{arkhangelsky2021sdid, author={Arkhangelsky, Dmitry and Athey, Susan and Hirshberg, David A. and Imbens, Guido W. and Wager, Stefan}, title={Synthetic Difference-in-Differences}, journal={American Economic Review}, volume={111}, number={12}, pages={4088--4118}, year={2021}}
@article{cengiz2019, author={Cengiz, Doruk and Dube, Arindrajit and Lindner, Attila and Zipperer, Ben}, title={The Effect of Minimum Wages on Low-Wage Jobs}, journal={Quarterly Journal of Economics}, volume={134}, number={3}, pages={1405--1454}, year={2019}}
@techreport{wing2024stacked, author={Wing, Coady and Freedman, Seth M. and Hollingsworth, Alex}, title={Stacked Difference-in-Differences}, institution={National Bureau of Economic Research}, type={Working Paper}, number={32054}, year={2024}}
@article{burlig2020panel, author={Burlig, Fiona and Preonas, Louis and Woerman, Matt}, title={Panel Data and Experimental Design}, journal={Journal of Development Economics}, volume={144}, pages={102458}, year={2020}}
@article{conley1999, author={Conley, Timothy G.}, title={GMM Estimation with Cross Sectional Dependence}, journal={Journal of Econometrics}, volume={92}, number={1}, pages={1--45}, year={1999}}
@article{cameron2008bootstrap, author={Cameron, A. Colin and Gelbach, Jonah B. and Miller, Douglas L.}, title={Bootstrap-Based Improvements for Inference with Clustered Errors}, journal={Review of Economics and Statistics}, volume={90}, number={3}, pages={414--427}, year={2008}}
@article{mackinnon2017wild, author={MacKinnon, James G. and Webb, Matthew D.}, title={Wild Bootstrap Inference for Wildly Different Cluster Sizes}, journal={Journal of Applied Econometrics}, volume={32}, number={2}, pages={233--254}, year={2017}}
@article{mackinnon2018few, author={MacKinnon, James G. and Webb, Matthew D.}, title={The Wild Bootstrap for Few (Treated) Clusters}, journal={Econometrics Journal}, volume={21}, number={2}, pages={114--135}, year={2018}}
@article{roodman2019fast, author={Roodman, David and Nielsen, Morten {\O}rregaard and MacKinnon, James G. and Webb, Matthew D.}, title={Fast and Wild: Bootstrap Inference in Stata Using boottest}, journal={Stata Journal}, volume={19}, number={1}, pages={4--60}, year={2019}}
@article{conley2011inference, author={Conley, Timothy G. and Taber, Christopher R.}, title={Inference with ``Difference in Differences'' with a Small Number of Policy Changes}, journal={Review of Economics and Statistics}, volume={93}, number={1}, pages={113--125}, year={2011}}
@article{abadie2023cluster, author={Abadie, Alberto and Athey, Susan and Imbens, Guido W. and Wooldridge, Jeffrey M.}, title={When Should You Adjust Standard Errors for Clustering?}, journal={Quarterly Journal of Economics}, volume={138}, number={1}, pages={1--35}, year={2023}}
@article{romano2005stepwise, author={Romano, Joseph P. and Wolf, Michael}, title={Stepwise Multiple Testing as Formalized Data Snooping}, journal={Econometrica}, volume={73}, number={4}, pages={1237--1282}, year={2005}}
@article{romano2016efficient, author={Romano, Joseph P. and Wolf, Michael}, title={Efficient Computation of Adjusted p-Values for Resampling-Based Stepdown Multiple Testing}, journal={Statistics \& Probability Letters}, volume={113}, pages={38--40}, year={2016}}
@article{benjamini1995, author={Benjamini, Yoav and Hochberg, Yosef}, title={Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing}, journal={Journal of the Royal Statistical Society: Series B}, volume={57}, number={1}, pages={289--300}, year={1995}}
@article{holm1979, author={Holm, Sture}, title={A Simple Sequentially Rejective Multiple Test Procedure}, journal={Scandinavian Journal of Statistics}, volume={6}, number={2}, pages={65--70}, year={1979}}
@article{anderson2008multiple, author={Anderson, Michael L.}, title={Multiple Inference and Gender Differences in the Effects of Early Intervention}, journal={Journal of the American Statistical Association}, volume={103}, number={484}, pages={1481--1495}, year={2008}}
@article{kling2007, author={Kling, Jeffrey R. and Liebman, Jeffrey B. and Katz, Lawrence F.}, title={Experimental Analysis of Neighborhood Effects}, journal={Econometrica}, volume={75}, number={1}, pages={83--119}, year={2007}}
@article{crump2009overlap, author={Crump, Richard K. and Hotz, V. Joseph and Imbens, Guido W. and Mitnik, Oscar A.}, title={Dealing with Limited Overlap in Estimation of Average Treatment Effects}, journal={Biometrika}, volume={96}, number={1}, pages={187--199}, year={2009}}
@article{hainmueller2012entropy, author={Hainmueller, Jens}, title={Entropy Balancing for Causal Effects}, journal={Political Analysis}, volume={20}, number={1}, pages={25--46}, year={2012}}
@article{hartman2018equivalence, author={Hartman, Erin and Hidalgo, F. Daniel}, title={An Equivalence Approach to Balance and Placebo Tests}, journal={American Journal of Political Science}, volume={62}, number={4}, pages={1000--1013}, year={2018}}
@article{lakens2017equivalence, author={Lakens, Dani{\"e}l}, title={Equivalence Tests: A Practical Primer for t Tests, Correlations, and Meta-Analyses}, journal={Social Psychological and Personality Science}, volume={8}, number={4}, pages={355--362}, year={2017}}
@article{solon2015weighting, author={Solon, Gary and Haider, Steven J. and Wooldridge, Jeffrey M.}, title={What Are We Weighting For?}, journal={Journal of Human Resources}, volume={50}, number={2}, pages={301--316}, year={2015}}
@article{keele2015boundaries, author={Keele, Luke J. and Titiunik, Roc{\'i}o}, title={Geographic Boundaries as Regression Discontinuities}, journal={Political Analysis}, volume={23}, number={1}, pages={127--155}, year={2015}}
@article{cinelli2020sensitivity, author={Cinelli, Carlos and Hazlett, Chad}, title={Making Sense of Sensitivity: Extending Omitted Variable Bias}, journal={Journal of the Royal Statistical Society: Series B}, volume={82}, number={1}, pages={39--67}, year={2020}}
@article{aronow2017interference, author={Aronow, Peter M. and Samii, Cyrus}, title={Estimating Average Causal Effects under General Interference, with Application to a Social Network Experiment}, journal={Annals of Applied Statistics}, volume={11}, number={4}, pages={1912--1947}, year={2017}}
@misc{butts2021spillovers, author={Butts, Kyle}, title={Difference-in-Differences Estimation with Spatial Spillovers}, howpublished={arXiv:2105.03737}, year={2021}, note={UNVERIFIED later journal version}}
@article{delgado2015spatial, author={Delgado, Michael S. and Florax, Raymond J. G. M.}, title={Difference-in-Differences Techniques for Spatial Data: Local Autocorrelation and Spatial Interaction}, journal={Economics Letters}, volume={137}, pages={123--126}, year={2015}}
@article{weisburd2006displacement, author={Weisburd, David and Wyckoff, Laura A. and Ready, Justin and Eck, John E. and Hinkle, Joshua C. and Gajewski, Frank}, title={Does Crime Just Move Around the Corner? A Controlled Study of Spatial Displacement and Diffusion of Crime Control Benefits}, journal={Criminology}, volume={44}, number={3}, pages={549--592}, year={2006}}
@article{guerette2009displacement, author={Guerette, Rob T. and Bowers, Kate J.}, title={Assessing the Extent of Crime Displacement and Diffusion of Benefits: A Review of Situational Crime Prevention Evaluations}, journal={Criminology}, volume={47}, number={4}, pages={1331--1368}, year={2009}}
@article{clarke1994diffusion, author={Clarke, Ronald V. and Weisburd, David}, title={Diffusion of Crime Control Benefits: Observations on the Reverse of Displacement}, journal={Crime Prevention Studies}, volume={2}, pages={165--184}, year={1994}, note={UNVERIFIED pages}}
@article{bowers2003wdq, author={Bowers, Kate J. and Johnson, Shane D.}, title={Measuring the Geographical Displacement and Diffusion of Benefit Effects of Crime Prevention Activity}, journal={Journal of Quantitative Criminology}, volume={19}, number={3}, pages={275--301}, year={2003}}
@article{ayres1998lojack, author={Ayres, Ian and Levitt, Steven D.}, title={Measuring Positive Externalities from Unobservable Victim Precaution: An Empirical Analysis of Lojack}, journal={Quarterly Journal of Economics}, volume={113}, number={1}, pages={43--77}, year={1998}}
@article{gonzaleznavarro2013, author={Gonzalez-Navarro, Marco}, title={Deterrence and Geographical Externalities in Auto Theft}, journal={American Economic Journal: Applied Economics}, volume={5}, number={4}, pages={92--110}, year={2013}}
@article{sidebottom2018gating, author={Sidebottom, Aiden and Tompson, Lisa and Thornton, Amy and Bullock, Karen and Tilley, Nick and Bowers, Kate and Johnson, Shane D.}, title={Gating Alleys to Reduce Crime: A Meta-Analysis and Realist Synthesis}, journal={Justice Quarterly}, volume={35}, number={1}, pages={55--86}, year={2018}, note={UNVERIFIED effect magnitude cited in memo}}
@article{macdonald2016private, author={MacDonald, John M. and Klick, Jonathan and Grunwald, Ben}, title={The Effect of Private Police on Crime: Evidence from a Geographic Regression Discontinuity Design}, journal={Journal of the Royal Statistical Society: Series A}, volume={179}, number={3}, pages={831--846}, year={2016}}
@article{cook2011bids, author={Cook, Philip J. and MacDonald, John}, title={Public Safety through Private Action: An Economic Assessment of BIDs}, journal={Economic Journal}, volume={121}, number={552}, pages={445--462}, year={2011}, note={UNVERIFIED effect magnitude cited in memo}}
@article{brooks2008bids, author={Brooks, Leah}, title={Volunteering to Be Taxed: Business Improvement Districts and the Extra-Governmental Provision of Public Safety}, journal={Journal of Public Economics}, volume={92}, number={1--2}, pages={388--406}, year={2008}, note={UNVERIFIED effect magnitude cited in memo}}
@book{hirschman1970exit, author={Hirschman, Albert O.}, title={Exit, Voice, and Loyalty: Responses to Decline in Firms, Organizations, and States}, publisher={Harvard University Press}, address={Cambridge, MA}, year={1970}}
@book{caldeira2000walls, author={Caldeira, Teresa P. R.}, title={City of Walls: Crime, Segregation, and Citizenship in S{\~a}o Paulo}, publisher={University of California Press}, address={Berkeley}, year={2000}}
```

---

## Revision log (round 2)

| ID | Change | Where |
|---|---|---|
| C1 | Re-timed switch $\tilde G$ for all arms; dip reported separately; table and code fixed. *The indexing was refined in round 3* (N-M1) | §2.2, §3.3–3.4, §4.2, §14 |
| M1 | One switcher definition; stock-bin comparisons in A1 and A2; zero-stock robustness; P-C share | §2.3, §3.3, §9.2 |
| M2 | Recount; common support; not-yet-treated within bin; dynamic clean controls; composition report | §3.2 |
| M3 | Area arms ITT-only by design; bounded exposure-scaled interval; E3 exception; gates gain a "licenses" column; §8 recomputed | §1.2(b), §8, §9.3 |
| M4 | First-switch dose; cohort P/Q; AR(1) inflation; P-E simulation protocol | §8.4, §9.2 |
| M5 | Applicant stack: truncation, rejections, withdrawals, TOST, contamination, failed applicants | §4.3, §2.4 |
| M6 | HonestDiD from common-reference event studies, with pre-coefficient counts | §4.2(5) |
| M7 | Zone × group FE; two imputation runs; recomputed MDE; point-reuse check | §1.2(d), §8.3 |
| M8 | Full E3 section | §5 |
| M9 | Hypotheses; interpretation matrix; F1b co-primary | §1.3, §11.1 |
| m1–m11 | Unit label; $\varepsilon_W$ includes $\pi$; extended algebra; PSC claims restricted to post-2012; 6–144; code plumbing; headline rule; RI read as a sharp null; A1 crime trajectory; A4 offset; BibTeX appendix | Various |
| Alt #4 | A6 added (*revised in rounds 3 and 4*) | §2.8 |
| User decisions | §18 consolidated | §18 |

## Revision log (round 3, targeted patch)

| ID | Critic issue | Change | Where |
|---|---|---|---|
| **N-M1** | $L=G-\tilde G$ varies, but effects were indexed from $\tilde G$ | Rule: the baseline is anchored at $\tilde G_u-1$; post effects are indexed by $\ell=t-G_u$; the dip $\ell\in[-L_u,-1]$ is reported separately; indexing from $\tilde G$ is prohibited. **Chosen option: BJS aggregated by $t-G$ is the A2-P primary** (the justification was softened in round 4, r2). **Re-timed dCDH by lag bin** $\{2,3,\ge4\}$ FY, re-aggregated by $\ell$, is the principal robustness check and the HonestDiD source; $L=2$-only is a further sensitivity. The BJS row in §3.4 now matches the A1 code (`wtr` by $t-G$). **At least 2 clean pre-waves per unit.** Code updated | §2.2, §3.3, §3.4, §4.2, §9.4, §14 steps 1, 3, 5; §15.1 #3 |
| **N-M2** | Pre-window FT switches were unhandled; $B_u$ was inconsistent | $G_u$ = first FT switch after panel start; `cohort_class` ∈ {reported, pre_window, insufficient_pre, post_window, never}. Pre-window cohorts are kept as treated (excluded from $Y(0)$ from $\tilde G$ on), never used as controls, never reported. $B_u$ = closures active at panel start only. Flag and counts added to P-C and to the code | §2.3, §9.2 P-C, §14 step 2 |
| **N-M3** | Metro × bin × wave cells too thin | Coarse bins {0,>0}; additive FE `metro^period + bin^period`; dCDH `trends_nonparam = bin`; **at least 5 eligible controls per bin × period and metro × period cell**; failing switchers dropped explicitly and reported; $J_T$ counted after the rule; P-E mirrors cells, FE and rule | §2.3, §3.2 rule 6, §8.2, §9.2–9.3, §14 step 2, §15.1 #7–8 |
| **N-M4** | A6's exogeneity overclaimed | Switch at the **scheduled** first post-policy expiry (ITT on intention-to-renew); lapsed and non-renewed closures kept; renewal × guard installation as the first stage; fuzzy Wald; imagery codes guard posts and physical changes; separate anticipation FY; G4 adds a first-stage floor, a physical-change condition and a timing-spread condition; the crime-evidence requirement for renewals is UNVERIFIED; objection 1 softened; F12 labelled a weak test (*further revised in round 4, r1*) | §1.1, §2.8, §3.3, §9.3 G4, §14 step 6, §15.2 F12, §16(1), §17.2 |
| n1 | TOST after entropy balancing was vacuous | Balance on (a) and (c); TOST on held-out (b) and (d); Kish ESS ≥ max(10, 50% of controls) | §4.3(4) |
| n2 | HonestDiD post count | All 8 effects passed; `l_vec` targets ℓ = 0..3 | §4.2(5), §14 step 7 |
| n3 | Window inconsistencies | One window per arm; $\tilde G\ge$ FY2009/10; A3 $G\ge$ FY2011/12; power average 0.307 | §3.3, §5.7, §8.4, §9.3–9.4 |
| n4 | $J_T$ inconsistent with the recount | JHB $J_T$ capped at 30; separate 3-metro column | §8.2, §8.4 |
| n5 | A1-I zones overlapped | Precedence in > ring > outer; cross-exposed outer respondents excluded | §1.2(d), §14 step 4 |
| n6 | G0 is really a register-or-imagery gate | Stated explicitly; new user decision added | §9.3, §18.7 |
| n7 | A3 RI too coarse | Report distinct assignments and the exact p-value grid; pair with timing RI | §5.7, §13.2 |
| n8 | A4 fixed offset | Labelled a bundle; bracketed with a time-varying denominator | §3.3 A4, §15.1 #23 |
| §18 | Thresholds; pooled construct | Thresholds stated as ratios to benchmarks; pooled estimate = "enclosure"; §18.7 and §18.8 added | §0, §2.1, §8.3, §18 |

## Revision log (round 4, clean-up)

| ID | Critic / coordinator item | Change | Where |
|---|---|---|---|
| **r4** | The round-3 rewrite dropped approved §6/§7 detail | Restored: §6.1(a) s.7.1.7 and the VERIFIED\* refusal evidence (highest access refusal in gated areas; the inaccessible QoL II Midvaal ward); §6.1(b) substitution toward non-enclosed SALs; §6.2(2) the predetermined-trait list (race, age, sex, home language, education, dwelling type, tenure, years at address); §6.2(3) expected interviews = Census dwellings × sampling fraction; §6.3(1) calibration target = Census 2011 SAL composition (dwelling type × race × income band); §6.3(2) Lee trimming share $p=(\pi_C-\pi_T)/\pi_C$ and the monotonicity assumption; §6.3(3) the imputation percentiles; §6.4 detail; §7(2) "weakly identified in the area arms"; §7(3) "§3.2 rule 3"; §7(4) the **"or within 1 km of the cluster boundary"** displacement trigger | §6, §7 |
| **r1** | A6 primary conditioned on behaviour after assignment; assumptions unstated | **All closures kept in the ITT** (lapsed, non-renewed, physically changed). Physical change treated as a first-stage/bundle component (component ii), with lapse/removal as component iii. No-physical-change sample is robustness only. §2.8, §3.3 and §15.1 #24 made consistent. **Exclusion restriction and monotonicity stated explicitly**, with a test for defiers (lapse of pre-existing voluntary guards). Stated that scheduled expiry also triggers the renewal process itself, so the ITT is a bundle. G4 condition 4 recast as a ceiling of ≤20% physical change, without dropping closures. P-D codes all three components plus pre-existing guards | §1.1, §2.8, §3.3 A6, §9.2 P-D, §9.3 G4, §14 step 6, §15.1 #24, §16(4) |
| **r2** | BJS relies on long-run PT; "only estimator" overstated | Added **mandatory** robustness: #3a BJS with a restricted untreated window (switchers' $t\ge\tilde G_u-6$), and #3b BJS with unit-specific linear trends. **BJS on the $L=2$ subsample reported next to the dCDH $L=2$ HonestDiD source.** Justification softened to efficiency, simplicity and consistency with A1 | §3.3 A2-P, §4.2(5), §14 step 5, §15.1 #3/3a/3b, §16(1) |
| **r3** | Code defects | Not fixed (left for the coder as instructed); listed in the new §14.1 "Coder hand-off notes" with four further plumbing notes | §14.1 |
| **r5** | E3 row not rescaled; header date stale | E3 rescaled to the 0.307 average (×1.015): MDE$_\theta$ 0.108, exposure-scaled 0.36, murder 0.27; high-dose subset 0.146 / 0.24; $J_T$ = 9 sensitivity 0.119 / 0.40. Knock-on text in §0, §5.8 and §18.1 (≈3.6×). Header date 2026-09-30 | Header, §0, §5.8, §8.4, §18.1 |
| **User decisions (2026-09-30)** | Record them | §18.1 thresholds accepted as proposed; §18.4 pooled "enclosure" headline; §18.8 A6 pursued, with the JRA request now covering renewal files, the pre-2012 policy and pre-policy authorisations; §18.7 **user will fund the continuous gazette + imagery compile if JRA refuses**, with the critic's scope condition that the fallback must include **imagery dating of installation for final-notice-only events (G0(b))**, not only classification. Propagated to §1.1, §2.1, §2.8, §9.2 P-A, §9.3 (G0 note), §16(3), §17.1, §17.2(5), §17.3, §17.4 | §18 and the listed sections |

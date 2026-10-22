# Data Exploration: PSC Exposure (Gated Communities & State Attitudes, South Africa)

**Agent:** explorer (creator; not self-scored)
**Round:** 2 (revised after explorer-critic round 1, 70/100; review at `quality_reports/data_review_explorer-critic_r1_2026-09-29.md`)
**Date:** 2026-09-29
**Phase:** Discovery (data)
**Plan:** `quality_reports/plans/2026-09-29_data-feasibility.md` (Workstream A)
**Scope:** Treatment sources (location, boundary, timing of enclosures, gated estates and PSC presence) and outcome sources (state attitudes, violence), graded A–D, with a joint-feasibility and identification assessment. No data files downloaded and no applications submitted. Gazette issues were opened only to read their contents pages for the desk check in Section 3.

## Evidence labels (revised, critic #6)

| Label | Meaning |
|---|---|
| **VERIFIED** | I read the primary text or image myself (PDF pages rendered in this session: the JHB SAR Policy 2018, the CoJ SAR notice of 2021, gazette contents pages, the AidData method PDF, the AB geocode application form, AB R9 SA summary pages, the ACLED 2023 codebook, the SAHRC boom-gate report, the JRA Ref 438 notice). |
| **VERIFIED\*** | A primary page or API read through the fetch tool's summariser (Overpass/taginfo JSON counts, the ArcGIS REST count/fields, DataFirst catalogue and variable-label pages). Low risk, but a figure could be mis-transcribed, so spot-check before use. |
| **SECONDARY** | A news article, blog, third-party repository or committee report, not the data owner. |
| **SNIPPET** | Only a search-engine summary. Treat as a lead, not a fact. |
| **UNVERIFIED** | Not confirmed. |
| **ESTIMATE** | My own calculation, with the method stated. |

Round-1 relabels: Tshwane "4-year validity" → SNIPPET; Lightstone "~5,000 estates / 430–460k properties" → VERIFIED\* and "nearly 8,000" → SNIPPET; GTI "249% growth" → SNIPPET; PSIRA figures → SECONDARY; ACLED SA composition → SNIPPET; QoL I–6 sample sizes → SNIPPET (QoL7 n = 13,795 VERIFIED\*); AB SA sample sizes for R1–R8 and R10 → SNIPPET (R9 n = 1,582 VERIFIED); AB R8+ GPS recording → SNIPPET; "145 Gauteng stations" → SNIPPET; JHB "in excess of 400" SARs → **VERIFIED** (CoJ notice, 29 June 2021); JHB "about 350" → SECONDARY. Round-1 "VERIFIED" items that came from API/catalogue summaries are now VERIFIED\*.

---

## 0. Headline findings (revised)

1. **The Gauteng SAR road-closure register is the right anchor, but gazette dates are mostly not dates of *first* enclosure.** Verified from the JHB SAR Policy 2018:
   - Authorisations last **2 years** from gazetting, extendable up to 6 years (s.3.2.4, s.8.1).
   - A closure must be **re-applied for** before it lapses, and the re-application is processed and advertised again (s.10–11).
   - Applicants must supply **crime evidence for the six months before** the application (s.4.4), consent from **67%** of affected persons (s.4.8), and a meeting with SAPS (s.5.3).
   - **Every closure must have at least one access point manned 24 hours by a PSIRA-registered security provider** (s.7.1.2, s.7.1.8), and the application names that provider (s.4.10.1).

   So a SAR is *enclosure plus mandated private guarding*, selected on recent crime. In a 6-issue gazette sample (Section 3), 2024 JHB final approvals carry **low reference numbers (42, 75, 84)**. This suggests that many 2020s notices re-authorise long-standing closures (inference, UNVERIFIED). **The number of first-time closures in 2009–2024 is unknown.** A one-metro pilot with a go/no-go threshold (Section 5.1) must settle it before Architecture 1 is adopted.
2. **Staggered DiD with SAR is *conditional*, not "strong"** (critic #1). It needs (a) enough first-time closures inside the ward-reliable QoL window (2013/14–2023/24), (b) credible pre-trends given crime-driven timing, and (c) handling of survey non-response caused by treatment (critic #2).
3. **OSM:**
   - Estate polygons are nearly absent: in Johannesburg, 852 residential-landuse features, only 2 of them `access=private` (VERIFIED\*).
   - There are many **private road *segments*** (Johannesburg 11,664; Tshwane 12,254; VERIFIED\*). A segment count is **not an enclave count**, and completeness is unvalidated. Enclaves must be constructed and validated (Section 2).
4. **GCRO QoL** is the strongest attitudes source for Gauteng, with public identifiers only at ward level (VERIFIED\*).
   - Ward-level analysis is credible only from **QoL III (2013/14)** onward (QoL I has about 13 respondents per ward; ESTIMATE).
   - The item audit (Section 6) finds performance-legitimacy, safety and victimisation items across several waves. It finds **no normative-legitimacy item and no private-security-use item** in QoL; those come only from Afrobarometer (normative) or VOCS/AB (reliance).
5. **Afrobarometer** cannot support boundary or distance-band designs. AidData geocodes are place-name centroids (VERIFIED). AB is the only source of normative-legitimacy items.
6. **Cape Town SRAs** (58 polygons, VERIFIED\*) remain the clean *patrol-only* PSC contrast.
7. **Architecture 1 (Gauteng) stays first, conditional on the pilot.** Read the headline construct as *state-sanctioned enclosure with mandated private guarding*. If the pilot fails the threshold, a combined "Gauteng estates (E2) + Cape Town SRA (E3)" design becomes the fallback (Section 9).

---

## 1. Source-by-source assessment

### 1A. Treatment sources

#### T1. OpenStreetMap (current snapshot). Grade **B** for location, not for timing
- **Provider / URL:** OSM; Overpass; Geofabrik extract https://download.geofabrik.de/africa/south-africa.html ; taginfo https://taginfo.geofabrik.de/africa:south-africa/
- **Access:** public, ODbL.
- **Counts (VERIFIED\*, taginfo 2026-09-28, Overpass 2026-09-29):**

| Tag / feature | National | Johannesburg | Tshwane | Ekurhuleni | Cape Town | eThekwini |
|---|---|---|---|---|---|---|
| `landuse=residential` | 23,801 | 852 (2 of them `access=private`) | | | 3,303 | |
| `residential=gated` | 276 | 23 | | | | |
| `gated=*` | 0 | | | | | |
| `barrier=gate` | 55,342 | 8,257 | 5,383 | | 8,582 | |
| `barrier=lift_gate` | 3,548 | 810 | 686 | | 608 | 177 |
| `access=private` | 156,341 | | | | | |
| `highway=residential` + `access=private` (road segments) | 47,656 | 11,664 | 12,254 | 4,120 | 6,009 | 1,486 |

- **Interpretation.** These are **road segments (OSM ways) and nodes, not enclaves.** One estate can contain dozens of ways. The number of enclaves and the recall of estates are unknown until connected components are built and validated against an independent list (Lightstone, a GCRO layer, the scrape's name gazetteer, or an imagery sample). Differences between metros (e.g. eThekwini's 1,486) may reflect mapping effort rather than prevalence. Tagging does not cleanly separate private estates from boomed public roads.

#### T2. OSM full history (ohsome). Grade **C** for timing
- ohsome returned HTTP 403 to this tool; SA history counts are UNVERIFIED.
- First-mapped date ≠ construction date. Usable only if triangulated with imagery (T10).

#### T3. Gauteng SAR notices (Provincial Gazette) and the JHB SAR Policy. Grade **B** (conditional on the pilot)
- **Legal basis:** Gauteng Rationalisation of Local Government Affairs Act 10 of 1998, Ch. 7 (ss.43–48). Applications possible since 5 March 1999 (VERIFIED, SAHRC report p.8).
- **JHB SAR Policy 2018** (VERIFIED, read to p.19; footer suggests a 2012 base text):
  - **s.4.3:** a 1:20,000 locality plan showing the boundary of the restricted area and all properties served. An **enclosure polygon exists in each application file.**
  - **s.4.4:** the motivation must cover "the seriousness and prevalence of crimes in the area" and "crime related statistics" for **the six months preceding** the application. **Timing is crime-driven by design.**
  - **s.4.7:** the applicant estimates the residents affected. This is a ready-made intensity numerator.
  - **s.4.8:** at least **67%** of affected persons must support.
  - **s.4.10.1, s.6.5, s.7.1.2 and s.7.1.8:** name and PSIRA registration of the guarding provider; at least one access point manned 24 hours; manned points only by registered providers.
  - **s.5.3:** a meeting with SAPS is mandatory. **s.9.1.4:** SAPS or JMPD can trigger withdrawal if the SAR is "proving ineffective in enhancing safety and security".
  - **s.3.2.4 and s.8.1:** 2-year validity; extension up to 6 years.
  - **s.10–12:** a timely "subsequent application" with a simplified traffic study and a fee of about 30% of the initial fee. A lapsed authority cannot be extended.
  - **s.5.5 and s.5.5.6.2:** web posting of drafts; final determination gazetted.
- **Scale:** "in excess of 400" SARs administered by CoJ (VERIFIED, 2021). Press: about 350 (SECONDARY). Many historic closures were "never formally approved" (SNIPPET).
- **Coverage:** notices for JHB, Tshwane and Ekurhuleni exist (VERIFIED for JHB via gazette contents and City PDFs; SNIPPET for Tshwane and Ekurhuleni notice titles). Whether the Tshwane and Ekurhuleni policies require crime evidence is UNVERIFIED (the Tshwane 2025 policy report hit a TLS error; the Ekurhuleni policy PDF was not read).
- **Limit:** notice titles often do **not** state first vs subsequent application. First-time status needs the **first appearance** of a closure in the full series, or JRA/municipal files.

#### T4. Municipal registers held directly. Grade **C** (eThekwini **D**)
- The JHB policy requires web posting of interim/final approvals (s.5.5.1.1). A CoJ "Interim Approvals" page is indexed (SNIPPET) but returned 404.
- Consolidated JRA, Tshwane and Ekurhuleni registers: UNVERIFIED. Route: request, or PAIA.
- eThekwini: no regime (2018 council vote; SECONDARY).
- Cape Town: gated developments use private roads approved through land use; booms on public roads need approval (SECONDARY). A register is UNVERIFIED.

#### T5. Academic and institutional inventories
- **GCRO gated-communities layer:** grade C; provenance undocumented; request from GCRO.
- **GTI Building-Based Land Use:** grade D; proprietary (the 249% figure is a SNIPPET).
- **Landman/CSIR (2000, 2003):** grade D; literature only.
- **Breetzke et al. (88 Tshwane gated communities):** grade C; author request.
- **Spocter (non-metro Western Cape):** grade C/D.

#### T6. Property-market sources
- **Lightstone estates:** grade C; licensed. About 5,000 estates and 430–460k properties, with vintage bands (VERIFIED\*). "Nearly 8,000" is a SNIPPET.
- **Deeds sectional-scheme register:** grade C.
- **CSOS:** grade D.
- **Estate gazetteers** (Property24 estate location IDs such as `/meadows-security-estate/pretoria/gauteng/17913` (VERIFIED\* search-result URL); gatedestates.co.za; Private Property developments): grade B, used as name lists.

#### T7. Cape Town Special Rating Areas. Grade **A** for boundaries, **B** for timing
- 58 polygons with fields `SRA_NAME` and shape area/length only (VERIFIED\*); SRA budgets XLSX by category, including security (VERIFIED\* listed).
- Start dates must be compiled from business plans (e.g. Observatory 2009, Glosderry 2013; VERIFIED\*).

#### T8. PSIRA. Grade **D** for spatial use
- National/provincial totals only (SECONDARY).
- **New:** SAR application files name the PSIRA-registered provider per closure (s.4.10.1, VERIFIED). PSC identity per enclosure is obtainable via JRA files, not PSIRA.

#### T9. Existing Property24 scrape (updated, critic #10). Grade **C** (covariate / gazetteer only)
- **Summary.** Being revised in parallel, so the figures below are qualitative. Sources: `quality_reports/scrape_audit_2026-09-29.md`; `quality_reports/code_review_scraper-fixes_r1_2026-09-29.md`.
- **Size and panel depth.**
  - About 17.5k unique listings (17,494 `p24_id`; 18,427 rows).
  - About 95% of listings are captured once, so in practice it is a cross-section.
- **Descriptions.**
  - About 30% of rows have no description.
  - Missingness is time-dependent: 65.5% missing in 2009–2012 vs 8.7% from 2013.
  - Titles carry no PSC signal.
- **Precision.** Coder-critic's by-eye coding of 25 flagged rows:
  - about **52% correct as a gated-enclave measure**;
  - about **88% correct as a residential PSC-presence measure**;
  - 3 of the 25 were commercial listings;
  - "24-hour security" dominates the flags;
  - some enclaves are missed ("security complex" phrases are not in the dictionary).
- **Geography.**
  - Gauteng = Johannesburg (about 1.2k rows) and Pretoria (about 4.2k); **no Ekurhuleni**.
  - The "Durban" city label is unreliable: about 55% of "Durban" rows are Durbanville/D'Urbanvale in the Western Cape. The province field is correct.
  - Coverage is 80 suburbs, including city-wide buckets.
  - Bulk of rows from 2013–2016.
- **Role.**
  - A pre-period suburb-level **PSC-presence** covariate.
  - An estate-name gazetteer for validating OSM enclaves.
  - Not a treatment.

#### T10. Remote sensing
- Google Open Buildings 2.5D Temporal (2016–2023, about 4 m, VERIFIED\*): grade B as a construction-timing aid for estates.
- Wall/gate detection: grade D.

#### T11. Cadastral parcels
- Grade B (Cape Town, VERIFIED\* exists) / C (Gauteng).

### 1B. Outcome sources

#### O1. Afrobarometer SA, public files. Grade **A** for measures, **D** for spatial designs
- **Rounds and n:** R1 2000 (2,200), R2 2002 (2,400), R3 2006 (2,400), R4 2008 (2,400), R5 2011 (about 2,400, UNVERIFIED), R6 2015 (2,400), R7 2018 (about 1,800, UNVERIFIED), R8 2021 (1,600), R10 2025 (1,600). All SNIPPET except R9 2022 (**1,582, VERIFIED**).
- **R9 design (VERIFIED):** 8 interviews per PSU (about 200 EAs); response rate 61.4%.
- **Items:** see Section 6.

#### O2. AidData geocodes, R1–R6. Grade **B**
- Place-name gazetteer matching, not GPS; precision 1 = most granular (VERIFIED).
- One application may cover **all rounds for one country**. A draft paper is required before further releases (VERIFIED).
- SA precision distribution UNVERIFIED. Distance bands under about 5 km are not identifiable.

#### O3. AB R7–R10 lower-level geography. Grade **C**
- GPS recording in R8+ manuals: SNIPPET. Release: UNVERIFIED.

#### O4. GCRO Quality of Life Survey. Grade **A** (ward-level, public)

**Waves** (sample sizes SNIPPET except QoL7; ward-representativeness and mode **UNVERIFIED per wave** unless stated; ward counts: 529 for QoL7 (VERIFIED\*), about 508 earlier (UNVERIFIED))

| Wave | Field | n | n per ward (ESTIMATE) | Ward-level use |
|---|---|---|---|---|
| I | 2009 | 6,636 | ~13 | **No** (municipal/region only) |
| II | 2011 | 16,729 | ~33 | Marginal |
| III | 2013/14 | 27,490 | ~54 | Yes |
| IV | 2015/16 | 30,002 | ~59 | Yes |
| V | 2017/18 | 24,889 | ~49 | Yes |
| 6 | 2020/21 | 13,616 | ~26 | Yes (new-weights file, VERIFIED\*) |
| 7 | 2023/24 | 13,795 (VERIFIED\*) | ~26 | Yes (≥20 per ward target in 529 wards, VERIFIED\*) |

- **Access:** DataFirst, CC-BY. Restricted QoL6/QoL7 adds only Section 15 sensitive items, including experiences of violence (VERIFIED\*). The lowest geography is the ward (VERIFIED\*). GPS/SAL on request from GCRO: UNVERIFIED.
- **Non-response:**
  - Gated communities have the highest access refusal; one QoL II Midvaal ward was inaccessible (VERIFIED\*).
  - A QoL7 feasibility study analysed survey-yield and access metadata (SNIPPET).
  - **Refusal/substitution counts by ward are not published (UNVERIFIED); request them.** See Section 5.2.

#### O5. HSRC SASAS. Grade **C** (≈3,500 per year; coarse public geography, UNVERIFIED)

#### O6. Stats SA VOCS → GPSJS. Grade **C**
- About 33k dwelling units; province geography (VERIFIED\*).
- `Q324PrivSecur`, `Q353PrivtSecrty` (VERIFIED\*).

#### O7. ACLED. Grade **B**
- Centroid coordinates; geo-precision 1–3 (VERIFIED, codebook).
- Private security firms = Inter 8; vigilante mobs = Rioters (Inter 5) (VERIFIED).
- SA totals UNVERIFIED; composition SNIPPET.

#### O8. SAPS station panel and boundaries. Grade **A** (panel), with unit-stability caveats (Section 7)
- DataFirst cat. 1012, 2005/06–2025/26; stations 1,141 → 1,151 → 1,172 → 1,174 (VERIFIED\*).
- Monthly data 2020–2025 via afrith/crime-stats (VERIFIED\*).
- Boundaries: current only, 2026-01-22 (VERIFIED\*).
- Incident points: grade D (UNVERIFIED route).

#### O9. Census
- 2011 SAL on request (VERIFIED\*): grade B.
- 2022 ward estimates with instability caveats (VERIFIED\*): grade B/C.

---

## 2. Treatment definition and exposure intensity (critic #3)

**Three arms, kept separate throughout:**

| Arm | Physical form | Legal status | PSC component | Mechanism of exposure |
|---|---|---|---|---|
| **E1 SAR enclosure** (JHB, Tshwane, Ekurhuleni) | Booms/gates across *public* roads | Municipal authorisation, time-limited, gazetted | **Mandated**: ≥1 point manned 24 hours by a PSIRA-registered provider (JHB s.7.1.2/7.1.8) | Acts on **incumbent** residents |
| **E2 Private estate** | Walled development with private internal roads | Township establishment / HOA | Usually guarded (UNVERIFIED; not mandated) | Mostly **new construction**, so exposure arises through **sorting** plus neighbour effects |
| **E3 Patrol-only PSC** (Cape Town SRA) | No barrier | Special rating area | Levy-funded patrols (budget share observable) | Acts on incumbents |

**Sectional-title rule (proposed default; the strategist or user may override):**
- A development is **E2** if its OSM private-road component has ≥1 gate/lift-gate node, ≥200 m of internal private road, and ≥10 dwellings inside (Open Buildings footprints) or ≥1 ha.
- Stand-alone sectional-title complexes (single-gate townhouse/cluster blocks without an internal road network) and secured apartment blocks are **E2c "complex"**. They are **not treated** in the main specification, enter as a control (the share of ward dwellings in complexes), and are included in a robustness specification.
- Rationale: complexes are near-ubiquitous in middle-class Gauteng and would make treatment almost universal in suburbs.

**Intensity measure (ward $w$, wave/year $t$; same form for precincts):**

$$E^{k}_{wt} = \frac{\sum_{s \in w} \text{dwellings}_{s}\,\mathbb{1}[s \text{ inside an arm-}k\text{ perimeter at } t]}{\sum_{s \in w}\text{dwellings}_{s}}, \quad k\in\{\text{SAR},\text{estate}\}$$

- $s$ = Census 2011 SALs; dwellings from the Census 2011 SAL counts.
- Where a SAL straddles a perimeter, allocate by the share of Open Buildings footprints inside the polygon (building-weighted, not area-weighted).
- For estates built after 2011, count footprints directly.
- **Near-exposure ring:** $R^{k}_{wt}$ = the share of ward dwellings 0–500 m *outside* a perimeter. It captures spillover and supports the displacement tests.
- **SAR perimeter:** gazetted road names and access points, snapped to OSM and closed along property lines; or the s.4.3 locality plan if the files are obtained. **Affected-persons count (s.4.7)** is a cross-check.
- **Binary versions** for event studies: $E^{k}_{wt}\ge0.10$ (proposed). Report the full distribution; "≥1 SAR in ward" is dropped.

---

## 3. SAR gazette desk check (critic #1): ESTIMATE

**Method.**
- Time-boxed to 6 issues. I sampled **6 ordinary Wednesday issues** of the Gauteng Provincial Gazette from Gazettes.Africa. On Wednesdays I took the lowest-numbered issue; I confirmed it was the ordinary issue by page count, since extraordinary issues are 1–8 pp.
- I read the full Contents and counted notices under Act 10 of 1998 Ch. 7 / "security access restriction" / "restriction of access … safety and security".
- **Not sampled:** extraordinary issues (SAR notices may appear there), and issues this tool could not open (2016 ordinary issues exceed its 10 MB fetch limit; the 2010 ordinary issue could not be identified among small scanned issues; one 2021 read hung once and was retried).

| Issue | SAR notices | Detail (VERIFIED from contents pages) |
|---|---|---|
| 16 May 2007, No. 131 (143 pp) | **0** | Archived PDF appears to start at page 2 |
| 22 May 2013, No. 136 (144 pp) | **0** | — |
| 22 May 2019, No. 154 (180 pp) | **0** | — |
| 20 Oct 2021, No. 355 (255 pp) | **1** | GN 1215 "Rationalization of Government Affairs Act, 1998: Bryanston River Club Community Forum" (JHB; type not stated) |
| 12 Jun 2024, No. 206 (108 pp) | **2** | PN 508 "Notice of Final Approval of a Security Access Restriction" (municipality not stated); PN 509 "…Act, 1998: President Park AH" (type not stated) |
| 19 Jun 2024, No. 211 | **4** | JHB: **final** Fourways RA No. 84; **intent** Urania Village No. 250; **final** Ryan Road Closure No. 42; **final** Chesham RA Ref 75 |

**Off-sample existence evidence** (not used for rates):
- GreenGazette notice titles dated 2013-06-12, 2014-11-12, 2015-07-08 (Ekurhuleni, Bedfordview) and 2017-10-11 (Ekurhuleni, Edenglen) (SNIPPET).
- Tshwane notices for Queenswood and Waterkloof Glen Ext 6, about Nov 2024 (SNIPPET).
- JHB City PDFs: Ref 11 (final, advertised Mar 2020), Ref 90, Ref 207, Ref 438 (interim, 2021; VERIFIED for Ref 438).
- JHB intent for Linksfield Ridge (2025-02-05, SNIPPET).

**Estimates (rough; wide uncertainty):**
- **2021–2024:** 7 notices in 3 ordinary issues, about 2.3 per issue. With about 50 ordinary issues a year, that is about **100–120 SAR notices a year across Gauteng** (ESTIMATE; the true rate could plausibly be half or double).
  - Each closure produces ≥2 notices, and JHB renewals recur every 2–6 years.
  - So roughly **40–60 closure decisions a year**. Given CoJ's stock of 400+ and low reference numbers finalised in 2024, **most are plausibly re-authorisations, not new enclosures** (inference, UNVERIFIED).
- **2007–2019:** 0 in 3 sampled issues. Off-sample notices show 2013–2017 activity, so the rate was **low but non-zero** (ESTIMATE: under 1 per ordinary issue).
- **Split of first-time approvals vs renewals, per metro, 2009–2024: UNKNOWN.** Titles rarely state the type.
- **Implication:** JHB physical enclosure dates may lie mostly in **1999–2012**, before the ward-reliable QoL window (2013/14+). This is the largest single threat to the SAR DiD.

**Archive completeness and search** (critic #7):
- Gazettes.Africa lists 1994–2026 (VERIFIED\*), but some months are thin: May 2007 lists 4 issues (the 23 May Wednesday is missing) against 23 in October 2007.
- Pre-2012 PDFs include JBIG2 scans that need OCR. Ordinary issues run 100–255 pages.
- **No working full-text search was confirmed:**
  - Gazettes.Africa search not reachable by this tool;
  - SAFLII search returned 403;
  - GreenGazette unresolvable from this tool, though its notice titles are search-indexed;
  - Sabinet full text is paywalled; university-library access is UNVERIFIED.

**Pilot to settle the first-approval count:**
- Johannesburg only. Read the contents of **every** ordinary and extraordinary issue for **2011, 2014, 2017 and 2021**.
- In parallel, request the JRA/CoJ SAR register with original approval dates and reference numbers.
- Classify each closure as first-seen vs previously seen (by reference number and street names), and cross-check against the register.

---

## 4. Joint feasibility (revised)

The "within 1/2/5 km" counts are unchanged ESTIMATES from round 1: metro shares × Lightstone totals × assumed proximity shares. Replace them with GIS overlays. **Time overlap is now rated conditionally.**

| # | Treatment × Outcome | Unit | Near-treatment respondents/events (ESTIMATE) | Time overlap for DiD (revised) | Designs |
|---|---|---|---|---|---|
| 1 | OSM enclaves × AB AidData R1–R6 | Place centroid / municipality | ~840 metro resp. per round; only the 5 km band meaningful; ~50 inside estates nationally per round | **None** (no treatment timing) | Area-level cross-section |
| 2 | E1/E2 × AB R7–R10 with GPS (if released) | EA point | ~560 metro resp. per round; ~5–15 EAs within 500 m | Weak | Distance-gradient cross-section; RD underpowered |
| 3 | AB EA-SEC-E × AB attitudes | EA | R9: ~110 resp. (~14 EAs); item double-barrelled | None | Individual-level association |
| 4 | **SAR (E1) × QoL ward** | Ward (2021, crosswalked) | Wards with $E^{SAR}\ge0.10$: UNKNOWN until the pilot; round-1 "15–30% of metro wards contain any SAR" kept as an upper bound | **CONDITIONAL**: needs first-time enclosures in 2014–2022 (between QoL III and 7); otherwise treatment predates the pre-period | Staggered ward event study **if GO**; otherwise intensity cross-section |
| 5 | Estates (E2) × QoL ward | Ward | Wards intersecting an enclave: 40–60% (unvalidated) | **CONDITIONAL**: Open Buildings timing (2016–2023) gives a QoL V → 6 → 7 contrast for new estates only | Intensity cross-section; limited DiD (sorting caveat) |
| 6 | E1/E2 × QoL with GPS (if GCRO releases) | Respondent | ~3,500–6,000 within 1 km per wave; ~200–500 inside estates after refusal | Conditional as in rows 4/5 | Spatial RD, DiD, individual level |
| 7 | **SAR (E1) × SAPS precinct** | Stable precinct cluster | Treated precincts: UNKNOWN until the pilot (round-1 "40–70 with any SAR" is an upper bound) | **CONDITIONAL**: first-time SARs from about 2008 give ≥3 pre-years; earlier ones give none | Staggered precinct event study **if GO** |
| 8 | Estates (E2) × SAPS | Precinct cluster | Intensity | Conditional (2016–2023 timing) | Cross-section; limited DiD |
| 9 | SRA (E3) × SAPS (Cape Town) | Precinct cluster | 58 SRAs (~20–30 residential, ESTIMATE) | **CONDITIONAL** on compiled start dates ≥2006 | Precinct event study |
| 10 | E1/E2/E3 × ACLED | ACLED centroid | SA totals UNVERIFIED | Weak | Actor-type descriptives |
| 11 | Scrape × QoL/SAPS | Suburb → ward/precinct | 80 suburbs; JHB/Pretoria only in Gauteng | None | PSC-presence covariate |
| 12 | Self-reports (QoL dwelling type; VOCS private security) | Individual (ward / province) | All respondents | QoL repeated cross-section | Association; mechanism evidence |

---

## 5. Identification notes per architecture, and go/no-go (critics #1–#2)

### 5.1 Architecture 1 (Gauteng: SAR + estates × QoL + SAPS)

1. **Crime-driven timing and reverse causality.**
   - JHB requires six months of pre-application crime evidence (s.4.4) and a SAPS meeting (s.5.3). Approvals therefore follow local crime spikes by construction. Expect an Ashenfelter-type dip and mean reversion in SAPS counts and QoL safety perceptions.
   - **Needed:**
     - an event study with **≥2 pre-periods** (≥2 pre-waves for QoL, ≥3 pre-years for SAPS);
     - not-yet-treated applicants as controls, where file dates allow;
     - exploiting the administrative lag between application and gazetting (the SAPS meeting alone is scheduled within 90 business days, s.5.3.1);
     - placebo outcome categories.
   - Attitudes may also drive adoption: the 67% consent rule (s.4.8) selects cohesive, state-sceptical neighbourhoods.
2. **First approvals vs renewals.**
   - Onset = **first physical enclosure**, not the latest gazette date. Renewals are continuations; lapses and withdrawals (s.9–10) are reversals.
   - Code the history per closure: first-seen / renewal / lapse / removal. Estimators must allow treatment to switch off.
3. **Spillover and displacement.**
   - Policy s.6.1.3(b) itself anticipates displacement of traffic to neighbouring areas. Crime displacement to adjacent wards and precincts breaks SUTVA and contaminates controls.
   - Use the $R^{k}_{wt}$ rings; exclude or model adjacent units; test displacement as an outcome.
4. **Bundled treatment.** E1 = enclosure + mandated guards (s.7.1.2/7.1.8) + often CPF membership (s.7.4.1). "Walls" and "PSC" cannot be separated within E1. The E3 (Cape Town) contrast is the only partial separation.
5. **Go/no-go threshold** (proposed heuristic; the strategist should replace it with an MDE calculation):
   - **GO for the SAR DiD** if the pilot plus scale-up yields **≥40 first-time physical enclosures across the three metros, dated 2014–2022, in ≥25 distinct 2021-delimited wards, each with $E^{SAR}_w\ge0.10$**, with ≥10 in each of ≥2 metros.
   - **SAPS arm:** ≥20 precinct clusters with a first enclosure dated 2008–2022.
   - **NO-GO:** SAR becomes a cross-sectional intensity measure and descriptive evidence; the DiD burden shifts to E2 and E3 (Section 9).
   - Rationale: at about 25–55 QoL respondents per ward per wave, 25 treated wards give roughly 1,000–2,000 treated post-treatment respondent-waves. That is a floor for moderate effects with ward clustering.

### 5.2 Post-treatment sample selection (critic #2)
- **Survey access is a treatment outcome.**
  - Guards may not demand ID or registers (s.7.1.7), but the SAHRC documented widespread non-compliance (VERIFIED).
  - If treated SALs yield fewer interviews, within-ward replacement shifts the post-treatment sample toward untreated parts. Ward ITT is then attenuated, or biased if composition shifts.
  - QoL's within-ward substitution/quota procedure is UNVERIFIED.
- **Diagnostics:**
  - (i) test whether treatment changes ward-wave n or the composition of predetermined traits (race, age, tenure, dwelling type, years at address);
  - (ii) request GCRO refusal/substitution metadata by ward and wave (existence UNVERIFIED);
  - (iii) reweight to Census SAL composition;
  - (iv) bound differential non-response (e.g. trimming bounds).
- **Sorting vs incumbent exposure.**
  - E1 acts mainly on incumbents, with possible later price-driven sorting.
  - E2 changes composition through new residents.
  - Keep the arms separate. For E2, estimate effects on incumbents by restricting to respondents resident before construction, using QoL migration items (QoL7 `q3_8_prev_dwelling_type` VERIFIED\*; years at address UNVERIFIED by wave).

### 5.3 Architecture 2 (national AB)
- EAs resampled each round, so there is no unit panel.
- Exposure is confounded with income, race and urbanity. Associational only.
- EA-SEC-E is double-barrelled (Section 8).

### 5.4 Architecture 3 (Cape Town SRA)
- SRA formation needs a property-owner majority (threshold UNVERIFIED) and is typically "crime and grime"-motivated. The same pre-trend requirements apply.
- Commercial SRAs are a different treatment. Displacement to adjacent precincts is likely.

---

## 6. Outcome construct mapping: QoL item × wave matrix (critic #4)

**Coverage and legend.**
- **Source:** DataFirst variable-label searches (VERIFIED\*).
- **✓** = found.
- **?** = not checked, or the label index returned "no records" (QoL I, II, V and 6 often returned nothing), so **absence is not established**; pull the questionnaires.
- **—** = searched and not found.

| Dimension | Item | I 2009 | II 2011 | III 2013/14 | IV 2015/16 | V 2017/18 | 6 2020/21 | 7 2023/24 |
|---|---|---|---|---|---|---|---|---|
| **Performance legitimacy** | Satisfaction with government safety & security where you live | ? | ? | ✓ `X9_12` | ✓ `Q9_6` | ? | ? | ✓ `q11_6_gov_security` |
| | Satisfaction with metro/traffic police | ? | ? | ? | ✓ `Q1_31` | ? | ? | ? |
| | Satisfaction with national / provincial government | ? | ? | ? | ✓ `Q6_6`, `Q6_7` | ? | ? | ? |
| **Procedural legitimacy** | Judiciary free from government influence | ? | ? | ? | ✓ `Q6_35` | ? | ? | ? |
| | Government officials doing their best | ? | ? | ? | ✓ `Q6_23` | ? | ? | ? |
| **Trust in state** | Trust current government leaders | ? | ? | ? | ? | ? | ? | ✓ `q7_11_gov_trust` |
| **Normative legitimacy** | — | ? | ? | — | — | ? | ? | — |
| **Reliance / co-production** | Attended community policing forum meeting | ? | ? | ✓ `X6_4_7` | ✓ `Q6_4_7` | ? | ? | ? |
| | Uses private security / lives in estate | ? | ? | ? | ? | ? | ? | — |
| **Safety perceptions** | Safe at home / by day / after dark | ? | ✓ `A_9_4–6` | ? | ? | ? | ? | ✓ `q11_3–5` |
| **Victimisation / crime trend** | Victim past 12 months; crime better/worse | ? | ? | ? | ✓ `Q9_2`, `Q9_1` | ? | ? | ✓ `q11_2`, `q11_1` |
| **Collective action** | Protest in neighbourhood / about crime; participated | ? | ? | ? | ✓ `Q10_3_8` | ? | ? | ✓ `q12_4`, `q12_5` |
| **Social trust** (control) | Can people in your community be trusted | ? | ? | ✓ `X6_40` | ? | ? | ? | ? |

**What only other sources supply:**
- **Normative legitimacy** comes only from **Afrobarometer**: "police always have the right to make people obey the law", "tax authorities always have the right to make people pay taxes", and a courts item. The items exist in AB publications (VERIFIED\*); **which SA rounds carry them is UNVERIFIED** (check the R3–R10 codebooks).
- **Procedural legitimacy of police:** AB R9 SA Q44A–E and Q33E (VERIFIED).
- **Trust battery:** AB R9 SA Q37A–K (police Q37G, courts Q37I) (VERIFIED).
- **Reliance on private security:** VOCS `Q324PrivSecur`, `Q353PrivtSecrty` (province only, VERIFIED\*). AB EA-SEC-E is *observed* booms, not respondent reliance.

**Pre-period implication:**
- Best verified coverage: satisfaction with government safety services (III, IV, 7), safety perceptions (II, 7), victimisation (IV, 7).
- **Trust in government is verified only in QoL7.** It cannot anchor a ward DiD until earlier waves are confirmed.

---

## 7. Unit stability and wave comparability (critic #5)

- **SAPS precinct splits.**
  - Stations rise 1,141 → 1,174; only current boundaries exist (VERIFIED\*).
  - **Handling:**
    - (i) find each new station's parent(s) by overlaying current polygons in its first year;
    - (ii) merge parents and children into **time-invariant precinct clusters** for 2005–2026;
    - (iii) robustness on never-split precincts.
  - Undocumented boundary shifts without a new station remain a residual threat.
- **Ward crosswalks.**
  - Municipal Demarcation Board (MDB) delimitations for the 2011, 2016 and 2021 elections; the delimitation used by each QoL wave is UNVERIFIED.
  - MDB ward shapefiles are available (MDB; openAFRICA "Demarcation Board – Gauteng GIS Data", SNIPPET).
  - Population-weight using Census 2011 SALs (nested in 2011 wards) plus Open Buildings for later growth. Analyse on **2021 wards** and report the share reallocated.
- **QoL comparability.**
  - Changes of mode, of design (ward representativeness from III), of weights (QoL6 "new weights" file, VERIFIED\*), of fieldwork conditions (QoL6 during COVID) and of wording are UNVERIFIED per wave.
  - Wave fixed effects absorb level shifts. Check outcome wording item by item before pooling.

---

## 8. Measurement error in outcomes (critic #8)

- **SAPS recorded crime.** Records are reported plus police-detected crime.
  - Treatment can change *reporting*:
    - guards call police, and insurance claims need case numbers (reporting up);
    - private resolution replaces police (reporting down);
    - legitimacy, the attitudinal outcome, itself shifts willingness to report.
  - So a change in recorded crime conflates victimisation and reporting.
  - **Mitigation:**
    - anchor on **murder** (least reporting-sensitive) and carjacking/aggravated robbery;
    - treat police-detected categories (drugs, illegal firearms) as *policing-intensity* outcomes, not crime;
    - use VOCS/GPSJS provincial reporting rates as context.
- **ACLED.** Media-sourced, with English-press and urban coverage bias.
  - Coverage per event plausibly differs between affluent suburbs and townships.
  - Inter 8 (private security) events are likely sparse (count UNVERIFIED).
  - Vigilante mobs are pooled with rioters, and locations are centroids.
  - Use for actor-type descriptives only.
- **AB EA-SEC-E.** Double-barrelled: "booms set up by private security providers **or** by the local community". In townships this likely captures community/street-committee roadblocks; in suburbs, PSC booms. It is a single enumerator observation per EA. PSC booms cannot be separated; interpret only jointly with EA urbanity and income.
- **QoL self-reports.** Safety perceptions are affected by the treatment salience itself (booms signal danger). Report perception and victimisation outcomes separately.

---

## 9. Ranked architectures and external validity (critic #11)

1. **Architecture 1: Gauteng enclosure panel (conditional GO).**
   - E1 SAR (gazette + JRA/municipal files) and E2 estates (OSM + Open Buildings) × QoL III–7 (ward) + SAPS precinct clusters + ACLED actor types.
   - *External validity:*
     - The instrument (Act 10 of 1998 Ch. 7) is Gauteng-specific. It generalises to **state-sanctioned privatisation of public streets**: Brazilian *loteamentos fechados* (closed public-street subdivisions) vs *condomínios fechados* (private estates), which mirror E1 vs E2; gated "colonies" run by Delhi resident-welfare associations; barriers in Nairobi estates.
     - The Act dates from 1999 but ward-reliable data start in 2013/14. Estimates therefore describe **later-cohort** enclosures (and continued authorisation), not the first 1999–2004 wave, which may have been more crime-driven.
     - SAR areas are mostly middle- and upper-income former suburbs, not townships.
2. **Architecture 3: Cape Town SRA module (complement).**
   - E3 patrol-only PSC × SAPS precinct clusters, with E2 estates as the gating contrast.
   - *External validity:* the closest analogue is business/residential improvement districts (US, UK, other SA cities). Cape Town's governance context (a single metro, DA-run since 2006) limits transfer.
3. **Architecture 2: national Afrobarometer extension.**
   - OSM intensity + EA-SEC-E × AB attitudes (AidData geocodes; one application for all SA rounds).
   - *External validity:* best for cross-country comparison (same instrument in Kenya, Nigeria and others), but associational and spatially coarse.
- **Fallback if the pilot is NO-GO:** "E2 + E3". Gauteng estates with Open Buildings timing (QoL V–7, SAPS 2016–2025) plus the Cape Town SRA event study. SAR is reported cross-sectionally.

---

## 10. Ranked source table (critic #10) and dispositions (critic #9)

| Rank | Source | Role | Grade | Why this rank |
|---|---|---|---|---|
| 1 | GCRO QoL (III–7) | Attitudes outcome (Gauteng) | A | Large n, ward-level, public; performance-legitimacy and safety items |
| 2 | SAPS station panel + boundaries | Violence outcome | A | 2005–2026 panel, public; needs precinct clusters |
| 3 | SAR gazette + JRA/municipal files | E1 treatment and timing | B (conditional) | Dated administrative record with mandated PSC; first-approval count unknown |
| 4 | OSM private roads/gates | E2 location | B | Public, fine-grained; enclaves must be constructed and validated |
| 5 | Cape Town SRA polygons + budgets | E3 treatment | A/B | Exact boundaries, security spend; timing to compile |
| 6 | Census 2011 SAL | Intensity denominators, controls | B | On request |
| 7 | Open Buildings Temporal | E2 timing (2016–2023) | B | Public; left-censored |
| 8 | Afrobarometer public + AidData geocodes | Normative legitimacy; national extension | A / B | Unique items; coarse geography |
| 9 | ACLED | Actor types | B | Centroids; media-driven |
| 10 | GCRO gated layer / Lightstone | Validation of E2 | C | Request / licence |
| 11 | Property24 scrape | PSC-presence covariate; name gazetteer | C | ~52% enclave precision; no Ekurhuleni |
| 12 | VOCS/GPSJS, SASAS | Mechanism context | C | Province-level |
| 13 | AB R7–R10 GPS, QoL GPS, SAPS incident points | RD upgrade path | C/D | Restricted or unverified |
| 14 | PSIRA, Landman/CSIR, GTI, CSOS, eThekwini register, imagery wall detection | — | D | Rejected for this design |

**Dispositions for remaining named sources:**
- **SACN urban node / State of Cities data:** municipal-level context only (about 8–9 cities). No within-city variation. **Reject for design; optional descriptive covariate.** Contents UNVERIFIED.
- **Stats SA General Household Survey (GHS):** annual national household survey. Public geography is province, possibly with a metro flag (UNVERIFIED); security items UNVERIFIED. **Context and validation of dwelling-type shares only.**
- **Census 2011 (and 2022) dwelling type as exposure proxy:** SAL-level share of dwellings in townhouse/cluster complexes (category wording UNVERIFIED). Builds **E2c** (complex share) and validates the sectional-title rule. **Covariate and robustness, not treatment.**
- **QoL `a3_dwelling_type`:** individual self-reported complex/estate proxy (categories UNVERIFIED). **Individual-level robustness and heterogeneity only**, since it is selection-prone.
- **SAHRIS** (listed in the domain profile): heritage layer, unrelated to enclosure. **Reject.**

---

## 11. Access instructions and timeline (revised; critic #7)

| Source | Route | Est. time to data (ESTIMATE) |
|---|---|---|
| OSM snapshot | Geofabrik / Overpass | Same day |
| OSM history | ohsome API or history planet | Days |
| **SAR pilot (JHB, 4 years)** | Gazettes.Africa PDFs, read contents; OCR pre-2012 scans | **3–8 working days**, depending on OCR need and archive gaps |
| **SAR full compile (3 metros, 1999–2024) + geocoding** | Same, plus street geocoding to OSM | **Conditional on the pilot:** 2–4 weeks if a searchable source works (e.g. Sabinet via a university library, UNVERIFIED); **6–12 weeks** with manual contents reading |
| JRA / Tshwane / Ekurhuleni SAR registers and files (incl. PSC provider, s.4.3 plans) | Email JRA Transport/Traffic Engineering (CoJ SAR contacts named in the 2021 notice); Tshwane Open Data request form; PAIA | 1–3 months; uncertain |
| GCRO requests: GPS/SAL IDs, refusal/substitution metadata, gated layer | Email GCRO with a proposal | Weeks to months; availability UNVERIFIED |
| GCRO QoL public / restricted | DataFirst | Same day / weeks |
| MDB ward shapefiles 2011/2016/2021 | MDB website / openAFRICA | Same day (URLs to confirm) |
| AB public; AB geocodes (all SA rounds) | Download; application to datarequests@afrobarometer.org | Same day; weeks to months |
| ACLED | Account with institutional email | Days |
| SAPS panel; boundaries | DataFirst cat. 1012, afrith/crime-stats; saps.gov.za | Same day |
| SAPS incident points | SAPS research request (route UNVERIFIED) | Months |
| Cape Town SRA polygons/budgets | City open data portal | Same day |
| Open Buildings Temporal | Earth Engine / GCS | Days |
| Census 2011 SAL | Stats SA request | Weeks |
| Lightstone | Licence negotiation | Months; cost UNVERIFIED |

---

## 12. Data dictionary: key variables for the top architecture (revised)

| Construct | Source | Variable(s) | Notes |
|---|---|---|---|
| E1 history | Gazette + JRA files | closure ID, ref no., metro, first-seen date, renewal dates, lapse/withdrawal date, notice type, road names, restriction type, relaxation hours | First-seen date = onset |
| E1 perimeter | Files (s.4.3) or constructed | polygon; access-control points | Snap to OSM |
| E1 PSC provider | Files (s.4.10.1) | provider name, PSIRA no. | Links E1 to PSC identity |
| E1 affected persons | Files (s.4.7) | estimated residents | Numerator cross-check |
| E2 enclave | OSM + Open Buildings | component ID, polygon, gate nodes, internal road length, footprint count, first-built year (2016–2023) | E2c complex flag |
| Intensity | Constructed | $E^{SAR}_{wt}$, $E^{estate}_{wt}$, rings $R^{k}_{wt}$, complex share | Census 2011 SAL dwellings |
| E3 SRA | Cape Town | SRA_NAME, polygon, start date, security budget share | Residential/commercial flag |
| Attitudes | QoL | see the Section 6 matrix | Harmonise wording |
| Normative legitimacy | AB | "police/tax/courts have the right" items (rounds UNVERIFIED) | National extension |
| Violence | SAPS | cluster × offence × year/month | Murder as anchor |
| Violence actors | ACLED | inter1/inter2 (5, 8), sub_event_type, geo_precision | Descriptive |
| Selection diagnostics | QoL / GCRO | ward-wave n, refusals, substitutions (request) | Section 5.2 |

---

## 13. What I could NOT verify (updated)

1. **The first-time vs renewal split of SAR approvals, per metro, 2009–2024** (central; needs the pilot). Whether Tshwane and Ekurhuleni require crime evidence. Tshwane validity periods. Consolidated municipal registers.
2. **A usable full-text search over Gauteng gazettes**, and archive completeness beyond the gaps observed.
3. OSM history for SA (ohsome 403); OSM enclave precision/recall.
4. **GCRO:** GPS/SAL access; refusal/substitution metadata by ward; the delimitation, mode and wording per wave; the provenance of the gated layer.
5. **QoL items in waves I, II, V and 6** (label index empty); trust in government before QoL7; the `a3_dwelling_type` categories; a years-at-address item.
6. **Afrobarometer:** which SA rounds carry normative-legitimacy items; SA precision codes; R5/R7 n; R7–R10 location release; EA-SEC-E in SA R8/R10.
7. **ACLED:** SA totals, Inter 8 frequency, sub-city location practice, post-2025 access terms.
8. **SAPS:** historical boundaries; incident-data route; precincts per metro.
9. **Lightstone** terms and estate counts (5,000 vs 8,000); Deeds/CSOS bulk access.
10. **VOCS/GPSJS** metro flags; **GHS** and **SACN** contents; Census dwelling-type category wording.
11. **SRA** formation voting thresholds and start dates.
12. **All Section 4 proximity counts** (ESTIMATE; replace with GIS overlays).

---

## 14. Decisions for the user (from explorer-critic; explorer's recommendation on each)

1. **Headline construct.**
   - *Options:* SAR enclosure (E1), private estates (E2), PSC patrol presence (E3).
   - *Recommendation:* make **E1, state-sanctioned enclosure with mandated private guarding**, the headline. The JHB policy makes guarding part of every SAR (s.7.1.2/7.1.8), so E1 *is* a PSC exposure, bundled with enclosure. Treat E2 as a secondary arm (sorting) and E3 as the patrol-only contrast. Reframe the project from "PSC exposure" to "enclosure and private guarding", because Gauteng offers no separate PSC-personnel measure.
2. **Area-level ITT now, or wait for restricted individual locations?**
   - *Recommendation:* proceed with **area-level ITT** (ward/precinct) as the main path. Immediately send the two low-cost requests (GCRO: GPS/SAL + refusal metadata + gated layer; JRA: SAR register/files). **Defer** the SAPS incident-data and AB geocode applications until the pilot result, since the AB condition of a draft paper before further releases favours applying later.
3. **Go/no-go on the gazette register.**
   - *Recommendation:* run the **JHB pilot** (2011, 2014, 2017, 2021 plus the JRA register request) and apply the Section 5.1 threshold: ≥40 first-time enclosures in 2014–2022, in ≥25 wards with intensity ≥10%, plus ≥20 SAPS precinct clusters for 2008–2022. On NO-GO, switch to the E2 + E3 fallback.
4. **Scope.**
   - *Recommendation:* **Gauteng core + Cape Town SRA module**. The national AB extension comes later, as an external-validity and normative-legitimacy supplement. Not Durban.
5. **Scrape.**
   - *Recommendation:* **freeze at covariate quality** once Workstream B fixes pass. No new listing scraping (Ekurhuleni/JHB expansion would not fix the lack of boundaries). An optional small scrape of Property24 *estate location names* is justified only if OSM enclave validation needs a gazetteer beyond Lightstone/GCRO.

---

## 15. Summary

**Top architecture (conditional):** Gauteng enclosure panel.
- **Treatment:** E1, gazetted security-access restrictions, which by policy require crime evidence, 67% consent and PSIRA-registered guards; plus E2, OSM-constructed estates dated with Open Buildings. Measured as dwelling-share intensity with 500 m rings.
- **Outcomes:** GCRO QoL III–7 at ward level (performance legitimacy, safety, victimisation; trust in QoL7) and SAPS precinct clusters (murder-anchored), with ACLED for actor types and Afrobarometer for normative legitimacy.
- **Adoption condition:** a JHB gazette/JRA pilot must show enough **first-time** enclosures in 2014–2022. The desk check (6 issues) finds SAR notices concentrated in 2021–2024, with low reference numbers suggesting re-authorisation of old closures.
- **Fallback:** Gauteng estates plus a Cape Town SRA event study.
- **Spatial RD** remains available only through restricted individual locations.

---

## Sources

- **OSM/Overpass/taginfo:** https://taginfo.geofabrik.de/africa:south-africa/ ; https://overpass-api.de/ ; ohsome: https://github.com/GIScience/ohsome-api
- **JHB SAR Policy 2018:** https://joburg.org.za/documents_/Documents/POLICIES/Security%20Access%20Restrictions%20Policy%202018.pdf
- **CoJ SAR notice (2021):** https://joburg.org.za/Documents/2021%20Notices/June/SAR%20Policy%202018%20-%20Section%2045(2)%20Interim%20and%20Final%20Approvals_Poster.pdf
- **JRA notices:**
  - Ref 438: https://joburg.org.za/documents_/Documents/POLICIES/Transport/Ref%20438%20-%20Hurlingham,%20Glenadrienne,%20Craighall%20Road%20Closure%20-%20Interim%20Approval.pdf
  - Ref 11: https://joburg.org.za/documents_/Documents/POLICIES/Security%20Access%20Restrictions/REF%2011%20La%20Gratitude%20Circle%20%20SAR%20GOV%20GAZ%20NOTICE%20(FINAL%20APPROVAL).pdf
  - Ref 207: https://joburg.org.za/documents_/Documents/POLICIES/Transport/Ref%20207%20-%20Kelvin%20Residents%20Association%20-%20Interim%20Approval.pdf
- **Sampled gazettes:**
  - https://archive.gazettes.africa/archive/za-gp/2007/za-gp-provincial-gazette-dated-2007-05-16-no-131.pdf
  - https://archive.gazettes.africa/archive/za-gp/2013/za-gp-provincial-gazette-dated-2013-05-22-no-136.pdf
  - https://archive.gazettes.africa/archive/za-gp/2019/za-gp-provincial-gazette-dated-2019-05-22-no-154.pdf
  - https://archive.gazettes.africa/archive/za-gp/2021/za-gp-provincial-gazette-dated-2021-10-20-no-355.pdf
  - https://archive.gazettes.africa/archive/za-gp/2024/za-gp-provincial-gazette-dated-2024-06-12-no-206.pdf
  - https://archive.gazettes.africa/archive/za-gp/2024/za-gp-provincial-gazette-dated-2024-06-19-no-211.pdf
- **Gazette indexes:**
  - Year listings, e.g. https://gazettes.africa/gazettes/za-gp/2012 ; https://opengazettes.org.za/gazettes/ZA-GT/ ; https://www.saflii.org/za/gaz/ZAGPPrGaz/
  - Sabinet: https://discover.sabinet.co.za/document/12462711 ; https://discover.sabinet.co.za/document/12462712
  - GreenGazette titles (SNIPPET): https://www.greengazette.co.za/notices/rationalisation-of-local-government-affairs-act-10-1998-ekurhuleni-metropolitan-municipality-restriction-of-access-for-security-and-safety-purposes-to-shannon-road-bedfordview_20150708-GAU-00294-01219.pdf
- **SAHRC boom-gate report:** https://www.sahrc.org.za/home/21/files/Reports/Boomgate%20Report%20Content.pdf
- **Ekurhuleni policy:** https://www.ekurhuleni.gov.za/wp-content/uploads/2023/07/0301C_RestrictionAccessPublicPlacesSafetySecurityPurposes.pdf
- **Tshwane:** https://www.tshwane.gov.za/wp-content/uploads/2025/08/Report-on-draft-policy-for-restriction-of-access-to-public-places-in-the-CoT.pdf
- **eThekwini:** https://www.citizen.co.za/north-glen-news/142064/city-not-open-boom-gates-public-areas/
- **Cape Town SRA:** https://odp-cctegis.opendata.arcgis.com/maps/cctegis::special-rating-areas-city-improvement-districts ; https://esapqa.capetown.gov.za/agsext/rest/services/Theme_Based/ODP_SPLIT_5/FeatureServer/4
- **GCRO:** https://gcro.ac.za/outputs/map-of-the-month/detail/socially-isolated-wards-and-gated-communities-in-the-gauteng-city-region/ ; https://www.gcro.ac.za/research/project/detail/quality-of-life-survey-ii-2011/ ; https://www.gcro.ac.za/outputs/dataportal/
- **QoL (DataFirst):**
  - Catalogues: https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/GCRO ; …/catalog/995 ; …/catalog/996 ; …/catalog/875
  - Variable searches: …/catalog/594/search?vk=trust ; …/catalog/594/search?vk=police ; …/catalog/595/search?vk=government ; …/catalog/595/search?vk=crime ; …/catalog/248/search?vk=safe ; …/catalog/995/search?vk=trust
- **Lightstone:** https://lightstone.co.za/newsletters/property/2023/Feb/A1Feb23 ; **GTI:** https://geoterraimage.com/over-28-million-buildings-mapped-and-classified-in-south-africa/
- **Breetzke et al.:** https://link.springer.com/article/10.1007/s10901-013-9362-5
- **PSIRA:** https://pmg.org.za/tabled-committee-report/5933/ ; https://pmg.org.za/tabled-committee-report/6196/
- **Open Buildings Temporal:** https://sites.research.google/gr/open-buildings/temporal/
- **Afrobarometer:**
  - https://docs.aiddata.org/ad4/pdfs/geocodingafrobarometer.pdf
  - https://www.afrobarometer.org/wp-content/uploads/2022/03/afrobarometer_application_for_restricted_data_w_geocodes_feb2020-1.pdf
  - https://www.afrobarometer.org/wp-content/uploads/2024/03/Summary-of-results-South-Africa-Afrobarometer-Round-9-7mar24.pdf
  - https://www.afrobarometer.org/wp-content/uploads/2022/02/ab_r6_dispatchno56_police_corruption_in_africa.pdf
- **VOCS:** https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/785 ; **SASAS:** https://hsrc.ac.za/special-projects/sasas/
- **ACLED codebook:** https://acleddata.com/sites/default/files/wp-content-archive/uploads/dlm_uploads/2023/06/ACLED_Codebook_2023.pdf
- **SAPS:** http://www.datafirst.uct.ac.za/dataportal/index.php/catalog/1012 ; https://github.com/afrith/crime-stats ; https://www.saps.gov.za/services/boundary.php
- **Census:** https://www.statssa.gov.za/?page_id=4086 ; https://www.statssa.gov.za/?p=18967
- **MDB wards (SNIPPET):** https://open.africa/dataset/demarcation-board-gauteng-gis-data

---

## Revision log (round 2)

| Critic item | Change | Where |
|---|---|---|
| #1 DiD overstated | "Strong" time overlap downgraded to CONDITIONAL. JHB SAR Policy 2018 read in full: crime evidence required (s.4.4), SAPS meeting, 67% consent, 2-year validity plus renewals, mandated PSIRA guards. Gazette desk check of 6 issues (7 notices, all 2021–24; zero in 2007/2013/2019 samples). Identification notes per architecture (crime-driven timing, pre-trends, renewals vs first approvals, spillover). Go/no-go threshold and pilot design. | §0, T3, §3, §4, §5 |
| #2 Post-treatment selection | Treatment-induced non-response and within-ward substitution; diagnostics; GCRO refusal metadata flagged as a request (by-ward publication UNVERIFIED); sorting (E2) vs incumbent (E1) arms separated | §5.2, O4, §2 |
| #3 Treatment measurement | Three arms (E1/E2/E3); dwelling-share intensity from Census SALs with building-weighted splits; 500 m rings; sectional-title rule (E2c complex, not treated in main spec); "densely mapped" removed; OSM ways ≠ enclaves | §2, T1, §0 |
| #4 Construct mapping | QoL item × wave matrix mapped to performance / procedural / trust / normative / reliance / safety; normative legitimacy only from AB (SA rounds UNVERIFIED); reliance only from VOCS/AB | §6 |
| #5 Unit stability | SAPS time-invariant precinct clusters; MDB ward crosswalk with SAL population weights; QoL wave comparability caveats | §7 |
| #6 Labels | Added VERIFIED\*, SECONDARY, SNIPPET; relabelled over-claimed items; per-wave ward representativeness table | Labels, O1, O4 |
| #7 Gazette effort | Effort made conditional on the pilot; archive gaps and absence of a confirmed full-text search documented | §3, §11 |
| #8 Measurement error | SAPS reporting bias, ACLED media/urban bias and sparse Inter 8, EA-SEC-E double-barrel | §8 |
| #9 Dispositions | SACN, GHS, Census/QoL dwelling type, SAHRIS | §10 |
| #10 Scrape + ranking | T9 updated from the audit and code review (qualitative; ~52% enclave / ~88% PSC precision; no Ekurhuleni; Durban label unreliable); ranked source table | T9, §10 |
| #11 External validity | Per-architecture paragraphs (Brazil loteamentos vs condomínios, Delhi RWAs, Nairobi, BIDs; 1999 vs 2013 cohort timing) | §9 |
| Decisions | Five decisions with recommendations | §14 |

**Process notes:**
- The report was saved in two stages.
- Gazette sampling was time-boxed at 6 issues. Fetches that failed or hung (2016 issues over 10 MB, the SAFLII search, GreenGazette DNS, the CoJ approvals page 404, the Tshwane TLS error) are marked UNVERIFIED.
- One fetch-tool summary of the CoJ 2021 notice falsely attributed crime-statistics requirements to it. It was discarded and replaced by direct reading of the policy PDF.

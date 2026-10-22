# Data Assessment Review: explorer-critic, round 1

**Date:** 2026-09-29 · **Severity:** LOW (Discovery)
**Artifact:** `quality_reports/data_exploration_psc-exposure.md`
**Score:** 70/100, a **FAIL** against the bar of 80. It goes back to the explorer for round 2 of 3.

## Verdict
The report is strong and honestly labelled. It rules out the spatial RD on sound grounds and finds something valuable: the dated SAR (road-closure) trail in the Gauteng gazette.

It fails because the recommended staggered ward/precinct DiD is assumed to work rather than shown to work. The report gives:
- no count of first-time approvals (as opposed to renewals) in 2009–2024
- no mention of reverse causality, even though closures are a response to crime
- no treatment of the fact that closures can change who gets surveyed

## Issues
| # | Issue | Section | Severity | Deduction | Recommendation |
|---|---|---|---|---|---|
| 1 | The DiD's fit is overstated. The time overlap for SAR × QoL/SAPS is rated "Strong" without a distribution of approval dates. Renewals are not separated from first approvals. Reverse causality and displacement/spillover are not raised. | §2 rows 4 & 7; Arch 1 | High | -6 | Downgrade the rating to conditional. Add an identification note for each architecture (timing driven by crime, pre-trends, renewals vs first approvals, spillover). Set a go/no-go threshold on the number of first approvals per metro within the window. |
| 2 | Post-treatment sample selection: booms can cut off enumerators' access, and ward quotas then substitute other households. New estates change a ward's make-up through migration (sorting) rather than by acting on existing residents. | O4; §2 rows 4–6, 8 | High | -5 | Discuss non-response caused by treatment. Separate the arms: SAR acts on existing residents, new estates act through sorting. |
| 3 | Ward-level treatment is too broad ("≥1 SAR in ward"). There is no intensity measure. OSM *ways* are counted, not *enclaves*. "Densely mapped" overstates. It is undecided whether sectional-title complexes count as treated. | §0.1; T1; §2; §5 | Medium | -4 | Define intensity (the share of dwellings behind a closure or estate edge). Decide how complexes are treated. Use neutral wording. |
| 4 | Outcomes are not mapped to performance, procedural and normative legitimacy, or to reliance. There is no check that items are available in the pre-period waves. | O4; §5 | Medium | -3 | Build an item × wave matrix mapped to each dimension. Say what only Afrobarometer can supply. |
| 5 | Unit stability: SAPS precincts split (1,141 → 1,174 stations). No ward crosswalk source is named (Municipal Demarcation Board). Changes in QoL mode across waves are not addressed. | O4; O8 | Medium | -2 | Say how split precincts are handled. Name the crosswalk. Note how comparable the waves are. |
| 6 | Verification labels are inflated: some "VERIFIED" items rest on search snippets or secondary sources. Ward representativeness is doubtful for QoL I (n=6,636). | several | Medium | -2 | Add a SECONDARY/SNIPPET label. State representativeness for each wave. |
| 7 | The gazette effort estimate (3–6 weeks) is optimistic. Archive completeness and full-text search are not checked. | T3; §4 | Low–Med | -2 | Make the estimate conditional on a pilot. Verify the archive. |
| 8 | Outcome measurement error: SAPS reporting bias could be affected by PSC and by legitimacy. ACLED has media and urban bias, and Inter 8 events are sparse. Afrobarometer EA-SEC-E asks about two things at once. | O7; O8 | Low–Med | -2 | Add paragraphs on each. |
| 9 | Missing dispositions: SACN, GHS, and Census/QoL dwelling-type as an exposure proxy. | O9 | Low | -2 | Give every named source one line. |
| 10 | The scrape section is stale: it predates the audit and precision coding. Ekurhuleni is missing. There is no ranked list of sources. | T9 | Low | -1 | Update T9 and add a source ranking. |
| 11 | External validity is thin: generalising from a Gauteng-specific instrument, the Global South comparators, and the 1999 vs 2009 timing. | §3 | Low | -1 | Add a short paragraph for each architecture. |

## Rejection table
| Dataset | Reason | Deal-breaker? |
|---|---|---|
| Property24 scrape as *primary* treatment | No boundaries; 80 suburbs; no Ekurhuleni; ~52% precision on enclaves | Yes as primary; No as a covariate or gazetteer |
| Afrobarometer AidData R1–R6 for RD or distance bands | Location centroids are off by 1–5 km or more | Yes for RD; No for municipality or 5 km cross-section |
| OSM history as the only timing source | First mapped ≠ built | Yes as the only source; No when triangulated |
| PSIRA stats | National or provincial only | Yes |
| Landman/CSIR inventories | 2000–03, no GIS | Yes (as literature only) |
| eThekwini register | Doesn't exist | Yes |
| StatsSA VOCS/GPSJS | Province-level geography only | Yes for spatial designs |
| HSRC SASAS | Geography too coarse; small n | Yes for spatial designs |
| ACLED for 1–2 km bands | Centroids; media-driven | Yes for distance; No for actor descriptives |
| JHB/Tshwane CIDs | Mostly commercial | Yes for residential |
| Imagery-based wall/gate detection | No product exists | Yes (this round) |
| Spocter inventory | Non-metro Western Cape | Yes for metro |
| Lightstone/GTI | Cost unknown | No (conditional) |
| CSOS / Deeds bulk | Access unverified | No (pending) |

## Is Architecture 1 sound?
It is directionally sound but not yet demonstrated. SAR is the right anchor: it is dated, administrative, and acts on existing residents. Three conditions must hold first:
1. enough first-time approvals in 2009–2024
2. a credible answer to endogenous timing (pre-trends)
3. an intensity definition, plus a plan for non-response caused by treatment

Keep the SAR and OSM-estate arms separate. Gauteng has **no credible measure of PSC personnel**, so as built the project studies *enclosure*, not *PSC exposure*.

## Decisions for the user and strategist
1. **Headline construct:** SAR enclosure, private estates, or PSC patrol presence. This may mean reframing to "enclosure".
2. **Area-level ITT, or restricted individual locations** (GCRO GPS, SAPS incident points, Afrobarometer geocodes)? The restricted route has long, uncertain timelines.
3. **Go/no-go on the gazette register:** pilot first, then set a minimum number of first approvals.
4. **Scope:** Gauteng only, adding the Cape Town SRA module, and whether to add the national Afrobarometer extension.
5. **Scrape:** freeze it at covariate quality, or scrape more (Ekurhuleni, JHB).

## Minimum fixes for round 2
#1–#4 are required. #5, #6 and #10 are quick edits. #7–#9 and #11 are recommended.

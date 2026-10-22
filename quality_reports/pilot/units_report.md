# WP2 Units Report: precinct clusters, stable ward units, Census 2011 covariates

**Date:** 2026-09-30 · **Agent:** data-engineer · **Status:** partial. Precinct clusters are final. Stable ward units (SWUs) exist only in PROVISIONAL form. SAL covariates are blocked until the user downloads the Census 2011 files manually (see §1).
**Code:** `scripts/cleaning/units/` (`00_download.R`, `01_precinct_clusters.R`, `02_stable_ward_units.R`, `03_sal_covariates.R`, `04_map_figure.R`, helpers `_common.R`, `_saps_parse.R`, `_swu_functions.R`, `_sal.R`, tests in `tests/test_units.R`).
**Figure:** `paper/figures/fig_units_swu_precinct_clusters.pdf`.

---

## 1. Action needed from the user: manual download (Census 2011 SAL)

Two inputs require a free DataFirst login, so the agent did not fetch them:
- the Census 2011 SAL attribute tables;
- the SAL boundaries.

| Item | Where | Files |
|---|---|---|
| South African Census Community Profiles 2011 (DataFirst study 517; Stats SA data at small-area-layer level; the Stats SA SAL GIS layer ships with it) | https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/517/get-microdata | `type-of-main-dwelling`, `population-group`, `population-group-household-head`, `household-income-annual`, `household-size`, `geo-type`, `enumeration-area-type`, `tenure-status` (.dta), **plus** the SAL GIS layer (any .shp/.gpkg/.gdb with a `SAL_CODE` field) |

**Where to put them:** `data/raw/units/census2011_saccp/`. Any subfolder is fine; keep the file names as delivered.

**Then run:**
1. `Rscript scripts/cleaning/units/02_stable_ward_units.R` (SAL mode is picked automatically);
2. `03_sal_covariates.R`;
3. `04_map_figure.R`;
4. the tests.

**Behaviour until then:**
- Without these files, `02` and `03` stop with this message (exit status 3).
- `02` runs only when `PSC_UNITS_PROVISIONAL=1` is set. It then uses GHSL population in place of SAL dwellings and writes to `data/cleaned/units/provisional/`.
- **Schema guards (fix round).** `_sal.R` now stops if a census table lacks an expected category column (only `dwltyp_13`, `inchh_13` and `pgrhhh_6` may be absent), and requires ≥99% of SAL polygon codes to match the table codes (`assert_sal_match`). `02` logs, rather than silently zeroes, SALs without a dwelling count. A synthetic three-SAL fixture in `tests/test_units.R` exercises the loaders, long form, apportionment and both guards; the real census files have not been tested.

**Optional second item (not needed to run the pipeline):** the current SAPS boundaries (dated 2026-01-22).
- They sit behind a request form at `saps.gov.za/services/boundary.php`: requester name and e-mail, plus acceptance of a Spatial Data Infrastructure (SDI) Act disclaimer. The agent does not submit that form on the user's behalf.
- The pipeline uses the SAPS v1.3.5 layer (Oct 2024), distributed by Stats SA. The newer vintage only matters if a station opened in the four metros after Oct 2024. Tafalehashe (WC) appears in the SAPS 2025/26 Q4 list but has no polygon and zero counts yet.

## 2. Unit counts per metro

### 2.1 Wards (MDB delimitations)

| Metro | 2011 | 2016 | 2021 (2020 delimitation) |
|---|---|---|---|
| Johannesburg (JHB) | 130 | 135 | 135 |
| Tshwane (TSH) | 105 | 107 | 107 |
| Ekurhuleni (EKU) | 101 | 112 | 112 |
| Cape Town (CPT) | 111 | 116 | 116 |

These match the memo's assumed 135/107/112 (§3.2 and §17.1) for 2016 and 2021.

### 2.2 Police stations and precinct clusters (final)

A station is assigned to a metro if its 2025 precinct has ≥50% of its GHSL population in that metro. A cluster is in scope if ≥50% of its population lies in the four metros combined; it is then assigned to the metro with the largest share.

| Metro | Stations (own metro) | In-scope clusters | Stations in those clusters | Never-split clusters (singletons) | Never-split, strict | Cross-metro clusters | Largest cluster (stations) |
|---|---|---|---|---|---|---|---|
| JHB | 45 | 34 | 51 | 25 | 24 | 4 | 6 |
| TSH | 36 | 25 | 34 | 20 | 20 | 1 | 6 |
| EKU | 37 | 25 | 37 | 20 | 20 | 1 | 5 |
| CPT | 63 | 55 | 63 | 49 | 47 | 1 | 4 |
| **3 Gauteng metros** | **118** | **84** | 122 | **65** | 64 | 6 | |

Definitions:
- **Strict never-split:** a singleton that has been active since the first observable year (FY2003/04) and was not a parent of an FY2004/05 opening.
- **Cross-metro:** less than 90% of the cluster's population lies in its assigned metro.

Checks:
- Every in-scope cluster has at least one station that was fully active in FY2005/06.
- Every in-scope cluster has an active station in every FY from 2005/06 to 2025/26 (tested).
- Stats SA's own municipality tags give 44/36/36/62 stations for JHB/TSH/EKU/CPT, against 45/36/37/63 here. The small differences come from edge precincts.

**Rule used (pre-specified; also written in `precinct_clusters.gpkg$rule`).** Clusters are the connected components of four kinds of link:
- **E1 (new station, post-2014):** a station first seen in boundary vintage v is linked to every v−1 precinct for which the overlap holds ≥5% of either the v−1 precinct's population or the new station's population (evidence = the larger of the two shares). The earlier wording ("supplied ≥5% of its population") described only the second share; the code always used the maximum, so no cluster changed.
- **E2 (boundary exchange):** two existing stations are linked if territory holding ≥5% of either's population moved between them across consecutive SAPS vintages (2014, 2015, 2016, 2017, 2018, 2020, 2025).
- **E3 (count-drop rule):** for stations that opened in FY2005/06–FY2014/15, which already appear in the earliest (2014) boundaries, parents are adjacent precincts whose 17-category count fell, using 2-year means relative to the provincial trend, by both:
  - ≥25% of the child's count, and
  - ≥5% of their own expected count.
  If no neighbour qualifies, the largest drop is used and flagged as weak (none are weak).
- **E4 (station without a polygon):** a station with no polygon joins the precinct that contains its station point. This applies to **Table Bay Harbour**, which reports about 1,000–2,000 crimes a year but has never had a polygon.
- Stations that opened before FY2005/06 are not merged.

**Stations opened in the panel, four metros (child ← parents):**

| Metro | Child (FY opened) ← parent(s) |
|---|---|
| CPT | Mfuleni (2005) ← Khayelitsha + Kuils River |
| CPT | Belhar (2007) ← Delft |
| CPT | Lwandle (2008) ← Strand |
| CPT | Lentegeur (2013) ← Mitchells Plain |
| CPT | Samora Machel (2018) ← Nyanga |
| CPT | Makhaza (2024) ← Harare |
| TSH | Mamelodi East (2006) ← Mamelodi |
| TSH | Olievenhoutbosch (2011) ← Erasmia + Wierdabrug |
| JHB | Diepsloot (2010) ← Erasmia |
| JHB | Moffatview (2012) ← Booysens + JHB Central |
| JHB | Doornkop (2020) ← Dobsonville |
| JHB | Cosmo City (2022) ← Honeydew |
| EKU | Katlehong North (2012) ← Katlehong |
| EKU | Tembisa South (2014) ← Tembisa |

**Sensitivity** (`intermediate/cluster_sensitivity.parquet`; clusters counted by the metro of their stations):

| Scenario | EKU | TSH | JHB | CPT |
|---|---|---|---|---|
| Primary (τ=0.05) | 26 | 26 | 35 | 55 |
| τ=0.10 for E1/E2 | 28 | 29 | 38 | 56 |
| No E2 exchanges | 35 | 33 | 41 | 56 |
| E3 off (no count-drop merges) | 27 | 28 | 38 | 60 |
| Primary + direct 2014→2025 overlay edges | 26 | 26 | 35 | 55 |

**Direct 2014→2025 overlay check** (`intermediate/overlay_2014_2025_check.parquet`): 50 station pairs show ≥5% exchange when the earliest and latest vintages are overlaid directly. 49 already sit in the same cluster. The one exception, Boons–Klerkskraal (8%), lies outside the four metros, so no in-scope cluster changes. Cluster membership is unchanged by the fix round (323 stations, 0 reassigned).

Most of the merging comes from E2 exchanges. 29 of the 47 E2 links occur between the 2014 and 2015 SAPS vintages, which looks like a boundary realignment exercise.

### 2.3 Stable ward units (PROVISIONAL: GHSL 2010 population weights, not SAL dwellings)

| Metro | SWUs | Single-ward SWUs, unchanged 2011–2021 | 2021 wards in multi-ward SWUs | Weight reallocated by the 2011 crosswalk |
|---|---|---|---|---|
| JHB | 64 | 42 | 69% | 0.48% |
| TSH | 17 | 11 | 90% | 0.21% |
| EKU | 13 | 10 | 91% | 0.05% |
| CPT | 9 | 2 | 98% | 0.02% |

**Crosswalks** (`ward_crosswalk_{2011,2016}_to_2021.parquet`):
- Weights sum to 1 per source ward (maximum deviation 2e−16).
- Each ward keeps ≥95% of its weight inside its own SWU. The 5th percentile is 0.98 for 2011 and 0.99 for 2016.
- Overlay: 1,232 atoms and 26 residual gap rows. Gaps hold 719 persons out of 14.1 million.

## 3. Comparison with the memo's §3.2 planning counts

| Memo planning count (ASSUMED) | Found here | Comment |
|---|---|---|
| ~115 SWUs in JHB; ~310 SWUs across 3 metros | **64 in JHB; 94 across 3 metros (provisional)** | **Does not hold. Needs a strategist decision (§5.1).** |
| ~35 precinct clusters in JHB; ~100 across 3 metros | **34 in JHB; 84 across 3 metros** | JHB matches. TSH and EKU come out lower because of E2 exchanges; without E2 the count would be about 104 (see sensitivity above). |
| ~110 stations in 3 metros | 118 | |
| Stations 1,141 → 1,174 (panel) | Polygon counts 1,140 (2014) → 1,167 (Oct 2024) | Consistent. 21 GT/WC stations opened in FY2005/06 or later. |

Planning rows that feed the recount:
- Effective J_C, ever-enclosed and never-enclosed counts: **not computed** (closures are mapped in P-C). The denominators above are the inputs.
- Common-support predictors: the Census-based ones are built by `03_sal_covariates.R` once the SAL data arrive. They are: income (band shares and mean from band midpoints), freestanding share, complex share (cluster + townhouse), race composition, household density, distance to own-metro CBD and to the nearest major CBD, owner share, and formal-residential enumeration-area (EA) share. The pre-window SAPS trajectory belongs to WP3.

## 4. Known problems

1. **The SWU rule collapses under three delimitations (substantive).**
   - The 2011→2016 redelimitation chains wards together across whole metros. Examples:
     - CPT: 116 wards form 9 SWUs, the largest containing 36 wards.
     - EKU: the largest SWU contains 98 of 112 wards.
   - Sensitivity grid (`provisional/intermediate/swu_sensitivity.parquet`), SWUs for JHB/TSH/EKU/CPT:
     - τ=0.05, all three vintages: 64/17/13/9;
     - τ=0.25, all three vintages: 106/53/48/66;
     - 2016+2021 only at τ=0.05: 109/38/82/40.
   - SAL dwelling weights will change these numbers somewhat, but not the pattern.
2. **Heuristic E3 parents.** Parents of openings before 2014 are inferred from count drops, because no public boundaries exist before 2014. Bekkersdal is linked to Lenasia with a drop of 34% of the child's count and 13% of Lenasia's own. This pulls Westonaria and Bekkersdal (Rand West) into a JHB cluster whose metro share is 0.60. Evidence for every link is in `intermediate/precinct_e3_evidence.parquet`. With E3 switched off, Bekkersdal and Lenasia fall into separate clusters, and 38 stations end up in smaller clusters; the largest effect is in Cape Town (55 → 60 clusters). E3 therefore matters for cluster counts, most of all in Cape Town, and the "E3 off" row above is the robustness case.
3. **Chained cross-metro clusters.**
   - `PCL_DIEPSLOOT` has 6 stations across JHB and TSH, with a JHB share of 0.48; it is assigned to JHB and flagged.
   - **Roodepoort (JHB) is lost from scope.** It exchanged 32% of its population with Kagiso in 2014→15 and exchanged it back in 2020→25 (a "flip-flop"). The merged cluster is mostly in Mogale City.
   - Flip-flops (Kagiso–Roodepoort, Carletonville–Wedela) suggest digitising errors in the 2015–2020 SAPS files rather than real changes. They are merged conservatively and flagged `e2_flip_flop`.
4. **Stations from other provinces.** Only GT and WC workbooks are parsed. Verena (Mpumalanga) sits in `PCL_BRONKHORSTSPRUIT` (TSH) through an E2 exchange, so WP3 must pull Verena's counts from the Mpumalanga series. Boons, Vosman and Hartbeespoortdam touch GT in older vintages only; they are out-of-scope singletons.
5. **Residual threat.** Boundary shifts before 2014 that did not involve a new station cannot be detected. This is as the memo anticipated.
6. **Data defects handled:**
   - MDB 2011 wards: every feature is stored twice (8,554 features for 4,277 wards); de-duplicated on WardID.
   - SAPS 2019 file: identical to the 2018 file (same CREATE_DT and version), so it is skipped.
   - The 2013 SAPS release drops the (GP)/(C) tags on Heidelberg and uses long names (Johannesburg Central, OR Tambo International Airport): handled with a province-aware alias table.
   - Protea Glen was renamed Protea.
   - Cape Town Int. Airport and Tafalehashe report zero counts and have no polygon: excluded.
7. **Slivers, CRS and population cells.**
   - All geometry work uses a South African Albers equal-area projection (central meridian 24°E, standard parallels −24°/−33°).
   - Overlay pieces smaller than 1,000 m² are dropped as noise: 39 of the SWU atoms.
   - GHSL population is summed by cell centre (about 90 m cells), so pieces smaller than a cell can read zero. This is immaterial at the 5% thresholds.
8. **Calibration target (memo §6.3).** The community-profile files are one-way marginals by SAL. `03` therefore writes **margins** for raking: 5 dwelling classes, household-head race, and 5 income bands. The joint dwelling type × race × income cell target needs a SuperWEB2 cross-tabulation from Stats SA (Incapsula-protected; manual). **Flag for the strategist:** raking to margins is probably sufficient.

## 5. Decisions needed

1. **SWU definition (strategist; escalation per `agents.md` if unresolved).** Options:
   - (a) Keep the memo rule; A1-W runs on about 94 SWUs in Gauteng (provisional).
   - (b) Relax to τ=0.20–0.25: 173–207 Gauteng SWUs, with up to 20–25% misallocation per ward, which must be reported.
   - (c) Analyse on 2021 wards with the SAL-weighted crosswalks as primary (the memo lists this as robustness) and use SWUs as robustness.
   - (d) SWUs from 2016+2021 only, for waves V–7 (229 Gauteng SWUs).
   - The delimitation used by each QoL wave is still UNVERIFIED (to be confirmed in WP4).
2. **E2 exchange merges (strategist).** Keep them (primary: 84 Gauteng clusters) or treat them as robustness (about 104)? Flip-flop cases argue for keeping them.

## 6. Provenance

The full register, with retrieval time (UTC), bytes and SHA-256 for each file, is in `data/raw/units/provenance.csv`.

| Source | URL (archived copies are byte-for-byte `id_` snapshots) | Role |
|---|---|---|
| SAPS station boundaries 2014, 2015, 2016, 2017, 2018 (file dated 2018-03-07), 2019, 2020 (dated 2020-03-20) | web.archive.org snapshots of `https://www.saps.gov.za/services/downloads/boundaries/...` | Parents and exchanges |
| Stats SA PoliceDistrict.zip (SAPS v1.3.5, created 2024-10-01) | web.archive.org/web/20260506045720id_/https://www.statssa.gov.za/wp-content/uploads/2025/08/PoliceDistrict.zip | Current precincts |
| SAPS station figures FY2003/04–2012/13 (.xls) | archived `saps.gov.za/resource_centre/publications/statistics/crimestats/2013/downloads/police_station_figures_per_province.xls`. Size matches afrith/sa-crime-stats. | Opening years |
| SAPS 2014/15, 2020/21 and 2023/24 releases | archived `saps.gov.za/.../crimestats_2014_2015_v1.xlsx`, `/services/downloads/Crime-Statistics-2020_2021-Release.xlsx`, `/services/downloads/2023-2024%20_Annual_Stats.xlsx` | Opening years |
| SAPS 2025/26 Q4 release | https://www.saps.gov.za/services/downloads/2025/2025-2026_-_4th_Quarter_WEB.xlsx | 2025/26 station list |
| MDB Wards 2011, 2016, 2021 (ArcGIS items 12d2deb9…, cfddb54a…, e0223a82…) | https://www.arcgis.com/sharing/rest/content/items/{id}/data (MDB "Know Your Wards" hub) | Ward vintages |
| JRC GHS-POP R2023A, epoch 2010, 3″ tiles R12_C21 and R13_C20 (CC-BY 4.0) | https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/GHS_POP_E2010_GLOBE_R2023A_4326_3ss/V1-0/tiles/ | Population materiality for clusters; PROVISIONAL SWU weights |
| Census 2011 community profiles and SAL layer (DataFirst 517) | manual, see §1 | SAL dwellings, covariates, margins |

**Terms of use.** The SAPS boundary disclaimer (SDI Act) forbids redistribution without SAPS permission. Raw boundary files therefore stay in gitignored `data/raw`, and the replication package will need SAPS permission or download instructions.

The community repository afrith/crime-stats was checked and not used: its boundaries derive from the same Stats SA file.

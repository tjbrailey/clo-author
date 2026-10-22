# Domain Profile

## Field

**Primary:** Political Science — Comparative Politics, State Legitimacy, Urban Violence
**Adjacent subfields:** Development Economics, African Studies, Criminology, Political Geography

---

## Target Journals (ranked by tier)

| Tier | Journals |
|------|----------|
| Top generalist | APSR, AJPS, JOP, World Politics |
| Top field | Journal of Conflict Resolution, Comparative Political Studies, Political Geography |
| Strong field | African Affairs, Journal of Peace Research, Journal of Modern African Studies |
| Specialty | Journal of Southern African Studies, African Security, Urban Studies |

---

## Common Data Sources

| Dataset | Type | Access | Notes |
|---------|------|--------|-------|
| Afrobarometer (SA waves 1–9) | survey/panel | public | Attitudes toward state, trust, legitimacy, police; geolocate respondents to ward/EA level |
| ACLED | event/georeferenced | public | Conflict and violence events; disaggregate by actor type (state, non-state, communal) |
| SAPS Crime Statistics | admin | public | Precinct-level crime counts; use for violence outcome validation |
| Property24 / Private Property | scraped | public website | Listing descriptions, gated community flags, PSC mentions; primary treatment variable source |
| SA Census / StatsSA (2011, 2016 CS, 2022) | admin | public | EA-level demographic controls, income, unemployment |
| OpenStreetMap | geospatial | public | Boundary polygons, road networks, amenities |
| SACN Urban Node Profiles | admin | public | Municipal-level contextual variables |
| SAHRIS (Heritage sites) | geospatial | public | Additional boundary reference layer |

---

## Common Identification Strategies

| Strategy | Typical Application | Key Assumption to Defend |
|----------|-------------------|------------------------|
| Spatial/Geographic RD | Treatment = inside vs. outside gated community boundary at fine resolution | No manipulation of residential location near boundary; continuity of potential outcomes |
| DiD with spatial FE | Exploit timing of new gated community construction | Parallel pre-trends in attitudes/violence between areas that later get gated communities and those that don't |
| Boundary discontinuity | Respondents on either side of estate perimeter | Boundary location is conditionally exogenous to outcome (not selected on violence or attitudes) |
| Matching + spatial controls | Observable neighborhood characteristics + spatial lag | Selection on observables; strong overlap requirement |

---

## Field Conventions

- Always report Moran's I test for spatial autocorrelation before and after including spatial controls
- Cluster standard errors at the lowest feasible geographic unit (ward or enumeration area level)
- Binary outcomes: report LPM alongside probit/logit marginal effects
- Geospatial analyses: report OLS with spatial fixed effects AND spatial lag/error model side by side
- Violence outcomes: disaggregate by actor type (state, non-state, communal), not just total incidence
- State legitimacy outcomes: separate performance legitimacy, procedural legitimacy, and normative legitimacy dimensions
- Always discuss external validity to other Global South contexts (Brazil favelas, Kenyan gated estates, Indian colonies)
- Maps and spatial figures must include scale bars, north arrows, and projection info

---

## Notation Conventions

| Symbol | Meaning | Anti-pattern |
|--------|---------|-------------|
| $Y_{it}$ | Outcome (attitude/violence) for unit $i$ at time $t$ | Don't use $y$ without subscripts |
| $D_i$ | Binary treatment: 1 if inside gated community | Don't use $T$ (reserved for time) |
| $r_i$ | Running variable: distance to nearest estate boundary (meters) | Don't use $x$ for the RD forcing variable |
| $\tau$ | Treatment effect / LATE | Don't use $\beta_1$ for the main effect in RD specs |
| $W$ | Spatial weights matrix | Must define row-normalization explicitly |

---

## Seminal References

| Paper | Why It Matters |
|-------|---------------|
| Caldeira (2000) — *City of Walls* | Foundational theory of gated communities and democratic fragmentation; Brazil comparator |
| Bratton & van de Walle (1997) — *Democratic Experiments in Africa* | State legitimacy and authority in African contexts |
| Ferree (2011) — *Framing the Race in South Africa* | SA-specific legitimacy and identity politics |
| Davis (2006) — *Planet of Slums* | Privatized security infrastructure and urban inequality globally |
| Raleigh & Hegre (2009) | Methods for georeferenced conflict analysis; spatial bandwidth and ACLED use |
| Acemoglu & Robinson (2006) — *Economic Origins* | Elite capture of security provision; institutional persistence |
| Goldstein (2004) — *The Spectacular City* | Urban governance, crime, and state legitimacy in Peru |
| Zhu et al. (2012) | Spatial RD methods near boundaries — design reference |
| Besley & Persson (2011) — *Pillars of Prosperity* | State capacity and private order substitution |

---

## Field-Specific Referee Concerns

- "Is the spatial bandwidth arbitrary?" — must defend bandwidth choice (IK selector, cross-validation, or explicit robustness across bandwidths)
- "Reverse causality: gated communities may locate where violence is already high" — pre-trends analysis and falsification tests required
- "Selection into gated communities is not random" — must address via RD design or rich controls + balance tests
- "Afrobarometer sampling does not oversample near estate boundaries" — must geolocate respondents, report spatial density, and acknowledge uncertainty
- "South Africa is exceptional (apartheid legacy, extreme inequality) — what's the external validity?" — must address with comparators (Brazil, Kenya, India) and discuss mechanisms
- "PSC and gated community are conflated" — must distinguish gated estates (physical infrastructure) from active PSC presence (personnel/patrol)
- "What is the mechanism?" — must distinguish between supply-side (PSC substitutes for state) and demand-side (residents opt out of state) channels

---

## Quality Tolerance Thresholds

| Quantity | Tolerance | Rationale |
|----------|-----------|-----------|
| Point estimates | 1e-6 | Numerical precision in spatial computations |
| Standard errors | 1e-4 | Clustering at small geographic units |
| Coverage rates | ± 0.01 | Bootstrap/simulation with B >= 1000 reps |
| Spatial bandwidth | ± 50m | RD sensitivity — report across 200m, 500m, 1km |

#!/usr/bin/env Rscript
# ============================================================
# 00_load_data.R
# Load every cleaned dataset into the session for exploration.
# Usage: source(here::here("scripts", "analysis", "00_load_data.R"))
# Set LOAD_SPATIAL <- TRUE before sourcing to also load boundary files (slower).
# ============================================================

suppressPackageStartupMessages({
  library(dplyr)
  library(arrow)
  library(readr)
})

if (!exists("LOAD_SPATIAL")) LOAD_SPATIAL <- FALSE
p <- function(...) here::here(...)

# ------ Surveys ------

# QoL waves I-7 (2009-2024), respondent level; ward_code (see notes), ea_code (V/6/7), interview_date (V/6/7)
qol <- read_parquet(p("data", "cleaned", "qol_harmonized.parquet"))
# QoL merged with PSC listing exposure and SAPS precinct crime by ward-wave
qol_merged <- read_parquet(p("data", "cleaned", "analysis_qol.parquet"))

# Afrobarometer Round 9 South Africa (2022), respondent level
ab <- read_parquet(p("data", "cleaned", "ab_r9_clean.parquet"))
ab_merged <- read_parquet(p("data", "cleaned", "analysis_ab.parquet"))

# GPSJS household files 2019/20-2024/25 (raw, not yet harmonised: names and codes differ by wave)
gpsjs_hh <- list(
  `2019/20` = read_csv(p("data", "raw", "gpsjs", "gpsjs_2019_2020", "gpsjs-2019-2020-hhold-v1.csv"),
                       show_col_types = FALSE, guess_max = 5000),
  `2020/21` = haven::read_dta(p("data", "raw", "gpsjs", "gpsjs_2020_2021", "gpsjs-2020-2021-hhold-v1.dta")),
  `2021/22` = haven::read_dta(p("data", "raw", "gpsjs", "gpsjs_2021_2022", "gpsjs-2021-2022-hhold-v1.dta")),
  `2022/23` = haven::read_dta(p("data", "raw", "gpsjs", "gpsjs_2022_2023", "gpsjs-2022-2023-hhold-v1.dta")),
  `2023/24` = haven::read_dta(p("data", "raw", "gpsjs", "gpsjs_2023_2024", "gpsjs-2023-2024-hhold-v1.dta")),
  `2024/25` = haven::read_dta(p("data", "raw", "gpsjs", "gpsjs_2024_2025", "household-2024-2025-v1.dta"))
)

# ------ Crime ------

# SAPS station x financial year, all 32 crime categories, national (fy = start year of Apr-Mar year)
saps_raw <- read_csv(p("data", "raw", "saps_crime", "sapacr-2005-2026-v1.5.csv"), show_col_types = FALSE) |>
  mutate(station = trimws(tolower(station)), fy = as.integer(substr(year, 1, 4)))
# Gauteng stations, station x year, crime families (V0-V4) with station coordinates
saps_station <- read_parquet(p("data", "cleaned", "saps_crime_ward.parquet"))
# Precinct crime area-weighted to 2016 wards: ward x calendar year, and ward x QoL wave
saps_ward_year <- read_parquet(p("data", "cleaned", "saps_crime_ward_year_full.parquet"))
saps_ward_wave <- read_parquet(p("data", "cleaned", "saps_crime_ward_wave_full.parquet"))
# Precinct-to-ward area weights (2016 precincts x 2016 wards)
precinct_ward_xwalk <- read_parquet(p("data", "cleaned", "precinct_ward_crosswalk.parquet"))

# ------ Police resources ------

# Residents per police officer, each Gauteng station, 2018 (PMG written reply NW3216)
police_ratio_2018 <- read_csv(p("data", "cleaned", "pmg_station_police_ratio_2018.csv"), show_col_types = FALSE)

# ------ Road closures (security access restrictions) ------

# Gazette notices 2014-2024 with location (lat/lon, ward_code = 2016, ward_code_2020, ea_code, geo_precision)
sar_notices <- read_parquet(p("data", "cleaned", "gazette", "sar_notices_geocoded.parquet"))
# Closure sites (notices grouped by place and street) with onset date
sar_sites <- read_parquet(p("scripts", "analysis", "closure_timing", "output", "02_sites.parquet"))
# QoL V/6/7 respondents near closure sites, with distance and timing relative to interview date
sar_exposure <- read_parquet(p("scripts", "analysis", "closure_timing", "output", "02_exposure.parquet"))

# ------ Private security in property listings (Property24) ------

listings <- read_parquet(p("data", "cleaned", "listings_geocoded.parquet"))
psc_ward <- read_parquet(p("data", "cleaned", "psc_exposure_ward.parquet"))   # ward x year
psc_ea <- read_parquet(p("data", "cleaned", "psc_exposure_ea.parquet"))       # EA ring buffers

# ------ Cape Town Special Rating Areas ------

sra_onsets <- read_parquet(p("data", "cleaned", "e3", "sra_onsets.parquet"))
sra_security_budget <- read_parquet(p("data", "cleaned", "e3", "sra_security_budget.parquet"))

# ------ Crosswalks ------

ward_concordance_2011_2016 <- read_parquet(p("data", "cleaned", "ward_concordance_2011_2016.parquet"))
station_to_cluster <- read_parquet(p("data", "cleaned", "units", "station_to_cluster.parquet"))

# ------ Boundaries (optional) ------

if (LOAD_SPATIAL) {
  library(sf)
  wards_2016 <- st_read(p("data", "raw", "units", "mdb", "wards_2016", "MDBWard2016.gdb"), quiet = TRUE)
  wards_2020 <- st_read(p("data", "raw", "units", "mdb", "wards_2021", "SA_Wards2020.shp"), quiet = TRUE)
  precincts_2016 <- st_read(p("data", "raw", "units", "saps", "boundaries_2016", "Police_bounds.shp"), quiet = TRUE)
  precinct_clusters <- st_read(p("data", "cleaned", "units", "precinct_clusters.gpkg"), quiet = TRUE)
  sra_polygons <- st_read(p("data", "cleaned", "e3", "sra_polygons.gpkg"), quiet = TRUE)
  eas_2011_gp <- st_read(p("data", "raw", "units", "statssa", "ea_boundaries_2013", "SA_nogaps_2013.shp"),
                         quiet = TRUE) |> filter(EA_CODE >= 7e7, EA_CODE < 8e7)
}

# ------ Summary ------

loaded <- Filter(function(x) is.data.frame(get(x)), ls())
cat("Loaded datasets:\n")
for (x in loaded) cat(sprintf("  %-28s %9s rows  %4s cols\n", x, format(nrow(get(x)), big.mark = ","), ncol(get(x))))
cat(sprintf("  %-28s %9s waves\n", "gpsjs_hh (list)", length(gpsjs_hh)))
cat("\nNotes:\n",
    " - qol$ward_code: waves II-6 use 2016 wards; wave 7 codes are the 2021 demarcation (not converted).\n",
    "   Wave I codes were mapped from 2006 wards (38% mapped). For consistent 2016 wards in V/6/7, use\n",
    "   sar_exposure$ward_2016 (derived from each respondent's EA centroid).\n",
    " - saps_raw$fy = start year of the SAPS financial year (April-March).\n",
    " - sar_notices: 238 of 815 notices have no location (lat NA); geo_precision = street or suburb.\n")

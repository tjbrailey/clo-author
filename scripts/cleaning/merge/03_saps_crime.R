#!/usr/bin/env Rscript
# ============================================================
# 03_saps_crime.R
# Prepare SAPS station-level crime data → ward-year panel.
#
# Input:  data/raw/saps_crime/sapacr-2005-2026-v1.5.csv
#         data/raw/units/mdb/wards_2016/ (ward boundaries)
# Output: data/cleaned/saps_crime_ward.parquet
#         (station-level panel with ward assignment + crime family totals,
#          ward-level aggregates, and QoL-wave-aligned summaries)
#
# Steps:
#   1. Read station-level annual crime counts
#   2. Fix coordinate encoding (comma→period decimals)
#   3. Parse fiscal year strings → calendar year midpoint
#   4. Filter to Gauteng stations
#   5. Compute crime family totals (V0-V4)
#   6. Spatial join stations → wards (2016 boundaries)
#   7. Aggregate to ward-year level
#   8. Align with QoL wave periods
#   9. Validation diagnostics
#  10. Save station-level and ward-level panels
# ============================================================

library(tidyverse)
library(arrow)
library(sf)
source(here::here("scripts", "cleaning", "merge", "00_config.R"))

cat("=== 03_saps_crime.R ===\n\n")

# ------ 1. read ------

raw <- read_csv(PATHS$saps_file, show_col_types = FALSE,
                col_types = cols(latitude = col_character(),
                                 longitude = col_character()))
cat(sprintf("SAPS raw: %s rows, %s stations, %s years\n",
            format(nrow(raw), big.mark = ","),
            n_distinct(raw$station),
            n_distinct(raw$year)))

# ------ 2. fix coordinates ------

raw <- raw |>
  mutate(
    latitude  = as.numeric(gsub(",", ".", latitude)),
    longitude = as.numeric(gsub(",", ".", longitude))
  )

cat(sprintf("Coordinate range: lat [%.2f, %.2f], lon [%.2f, %.2f]\n",
            min(raw$latitude, na.rm = TRUE), max(raw$latitude, na.rm = TRUE),
            min(raw$longitude, na.rm = TRUE), max(raw$longitude, na.rm = TRUE)))


# ------ 3. parse fiscal year ------
# "2005/2006" → fiscal_year_start = 2005, fiscal_year_end = 2006
# Calendar midpoint = April of end year (SA fiscal year: April–March)

raw <- raw |>
  mutate(
    fy_start = as.integer(str_extract(year, "^\\d{4}")),
    fy_end   = as.integer(str_extract(year, "\\d{4}$")),
    cal_year = fy_end  # use end year as the reference (most of the period falls here)
  )

cat(sprintf("Fiscal years: %s to %s (calendar: %d–%d)\n",
            min(raw$year), max(raw$year),
            min(raw$cal_year), max(raw$cal_year)))


# ------ 4. filter to Gauteng ------

gauteng_districts <- c(
  "City of Johannesburg", "City of Tshwane", "Ekurhuleni",
  "Sedibeng", "West Rand"
)

dc_col <- intersect(c("dc_mn", "district"), names(raw))[1]
if (!is.na(dc_col)) {
  gauteng_mask <- grepl(
    "johannesburg|tshwane|ekurhuleni|sedibeng|west rand",
    raw[[dc_col]], ignore.case = TRUE
  )
  gp <- raw |> filter(gauteng_mask)
} else {
  gp <- raw |>
    filter(latitude > -27.0, latitude < -25.0,
           longitude > 27.0, longitude < 29.5)
}

cat(sprintf("Gauteng: %s stations, %s station-years\n",
            n_distinct(gp$station), format(nrow(gp), big.mark = ",")))


# ------ 5. crime family totals ------

crime_cols <- names(gp)[!names(gp) %in%
  c("year", "station", "loc_mn", "dc_mn", "longitude", "latitude",
    "fy_start", "fy_end", "cal_year")]

assign_family <- function(col) {
  col_lower <- tolower(col)
  for (fam_name in names(SAPS_FAMILIES)) {
    for (pat in SAPS_FAMILIES[[fam_name]]) {
      if (grepl(pat, col_lower, fixed = TRUE)) return(fam_name)
    }
  }
  "other"
}

col_family <- tibble(
  col    = crime_cols,
  family = map_chr(crime_cols, assign_family)
)

cat("\nCrime column → family:\n")
for (fam in sort(unique(col_family$family))) {
  cols_in_fam <- col_family$col[col_family$family == fam]
  cat(sprintf("  %s: %s\n", fam, paste(cols_in_fam, collapse = ", ")))
}

gp <- gp |>
  mutate(across(all_of(crime_cols), ~suppressWarnings(as.numeric(.x))))

station_panel <- gp |>
  select(cal_year, fy_start, fy_end, year, station, dc_mn, loc_mn,
         latitude, longitude)

for (fam in unique(col_family$family)) {
  fam_cols <- col_family$col[col_family$family == fam]
  station_panel[[paste0("total_", fam)]] <- rowSums(
    gp[, fam_cols, drop = FALSE], na.rm = TRUE
  )
}

station_panel <- station_panel |>
  mutate(total_all = total_V0_anchor + total_V1_primary + total_V2_person +
           total_V3_detection + total_V4_falsif + total_other)


# ------ 6. spatial join to wards (2016 boundaries) ------

ward_shp_path <- PATHS$wards_2016
gdb_dirs <- list.dirs(ward_shp_path, recursive = TRUE, full.names = TRUE)
gdb_dirs <- gdb_dirs[grepl("\\.gdb$", gdb_dirs)]
shp_files <- list.files(ward_shp_path, pattern = "\\.shp$",
                        full.names = TRUE, recursive = TRUE)
ward_shp_exists <- dir.exists(ward_shp_path) &&
  (length(gdb_dirs) > 0 || length(shp_files) > 0)

if (ward_shp_exists) {
  cat("\nSpatial join: stations → 2016 wards...\n")

  if (length(gdb_dirs) > 0) {
    layers <- st_layers(gdb_dirs[1])$name
    wards <- st_read(gdb_dirs[1], layer = layers[1], quiet = TRUE)
  } else {
    wards <- st_read(shp_files[1], quiet = TRUE)
  }
  wards <- st_transform(wards, 4326)

  ward_id_col <- intersect(
    c("WardID", "WARD_ID", "WARDID", "WARD", "ward_code", "CAT_B",
      "WardNumber", "wardid", "ward_id"),
    names(wards)
  )[1]

  if (!is.na(ward_id_col)) {
    station_locs <- station_panel |>
      distinct(station, latitude, longitude) |>
      filter(!is.na(latitude), !is.na(longitude))

    station_sf <- st_as_sf(station_locs, coords = c("longitude", "latitude"),
                           crs = 4326)
    station_ward <- st_join(station_sf, wards[, ward_id_col],
                            join = st_within) |>
      st_drop_geometry() |>
      rename(ward_code = !!ward_id_col) |>
      mutate(ward_code = as.character(ward_code))

    station_panel <- station_panel |>
      left_join(station_ward |> select(station, ward_code), by = "station")

    n_matched <- sum(!is.na(station_ward$ward_code))
    cat(sprintf("  Stations with ward: %d / %d (%.0f%%)\n",
                n_matched, nrow(station_ward),
                100 * n_matched / nrow(station_ward)))
  } else {
    cat("  WARNING: No ward ID column found in shapefile\n")
    station_panel$ward_code <- NA_character_
  }
} else {
  cat("Ward boundaries not found; skipping spatial join\n")
  station_panel$ward_code <- NA_character_
}


# ------ 7. ward-year aggregation ------

crime_total_cols <- names(station_panel)[grepl("^total_", names(station_panel))]

ward_year <- station_panel |>
  filter(!is.na(ward_code)) |>
  group_by(ward_code, cal_year) |>
  summarise(
    n_stations = n_distinct(station),
    across(all_of(crime_total_cols), sum, na.rm = TRUE),
    .groups = "drop"
  )

cat(sprintf("\nWard-year panel: %s wards, %d years, %s rows\n",
            n_distinct(ward_year$ward_code),
            n_distinct(ward_year$cal_year),
            format(nrow(ward_year), big.mark = ",")))


# ------ 8. QoL wave alignment ------
# Map each QoL wave to the SAPS fiscal years that overlap its fieldwork

wave_fy_map <- tibble(
  wave       = c("II",    "III",   "IV",    "V",     "6",     "7"),
  wave_label = c("II",    "III",   "IV",    "V",     "6",     "7"),
  # QoL fieldwork spans these calendar years
  qol_start  = c(2011L,   2013L,   2015L,   2017L,   2020L,   2023L),
  qol_end    = c(2011L,   2014L,   2016L,   2018L,   2021L,   2024L)
)

# For each wave, average SAPS crime over the overlapping fiscal years
# (cal_year = fy_end, so cal_year 2017 = FY 2016/2017 = Apr 2016–Mar 2017)
ward_wave <- wave_fy_map |>
  rowwise() |>
  mutate(
    data = list(
      ward_year |>
        filter(cal_year >= qol_start, cal_year <= qol_end) |>
        group_by(ward_code) |>
        summarise(
          n_fy_covered  = n(),
          across(all_of(crime_total_cols), mean, na.rm = TRUE),
          .groups = "drop"
        )
    )
  ) |>
  ungroup() |>
  unnest(data) |>
  select(-qol_start, -qol_end)

cat(sprintf("Ward-wave panel: %s rows (%s wards × %d waves)\n",
            format(nrow(ward_wave), big.mark = ","),
            n_distinct(ward_wave$ward_code),
            n_distinct(ward_wave$wave)))


# ------ 9. validation ------

cat("\n--- Validation ---\n")

cat("\nStations per district:\n")
station_panel |>
  distinct(station, dc_mn) |>
  count(dc_mn, name = "n_stations") |>
  arrange(desc(n_stations)) |>
  print(n = 10)

cat("\nStation-years by calendar year:\n")
station_panel |>
  count(cal_year, name = "n_station_years") |>
  print(n = 25)

cat("\nWard-year crime totals (V1 primary, summary across all ward-years):\n")
ward_year |>
  summarise(
    wards    = n_distinct(ward_code),
    years    = n_distinct(cal_year),
    rows     = n(),
    V1_mean  = round(mean(total_V1_primary), 1),
    V1_sd    = round(sd(total_V1_primary), 1),
    V1_min   = min(total_V1_primary),
    V1_max   = max(total_V1_primary)
  ) |>
  print()

cat("\nWards with no station assignment:\n")
n_no_ward <- sum(is.na(station_panel$ward_code))
cat(sprintf("  %d station-years (%.1f%%) lack ward assignment\n",
            n_no_ward, 100 * n_no_ward / nrow(station_panel)))

cat("\nStations per ward (among assigned):\n")
station_panel |>
  filter(!is.na(ward_code)) |>
  distinct(station, ward_code) |>
  count(ward_code, name = "n_stations") |>
  summarise(
    mean = round(mean(n_stations), 2),
    sd   = round(sd(n_stations), 2),
    max  = max(n_stations),
    one_station = sum(n_stations == 1),
    multi_station = sum(n_stations > 1)
  ) |>
  print()


# ------ 10. save ------

write_parquet(station_panel, PATHS$saps_ward)
cat(sprintf("\nSaved station panel: %s (%s rows)\n",
            PATHS$saps_ward, format(nrow(station_panel), big.mark = ",")))

ward_year_path <- gsub("saps_crime_ward", "saps_crime_ward_year", PATHS$saps_ward)
write_parquet(ward_year, ward_year_path)
cat(sprintf("Saved ward-year panel: %s (%s rows)\n",
            ward_year_path, format(nrow(ward_year), big.mark = ",")))

ward_wave_path <- gsub("saps_crime_ward", "saps_crime_ward_wave", PATHS$saps_ward)
write_parquet(ward_wave, ward_wave_path)
cat(sprintf("Saved ward-wave panel: %s (%s rows)\n",
            ward_wave_path, format(nrow(ward_wave), big.mark = ",")))

cat("\n=== Done ===\n")

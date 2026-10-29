#!/usr/bin/env Rscript
# ============================================================
# 02_psc_exposure.R
# Compute PSC exposure measures at ward level from geocoded
# Property24 listings.
#
# Input:  data/cleaned/listings_geocoded.parquet
# Output: data/cleaned/psc_exposure_ward.parquet   (ward-year panel)
#         data/cleaned/psc_exposure_ea.parquet      (EA ring buffers)
#
# Ward-year panel:
#   For each QoL wave year, compute PSC share from listings whose
#   first_captured date falls on or before the survey midpoint.
#   Gated communities persist once built, so cumulative stock is
#   the right measure. This yields time-varying PSC exposure that
#   can be used with ward fixed effects.
#
# Also outputs a cross-sectional summary (all years pooled) for
# backwards compatibility.
# ============================================================

library(tidyverse)
library(arrow)
library(sf)
source(here::here("scripts", "cleaning", "merge", "00_config.R"))

listings <- read_parquet(PATHS$listings_file)
cat(sprintf("Loaded %s listings\n", nrow(listings)))

psc_col <- PSC_PARAMS$psc_col
stopifnot(psc_col %in% names(listings))

# parse dates
listings <- listings |>
  mutate(
    fc_date = as.Date(first_captured, format = "%Y%m%d"),
    fc_year = as.integer(format(fc_date, "%Y"))
  )

# keep geocoded residential listings only
geo <- listings |>
  filter(!is.na(lat), !is.na(lon), !is.na(fc_year))
cat(sprintf("Geocoded listings with date: %s\n", nrow(geo)))
cat(sprintf("Year range: %d - %d\n", min(geo$fc_year), max(geo$fc_year)))


# ======== LOAD WARD BOUNDARIES ========

ward_shp_path <- PATHS$wards_2016
gdb_dirs <- list.dirs(ward_shp_path, recursive = TRUE, full.names = TRUE)
gdb_dirs <- gdb_dirs[grepl("\\.gdb$", gdb_dirs)]
shp_files <- list.files(ward_shp_path, pattern = "\\.shp$",
                        full.names = TRUE, recursive = TRUE)
ward_shp_exists <- dir.exists(ward_shp_path) &&
  (length(gdb_dirs) > 0 || length(shp_files) > 0)

if (!ward_shp_exists) {
  stop("Ward boundary files not found at ", ward_shp_path,
       "\n  Download ward boundaries from Municipal Demarcation Board.")
}

cat("Loading ward boundaries (2016)...\n")
if (length(gdb_dirs) > 0) {
  layers <- st_layers(gdb_dirs[1])$name
  wards <- st_read(gdb_dirs[1], layer = layers[1], quiet = TRUE)
} else {
  wards <- st_read(shp_files[1], quiet = TRUE)
}
wards <- st_transform(wards, 4326)
cat(sprintf("Ward boundaries: %s features\n", nrow(wards)))

ward_id_col <- intersect(
  c("WardID", "WARD_ID", "WARDID", "WARD", "ward_code", "CAT_B",
    "WardNumber", "wardid", "ward_id"),
  names(wards)
)[1]
if (is.na(ward_id_col)) {
  stop("Cannot identify ward ID column in boundaries. Available: ",
       paste(names(wards), collapse = ", "))
}


# ======== SPATIAL JOIN: LISTINGS -> WARDS ========

cat("Spatial join: listings -> wards...\n")
pts <- st_as_sf(geo, coords = c("lon", "lat"), crs = 4326)
joined <- st_join(pts, wards[, ward_id_col], join = st_within) |>
  st_drop_geometry() |>
  rename(ward_code = !!ward_id_col) |>
  filter(!is.na(ward_code)) |>
  mutate(ward_code = as.character(ward_code))

cat(sprintf("Listings matched to wards: %s / %s (%.1f%%)\n",
            nrow(joined), nrow(geo), nrow(joined) / nrow(geo) * 100))


# ======== WARD-YEAR PANEL (cumulative stock) ========

# Define cutoff years: for each QoL wave, PSC stock is all listings
# first captured up to the survey midpoint year.
# Also include a full-sample (all-years) cross-section.
cutoff_years <- sort(unique(c(
  QOL_WAVES$year_start,
  max(geo$fc_year)           # full sample
)))
cat(sprintf("Computing PSC stock for cutoff years: %s\n",
            paste(cutoff_years, collapse = ", ")))

ward_year_list <- list()

for (cy in cutoff_years) {
  stock <- joined |>
    filter(fc_year <= cy) |>
    group_by(ward_code) |>
    summarise(
      n_listings     = n(),
      n_psc          = sum(.data[[psc_col]] == 1, na.rm = TRUE),
      psc_share      = n_psc / n_listings,
      n_estates      = sum(security_estate_v2 == 1, na.rm = TRUE),
      n_boom_gate    = sum(boom_gate_v2 == 1, na.rm = TRUE),
      .groups = "drop"
    ) |>
    mutate(year_start = cy)
  ward_year_list[[as.character(cy)]] <- stock
}

ward_year <- bind_rows(ward_year_list)
cat(sprintf("\nWard-year panel: %d rows (%d wards x %d years)\n",
            nrow(ward_year),
            n_distinct(ward_year$ward_code),
            n_distinct(ward_year$year_start)))

# Diagnostics
cat("\n--- Ward-year panel diagnostics ---\n")
ward_year |>
  group_by(year_start) |>
  summarise(
    n_wards = n(),
    mean_listings = round(mean(n_listings), 1),
    mean_psc = round(mean(n_psc), 1),
    mean_share = round(mean(psc_share), 4),
    wards_any_psc = sum(n_psc > 0),
    .groups = "drop"
  ) |>
  print(n = 20)

# Save ward-year panel
write_parquet(ward_year, PATHS$psc_ward)
cat(sprintf("\nSaved: %s\n", PATHS$psc_ward))


# ======== CROSS-SECTIONAL SUMMARY (backwards compat) ========
# Full pooled cross-section for use cases that don't need time variation
ward_xsec <- joined |>
  group_by(ward_code) |>
  summarise(
    n_listings     = n(),
    n_psc          = sum(.data[[psc_col]] == 1, na.rm = TRUE),
    psc_share      = n_psc / n_listings,
    n_estates      = sum(security_estate_v2 == 1, na.rm = TRUE),
    n_boom_gate    = sum(boom_gate_v2 == 1, na.rm = TRUE),
    first_listing  = min(fc_year),
    last_listing   = max(fc_year),
    .groups = "drop"
  )
# Save as a separate file so 05_compile can choose which to use
xsec_path <- here::here("data", "cleaned", "psc_exposure_ward_xsec.parquet")
write_parquet(ward_xsec, xsec_path)
cat(sprintf("Saved cross-section: %s (%d wards)\n", xsec_path, nrow(ward_xsec)))


# ======== EA-LEVEL EXPOSURE ========

ea_centroid_path <- here::here("data", "raw", "units", "statssa", "ea_centroids.csv")

if (file.exists(ea_centroid_path)) {
  cat("\nComputing EA-level ring exposure...\n")

  ea_centroids <- read_csv(ea_centroid_path, show_col_types = FALSE) |>
    filter(!is.na(lat), !is.na(lon))

  ea_pts <- st_as_sf(ea_centroids, coords = c("lon", "lat"), crs = 4326)
  listing_pts <- st_as_sf(geo, coords = c("lon", "lat"), crs = 4326)

  ea_utm <- st_transform(ea_pts, 32735)
  listing_utm <- st_transform(listing_pts, 32735)

  ring_results <- list()

  for (radius in PSC_PARAMS$ring_radii_m) {
    cat(sprintf("  Buffer radius: %sm\n", radius))
    buffers <- st_buffer(ea_utm, radius)
    counts <- st_join(buffers, listing_utm, join = st_contains) |>
      st_drop_geometry() |>
      group_by(ea_code) |>
      summarise(
        n_listings = sum(!is.na(.data[[psc_col]])),
        n_psc      = sum(.data[[psc_col]] == 1, na.rm = TRUE),
        .groups = "drop"
      ) |>
      mutate(
        psc_share = ifelse(n_listings >= PSC_PARAMS$min_listings,
                           n_psc / n_listings, NA_real_),
        radius_m  = radius
      )
    ring_results[[as.character(radius)]] <- counts
  }

  ea_exposure <- bind_rows(ring_results) |>
    mutate(ea_code = as.character(ea_code))

  write_parquet(ea_exposure, PATHS$psc_ea)
  cat(sprintf("Saved: %s (%s rows)\n", PATHS$psc_ea, nrow(ea_exposure)))

} else {
  cat("\nNOTE: EA centroids not found at ", ea_centroid_path, "\n")
  cat("  EA-level exposure skipped.\n")

  stub <- tibble(
    ea_code = character(), n_listings = integer(), n_psc = integer(),
    psc_share = double(), radius_m = double()
  )
  write_parquet(stub, PATHS$psc_ea)
  cat("Saved empty EA exposure stub\n")
}

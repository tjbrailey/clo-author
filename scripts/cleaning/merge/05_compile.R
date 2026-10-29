#!/usr/bin/env Rscript
# ============================================================
# 05_compile.R
# Join all intermediate datasets into analysis-ready files.
#
# Outputs:
#   data/cleaned/analysis_qol.parquet  — QoL panel + PSC + SAPS
#   data/cleaned/analysis_ab.parquet   — Afrobarometer cross-section + PSC
#
# To add variables: update 00_config.R and re-run the relevant
# upstream script, then re-run this file.
# ============================================================

library(tidyverse)
library(arrow)
source(here::here("scripts", "cleaning", "merge", "00_config.R"))


# ------ load intermediates ------

qol  <- read_parquet(PATHS$qol_harmonized)
psc_w <- read_parquet(PATHS$psc_ward)
saps <- read_parquet(PATHS$saps_ward)
saps_full <- if (file.exists(PATHS$saps_ward_wave_full)) {
  read_parquet(PATHS$saps_ward_wave_full)
} else NULL
ab   <- read_parquet(PATHS$ab_clean)

cat("Loaded intermediates:\n")
cat(sprintf("  QoL harmonized: %s rows\n", nrow(qol)))
cat(sprintf("  PSC ward:       %s wards\n", nrow(psc_w)))
cat(sprintf("  SAPS:           %s rows\n", nrow(saps)))
if (!is.null(saps_full)) {
  cat(sprintf("  SAPS full:      %s rows (%s wards)\n",
              nrow(saps_full), n_distinct(saps_full$ward_code)))
}
cat(sprintf("  AB R9:          %s rows\n", nrow(ab)))


# ======== QoL ANALYSIS DATASET ========

analysis_qol <- qol

# ---- merge PSC ward exposure (ward-year panel) ----
if (nrow(psc_w) > 0 && "ward_code" %in% names(psc_w)) {
  psc_w <- psc_w |> mutate(ward_code = as.character(ward_code))

  if ("year_start" %in% names(psc_w)) {
    # Ward-year panel: join on ward_code + year_start (cumulative stock)
    psc_w <- psc_w |> mutate(year_start = as.integer(year_start))
    analysis_qol <- analysis_qol |>
      left_join(psc_w, by = c("ward_code", "year_start"), suffix = c("", "_psc"))
    cat(sprintf("  QoL+PSC (ward-year): %s rows matched\n",
                sum(!is.na(analysis_qol$psc_share))))
  } else {
    # Fallback: cross-sectional (no year_start in PSC file)
    analysis_qol <- analysis_qol |>
      left_join(psc_w, by = "ward_code", suffix = c("", "_psc"))
    cat(sprintf("  QoL+PSC (cross-section): %s rows matched ward\n",
                sum(!is.na(analysis_qol$psc_share))))
  }
} else {
  cat("  PSC ward exposure empty; skipping merge\n")
  analysis_qol$n_listings <- NA_integer_
  analysis_qol$n_psc      <- NA_integer_
  analysis_qol$psc_share  <- NA_real_
}

# ---- merge SAPS crime ----
# Prefer precinct-based full panel (542 wards) over station-within (133 wards)
if (!is.null(saps_full) && nrow(saps_full) > 0) {
  saps_full <- saps_full |> mutate(ward_code = as.character(ward_code))
  total_cols <- names(saps_full)[grepl("^total_", names(saps_full))]
  analysis_qol <- analysis_qol |>
    left_join(saps_full, by = c("ward_code", "wave"), suffix = c("", "_saps"))
  cat(sprintf("  QoL+SAPS (precinct-based): %s rows matched ward-wave\n",
              sum(!is.na(analysis_qol$n_fy_covered))))
} else if (nrow(saps) > 0 && "ward_code" %in% names(saps)) {
  saps <- saps |> mutate(
    ward_code = as.character(ward_code),
    saps_year = suppressWarnings(as.integer(substr(year, 1, 4)))
  )
  total_cols <- names(saps)[grepl("^total_", names(saps))]
  saps_ward_yr <- saps |>
    filter(!is.na(ward_code)) |>
    group_by(ward_code, saps_year) |>
    summarise(across(all_of(total_cols), \(x) sum(x, na.rm = TRUE)),
              n_stations = n(),
              .groups = "drop")
  analysis_qol <- analysis_qol |>
    left_join(saps_ward_yr, by = c("ward_code", "year_start" = "saps_year"),
              suffix = c("", "_saps"))
  cat(sprintf("  QoL+SAPS (station-within): %s rows matched ward-year\n",
              sum(!is.na(analysis_qol$n_stations))))
} else {
  cat("  SAPS ward-level empty; skipping merge\n")
}

# ---- treatment indicator (binary PSC exposure) ----
analysis_qol <- analysis_qol |>
  mutate(
    psc_treated = case_when(
      is.na(psc_share)  ~ NA,
      psc_share > 0     ~ TRUE,
      TRUE              ~ FALSE
    ),
    psc_high = case_when(
      is.na(psc_share)  ~ NA,
      psc_share > median(psc_share[psc_share > 0], na.rm = TRUE) ~ TRUE,
      TRUE              ~ FALSE
    )
  )


# ------ save QoL analysis dataset ------

write_parquet(analysis_qol, PATHS$analysis_qol)
cat(sprintf("\nSaved: %s (%s rows, %s cols)\n",
            PATHS$analysis_qol, nrow(analysis_qol), ncol(analysis_qol)))


# ======== AFROBAROMETER ANALYSIS DATASET ========

analysis_ab <- ab

# ---- merge PSC ward exposure (cross-section for AB) ----
# AB R9 is a single wave — use cross-sectional PSC or latest year from panel
if (nrow(psc_w) > 0 && "ward_code" %in% names(analysis_ab)) {
  if ("year_start" %in% names(psc_w)) {
    # Use the full-sample (max year) cross-section from the panel
    psc_ab <- psc_w |>
      filter(year_start == max(year_start)) |>
      select(-year_start)
  } else {
    psc_ab <- psc_w
  }
  analysis_ab <- analysis_ab |>
    left_join(psc_ab, by = "ward_code", suffix = c("", "_psc"))
  cat(sprintf("  AB+PSC ward: %s matched\n",
              sum(!is.na(analysis_ab$psc_share))))
}

# ---- PSC ring exposure from GPS ----
# If EA-level PSC exposure exists and AB has GPS, compute
# nearest-EA match or direct ring counts.
psc_ea_path <- PATHS$psc_ea
if (file.exists(psc_ea_path)) {
  psc_ea <- read_parquet(psc_ea_path)
  if (nrow(psc_ea) > 0) {
    cat("  EA-level PSC exposure available for AB GPS merge\n")
    # This requires a spatial nearest-neighbour join.
    # For now, flag that it's available; implementation depends
    # on whether AB ea_codes overlap with Census EA codes.
    # TODO: spatial nn-join AB GPS → PSC ring exposure
  }
}

# ---- merge SAPS crime to AB wards ----
# AB R9 fielded 2022 -> closest wave is "7" (2023-24) or use year-level
if (!is.null(saps_full) && nrow(saps_full) > 0) {
  saps_ab <- saps_full |>
    filter(wave == "7") |>
    mutate(ward_code = as.character(ward_code)) |>
    select(-wave, -n_fy_covered)
  analysis_ab <- analysis_ab |>
    left_join(saps_ab, by = "ward_code", suffix = c("", "_saps"))
  cat(sprintf("  AB+SAPS (precinct-based, wave 7): %s matched\n",
              sum(!is.na(analysis_ab[[names(saps_ab)[2]]]))))
} else if (nrow(saps) > 0 && "ward_code" %in% names(saps)) {
  saps_2021 <- saps |>
    filter(!is.na(ward_code)) |>
    mutate(
      ward_code = as.character(ward_code),
      saps_year = suppressWarnings(as.integer(substr(year, 1, 4)))
    ) |>
    filter(saps_year == 2021) |>
    group_by(ward_code) |>
    summarise(across(all_of(total_cols), \(x) sum(x, na.rm = TRUE)),
              .groups = "drop")
  analysis_ab <- analysis_ab |>
    left_join(saps_2021, by = "ward_code", suffix = c("", "_saps"))
  cat(sprintf("  AB+SAPS (station-within): %s matched\n",
              sum(!is.na(analysis_ab[[total_cols[1]]]))))
}

# ---- treatment indicators ----
analysis_ab <- analysis_ab |>
  mutate(
    psc_treated = case_when(
      is.na(psc_share)  ~ NA,
      psc_share > 0     ~ TRUE,
      TRUE              ~ FALSE
    )
  )


# ------ save AB analysis dataset ------

write_parquet(analysis_ab, PATHS$analysis_ab)
cat(sprintf("Saved: %s (%s rows, %s cols)\n",
            PATHS$analysis_ab, nrow(analysis_ab), ncol(analysis_ab)))


# ======== FINAL DIAGNOSTICS ========

cat("\n========================================\n")
cat("MERGE PIPELINE COMPLETE\n")
cat("========================================\n\n")

cat("QoL analysis dataset:\n")
cat(sprintf("  Rows: %s | Wards: %s | EA waves: V/6/7\n",
            nrow(analysis_qol),
            n_distinct(analysis_qol$ward_code, na.rm = TRUE)))
cat(sprintf("  PSC coverage: %s%% of rows have psc_share\n",
            round(mean(!is.na(analysis_qol$psc_share)) * 100, 1)))

cat("\nAfrobarometer analysis dataset:\n")
cat(sprintf("  Rows: %s | Gauteng: %s\n",
            nrow(analysis_ab),
            sum(analysis_ab$in_gauteng, na.rm = TRUE)))
cat(sprintf("  PSC coverage: %s%% have psc_share\n",
            round(mean(!is.na(analysis_ab$psc_share)) * 100, 1)))

cat("\nOutput files:\n")
cat(sprintf("  %s\n", PATHS$analysis_qol))
cat(sprintf("  %s\n", PATHS$analysis_ab))

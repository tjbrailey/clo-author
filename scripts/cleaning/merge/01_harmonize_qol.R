#!/usr/bin/env Rscript
# ============================================================
# 01_harmonize_qol.R
# Read all QoL waves, standardize variable names and scales,
# stack into one long dataset.
#
# Input:  CSV files in data/raw/qol/ (one per wave)
# Output: data/cleaned/qol_harmonized.parquet
#
# Geography: ward_code (all waves I-7), ea_code (V/6/7 only)
# Outcomes:  governed by QOL_VARMAP in 00_config.R
#
# Wave I (2009) uses 2006-era ward codes. Non-metro codes that appear
# in the 2016 ward list are kept; the rest are mapped via the
# 2011-to-2016 concordance where possible. Metro wards that can't be
# matched (need 2006 boundaries from MDB) are set to NA.
# ============================================================

library(tidyverse)
library(arrow)
source(here::here("scripts", "cleaning", "merge", "00_config.R"))

# ------ ward concordance (pre-2016 → 2016) ------

build_ward_2016_set <- function() {
  gdb_path <- here::here("data", "raw", "units", "mdb", "wards_2016", "MDBWard2016.gdb")
  if (dir.exists(gdb_path)) {
    w16 <- sf::st_read(gdb_path, quiet = TRUE)
    unique(as.character(w16$WardID))
  } else {
    character(0)
  }
}

load_concordance_2011_2016 <- function() {
  conc_path <- here::here("data", "cleaned", "ward_concordance_2011_2016.parquet")
  if (file.exists(conc_path)) {
    read_parquet(conc_path)
  } else {
    NULL
  }
}

WARD_2016_SET <- build_ward_2016_set()
CONC_2011_2016 <- load_concordance_2011_2016()

concordance_to_2016 <- function(ward_codes, from_demarcation) {
  result <- rep(NA_character_, length(ward_codes))

  direct <- ward_codes %in% WARD_2016_SET
  result[direct] <- ward_codes[direct]

  remaining <- !direct & !is.na(ward_codes)
  if (any(remaining) && !is.null(CONC_2011_2016)) {
    conc <- CONC_2011_2016 |>
      group_by(ward_2011) |>
      slice_max(weight, n = 1, with_ties = FALSE) |>
      ungroup()
    lookup <- setNames(conc$ward_2016, conc$ward_2011)
    mapped <- lookup[ward_codes[remaining]]
    result[remaining] <- unname(mapped)
  }

  cat(sprintf("    Direct 2016 match: %s | Via concordance: %s | Unmapped: %s\n",
              sum(direct, na.rm = TRUE),
              sum(!is.na(result) & !direct & !is.na(ward_codes)),
              sum(is.na(result) & !is.na(ward_codes))))
  result
}


# ------ read one wave ------

read_qol_wave <- function(wave_id) {

  meta <- QOL_WAVES |> filter(wave == wave_id)
  stopifnot(nrow(meta) == 1)

  fpath <- file.path(PATHS$qol_dir, meta$file)
  stopifnot(file.exists(fpath))

  geo <- QOL_GEO |> filter(wave == wave_id)

  # read raw (Wave I uses latin-1 encoding)
  enc <- if (!is.null(meta$encoding) && !is.na(meta$encoding)) meta$encoding else "UTF-8"
  raw <- read_csv(fpath, show_col_types = FALSE, guess_max = 5000,
                  locale = locale(encoding = enc))
  cat(sprintf("  Wave %s: %s rows, %s cols\n", wave_id, nrow(raw), ncol(raw)))

  # ---- geography ----
  out <- tibble(.rows = nrow(raw))
  out$wave       <- wave_id
  out$year_start <- meta$year_start
  out$year_end   <- meta$year_end

  # ward (apply concordance for pre-2016 demarcations)
  if (!is.na(geo$ward_col) && geo$ward_col %in% names(raw)) {
    raw_ward <- as.character(raw[[geo$ward_col]])

    if (!is.null(geo$ward_demarcation) && !is.na(geo$ward_demarcation) &&
        geo$ward_demarcation != "2016") {
      out$ward_code <- concordance_to_2016(raw_ward, geo$ward_demarcation)
      n_mapped <- sum(!is.na(out$ward_code))
      cat(sprintf("    Ward concordance (%s->2016): %s/%s mapped (%.1f%%)\n",
                  geo$ward_demarcation, n_mapped, length(raw_ward),
                  n_mapped / length(raw_ward) * 100))
    } else {
      out$ward_code <- raw_ward
    }
  } else {
    out$ward_code <- NA_character_
  }

  # ea
  if (!is.na(geo$ea_col) && geo$ea_col %in% names(raw)) {
    out$ea_code <- as.character(raw[[geo$ea_col]])
  } else {
    out$ea_code <- NA_character_
  }

  # municipality
  if (!is.na(geo$munic_col) && geo$munic_col %in% names(raw)) {
    out$municipality <- as.character(raw[[geo$munic_col]])
  } else {
    out$municipality <- NA_character_
  }

  # interview date
  dmeta <- QOL_DATE |> filter(wave == wave_id)
  out$interview_date <- as.Date(NA)
  if (nrow(dmeta) == 1 && dmeta$col %in% names(raw)) {
    out$interview_date <- withr::with_locale(c(LC_TIME = "C"),
      as.Date(trimws(as.character(raw[[dmeta$col]])), format = dmeta$format))
    cat(sprintf("    Interview date parsed: %.1f%% (%s to %s)\n",
                mean(!is.na(out$interview_date)) * 100,
                min(out$interview_date, na.rm = TRUE), max(out$interview_date, na.rm = TRUE)))
  }

  # weight
  if (!is.na(geo$weight_col) && geo$weight_col %in% names(raw)) {
    out$weight <- as.numeric(raw[[geo$weight_col]])
  } else {
    out$weight <- NA_real_
  }

  # ---- outcome/control variables from VARMAP ----
  vars_this_wave <- QOL_VARMAP |> filter(wave == wave_id)

  for (i in seq_len(nrow(vars_this_wave))) {
    row <- vars_this_wave[i, ]
    if (row$raw_col %in% names(raw)) {
      out[[row$harmonized]] <- apply_recode(raw[[row$raw_col]], row$recode)
    } else {
      warning(sprintf("Wave %s: column '%s' not found (mapped to '%s')",
                      wave_id, row$raw_col, row$harmonized))
      # still create the column as NA so rbind works
      out[[row$harmonized]] <- NA
    }
  }

  out
}


# ------ stack all waves ------

cat("Reading QoL waves...\n")
all_waves <- map(QOL_WAVES$wave, read_qol_wave)

# align columns before binding (waves have different variable coverage)
all_cols <- unique(unlist(map(all_waves, names)))
align_cols <- function(df) {
  missing <- setdiff(all_cols, names(df))
  for (col in missing) df[[col]] <- NA
  df[all_cols]
}

qol <- bind_rows(map(all_waves, align_cols))

cat(sprintf("\nStacked QoL: %s rows, %s columns\n", nrow(qol), ncol(qol)))
cat("Rows by wave:\n")
print(table(qol$wave))


# ------ diagnostics ------

outcome_cols <- unique(QOL_VARMAP$harmonized)
cat("\n--- Variable coverage by wave ---\n")
coverage <- qol |>
  group_by(wave) |>
  summarise(
    n = n(),
    across(all_of(outcome_cols), ~sum(!is.na(.x)), .names = "n_{.col}"),
    .groups = "drop"
  )
print(as.data.frame(coverage))

cat("\n--- Geography coverage ---\n")
geo_summary <- qol |>
  group_by(wave) |>
  summarise(
    n = n(),
    pct_ward = mean(!is.na(ward_code)) * 100,
    n_wards  = n_distinct(ward_code, na.rm = TRUE),
    pct_ea   = mean(!is.na(ea_code)) * 100,
    n_eas    = n_distinct(ea_code, na.rm = TRUE),
    .groups = "drop"
  )
print(as.data.frame(geo_summary))

cat("\n--- sat_gov_security distribution by wave ---\n")
qol |>
  filter(!is.na(sat_gov_security)) |>
  group_by(wave) |>
  summarise(
    n    = n(),
    mean = round(mean(sat_gov_security), 2),
    sd   = round(sd(sat_gov_security), 2),
    .groups = "drop"
  ) |>
  print()


# ------ save ------

write_parquet(qol, PATHS$qol_harmonized)
cat(sprintf("\nSaved: %s (%s rows)\n", PATHS$qol_harmonized, nrow(qol)))

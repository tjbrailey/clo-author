#!/usr/bin/env Rscript
# ============================================================
# 04_afrobarometer.R
# Harmonize Afrobarometer Round 9 (South Africa) for merge.
#
# Input:  data/raw/afrobarometer/...sav (SPSS format)
# Output: data/cleaned/ab_r9_clean.parquet
#
# Keeps GPS, ward, trust/safety/police outcomes, demographics.
# Labels converted to numeric scales matching QoL where possible.
# ============================================================

library(tidyverse)
library(arrow)
library(haven)
source(here::here("scripts", "cleaning", "merge", "00_config.R"))


# ------ read ------

raw <- read_sav(PATHS$ab_file)
cat(sprintf("Afrobarometer R9: %s rows, %s cols\n", nrow(raw), ncol(raw)))


# ------ select and rename ------

# build rename vector from AB_VARMAP
rename_vec <- setNames(AB_VARMAP$raw_col, AB_VARMAP$harmonized)

# check which columns exist
missing <- setdiff(AB_VARMAP$raw_col, names(raw))
if (length(missing) > 0) {
  cat("WARNING: columns not found in AB data:\n")
  cat(paste(" ", missing, collapse = "\n"), "\n")
  # keep only mappable columns
  keep <- AB_VARMAP$raw_col %in% names(raw)
  rename_vec <- rename_vec[keep]
}

ab <- raw |>
  select(all_of(unname(rename_vec))) |>
  rename(!!!rename_vec)

cat(sprintf("Selected %s variables\n", ncol(ab)))


# ------ convert haven_labelled to values ------

# haven_labelled columns: extract numeric codes (the underlying values)
# For Likert items this gives the numeric scale directly.
# For text labels we'd need zap_labels + manual recode, but AB
# uses numeric codes with value labels.

ab <- ab |>
  mutate(across(where(is.labelled), ~as.numeric(zap_labels(.x))))


# ------ recode missing/refused/don't know ------

# AB convention: -1 = Missing, 9 = Don't know, 998 = Refused, 8 = Refused
# for 0-4 scales. Specifics vary by question. Set all negative and
# conventional missing codes to NA.

recode_ab_missing <- function(x) {
  ifelse(x < 0 | x %in% c(7, 8, 9, 98, 99, 998, 999, -1), NA_real_, x)
}

# apply to non-geography, non-demographic columns
outcome_cols <- AB_VARMAP |>
  filter(!family %in% c("geography", "demographic")) |>
  pull(harmonized) |>
  intersect(names(ab))

ab <- ab |>
  mutate(across(all_of(outcome_cols), recode_ab_missing))


# ------ geography ------

# GPS coordinates
ab <- ab |>
  mutate(
    ea_lat    = as.numeric(ea_lat),
    ea_lon    = as.numeric(ea_lon),
    ward_code = as.character(ward_code),
    district  = as.character(district)
  )

# filter to Gauteng respondents (for QoL merge compatibility)
# keep all respondents but flag Gauteng
gauteng_districts <- c(
  "city of johannesburg", "city of tshwane", "ekurhuleni",
  "sedibeng", "west rand"
)

ab <- ab |>
  mutate(
    in_gauteng = tolower(trimws(district)) %in% gauteng_districts |
      (!is.na(ea_lat) & ea_lat > -27.0 & ea_lat < -25.0 &
       ea_lon > 27.0 & ea_lon < 29.5)
  )

cat(sprintf("Gauteng respondents: %s / %s\n",
            sum(ab$in_gauteng, na.rm = TRUE), nrow(ab)))


# ------ diagnostics ------

cat("\n--- Key outcome distributions ---\n")

for (v in c("trust_police", "trust_local_council", "unsafe_walking",
            "ea_private_security_roadblock", "handling_crime")) {
  if (v %in% names(ab)) {
    vals <- ab[[v]]
    cat(sprintf("  %s: n=%s, mean=%.2f, range=[%s, %s]\n",
                v, sum(!is.na(vals)),
                mean(vals, na.rm = TRUE),
                min(vals, na.rm = TRUE),
                max(vals, na.rm = TRUE)))
  }
}

cat(sprintf("\nGPS coverage: %s / %s have coordinates\n",
            sum(!is.na(ab$ea_lat)), nrow(ab)))
cat(sprintf("Unique EAs (by GPS): %s\n",
            n_distinct(paste(ab$ea_lat, ab$ea_lon), na.rm = TRUE)))
cat(sprintf("Unique wards: %s\n", n_distinct(ab$ward_code, na.rm = TRUE)))


# ------ save ------

write_parquet(ab, PATHS$ab_clean)
cat(sprintf("\nSaved: %s (%s rows)\n", PATHS$ab_clean, nrow(ab)))

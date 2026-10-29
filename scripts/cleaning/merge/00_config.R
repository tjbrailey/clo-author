#!/usr/bin/env Rscript
# ============================================================
# 00_config.R
# Central configuration for the merge pipeline.
# Sources: QoL (GCRO), Afrobarometer, SAPS crime, Property24 scrape.
#
# To add a variable:
#   1. Add a row to the appropriate VARMAP table below
#   2. If recoding is needed, add a case in the recode function
#   3. Re-run 05_compile.R
# ============================================================

library(here)

# ------ paths ------

PATHS <- list(
  # raw inputs
  qol_dir       = here("data", "raw", "qol"),
  ab_file       = here("data", "raw", "afrobarometer",
                        "SOUTHAFRICA_R9.data.final.wtd_release.local_info.30May23.sav"),
  saps_file     = here("data", "raw", "saps_crime", "sapacr-2005-2026-v1.5.csv"),
  listings_file = here("data", "cleaned", "listings_geocoded.parquet"),

  # boundaries
  wards_2011    = here("data", "raw", "units", "mdb", "wards_2011"),
  wards_2016    = here("data", "raw", "units", "mdb", "wards_2016"),
  wards_2021    = here("data", "raw", "units", "mdb", "wards_2021"),
  saps_bnd      = here("data", "raw", "units", "saps"),
  police_dist   = here("data", "raw", "units", "statssa", "PoliceDistrict_2025"),

  # intermediate outputs (one per step)
  qol_harmonized  = here("data", "cleaned", "qol_harmonized.parquet"),
  psc_ward        = here("data", "cleaned", "psc_exposure_ward.parquet"),
  psc_ea          = here("data", "cleaned", "psc_exposure_ea.parquet"),
  saps_ward       = here("data", "cleaned", "saps_crime_ward.parquet"),
  saps_ward_wave_full = here("data", "cleaned", "saps_crime_ward_wave_full.parquet"),
  ab_clean        = here("data", "cleaned", "ab_r9_clean.parquet"),


  # final analysis datasets
  analysis_qol    = here("data", "cleaned", "analysis_qol.parquet"),
  analysis_ab     = here("data", "cleaned", "analysis_ab.parquet")
)


# ------ QoL wave metadata ------

QOL_WAVES <- data.frame(
  wave       = c(     "I",    "II",    "III",     "IV",      "V",       "6",       "7"),
  year_start = c(   2009L,   2011L,   2013L,    2015L,    2017L,     2020L,     2023L),
  year_end   = c(   2009L,   2011L,   2014L,    2016L,    2018L,     2021L,     2024L),
  file       = c(
    "gcro-qlf-2009-v1.1-20011209-s10.csv",
    "gcro 2011_28feb12nogis-v1-s10.csv",
    "qol-iii-2013-2014-v1.csv",
    "qol-iv-2014-2015-v1.csv",
    "qols-v-2017-2018-v2.csv",
    "qols-2020-2021-new-weights-v1.csv",
    "qols-2023-2024.csv"
  ),
  has_ea     = c( FALSE,    FALSE,    FALSE,     FALSE,     TRUE,      TRUE,      TRUE),
  encoding   = c("Latin1",    NA,       NA,        NA,        NA,        NA,        NA),
  stringsAsFactors = FALSE
)


# ------ QoL variable mapping ------
# Each row: harmonized name, wave, raw column name, recode method.
# recode methods:
#   "numeric"    = already 1-5 numeric, use as-is
#   "sat5_text"  = text labels ("Very dissatisfied" .. "Very satisfied") -> 1-5
#   "safe5_text" = text labels ("Very unsafe" .. "Very safe") -> 1-5
#   "yn_text"    = "Yes"/"No" -> 1/0
#   "crime3_text"= "Got worse"/"Stayed the same"/"Got better" -> -1/0/1
#   "trust_text" = "Distrust"/"Neither"/"Trust" (or finer) -> numeric
#   "binary01"   = already 0/1
#   "multiselect_item" = multi-select battery: -1 -> 0 (not selected), positive -> 1 (selected)
#   "crime3_numeric" = numeric 1/2/3 -> 1/0/-1 (improved/same/worse)
#   "safe5_reverse"  = numeric 1-5 reversed via 6-x (1=safe->5=unsafe becomes 1=unsafe->5=safe)
#   "index"      = continuous index, use as-is
#   "factor"     = keep as factor (for demographics)
#   "none"       = pass through unchanged

QOL_VARMAP <- data.frame(
  harmonized = character(),
  wave       = character(),
  raw_col    = character(),
  recode     = character(),
  family     = character(),
  stringsAsFactors = FALSE
)

# Helper to add rows compactly
add_var <- function(harmonized, wave, raw_col, recode, family) {
  data.frame(harmonized = harmonized, wave = wave, raw_col = raw_col,
             recode = recode, family = family, stringsAsFactors = FALSE)
}

QOL_VARMAP <- rbind(QOL_VARMAP,
  # ---- F1a: satisfaction with government safety/security (1-5) ----
  # Wave I has no security-specific satisfaction question; Q5_5/6/7 are general govt sat
  add_var("sat_gov_security", "III", "X9_12",               "numeric",   "F1_performance"),
  add_var("sat_gov_security", "IV",  "Q9_6",                "numeric",   "F1_performance"),
  add_var("sat_gov_security", "V",   "Q12.06_security_reside", "numeric","F1_performance"),
  add_var("sat_gov_security", "6",   "q11_6_gov_security",  "sat5_text", "F1_performance"),
  add_var("sat_gov_security", "7",   "q11_6_gov_security",  "sat5_text", "F1_performance"),

  # ---- F4: safety perceptions ----
  add_var("safe_day",         "I",   "Q8_3",                 "safe5_reverse", "F4_safety"),
  add_var("safe_day",         "III", "X9_9",                 "safe5_reverse", "F4_safety"),
  add_var("safe_day",         "IV",  "Q9_3",                 "safe5_reverse", "F4_safety"),
  add_var("safe_day",         "V",   "Q12.03_day",           "safe5_reverse", "F4_safety"),
  add_var("safe_day",         "6",   "q11_3_daytime_safety", "safe5_text",    "F4_safety"),
  add_var("safe_day",         "7",   "q11_3_daytime_safety", "safe5_text",    "F4_safety"),
  add_var("safe_night",       "I",   "Q8_4",                 "safe5_reverse", "F4_safety"),
  add_var("safe_night",       "III", "X9_10",                "safe5_reverse", "F4_safety"),
  add_var("safe_night",       "IV",  "Q9_4",                 "safe5_reverse", "F4_safety"),
  add_var("safe_night",       "V",   "Q12.04_night",         "safe5_reverse", "F4_safety"),
  add_var("safe_night",       "6",   "q11_4_night_safety",   "safe5_text",    "F4_safety"),
  add_var("safe_night",       "7",   "q11_4_night_safety",   "safe5_text",    "F4_safety"),
  add_var("safe_home",        "I",   "Q8_5",                 "safe5_reverse", "F4_safety"),
  add_var("safe_home",        "III", "X9_11",                "safe5_reverse", "F4_safety"),
  add_var("safe_home",        "IV",  "Q9_5",                 "safe5_reverse", "F4_safety"),
  add_var("safe_home",        "V",   "Q12.05_home",          "safe5_reverse", "F4_safety"),
  add_var("safe_home",        "6",   "q11_5_home_safety",    "safe5_text",    "F4_safety"),
  add_var("safe_home",        "7",   "q11_5_home_safety",    "safe5_text",    "F4_safety"),
  add_var("safety_index",     "V",   "F6safety",             "index",      "F4_safety"),
  add_var("safety_index",     "6",   "F6safety",             "index",      "F4_safety"),
  add_var("safety_index",     "7",   "F6safety",             "index",      "F4_safety"),

  # ---- F2: trust ----
  add_var("trust_gov",        "6",   "q7_11_gov_trust",     "trust_text", "F2_trust"),
  add_var("trust_gov",        "7",   "q7_11_gov_trust",     "trust_text", "F2_trust"),
  add_var("trust_community",  "6",   "q4_3_community_trust","trust_binary", "F2_trust"),
  add_var("trust_community",  "7",   "q4_3_community_trust","trust_binary", "F2_trust"),

  # ---- F4: crime/victimisation ----
  add_var("crime_victim",     "I",   "Q8_2",                "yn_num12",       "F4_safety"),
  add_var("crime_victim",     "III", "X9_8",                "binary01",       "F4_safety"),
  add_var("crime_victim",     "IV",  "Q9_2",                "binary01",       "F4_safety"),
  add_var("crime_victim",     "V",   "Q12.02_victim",       "binary01",       "F4_safety"),
  add_var("crime_victim",     "6",   "q11_2_crime_victim",  "yn_text",        "F4_safety"),
  add_var("crime_victim",     "7",   "q11_2_crime_victim",  "yn_text",        "F4_safety"),
  add_var("crime_direction",  "I",   "Q8_1",                "crime3_numeric", "F4_safety"),
  add_var("crime_direction",  "III", "X9_7",                "crime3_numeric", "F4_safety"),
  add_var("crime_direction",  "IV",  "Q9_1",                "crime3_numeric", "F4_safety"),
  add_var("crime_direction",  "V",   "Q12.01_crime",        "crime3_numeric", "F4_safety"),
  add_var("crime_direction",  "6",   "q11_1_crime",         "crime3_text",    "F4_safety"),
  add_var("crime_direction",  "7",   "q11_1_crime",         "crime3_text",    "F4_safety"),

  # ---- F3: civic participation ----
  add_var("cpf_attend",       "III", "X6_4_7",              "multiselect_item", "F3_reliance"),
  add_var("cpf_attend",       "IV",  "Q6_4_7",              "binary01",   "F3_reliance"),
  add_var("cpf_attend",       "6",   "q12_2_7_cpf",         "yn_text",    "F3_reliance"),
  add_var("cpf_attend",       "7",   "q12_2_7_cpf",         "yn_text",    "F3_reliance"),

  # ---- D1: sex/gender → female (binary 0/1) ----
  add_var("female",          "I",   "A19",                  "sex_num",    "demographic"),
  add_var("female",          "II",  "Sex",                  "sex_num",    "demographic"),
  add_var("female",          "V",   "A2_Sex",               "sex_num",    "demographic"),
  add_var("female",          "6",   "a2_sex",               "sex_text",   "demographic"),
  add_var("female",          "7",   "a2_sex",               "sex_text",   "demographic"),

  # ---- D2: population group / race (factor) ----
  add_var("pop_group",       "I",   "A18",                  "race_num4",  "demographic"),
  add_var("pop_group",       "II",  "Race",                 "race_num4",  "demographic"),
  add_var("pop_group",       "V",   "A1_Pop_group",         "race_num_v5","demographic"),
  add_var("pop_group",       "6",   "a1_pop_group",         "race_text",  "demographic"),
  add_var("pop_group",       "7",   "a1_pop_group",         "race_text",  "demographic"),

  # ---- D3: age (continuous) ----
  add_var("age",             "I",   "A3",                   "numeric",    "demographic"),
  add_var("age",             "V",   "Q15.02_age",           "numeric",    "demographic"),
  add_var("age",             "6",   "q14_2_age_topcode",    "numeric",    "demographic"),
  add_var("age",             "7",   "q14_2_age_topcode",    "numeric",    "demographic"),

  # ---- D4: education level (ordinal 1-4) ----
  add_var("educ_level",      "I",   "Educ",                 "educ_w1",    "demographic"),
  add_var("educ_level",      "II",  "Education",            "educ_w2",    "demographic"),
  add_var("educ_level",      "V",   "Q15.01_education_recode", "educ_w5","demographic"),
  add_var("educ_level",      "6",   "q14_1_education_recode","educ_text", "demographic"),
  add_var("educ_level",      "7",   "q14_1_education_recode","educ_text", "demographic"),

  # ---- D5: dwelling type (formal = 1) ----
  add_var("dwelling_formal", "I",   "Housing",              "dwelling_num","demographic"),
  add_var("dwelling_formal", "II",  "DwellingType",         "dwelling_num","demographic"),
  add_var("dwelling_formal", "IV",  "Q1_Recode_Dwelling",   "dwelling_num","demographic"),
  add_var("dwelling_formal", "V",   "A3_dwelling_recode",   "dwelling_num","demographic"),
  add_var("dwelling_formal", "6",   "a3_dwelling_type_recode","dwelling_text","demographic"),
  add_var("dwelling_formal", "7",   "a3_dwelling_type_recode","dwelling_text","demographic"),

  # ---- D6: unemployed (binary 0/1) ----
  add_var("unemployed",      "I",   "Empl",                 "employ_w1",  "demographic"),
  add_var("unemployed",      "III", "employment_status",    "employ_w3",  "demographic"),
  add_var("unemployed",      "IV",  "Employment_Status",    "employ_w4",  "demographic"),
  add_var("unemployed",      "V",   "Q11.20_employment",    "employ_w5",  "demographic"),
  add_var("unemployed",      "6",   "q10_4_unemployed",     "yn_text",    "demographic"),
  add_var("unemployed",      "7",   "q10_4_unemployed",     "yn_text",    "demographic"),

  # ---- Geography (always extracted, not from VARMAP) ----
  # ward_code, ea_code, municipality are handled in 01_harmonize_qol.R directly
  NULL
)

# Drop the trailing NULL row
QOL_VARMAP <- QOL_VARMAP[!sapply(QOL_VARMAP$harmonized, is.null), ]


# ------ Recode functions ------

recode_sat5_text <- function(x) {
  dplyr::case_match(
    tolower(trimws(x)),
    "very dissatisfied" ~ 1L,
    "dissatisfied"      ~ 2L,
    c("neither satisfied nor dissatisfied", "neither") ~ 3L,
    "satisfied"         ~ 4L,
    "very satisfied"    ~ 5L,
    .default = NA_integer_
  )
}

recode_safe5_text <- function(x) {
  dplyr::case_match(
    tolower(trimws(x)),
    "very unsafe"  ~ 1L,
    c("bit unsafe", "a bit unsafe", "unsafe") ~ 2L,
    c("neither safe nor unsafe", "neither")   ~ 3L,
    c("bit safe", "a bit safe", "fairly safe", "safe") ~ 4L,
    "very safe"    ~ 5L,
    .default = NA_integer_
  )
}

recode_yn_text <- function(x) {
  dplyr::case_match(
    tolower(trimws(x)),
    "yes" ~ 1L,
    "no"  ~ 0L,
    .default = NA_integer_
  )
}

recode_crime3_text <- function(x) {
  dplyr::case_match(
    tolower(trimws(x)),
    "got worse"      ~ -1L,
    "stayed the same" ~ 0L,
    c("got better", "improved") ~ 1L,
    .default = NA_integer_
  )
}

recode_trust_text <- function(x) {
  dplyr::case_match(
    tolower(trimws(x)),
    c("strongly distrust", "distrust a lot") ~ 1L,
    "distrust"                                ~ 2L,
    c("neither trust nor distrust", "neither", "dont know") ~ 3L,
    "trust"                                   ~ 4L,
    c("strongly trust", "trust a lot")        ~ 5L,
    .default = NA_integer_
  )
}

recode_trust_binary <- function(x) {
  dplyr::case_match(
    tolower(trimws(x)),
    "most people can be trusted"    ~ 1L,
    "you need to be very careful"   ~ 0L,
    "dont know"                     ~ NA_integer_,
    .default = NA_integer_
  )
}

recode_multiselect_item <- function(x) {
  x <- suppressWarnings(as.numeric(x))
  ifelse(is.na(x), NA_integer_, ifelse(x > 0, 1L, 0L))
}

recode_yn_num12 <- function(x) {
  x <- suppressWarnings(as.integer(x))
  dplyr::case_match(x, 1L ~ 1L, 2L ~ 0L, .default = NA_integer_)
}

recode_crime3_numeric <- function(x) {
  x <- suppressWarnings(as.integer(x))
  dplyr::case_match(x, 1L ~ 1L, 2L ~ 0L, 3L ~ -1L, .default = NA_integer_)
}

recode_safe5_reverse <- function(x) {
  x <- suppressWarnings(as.integer(x))
  ifelse(!is.na(x) & x >= 1L & x <= 5L, 6L - x, NA_integer_)
}

recode_sex_num <- function(x) {
  x <- suppressWarnings(as.integer(x))
  dplyr::case_match(x, 1L ~ 0L, 2L ~ 1L, .default = NA_integer_)
}

recode_sex_text <- function(x) {
  dplyr::case_match(
    tolower(trimws(x)),
    "male"   ~ 0L,
    "female" ~ 1L,
    .default = NA_integer_
  )
}

recode_race_num4 <- function(x) {
  x <- suppressWarnings(as.integer(x))
  dplyr::case_match(x,
    1L ~ "Black African", 2L ~ "Coloured",
    3L ~ "Indian/Asian",  4L ~ "White",
    .default = NA_character_
  )
}

recode_race_num_v5 <- function(x) {
  x <- suppressWarnings(as.integer(x))
  dplyr::case_match(x,
    1L ~ "Black African", 2L ~ "Coloured",
    3L ~ "Indian/Asian",  4L ~ "White", 5L ~ "Other",
    .default = NA_character_
  )
}

recode_race_text <- function(x) {
  x <- trimws(x)
  dplyr::case_match(
    x,
    c("Black African", "Coloured", "Indian/Asian", "White", "Other") ~ x,
    .default = NA_character_
  )
}

recode_educ_w1 <- function(x) {
  suppressWarnings(as.integer(x))
}

recode_educ_w2 <- function(x) {
  x <- suppressWarnings(as.integer(x))
  dplyr::case_match(x,
    0L ~ 1L, 1L ~ 1L, 2L ~ 2L, 3L ~ 3L, 4L ~ 4L,
    .default = NA_integer_
  )
}

recode_educ_w5 <- function(x) {
  x <- suppressWarnings(as.integer(x))
  dplyr::case_match(x,
    1L ~ 1L, 2L ~ 1L, 3L ~ 2L, 4L ~ 3L, 5L ~ 4L, 6L ~ 4L,
    .default = NA_integer_
  )
}

recode_educ_text <- function(x) {
  dplyr::case_match(
    tolower(trimws(x)),
    "no education"          ~ 1L,
    "primary only"          ~ 1L,
    "secondary incomplete"  ~ 2L,
    "matric"                ~ 3L,
    "more"                  ~ 4L,
    .default = NA_integer_
  )
}

recode_dwelling_num <- function(x) {
  x <- suppressWarnings(as.integer(x))
  dplyr::case_match(x, 1L ~ 1L, 2L ~ 0L, 3L ~ 0L, .default = NA_integer_)
}

recode_dwelling_text <- function(x) {
  dplyr::case_match(
    tolower(trimws(x)),
    "formal"   ~ 1L,
    "informal" ~ 0L,
    "other"    ~ 0L,
    .default = NA_integer_
  )
}

recode_employ_w1 <- function(x) {
  x <- suppressWarnings(as.integer(x))
  dplyr::case_match(x, 1L ~ 0L, 2L ~ 1L, 3L ~ NA_integer_, .default = NA_integer_)
}

recode_employ_w3 <- function(x) {
  dplyr::case_match(
    tolower(trimws(x)),
    "employed"   ~ 0L,
    "unemployed" ~ 1L,
    "other"      ~ NA_integer_,
    .default = NA_integer_
  )
}

recode_employ_w4 <- function(x) {
  x <- suppressWarnings(as.integer(x))
  dplyr::case_match(x, 1L ~ 0L, 2L ~ 1L, 3L ~ NA_integer_, .default = NA_integer_)
}

recode_employ_w5 <- function(x) {
  x <- suppressWarnings(as.integer(x))
  dplyr::case_match(x,
    1L ~ 0L, 2L ~ 0L, 3L ~ 1L, 4L ~ 1L, 5L ~ NA_integer_, 6L ~ NA_integer_,
    .default = NA_integer_
  )
}

apply_recode <- function(x, method) {
  switch(method,
    "numeric"     = suppressWarnings(as.numeric(x)),
    "sat5_text"   = recode_sat5_text(x),
    "safe5_text"  = recode_safe5_text(x),
    "yn_text"     = recode_yn_text(x),
    "crime3_text" = recode_crime3_text(x),
    "trust_text"  = recode_trust_text(x),
    "trust_binary"= recode_trust_binary(x),
    "binary01"    = suppressWarnings(as.integer(x)),
    "yn_num12"    = recode_yn_num12(x),
    "multiselect_item" = recode_multiselect_item(x),
    "crime3_numeric"   = recode_crime3_numeric(x),
    "safe5_reverse"    = recode_safe5_reverse(x),
    "index"       = suppressWarnings(as.numeric(x)),
    "factor"      = as.character(x),
    "none"        = x,
    "educ_w1"     = recode_educ_w1(x),
    "employ_w1"   = recode_employ_w1(x),
    "sex_num"     = recode_sex_num(x),
    "sex_text"    = recode_sex_text(x),
    "race_num4"   = recode_race_num4(x),
    "race_num_v5" = recode_race_num_v5(x),
    "race_text"   = recode_race_text(x),
    "educ_w2"     = recode_educ_w2(x),
    "educ_w5"     = recode_educ_w5(x),
    "educ_text"   = recode_educ_text(x),
    "dwelling_num"  = recode_dwelling_num(x),
    "dwelling_text" = recode_dwelling_text(x),
    "employ_w3"   = recode_employ_w3(x),
    "employ_w4"   = recode_employ_w4(x),
    "employ_w5"   = recode_employ_w5(x),
    stop("Unknown recode method: ", method)
  )
}


# ------ QoL geography column mapping ------

QOL_GEO <- data.frame(
  wave         = c("I",    "II",   "III",  "IV",         "V",    "6",         "7"),
  ward_col     = c("A4",   "Ward", "Ward", "WardNumber", "ward", "ward_code", "ward_code"),
  ea_col       = c(NA,     NA,     NA,     NA,           "ea_code", "ea_code", "ea_code"),
  munic_col    = c("A5",   NA,     "Munic","Municipality",NA,     "municipality_coded", "municipality_coded"),
  weight_col   = c("Weight",NA,    "GCROweight", "Bench_wgt_30002", NA, NA,   NA),
  ward_demarcation = c("2006", "2011", "2011", "2016", "2016", "2016", "2016"),
  stringsAsFactors = FALSE
)


# ------ QoL interview date (waves that record it) ------

QOL_DATE <- data.frame(
  wave   = c("V",          "6",              "7"),
  col    = c("date",       "interview_date", "interview_date"),
  format = c("%m/%d/%Y",   "%d %b %y",       "%d-%b-%Y"),
  stringsAsFactors = FALSE
)


# ------ SAPS crime families (from strategy memo) ------

SAPS_FAMILIES <- list(
  V0_anchor    = c("murder", "attempted_murder"),
  V1_primary   = c("burglary_res", "robbery_res", "carjacking", "vehicle_theft"),
  V2_person    = c("assault_gbh", "common_assault", "sexual_offences"),
  V3_detection = c("drug_crime", "illegal_firearms", "dui"),
  V4_falsif    = c("commercial_crime", "shoplifting", "stock_theft")
)


# ------ Afrobarometer variable mapping ------

AB_VARMAP <- data.frame(
  harmonized = c(
    # trust
    "trust_police",       "trust_courts",        "trust_local_council",
    "trust_president",    "trust_parliament",     "trust_ruling_party",
    # police perceptions
    "police_professional","police_unnecessary_stops", "police_excessive_force",
    "police_criminal",    "police_corruption",
    # safety
    "unsafe_walking",     "fear_crime_home",
    # govt performance
    "handling_crime",     "handling_corruption",  "local_councillor_perf",
    # social trust
    "trust_neighbours",   "trust_other_citizens",
    # police contact
    "requested_police",   "difficulty_police",
    # PSC exposure (EA-level)
    "ea_private_security_roadblock", "ea_police_present",
    # satisfaction with democracy
    "sat_democracy",
    # corruption perceptions
    "corruption_level",
    # demographics
    "age", "gender", "education", "urban_rural",
    # location
    "ea_lat", "ea_lon", "ward_code", "district", "municipality"
  ),
  raw_col = c(
    "Q37G", "Q37I", "Q37D",
    "Q37A", "Q37B", "Q37E",
    "Q44A", "Q44B", "Q44C",
    "Q44E", "Q38E",
    "Q7A",  "Q7B",
    "Q46F", "Q46J", "Q47C",
    "Q86C", "Q86A",
    "Q43A", "Q43B",
    "EA_SEC_E", "EA_SEC_A",
    "Q31",
    "Q39A",
    "Q1", "Q101", "Q97", "URBRUR",
    "EA_GPS_LA", "EA_GPS_LO", "LOCATION.LEVEL.3",
    "LOCATION.LEVEL.1", "LOCATION.LEVEL.2"
  ),
  family = c(
    rep("trust", 6),
    rep("police_perceptions", 5),
    rep("safety", 2),
    rep("govt_performance", 3),
    rep("social_trust", 2),
    rep("police_contact", 2),
    rep("psc_exposure", 2),
    "democracy", "corruption",
    rep("demographic", 4),
    rep("geography", 5)
  ),
  stringsAsFactors = FALSE
)


# ------ Gauteng metro ward-code prefixes ------

GAUTENG_METROS <- list(
  johannesburg = "798",
  tshwane      = "799",
  ekurhuleni   = "797"
)


# ------ PSC exposure parameters ------

PSC_PARAMS <- list(
  ring_radii_m   = c(500, 1000, 2000),
  min_listings   = 5L,
  psc_col        = "psc_flag_v2"
)

# ==============================================================================
# _sal.R -- Census 2011 Small Area Layer (SAL) loading and derivations
# Project: PSC Exposure (memo 2.6 dwellings; 3.2 common-support predictors;
#          6.3 calibration target dwelling type x race x income band)
# Author:  data-engineer agent for Thomas Brailey
# Date:    2026-09-30
# Purpose: Functions only. Reads the DataFirst study-517 files (South African
#          Census Community Profiles 2011: one Stata file per variable at SAL
#          level, counts rounded to base 3 by Stats SA) and the Stats SA SAL
#          GIS layer; derives SAL covariates; apportions SALs to units.
# Inputs:  data/raw/units/census2011_saccp/** (manual download, see 00_download.R)
# ==============================================================================

suppressPackageStartupMessages(library(haven))

saccp_tables <- c("type-of-main-dwelling", "population-group",
                  "population-group-household-head", "household-income-annual",
                  "household-size", "geo-type", "enumeration-area-type",
                  "tenure-status")

sal_available <- function() {
  tabs_ok <- all(vapply(saccp_tables, function(f) length(list.files(
    dir_saccp, pattern = paste0("^", f, "[.](dta|csv)$"), recursive = TRUE,
    ignore.case = TRUE)) > 0, logical(1)))
  gis_ok <- length(list.files(dir_saccp, pattern = "[.](shp|gpkg)$|[.]gdb$",
                              recursive = TRUE, include.dirs = TRUE,
                              ignore.case = TRUE)) > 0
  tabs_ok && gis_ok
}

stop_if_no_sal <- function(component) {
  if (sal_available()) return(invisible(TRUE))
  message(conditionMessage(stop_manual(
    component = component,
    files = c(paste0(saccp_tables, ".dta"), "Stats SA Census 2011 SAL GIS layer"),
    url = "https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/517/get-microdata",
    dest = dir_saccp,
    extra = "Free DataFirst login required. Re-run this script afterwards.")))
  quit(save = "no", status = 3)
}

read_saccp <- function(name) {
  f <- list.files(dir_saccp, pattern = paste0("^", name, "[.](dta|csv)$"),
                  recursive = TRUE, full.names = TRUE, ignore.case = TRUE)[1]
  x <- if (grepl("[.]dta$", f, ignore.case = TRUE)) as.data.table(zap_labels(read_dta(f)))
       else fread(f)
  setnames(x, tolower(names(x)))
  stopifnot("SAL table lacks a sal_code column" = "sal_code" %in% names(x))
  x[, sal_code := as.character(as.integer(sal_code))]
  x
}

# Category columns that may legitimately be absent from a community-profile table.
optional_cols <- c("dwltyp_13", "inchh_13", "pgrhhh_6")

# Columns of `map` found in table `x`. Fails loudly if any non-optional code is
# missing, so a renamed/partial file can never silently drop a category.
saccp_cols <- function(x, map, tab) {
  miss <- setdiff(names(map), c(names(x), optional_cols))
  if (length(miss))
    stop("SAL table '", tab, "' is missing expected columns: ", paste(miss, collapse = ", "),
         "\nFound: ", paste(head(names(x), 40), collapse = ", "), call. = FALSE)
  cols <- intersect(names(map), names(x))
  stopifnot("no category columns matched" = length(cols) > 0)
  cols
}

# Share of `codes` (e.g. SAL polygon codes) found in the table's sal_code column.
# Fails below `min_share` so a code-format mismatch cannot yield silent zero counts.
assert_sal_match <- function(poly_codes, table_codes, min_share = 0.99, what = "SAL") {
  sh <- mean(poly_codes %in% table_codes)
  log_msg(what, "polygon codes matched to census table codes:", round(100 * sh, 2), "%")
  if (!is.finite(sh) || sh < min_share)
    stop(what, " code match ", round(100 * sh, 2), "% < ", 100 * min_share,
         "%: check SAL_CODE formatting between polygons and tables", call. = FALSE)
  invisible(sh)
}

# SAL polygons: first polygon layer with a SAL code field. Codes are stored as
# character integers to match the Stata files.
read_sal_geom <- function() {
  f <- list.files(dir_saccp, pattern = "[.](shp|gpkg)$|[.]gdb$", recursive = TRUE,
                  full.names = TRUE, include.dirs = TRUE, ignore.case = TRUE)
  for (src in f) {
    for (ly in st_layers(src)$name) {
      g <- st_read(src, layer = ly, quiet = TRUE)
      fld <- grep("^sal_?code$", names(g), ignore.case = TRUE, value = TRUE)[1]
      if (is.na(fld)) next
      g$sal_code <- as.character(as.integer(g[[fld]]))
      g <- st_zm(g, drop = TRUE, what = "ZM")
      g <- st_make_valid(st_transform(g[, "sal_code"], crs_sa_albers))
      g <- st_collection_extract(g, "POLYGON", warn = FALSE)
      return(aggregate(g, by = list(sal = g$sal_code), FUN = function(x) x[1])[, "sal_code"])
    }
  }
  stop("No SAL polygon layer with a SAL_CODE field found under ", dir_saccp)
}

# ---- Category maps (Census 2011 community-profile codes) ----------------------
dw_map <- c(dwltyp_1 = "house", dwltyp_2 = "traditional_other", dwltyp_3 = "flat",
            dwltyp_4 = "complex", dwltyp_5 = "complex", dwltyp_6 = "semi_detached",
            dwltyp_7 = "backyard_room", dwltyp_8 = "informal", dwltyp_9 = "informal",
            dwltyp_10 = "backyard_room", dwltyp_11 = "informal",
            dwltyp_12 = "traditional_other", dwltyp_13 = "unspecified")
# calibration grouping (memo 6.3): 5 dwelling classes
dw_cal <- c(house = "house", semi_detached = "house", complex = "complex",
            flat = "flat", backyard_room = "backyard_room", informal = "informal_other",
            traditional_other = "informal_other")
inc_map <- c(inchh_1 = "none", inchh_2 = "low", inchh_3 = "low", inchh_4 = "low",
             inchh_5 = "lower_mid", inchh_6 = "lower_mid", inchh_7 = "mid",
             inchh_8 = "mid", inchh_9 = "high", inchh_10 = "high", inchh_11 = "high",
             inchh_12 = "high")
# annual household income band midpoints (ZAR, 2011); open top band at 1.5x floor
inc_mid <- c(inchh_1 = 0, inchh_2 = 2400, inchh_3 = 7200, inchh_4 = 14600,
             inchh_5 = 28900, inchh_6 = 57300, inchh_7 = 115100, inchh_8 = 230700,
             inchh_9 = 461000, inchh_10 = 921600, inchh_11 = 1843200,
             inchh_12 = 3686400)
race_map <- c(pgrhhh_1 = "black", pgrhhh_2 = "coloured", pgrhhh_3 = "indian",
              pgrhhh_4 = "white", pgrhhh_5 = "other", pgrhhh_6 = "unspecified")

# SAL-level counts in long form: sal_code, dimension, category, n (households
# unless the dimension says persons).
sal_long <- function() {
  one <- function(tab, map, dim) {
    x <- read_saccp(tab)
    cols <- saccp_cols(x, map, tab)
    m <- melt(x[, c("sal_code", cols), with = FALSE], id.vars = "sal_code",
              variable.name = "code", value.name = "n")
    m[, `:=`(dimension = dim, category = map[as.character(code)], n = as.numeric(n))]
    m[, .(n = sum(n, na.rm = TRUE)), by = .(sal_code, dimension, category)]
  }
  pg <- c(pgrp_1 = "black", pgrp_2 = "coloured", pgrp_3 = "indian", pgrp_4 = "white",
          pgrp_5 = "other")
  ten <- c(tensta_1 = "rented", tensta_2 = "owned_bond", tensta_3 = "rent_free",
           tensta_4 = "owned_paid", tensta_5 = "other")
  ea <- c(eatyp_1 = "formal_res", eatyp_2 = "informal_res", eatyp_3 = "traditional_res",
          eatyp_4 = "farms", eatyp_5 = "parks", eatyp_6 = "collective",
          eatyp_7 = "industrial", eatyp_8 = "smallholdings", eatyp_9 = "vacant",
          eatyp_10 = "commercial")
  hs <- setNames(as.character(1:10), paste0("hhsize_", 1:10))
  rbindlist(list(
    one("type-of-main-dwelling", dw_map, "dwelling_type"),
    one("household-income-annual", c(inc_map, inchh_13 = "unspecified"), "income_band"),
    one("population-group-household-head", race_map, "race_hh_head"),
    one("population-group", pg, "race_persons"),
    one("tenure-status", ten, "tenure"),
    one("enumeration-area-type", ea, "ea_type_persons"),
    one("household-size", hs, "household_size")
  ))
}

# Mean annual household income from band midpoints (unspecified excluded).
sal_income_mean <- function() {
  x <- read_saccp("household-income-annual")
  cols <- saccp_cols(x, inc_mid, "household-income-annual")
  m <- melt(x[, c("sal_code", cols), with = FALSE], id.vars = "sal_code",
            variable.name = "code", value.name = "n")
  m[, mid := inc_mid[as.character(code)]]
  m[, .(inc_mid_sum = sum(as.numeric(n) * mid, na.rm = TRUE),
        inc_n = sum(as.numeric(n), na.rm = TRUE)), by = sal_code]
}

# Area-share apportionment of SALs to a unit layer (column `uid`). Returns one
# row per SAL x unit with share of SAL area, plus the majority assignment.
sal_to_units <- function(sal, units, uid) {
  u <- units[, uid]; names(u)[names(u) == uid] <- "uid"
  x <- suppressWarnings(st_intersection(sal[, "sal_code"], u))
  x <- st_collection_extract(x, "POLYGON", warn = FALSE)
  dt <- data.table(sal_code = x$sal_code, uid = x$uid, area = as.numeric(st_area(x)))
  dt <- dt[, .(area = sum(area)), by = .(sal_code, uid)]
  sa <- data.table(sal_code = sal$sal_code, sal_area = as.numeric(st_area(sal)))
  dt <- merge(dt, sa, by = "sal_code")
  dt[, share := area / sal_area]
  dt[, is_majority := share == max(share), by = sal_code]
  dt[]
}

# ==============================================================================
# _saps_parse.R -- Parse SAPS station-level workbooks into station x FY presence
# Project: PSC Exposure
# Author:  data-engineer agent for Thomas Brailey
# Date:    2026-09-30
# Purpose: Harmonise five SAPS releases into one long table of the
#          "17 community-reported serious crimes" total by station and financial
#          year (FY coded by its starting year: 2005 = FY2005/06). Used ONLY to
#          date station openings and to identify split parents; no outcome
#          analysis is done with these counts.
# Inputs:  data/raw/units/saps/stats_*.xls(x)
# Outputs: none (functions); called by 01_precinct_clusters.R
# ==============================================================================

suppressPackageStartupMessages(library(readxl))

prov_map <- c("GAUTENG" = "GT", "GP" = "GT", "WESTERN CAPE" = "WC", "WC" = "WC",
              "WESTERN_CAPE" = "WC")

cat17_2013 <- c(
  "Murder", "Total Sexual Crimes", "Attempted murder",
  "Assault with the intent to inflict grievous bodily harm", "Common assault",
  "Common robbery", "Robbery with aggravating circumstances", "Arson",
  "Malicious damage to property", "Burglary at non-residential premises",
  "Burglary at residential premises", "Theft of motor vehicle and motorcycle",
  "Theft out of or from motor vehicle", "Stock-theft",
  "All theft not mentioned elsewhere", "Commercial crime", "Shoplifting")

# SAPS appends footnote markers such as "[169] [P]" to some station names.
clean_raw_name <- function(x) trimws(gsub("\\[[^]]*\\]", "", x))

fy_from_label <- function(x) {
  # "2005-2006", "April 2005 to March 2006" -> 2005
  as.integer(sub(".*?(\\d{4}).*", "\\1", x))
}

# ---- FY2003/04-2012/13 (2013 release; one block per station per province) ----
parse_2013 <- function(path) {
  out <- list()
  for (sh in c("GP", "WC")) {
    x <- as.data.table(suppressMessages(
      read_excel(path, sheet = sh, col_names = FALSE, col_types = "text")))
    hdr <- grep("^Crime in", x[[1]])
    for (k in seq_along(hdr)) {
      title <- x[[1]][hdr[k]]
      m <- regmatches(title, regexec("^Crime in\\s+(.*?)\\s*\\((GP|WC)\\)", title))[[1]]
      if (length(m) == 0) next  # the province-total block
      rows <- (hdr[k] + 1):(if (k < length(hdr)) hdr[k + 1] - 1 else nrow(x))
      blk <- x[rows]
      lab <- blk[[1]] == "Crime Category"
      years <- fy_from_label(unlist(blk[which(lab)[1], -1]))
      vals <- blk[blk[[1]] %in% cat17_2013]
      tot <- colSums(sapply(vals[, -1], as.numeric), na.rm = TRUE)
      out[[length(out) + 1]] <- data.table(
        source = "saps_stats_2013", province = prov_map[sh],
        station_raw = clean_raw_name(m[2]), fy = years, tot17 = as.numeric(tot))
    }
  }
  rbindlist(out)
}

# ---- FY2005/06-2014/15 (2014/15 release, sheet "Data") ----
parse_2015 <- function(path) {
  y <- as.data.table(suppressMessages(read_excel(path, sheet = "Data", skip = 2)))
  setnames(y, 3, "province_name")
  y <- y[Type == "Station" & `Crime Category` == "17 Community Reported Crimes"]
  fy_cols <- grep("^\\d{4}-\\d{4}$", names(y), value = TRUE)
  y <- melt(y, id.vars = c("province_name", "Station"), measure.vars = fy_cols,
            variable.name = "fy_lab", value.name = "tot17")
  y[, `:=`(province = prov_map[toupper(province_name)],
           fy = fy_from_label(as.character(fy_lab)),
           tot17 = as.numeric(tot17))]
  y[!is.na(province), .(source = "saps_stats_2015", province,
                        station_raw = clean_raw_name(Station), fy, tot17)]
}

# ---- FY2008/09-2020/21 (2020/21 release, sheet "station data 2021") ----
parse_2021 <- function(path) {
  q <- as.data.table(suppressMessages(read_excel(path, sheet = "station data 2021")))
  q <- q[Station_type != 0 & grepl("^17 Community", `Crime Category`)]
  fy_cols <- grep("^\\d{4}-\\d{4}$", names(q), value = TRUE)
  q <- melt(q, id.vars = c("station", "prov"), measure.vars = fy_cols,
            variable.name = "fy_lab", value.name = "tot17")
  q[, `:=`(province = prov_map[toupper(prov)], fy = fy_from_label(as.character(fy_lab)),
           tot17 = as.numeric(tot17))]
  q[!is.na(province), .(source = "saps_stats_2021", province,
                        station_raw = clean_raw_name(station), fy, tot17)]
}

# ---- FY2013/14-2022/23+ (2023/24 release, sheet "RAW Data", header row 3) ----
parse_2024 <- function(path) {
  z <- as.data.table(suppressMessages(read_excel(path, sheet = "RAW Data", skip = 2,
                                                 .name_repair = "unique_quiet")))
  nm <- names(z)
  st_col <- nm[nm == "Station"][1]
  pr_col <- grep("^Province", nm, value = TRUE)[1]
  cc_col <- grep("^Crime_Category", nm, value = TRUE)
  cc_col <- cc_col[vapply(cc_col, function(cn) any(grepl("^Murder$", z[[cn]])), TRUE)][1]
  fy_cols <- grep("^\\d{4}-\\d{4}$", nm, value = TRUE)
  z <- z[`Comp level` == "Station"]
  zz <- z[, c(st_col, pr_col, cc_col, fy_cols), with = FALSE]
  setnames(zz, 1:3, c("station", "province_name", "cat"))
  # The 17-category aggregate is not a row in this release: sum its members.
  cats <- c(setdiff(cat17_2013, "Total Sexual Crimes"), "Sexual Offences",
            "Sexual offences")
  zz <- zz[cat %in% cats]
  zz <- melt(zz, id.vars = c("station", "province_name", "cat"),
             measure.vars = fy_cols, variable.name = "fy_lab", value.name = "n")
  zz[, n := as.numeric(n)]
  zz <- zz[, .(tot17 = sum(n, na.rm = TRUE)), by = .(station, province_name, fy_lab)]
  zz[, `:=`(province = prov_map[toupper(province_name)],
            fy = fy_from_label(as.character(fy_lab)))]
  zz[!is.na(province), .(source = "saps_stats_2024", province,
                         station_raw = clean_raw_name(station), fy, tot17)]
}

# ---- Q4 (Jan-Mar) of FY2021/22-2025/26 (2025/26 Q4 release) ----
parse_2026q4 <- function(path) {
  hdr <- suppressMessages(read_excel(path, sheet = "RAW Data", col_names = FALSE,
                                     n_max = 3))
  lab <- as.character(unlist(hdr[3, ]))
  z <- as.data.table(suppressMessages(read_excel(path, sheet = "RAW Data", skip = 3,
                                                 col_names = FALSE)))
  qcols <- grep("^January \\d{4} to", lab)            # quarter totals
  st <- which(lab == "Station")[1]; pr <- which(lab == "Province")[1]
  cc <- which(lab == "Crime_Category")
  cc <- cc[vapply(cc, function(j) any(z[[j]] == "Murder", na.rm = TRUE), TRUE)][1]
  lv <- which(lab == "Comp level")[1]
  z <- z[z[[lv]] == "Station"]
  cats <- c(setdiff(cat17_2013, "Total Sexual Crimes"), "Sexual Offences",
            "Sexual offences")
  z <- z[z[[cc]] %in% cats]
  yrs <- as.integer(sub("^January (\\d{4}).*", "\\1", lab[qcols])) - 1L  # Jan 2022 in FY2021
  out <- rbindlist(lapply(seq_along(qcols), function(k) {
    data.table(station_raw = z[[st]], province_name = z[[pr]], fy = yrs[k],
               n = as.numeric(z[[qcols[k]]]))
  }))
  out <- out[, .(tot17 = sum(n, na.rm = TRUE)), by = .(station_raw, province_name, fy)]
  out[, province := prov_map[toupper(province_name)]]
  out[!is.na(province), .(source = "saps_stats_2026q4", province,
                          station_raw = clean_raw_name(station_raw), fy, tot17)]
}

parse_all_saps <- function(dir) {
  rbindlist(list(
    parse_2013(file.path(dir, "stats_2003_2013.xls")),
    parse_2015(file.path(dir, "stats_2014_15.xlsx")),
    parse_2021(file.path(dir, "stats_2020_21.xlsx")),
    parse_2024(file.path(dir, "stats_2023_24.xlsx")),
    parse_2026q4(file.path(dir, "stats_2025_26_q4.xlsx"))
  ), use.names = TRUE)
}

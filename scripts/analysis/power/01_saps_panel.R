# ==============================================================================
# 01_saps_panel.R -- SAPS precinct-cluster x financial-year crime panel (P-E input)
# Project: PSC Exposure (WP3, pilot step P-E)
# Purpose: Build the crime panel used by the placebo power simulation. Station x FY
#          counts for the memo S11 outcome families are parsed from the public SAPS
#          workbooks and aggregated to the WP2 time-invariant precinct clusters
#          (3 Gauteng metros + Cape Town). FY is coded by its start year
#          (2005 = FY2005/06 ... 2025 = FY2025/26).
#            V0      murder, attempted murder
#            V1      residential burglary + residential robbery + carjacking +
#                    theft of motor vehicle/motorcycle (memo S11.2 primary family)
#            contact = murder + attempted murder + sexual offences + GBH + common
#                      assault + common robbery + aggravated robbery
#            property = burglary (non-res + res) + theft of/from motor vehicle +
#                      stock theft
# Inputs:  data/raw/units/saps/stats_*.xls(x)   (WP2 downloads; the three 2025/26
#            Q1-Q3 quarterly workbooks are fetched here if missing)
#          data/cleaned/units/station_to_cluster.parquet, precinct_clusters.gpkg,
#          data/cleaned/units/intermediate/station_aliases.parquet
# Outputs: data/cleaned/power/saps_cluster_panel.parquet
#          data/cleaned/power/intermediate/saps_station_long.parquet
#          data/cleaned/power/intermediate/saps_panel_checks.rds
# Dependencies: readxl, data.table, arrow, sf, here; scripts/cleaning/units/_common.R
#          (norm_station) is re-declared here to avoid its side effects.
# Notes:   No treatment information is used in this script.
#          Release precedence per station-FY: 2023/24-file (FY2013-22) > 2020/21
#          (FY2008-20) > 2014/15 (FY2005-14) > 2013 (FY2003-12); FY2023+ come from
#          the sum of four quarterly releases. Overlaps are compared and logged.
# ==============================================================================

suppressPackageStartupMessages({
  library(data.table); library(arrow); library(readxl); library(sf); library(here)
})
set.seed(20260930)

dir_saps  <- here("data", "raw", "units", "saps")
dir_out   <- here("data", "cleaned", "power")
dir_int   <- file.path(dir_out, "intermediate")
for (d in c(dir_out, dir_int)) dir.create(d, recursive = TRUE, showWarnings = FALSE)
log_msg <- function(...) cat(format(Sys.time(), "%H:%M:%S"), "|", ..., "\n")

# ---- 0. Fetch the quarterly releases for FY2023/24-2025/26 if absent ----------
for (q in 1:3) {
  f <- file.path(dir_saps, sprintf("stats_2025_26_q%d.xlsx", q))
  if (!file.exists(f)) {
    ord <- c("1st", "2nd", "3rd")[q]
    u <- sprintf("https://www.saps.gov.za/services/downloads/2025/2025-2026_-_%s_Quarter_WEB.xlsx", ord)
    log_msg("downloading", u)
    download.file(u, f, mode = "wb", quiet = TRUE,
                  headers = c("User-Agent" = "Mozilla/5.0"))
  }
}

# ---- 1. Category map and helpers ----------------------------------------------
keymap <- c(
  "murder" = "murder", "attempted murder" = "att_murder",
  "total sexual crimes" = "sexual", "total sexual offences" = "sexual",
  "sexual offences" = "sexual",
  "assault with the intent to inflict grievous bodily harm" = "assault_gbh",
  "common assault" = "common_assault", "common robbery" = "common_robbery",
  "robbery with aggravating circumstances" = "robbery_agg",
  "burglary at non-residential premises" = "burg_nonres",
  "burglary at residential premises" = "burg_res",
  "theft of motor vehicle and motorcycle" = "theft_mv",
  "theft out of or from motor vehicle" = "theft_from_mv",
  "stock-theft" = "stock_theft", "carjacking" = "carjacking",
  "robbery at residential premises" = "robbery_res")
cat_key <- function(x) unname(keymap[tolower(trimws(x))])

clean_raw_name <- function(x) trimws(gsub("\\[[^]]*\\]", "", x))
fy_from_label  <- function(x) as.integer(sub(".*?([0-9]{4}).*", "\\1", x))
prov_code <- function(x) {
  x <- toupper(trimws(x))
  fifelse(x %in% c("GAUTENG", "GP", "GT"), "GT",
          fifelse(x %in% c("WESTERN CAPE", "WC", "WESTERN_CAPE"), "WC", "OTH"))
}
norm_station <- function(x) {  # identical to scripts/cleaning/units/_common.R
  x <- toupper(trimws(x)); x <- iconv(x, to = "ASCII//TRANSLIT")
  x <- gsub("[()]", " ", x); x <- gsub("[-/'`.,]", " ", x)
  x <- gsub("\\bSAPS\\b|\\bPOLICE STATION\\b", " ", x)
  gsub("\\s+", " ", trimws(x))
}
aliases <- as.data.table(read_parquet(here("data", "cleaned", "units", "intermediate",
                                           "station_aliases.parquet")))
canon <- function(k, prov) {
  out <- k
  for (i in seq_len(nrow(aliases))) {
    hit <- k == aliases$from[i] & (is.na(aliases$province[i]) | prov == aliases$province[i])
    out[hit] <- aliases$to[i]
  }
  out
}

# ---- 2. Parsers (station x FY x category; annual counts) -----------------------
parse_2013 <- function(path) {
  out <- list()
  for (sh in c("GP", "WC", "MP")) {
    x <- as.data.table(suppressMessages(read_excel(path, sheet = sh, col_names = FALSE,
                                                   col_types = "text")))
    hdr <- grep("^Crime in", x[[1]])
    for (k in seq_along(hdr)) {
      title <- x[[1]][hdr[k]]
      m <- regmatches(title, regexec("^Crime in\\s+(.*?)\\s*\\((GP|WC|MP)\\)", title))[[1]]
      if (length(m) == 0) next
      rows <- (hdr[k] + 1):(if (k < length(hdr)) hdr[k + 1] - 1 else nrow(x))
      blk <- x[rows]
      lab <- which(blk[[1]] == "Crime Category")[1]
      years <- fy_from_label(unlist(blk[lab, -1]))
      ck <- cat_key(blk[[1]])
      sel <- which(!is.na(ck))
      for (j in sel) {
        v <- suppressWarnings(as.numeric(unlist(blk[j, -1])))
        out[[length(out) + 1]] <- data.table(
          source = "s2013", province = prov_code(sh), station_raw = clean_raw_name(m[2]),
          fy = years, cat = ck[j], n = v)
      }
    }
  }
  rbindlist(out)[!is.na(fy)]
}

parse_2015 <- function(path) {
  y <- as.data.table(suppressMessages(read_excel(path, sheet = "Data", skip = 2)))
  setnames(y, 3, "province_name")
  y <- y[Type == "Station"]
  y[, cat := cat_key(`Crime Category`)]; y <- y[!is.na(cat)]
  fyc <- grep("^[0-9]{4}-[0-9]{4}$", names(y), value = TRUE)
  y <- melt(y, id.vars = c("province_name", "Station", "cat"), measure.vars = fyc,
            variable.name = "fy_lab", value.name = "n")
  y[, .(source = "s2015", province = prov_code(province_name),
        station_raw = clean_raw_name(Station), fy = fy_from_label(as.character(fy_lab)),
        cat, n = as.numeric(n))]
}

parse_2021 <- function(path) {
  q <- as.data.table(suppressMessages(read_excel(path, sheet = "station data 2021")))
  q <- q[Station_type != 0]
  q[, cat := cat_key(`Crime Category`)]; q <- q[!is.na(cat)]
  fyc <- grep("^[0-9]{4}-[0-9]{4}$", names(q), value = TRUE)
  q <- melt(q, id.vars = c("station", "prov", "cat"), measure.vars = fyc,
            variable.name = "fy_lab", value.name = "n")
  q[, .(source = "s2021", province = prov_code(prov), station_raw = clean_raw_name(station),
        fy = fy_from_label(as.character(fy_lab)), cat, n = as.numeric(n))]
}

parse_2024 <- function(path) {
  z <- as.data.table(suppressWarnings(suppressMessages(
    read_excel(path, sheet = "RAW Data", skip = 2, .name_repair = "unique_quiet"))))
  nm <- names(z)
  st_col <- nm[nm == "Station"][1]
  pr_col <- grep("^Province", nm, value = TRUE)[1]
  cc_col <- grep("^Crime_Category", nm, value = TRUE)
  cc_col <- cc_col[vapply(cc_col, function(cn) any(grepl("^Murder$", z[[cn]])), TRUE)][1]
  fyc <- grep("^[0-9]{4}-[0-9]{4}$", nm, value = TRUE)
  z <- z[`Comp level` == "Station"]
  zz <- z[, c(st_col, pr_col, cc_col, fyc), with = FALSE]
  setnames(zz, 1:3, c("station", "province_name", "cat_raw"))
  zz[, cat := cat_key(cat_raw)]; zz <- zz[!is.na(cat)]
  zz <- melt(zz, id.vars = c("station", "province_name", "cat"), measure.vars = fyc,
             variable.name = "fy_lab", value.name = "n")
  zz[, .(source = "s2024", province = prov_code(province_name),
         station_raw = clean_raw_name(station), fy = fy_from_label(as.character(fy_lab)),
         cat, n = as.numeric(n))]
}

# Quarterly release: columns "<Month> <year> to <Month> <year>" are quarter totals.
parse_quarter <- function(path, tag) {
  hdr <- suppressWarnings(suppressMessages(read_excel(path, sheet = "RAW Data",
                                                      col_names = FALSE, n_max = 3)))
  lab <- gsub("[\r\n]+", " ", as.character(unlist(hdr[3, ])))
  z <- as.data.table(suppressWarnings(suppressMessages(
    read_excel(path, sheet = "RAW Data", skip = 3, col_names = FALSE))))
  qcols <- grep("^(January|April|July|October) [0-9]{4} to", lab)
  st <- which(lab == "Station")[1]; pr <- which(lab == "Province")[1]
  cc <- which(lab == "Crime_Category")
  cc <- cc[vapply(cc, function(j) any(z[[j]] == "Murder", na.rm = TRUE), TRUE)][1]
  lv <- which(lab == "Comp level")[1]
  z <- z[z[[lv]] == "Station"]
  ck <- cat_key(z[[cc]]); z <- z[!is.na(ck)]; ck <- ck[!is.na(ck)]
  yr <- as.integer(sub("^[A-Za-z]+ ([0-9]{4}) to.*", "\\1", lab[qcols]))
  mo <- sub("^([A-Za-z]+) .*", "\\1", lab[qcols])
  fy <- yr - as.integer(mo == "January")
  rbindlist(lapply(seq_along(qcols), function(k)
    data.table(source = tag, province = prov_code(z[[pr]]),
               station_raw = clean_raw_name(z[[st]]), fy = fy[k], cat = ck,
               n = as.numeric(z[[qcols[k]]]), quarter = mo[k])))
}

cache <- file.path(dir_int, "saps_station_long.parquet")
if (!file.exists(cache)) {
  log_msg("parsing SAPS workbooks (several minutes)")
  ann <- rbindlist(list(
    parse_2013(file.path(dir_saps, "stats_2003_2013.xls")),
    parse_2015(file.path(dir_saps, "stats_2014_15.xlsx")),
    parse_2021(file.path(dir_saps, "stats_2020_21.xlsx")),
    parse_2024(file.path(dir_saps, "stats_2023_24.xlsx"))), fill = TRUE)
  ann[, quarter := "annual"]
  qs <- rbindlist(lapply(1:4, function(q) {
    f <- if (q == 4) "stats_2025_26_q4.xlsx" else sprintf("stats_2025_26_q%d.xlsx", q)
    log_msg("quarter file", f)
    parse_quarter(file.path(dir_saps, f), "qsum")
  }))
  # Sum four quarters to a FY; require all four quarters present
  qsum <- qs[, .(n = sum(n, na.rm = TRUE), nq = uniqueN(quarter[!is.na(n)])),
             by = .(source, province, station_raw, fy, cat)]
  qsum <- qsum[nq == 4][, nq := NULL][, quarter := "sum4q"]
  long <- rbindlist(list(ann, qsum), fill = TRUE)
  write_parquet(long, cache)
} else {
  long <- as.data.table(read_parquet(cache))
}
long[, sid := canon(norm_station(station_raw), province)]
log_msg("long table rows:", nrow(long))

# ---- 3. Map stations to WP2 precinct clusters ----------------------------------
s2c <- as.data.table(read_parquet(here("data", "cleaned", "units", "station_to_cluster.parquet")))
s2c <- s2c[, .(station_id, workbook_province, cluster_id, metro_code, in_scope)]
# WP2 parsed GT/WC workbooks only: stations with NA workbook_province are other
# provinces (e.g. Verena, Mpumalanga); match those on name within non-GT/WC rows.
s2c[, prov_key := fifelse(is.na(workbook_province), "OTH", workbook_province)]
long <- merge(long, s2c, by.x = c("sid", "province"), by.y = c("station_id", "prov_key"))
log_msg("matched station-FY-category rows:", nrow(long))
miss <- setdiff(s2c[in_scope == TRUE]$station_id, long$sid)
log_msg("in-scope stations without any SAPS rows:", length(miss),
        if (length(miss)) paste(miss, collapse = "; ") else "")

# ---- 4. Precedence across releases (station x FY x category) -------------------
rank_src <- c(s2013 = 1, s2015 = 2, s2021 = 3, s2024 = 4, qsum = 4.5)
long[, rank := rank_src[source]]
# FY2021-22 exist in both the 2023/24 annual file and the quarterly sums; keep the
# annual file (rank 4 < 4.5 would pick qsum), so demote qsum where annual exists.
long[source == "qsum" & fy <= 2022, rank := 3.5]
setorder(long, sid, fy, cat, -rank)
chosen <- long[, .SD[1], by = .(sid, fy, cat)]
chosen[, src_used := source]

# ---- 5. Checks on release splices ---------------------------------------------
clus_sum <- function(d) d[cluster_id %in% s2c[in_scope == TRUE]$cluster_id,
                          .(n = sum(n, na.rm = TRUE)), by = .(cluster_id, fy, source, cat)]
ov <- clus_sum(long[cat %in% c("murder", "burg_res", "robbery_res", "carjacking", "theft_mv")])
ov[, grp := fifelse(cat == "murder", "V0_murder", "V1")]
ov <- ov[, .(n = sum(n)), by = .(cluster_id, fy, source, grp)]
cmp_pairs <- list(c("s2013", "s2015"), c("s2015", "s2021"), c("s2021", "s2024"),
                  c("s2024", "qsum"))
splice <- rbindlist(lapply(cmp_pairs, function(p) {
  a <- ov[source == p[1]]; b <- ov[source == p[2]]
  m <- merge(a, b, by = c("cluster_id", "fy", "grp"), suffixes = c("_a", "_b"))
  m[, .(pair = paste(p, collapse = " vs "), n_cells = .N,
        fy_min = min(fy), fy_max = max(fy),
        agg_ratio_b_over_a = sum(n_b) / sum(n_a),
        med_abs_logratio = median(abs(log((n_b + 1) / (n_a + 1)))),
        p90_abs_logratio = quantile(abs(log((n_b + 1) / (n_a + 1))), .9)), by = grp]
}))
print(splice)

# ---- 6. Aggregate to clusters and build the panel ------------------------------
pc <- chosen[cluster_id %in% s2c[in_scope == TRUE]$cluster_id,
             .(n = sum(n, na.rm = TRUE), n_na = sum(is.na(n)), n_st = uniqueN(sid)),
             by = .(cluster_id, fy, cat)]
w <- dcast(pc, cluster_id + fy ~ cat, value.var = "n", fill = 0)
for (k in unname(keymap)) if (!k %in% names(w)) w[, (k) := 0]
w[, `:=`(
  V0_murder   = murder,
  V0_attmurder = att_murder,
  V0_index    = murder + att_murder,
  V1_burg_res = burg_res, V1_robbery_res = robbery_res,
  V1_carjacking = carjacking, V1_theft_mv = theft_mv,
  V1_total    = burg_res + robbery_res + carjacking + theft_mv,
  contact_total  = murder + att_murder + sexual + assault_gbh + common_assault +
                   common_robbery + robbery_agg,
  property_total = burg_nonres + burg_res + theft_mv + theft_from_mv + stock_theft)]
keep <- c("cluster_id", "fy", grep("^(V0|V1|contact|property)", names(w), value = TRUE))
panel <- w[, ..keep]

# Cluster attributes
cl <- st_drop_geometry(st_read(here("data", "cleaned", "units", "precinct_clusters.gpkg"),
                               layer = "precinct_clusters", quiet = TRUE))
cl <- as.data.table(cl)[in_scope == TRUE, .(cluster_id, metro_code, pop_ghsl2010, area_km2,
                                            n_stations, cross_metro)]
panel <- merge(panel, cl, by = "cluster_id")
stn_src <- chosen[, .(n_st_reporting = uniqueN(sid[!is.na(n)]),
                      src = paste(sort(unique(src_used)), collapse = "+")),
                  by = .(cluster_id, fy)]
panel <- merge(panel, stn_src, by = c("cluster_id", "fy"), all.x = TRUE)
panel <- panel[fy >= 2005 & fy <= 2025]
setorder(panel, cluster_id, fy)

# Balance and sanity checks
chk <- list()
chk$n_clusters <- panel[, uniqueN(cluster_id)]
chk$by_metro   <- unique(panel[, .(cluster_id, metro_code)])[, .N, by = metro_code]
chk$fy_range   <- range(panel$fy)
chk$balanced   <- panel[, .N, by = cluster_id][, all(N == 21)]
chk$zero_V1_cells <- panel[V1_total == 0, .N]
chk$stations_missing_fy <- panel[n_st_reporting < n_stations, .N]
chk$citywide_V1_by_fy <- panel[, .(V1 = sum(V1_total), murder = sum(V0_murder)), by = .(metro_code, fy)]
chk$splice <- splice
saveRDS(chk, file.path(dir_int, "saps_panel_checks.rds"))
print(chk[c("n_clusters", "by_metro", "fy_range", "balanced", "zero_V1_cells",
            "stations_missing_fy")])
print(dcast(chk$citywide_V1_by_fy, fy ~ metro_code, value.var = "V1"))

write_parquet(panel, file.path(dir_out, "saps_cluster_panel.parquet"))
log_msg("wrote", file.path(dir_out, "saps_cluster_panel.parquet"), "rows", nrow(panel))

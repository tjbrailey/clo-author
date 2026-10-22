# ==============================================================================
# 00_download.R -- Fetch public sources for the units pipeline (WP2)
# Project: PSC Exposure
# Author:  data-engineer agent for Thomas Brailey
# Date:    2026-09-30
# Purpose: Download police-station boundaries (all public vintages), SAPS
#          station-level crime-statistics workbooks (used ONLY to date station
#          openings), MDB ward boundaries 2011/2016/2021, and cropped GHSL
#          GHS-POP 2010 grids (used ONLY for the explicitly provisional SWU run
#          and precinct-exchange materiality). Checks
#          for the Census 2011 SAL files, which need a DataFirst login.
#          Every file gets a provenance row (URL, archived-from URL, retrieval
#          time, bytes, SHA-256) in data/raw/units/provenance.csv.
# Inputs:  network
# Outputs: data/raw/units/** ; data/raw/units/provenance.csv
# Usage:   Rscript scripts/cleaning/units/00_download.R      (skip existing)
#          PSC_UNITS_FORCE=1 Rscript ...                       (re-download)
# Notes:   saps.gov.za/services/boundary.php now sits behind a request form
#          (name, e-mail, acceptance of an SDI Act disclaimer). The agent does
#          not submit that form on the user's behalf. Earlier vintages were
#          published at direct URLs and are fetched from the Internet Archive
#          byte-for-byte ("id_" snapshots). statssa.gov.za is behind an
#          Incapsula JS challenge; its PoliceDistrict.zip is fetched the same
#          way. The SDI-Act disclaimer restricts redistribution of SAPS
#          boundaries: raw files stay in data/raw (gitignored).
# ==============================================================================

source(here::here("scripts", "cleaning", "units", "_common.R"))
suppressPackageStartupMessages({
  library(curl)
  library(terra)
})

force <- identical(Sys.getenv("PSC_UNITS_FORCE"), "1")
ua <- "psc-exposure-research/0.1 (academic; R libcurl)"
pause_s <- 4  # polite gap between requests

wb <- function(ts, url) sprintf("https://web.archive.org/web/%sid_/%s", ts, url)
saps_b <- "https://www.saps.gov.za/services/downloads/boundaries"
saps_d <- "https://www.saps.gov.za/services/downloads"
saps_old <- "http://www.saps.gov.za/resource_centre/publications/statistics/crimestats"
agol <- "https://www.arcgis.com/sharing/rest/content/items"

# ---- Source register ------------------------------------------------------------
# role: what the file is used for. Crime workbooks: station x FY presence only.
src <- rbindlist(list(
  # SAPS station boundaries, archived vintages (directory dates in comment)
  list("saps_bnd_2014", "SAPS station boundaries 2014 (dir 2019-10-07)",
       wb("20210725065659", paste0(saps_b, "/2014/station_boundaries.zip")),
       paste0(saps_b, "/2014/station_boundaries.zip"),
       "saps/boundaries_2014.zip", "precinct parents"),
  list("saps_bnd_2015", "SAPS station boundaries 2015",
       wb("20210725065908", paste0(saps_b, "/2015/station_boundaries.zip")),
       paste0(saps_b, "/2015/station_boundaries.zip"),
       "saps/boundaries_2015.zip", "precinct parents"),
  list("saps_bnd_2016", "SAPS station boundaries 2016",
       wb("20210725070126", paste0(saps_b, "/2016/station_boundaries.zip")),
       paste0(saps_b, "/2016/station_boundaries.zip"),
       "saps/boundaries_2016.zip", "precinct parents"),
  list("saps_bnd_2017", "SAPS station boundaries 2017",
       wb("20210725093654", paste0(saps_b, "/2017/station_boundaries.zip")),
       paste0(saps_b, "/2017/station_boundaries.zip"),
       "saps/boundaries_2017.zip", "precinct parents"),
  list("saps_bnd_2018", "SAPS station boundaries+points (file dated 2018-03-07)",
       wb("20210725065541", paste0(saps_b, "/station_boundaries_points___.zip")),
       paste0(saps_b, "/station_boundaries_points___.zip"),
       "saps/boundaries_2018.zip", "precinct parents"),
  list("saps_bnd_2019", "SAPS station boundaries 2019",
       wb("20210725093909", paste0(saps_b, "/2019/station_boundaries__.zip")),
       paste0(saps_b, "/2019/station_boundaries__.zip"),
       "saps/boundaries_2019.zip", "precinct parents"),
  list("saps_bnd_2020", "SAPS station boundaries (file dated 2020-03-20)",
       wb("20210725065327", paste0(saps_b, "/station_boundaries.zip")),
       paste0(saps_b, "/station_boundaries.zip"),
       "saps/boundaries_2020.zip", "precinct parents"),
  # Stats SA police districts (SAPS precincts as used for Census 2022 outputs)
  list("statssa_police_2025", "Stats SA PoliceDistrict.zip (files dated 2025-07-31)",
       wb("20260506045720",
          "https://www.statssa.gov.za/wp-content/uploads/2025/08/PoliceDistrict.zip"),
       "https://www.statssa.gov.za/wp-content/uploads/2025/08/PoliceDistrict.zip",
       "statssa/PoliceDistrict_2025.zip", "current precincts (base geometry)"),
  # SAPS station-level workbooks -- station x FY presence only
  list("saps_stats_2013", "SAPS police station figures per province, FY2003/04-2012/13",
       wb("20140819181803",
          paste0(saps_old, "/2013/downloads/police_station_figures_per_province.xls")),
       paste0(saps_old, "/2013/downloads/police_station_figures_per_province.xls"),
       "saps/stats_2003_2013.xls", "station opening years"),
  list("saps_stats_2015", "SAPS crime stats 2014/15 release (station level)",
       wb("20151004041328",
          paste0(saps_old, "/2015/crimestats_2014_2015_v1.xlsx")),
       paste0(saps_old, "/2015/crimestats_2014_2015_v1.xlsx"),
       "saps/stats_2014_15.xlsx", "station opening years"),
  list("saps_stats_2021", "SAPS crime statistics 2020/21 release",
       wb("20220123072823",
          paste0(saps_d, "/Crime-Statistics-2020_2021-Release.xlsx")),
       paste0(saps_d, "/Crime-Statistics-2020_2021-Release.xlsx"),
       "saps/stats_2020_21.xlsx", "station opening years"),
  list("saps_stats_2024", "SAPS annual crime statistics 2023/24",
       wb("20240724054433", paste0(saps_d, "/2023-2024%20_Annual_Stats.xlsx")),
       paste0(saps_d, "/2023-2024%20_Annual_Stats.xlsx"),
       "saps/stats_2023_24.xlsx", "station opening years"),
  list("saps_stats_2026q4", "SAPS 2025/26 Q4 release (live site)",
       paste0(saps_d, "/2025/2025-2026_-_4th_Quarter_WEB.xlsx"),
       paste0(saps_d, "/2025/2025-2026_-_4th_Quarter_WEB.xlsx"),
       "saps/stats_2025_26_q4.xlsx", "station list 2025/26"),
  # MDB ward boundaries (MDB 'Know Your Wards' hub, public ArcGIS items)
  list("mdb_wards_2011", "MDB Wards 2011 (File Geodatabase item 12d2deb9...)",
       paste0(agol, "/12d2deb98816451ab7c4dc09cdfeee6b/data"),
       "https://spatialhub-mdb-sa.opendata.arcgis.com/ (MDB Wards 2011)",
       "mdb/wards_2011.zip", "ward vintage 2011"),
  list("mdb_wards_2016", "MDB Wards 2016 (File Geodatabase item cfddb54a...)",
       paste0(agol, "/cfddb54aab5f4d62b2144d80d49b3fdb/data"),
       "https://spatialhub-mdb-sa.opendata.arcgis.com/ (MDB Wards 2016)",
       "mdb/wards_2016.zip", "ward vintage 2016"),
  list("mdb_wards_2021", "MDB Wards 2021 = SA_Wards2020 delimitation (item e0223a82...)",
       paste0(agol, "/e0223a825ea2481fa72220ad3204276b/data"),
       "https://spatialhub-mdb-sa.opendata.arcgis.com/ (MDB Wards 2021)",
       "mdb/wards_2021.zip", "ward vintage 2021 (SWU base)")
))
setnames(src, c("id", "title", "url", "original_url", "dest", "role"))

# ---- Downloader -------------------------------------------------------------------
fetch <- function(i) {
  s <- src[i]
  dest <- file.path(dir_raw, s$dest)
  dir.create(dirname(dest), recursive = TRUE, showWarnings = FALSE)
  if (file.exists(dest) && !force) {
    log_msg("skip (exists):", s$dest)
    return(invisible("exists"))
  }
  log_msg("GET", s$id, "->", s$dest)
  h <- new_handle(useragent = ua, followlocation = TRUE, timeout = 900,
                  connecttimeout = 60)
  tmp <- paste0(dest, ".part")
  ok <- NA_integer_
  for (attempt in 1:3) {  # the Internet Archive drops connections intermittently
    ok <- tryCatch({
      res <- curl_fetch_disk(s$url, tmp, handle = h)
      res$status_code
    }, error = function(e) {
      log_msg("  ERROR (attempt", attempt, "):", conditionMessage(e)); NA_integer_
    })
    if (!is.na(ok) && ok == 200) break
    Sys.sleep(pause_s * 5 * attempt)
  }
  # A 200 that is actually an HTML challenge page is a failure, not a file.
  is_html <- file.exists(tmp) && {
    b <- readBin(tmp, "raw", n = 300)
    b <- b[b >= as.raw(32) & b < as.raw(127)]  # printable ASCII only
    grepl("<html", tolower(rawToChar(b)), fixed = TRUE)
  }
  if (is.na(ok) || ok != 200 || is_html) {
    unlink(tmp)
    log_msg("  FAILED:", s$id, "status", ok, if (is_html) "(HTML challenge)")
    append_provenance(list(
      id = s$id, title = s$title, url = s$url, original_url = s$original_url,
      dest = s$dest, role = s$role, retrieved_utc = format(Sys.time(), tz = "UTC"),
      bytes = NA, sha256 = NA, status = paste0("FAILED_", ok)))
    return(invisible("failed"))
  }
  file.rename(tmp, dest)
  append_provenance(list(
    id = s$id, title = s$title, url = s$url, original_url = s$original_url,
    dest = s$dest, role = s$role, retrieved_utc = format(Sys.time(), tz = "UTC"),
    bytes = file.size(dest), sha256 = sha256_file(dest), status = "OK"))
  Sys.sleep(pause_s)
  invisible("ok")
}

status <- vapply(seq_len(nrow(src)), fetch, character(1))

# Unzip archives next to themselves (idempotent)
for (z in list.files(dir_raw, pattern = "\\.zip$", recursive = TRUE, full.names = TRUE)) {
  exdir <- sub("\\.zip$", "", z)
  if (!dir.exists(exdir) || force) unzip(z, exdir = exdir, overwrite = TRUE)
}

# ---- GHSL GHS-POP epoch 2010 (provisional SWU weights only) -----------------------
# JRC GHS-POP R2023A, 3 arc-second tiles (CC-BY 4.0). Used solely when SAL
# dwellings are unavailable; every output built on it goes to
# data/cleaned/units/provisional/. (WorldPop 2011 was tried first but its server
# refuses HTTP range requests, and the national file is 746 MB.)
ghsl_base <- paste0(
  "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/",
  "GHS_POP_E2010_GLOBE_R2023A_4326_3ss/V1-0/tiles/")
ghsl_tiles <- list(
  gauteng  = list(tile = "R12_C21", win = c(27.55, 29.15, -26.90, -25.05)),
  capetown = list(tile = "R13_C20", win = c(18.25, 19.10, -34.40, -33.40)))
dir.create(file.path(dir_raw, "ghsl"), showWarnings = FALSE)
for (nm in names(ghsl_tiles)) {
  t <- ghsl_tiles[[nm]]
  zname <- sprintf("GHS_POP_E2010_GLOBE_R2023A_4326_3ss_V1_0_%s.zip", t$tile)
  src <- rbind(src, data.table(
    id = paste0("ghsl_pop2010_", t$tile),
    title = sprintf("GHS-POP E2010 R2023A 3ss tile %s (%s)", t$tile, nm),
    url = paste0(ghsl_base, zname), original_url = paste0(ghsl_base, zname),
    dest = file.path("ghsl", zname),
    role = "PROVISIONAL SWU weights / precinct exchange materiality"))
  fetch(nrow(src))
  zpath <- file.path(dir_raw, "ghsl", zname)
  dest <- file.path(dir_raw, "ghsl", sprintf("ghs_pop_2010_%s.tif", nm))
  if (file.exists(dest) && !force) { log_msg("skip (exists):", basename(dest)); next }
  tifname <- sub("\\.zip$", ".tif", zname)
  unzip(zpath, files = tifname, exdir = tempdir(), overwrite = TRUE)
  r <- rast(file.path(tempdir(), tifname))
  e <- t$win
  r_c <- crop(r, ext(e[1], e[2], e[3], e[4]))
  writeRaster(r_c, dest, overwrite = TRUE, gdal = c("COMPRESS=DEFLATE"))
  unlink(file.path(tempdir(), tifname))
  append_provenance(list(
    id = paste0("ghsl_pop2010_", nm, "_crop"),
    title = sprintf("Crop of %s to %s window [%s]", t$tile, nm, paste(e, collapse = ", ")),
    url = paste0(ghsl_base, zname), original_url = paste0(ghsl_base, zname),
    dest = file.path("ghsl", basename(dest)),
    role = "PROVISIONAL SWU weights / precinct exchange materiality",
    retrieved_utc = format(Sys.time(), tz = "UTC"), bytes = file.size(dest),
    sha256 = sha256_file(dest), status = "OK (derived crop)"))
}

# ---- Census 2011 SAL (manual) ---------------------------------------------------------
# DataFirst study 517 (South African Census Community Profiles 2011) holds the
# SAL-level Stata files and the Stats SA SAL GIS layer. It needs a free
# DataFirst account, so the agent does not fetch it.
saccp_needed <- c("type-of-main-dwelling", "population-group",
                  "population-group-household-head", "household-income-annual",
                  "household-size", "geo-type", "enumeration-area-type",
                  "tenure-status")
have_tab <- vapply(saccp_needed, function(f) {
  length(list.files(dir_saccp, pattern = paste0("^", f, "\\.(dta|csv)$"),
                    recursive = TRUE, ignore.case = TRUE)) > 0
}, logical(1))
have_gis <- length(list.files(dir_saccp, pattern = "\\.(shp|gpkg)$|\\.gdb$",
                              recursive = TRUE, include.dirs = TRUE,
                              ignore.case = TRUE)) > 0
saccp_ok <- all(have_tab) && have_gis
append_provenance(list(
  id = "census2011_saccp", title = "Census 2011 Community Profiles (SAL) + SAL GIS",
  url = "https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/517",
  original_url = "Statistics South Africa via DataFirst (doi pending on page)",
  dest = "census2011_saccp/", role = "SAL dwellings, covariates, calibration margins",
  retrieved_utc = format(Sys.time(), tz = "UTC"), bytes = NA, sha256 = NA,
  status = if (saccp_ok) "PRESENT (manual)" else "MANUAL_REQUIRED"))
if (!saccp_ok) {
  message(conditionMessage(stop_manual(
    component = "Census 2011 SAL boundaries + SAL attribute tables",
    files = c(paste0(saccp_needed[!have_tab], ".dta"),
              if (!have_gis) "Stats SA Census 2011 Small Area Layer (SAL) GIS files"),
    url = "https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/517/get-microdata",
    dest = dir_saccp,
    extra = paste(
      "Free DataFirst account needed. Keep file names as delivered; any",
      "subfolder is fine. 01_precinct_clusters.R runs without these;",
      "02 runs only in PROVISIONAL mode; 03 stops until they are present.")
  )))
}

prov <- fread(provenance_file)
log_msg("Provenance rows:", nrow(prov), "| failed:", sum(grepl("FAILED", prov$status)),
        "| manual:", sum(prov$status == "MANUAL_REQUIRED"))
if (any(grepl("FAILED", prov$status))) quit(status = 1)

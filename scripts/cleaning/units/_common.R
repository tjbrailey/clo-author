# ==============================================================================
# _common.R -- Shared configuration and helpers for the units pipeline (WP2)
# Project: PSC Exposure (enclosure, private guarding, state attitudes; SA)
# Author:  data-engineer agent for Thomas Brailey
# Date:    2026-09-30
# Purpose: Paths, metro scope, CRS, logging, provenance, name normalisation and
#          the generic overlap-graph / crosswalk helpers used by 01-03 and the
#          tests. Sourced by every script in scripts/cleaning/units/.
# Inputs:  none (sourced)
# Outputs: none (defines objects and functions)
# ==============================================================================

suppressPackageStartupMessages({
  library(sf)
  library(data.table)
  library(arrow)
  library(here)
  library(igraph)
  library(digest)
})

sf_use_s2(FALSE)  # planar ops in a projected CRS; s2 is slower and stricter here

# ---- Paths --------------------------------------------------------------------
dir_raw     <- here("data", "raw", "units")
dir_clean   <- here("data", "cleaned", "units")
dir_prov    <- file.path(dir_clean, "provisional")
dir_report  <- here("quality_reports", "pilot")
dir_fig     <- here("paper", "figures")
dir_intermediate <- file.path(dir_clean, "intermediate")
for (d in c(dir_raw, dir_clean, dir_report, dir_fig, dir_intermediate)) {
  dir.create(d, recursive = TRUE, showWarnings = FALSE)
}
provenance_file <- file.path(dir_raw, "provenance.csv")

# Census 2011 community profiles + SAL layer (manual download; DataFirst #517)
dir_saccp <- file.path(dir_raw, "census2011_saccp")

# ---- Scope --------------------------------------------------------------------
# MDB category-A codes are stable across the 2011/2016/2021 delimitations.
metros <- data.table(
  metro_code = c("JHB", "TSH", "EKU", "CPT"),
  metro_name = c("City of Johannesburg", "City of Tshwane",
                 "City of Ekurhuleni", "City of Cape Town"),
  province   = c("GT", "GT", "GT", "WC")
)

# South African Albers equal-area (standard parallels -24/-33, CM 24E): all
# areas, overlaps and buffers are computed in metres in this CRS.
crs_sa_albers <- paste(
  "+proj=aea +lat_1=-24 +lat_2=-33 +lat_0=0 +lon_0=24 +x_0=0 +y_0=0",
  "+datum=WGS84 +units=m +no_defs"
)

# ---- Pre-specified thresholds (memo 2.6 / 7; changing these = re-run) --------
swu_nest_tau      <- 0.05   # >= 95% population nesting -> no merge edge
swu_nest_tau_sens <- 0.10   # sensitivity
pcl_parent_min_share <- 0.05  # child-area share of a parent overlap to count
sliver_m2         <- 1000   # intersections below 1,000 m2 treated as slivers

# ---- Logging ------------------------------------------------------------------
log_msg <- function(...) {
  cat(format(Sys.time(), "%H:%M:%S"), "|", ..., "\n", sep = " ")
}

stop_manual <- function(component, files, url, dest, extra = NULL) {
  msg <- paste0(
    "\n==================== MANUAL DOWNLOAD REQUIRED ====================\n",
    "Component: ", component, "\n",
    "Source:    ", url, "\n",
    "Needed:    ", paste(files, collapse = "\n           "), "\n",
    "Place in:  ", dest, "\n",
    if (!is.null(extra)) paste0("Notes:     ", extra, "\n") else "",
    "==================================================================\n"
  )
  structure(class = c("manual_download", "error", "condition"),
            list(message = msg, call = NULL))
}

# ---- Provenance ---------------------------------------------------------------
sha256_file <- function(path) digest(file = path, algo = "sha256")

append_provenance <- function(row) {
  row <- as.data.table(row)
  if (file.exists(provenance_file)) {
    old <- fread(provenance_file, colClasses = "character")
    old <- old[!(dest == row$dest)]
    row <- rbind(old, row[, lapply(.SD, as.character)], fill = TRUE)
  }
  fwrite(row, provenance_file)
}

# ---- Names --------------------------------------------------------------------
# SAPS spells stations inconsistently across releases (case, hyphens); matching
# is on a normalised key plus an explicit rename table. Parenthetical province
# tags are KEPT as a suffix because they separate homonyms nationally
# ("HEIDELBERG (GP)" vs "HEIDELBERG(C)", "MIDDELBURG(EC)", "RICHMOND(C)").
norm_station <- function(x) {
  x <- toupper(trimws(x))
  x <- iconv(x, to = "ASCII//TRANSLIT")
  x <- gsub("[()]", " ", x)
  x <- gsub("[-/'`.,]", " ", x)
  x <- gsub("\\bSAPS\\b|\\bPOLICE STATION\\b", " ", x)
  x <- gsub("\\s+", " ", trimws(x))
  x
}

# ---- Geometry helpers ---------------------------------------------------------
read_layer_albers <- function(path, layer = NULL) {
  g <- if (is.null(layer)) st_read(path, quiet = TRUE)
       else st_read(path, layer = layer, quiet = TRUE)
  g <- st_zm(g, drop = TRUE, what = "ZM")
  g <- st_make_valid(st_transform(g, crs_sa_albers))
  g <- st_collection_extract(g, "POLYGON", warn = FALSE)
  g
}

area_m2 <- function(g) as.numeric(st_area(g))

# Intersect two polygon layers and return a data.table of piece areas. Pieces
# under `sliver_m2` are dropped as digitising noise and counted for the report.
overlay_areas <- function(a, b, id_a, id_b) {
  a <- a[, id_a]; b <- b[, id_b]
  x <- suppressWarnings(st_intersection(a, b))
  x <- st_collection_extract(x, "POLYGON", warn = FALSE)
  dt <- data.table(st_drop_geometry(x))
  dt[, area := area_m2(x)]
  dt <- dt[, .(area = sum(area)), by = c(id_a, id_b)]
  dt
}

# Connected components of a bipartite/multipartite overlap graph.
# edges: data.table with columns from, to (character node ids).
# nodes: character vector of all node ids (isolated nodes form singletons).
overlap_components <- function(edges, nodes) {
  g <- graph_from_data_frame(unique(edges[, .(from, to)]), directed = FALSE,
                             vertices = data.frame(name = unique(nodes)))
  comp <- components(g)$membership
  data.table(node = names(comp), comp = as.integer(comp))
}

# Row-normalise apportionment weights so they sum to 1 per source unit.
normalise_weights <- function(dt, by, w = "w") {
  dt[, (w) := get(w) / sum(get(w)), by = by]
  dt
}

# ---- Population surface (GHSL GHS-POP 2010; provisional/materiality only) -----
ghsl_files <- function() {
  f <- file.path(dir_raw, "ghsl", c("ghs_pop_2010_gauteng.tif",
                                    "ghs_pop_2010_capetown.tif"))
  f[file.exists(f)]
}

# Sum of GHSL persons inside each polygon, by cell centre (~90 m cells). Exact
# cell-fraction weighting was ~100x slower and changes nothing at the 5%
# materiality thresholds used here; pieces smaller than a cell can read 0.
# Returns NA where a polygon lies outside both crop windows.
pop_in_polys <- function(g) {
  fs <- ghsl_files()
  if (length(fs) == 0) stop("GHSL crops missing: run 00_download.R")
  v <- terra::vect(st_transform(st_geometry(g), 4326))
  tot <- rep(0, nrow(g)); hit <- rep(FALSE, nrow(g))
  for (f in fs) {
    r <- terra::rast(f)
    inside <- terra::relate(v, terra::as.polygons(terra::ext(r), crs = terra::crs(r)),
                            "intersects")[, 1]
    if (!any(inside)) next
    e <- terra::extract(r, v[inside], fun = "sum", na.rm = TRUE, ID = FALSE)
    tot[inside] <- tot[inside] + fcoalesce(e[[1]], 0)
    hit[inside] <- TRUE
  }
  tot[!hit] <- NA_real_
  tot
}

write_gpkg <- function(x, path, layer) {
  if (file.exists(path)) unlink(path)
  st_write(x, path, layer = layer, quiet = TRUE, delete_dsn = TRUE)
}

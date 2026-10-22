# ==============================================================================
# test_units.R -- Tests for the units pipeline (WP2)
# Project: PSC Exposure
# Author:  data-engineer agent for Thomas Brailey
# Date:    2026-09-30
# Purpose: (A) synthetic-fixture tests of the crosswalk / SWU / graph helpers
#          (always run); (B) checks on the real outputs in data/cleaned/units
#          (skipped with a message when an output does not exist yet, e.g. SAL-
#          dependent files before the DataFirst download).
# Usage:   Rscript -e 'testthat::test_file("scripts/cleaning/units/tests/test_units.R",
#                        stop_on_failure = TRUE)'   (non-zero exit on failure)
# Note:    SWU checks read data/cleaned/units/ if swu.gpkg exists there (SAL mode),
#          otherwise the provisional outputs in data/cleaned/units/provisional/.
# ==============================================================================

source(here::here("scripts", "cleaning", "units", "_common.R"))
source(here::here("scripts", "cleaning", "units", "_swu_functions.R"))
suppressPackageStartupMessages(library(testthat))

sq <- function(x0, y0, x1, y1) st_polygon(list(rbind(c(x0, y0), c(x1, y0), c(x1, y1),
                                                     c(x0, y1), c(x0, y0))))
mk <- function(ids, polys) st_sf(wid = ids, geometry = st_sfc(polys, crs = crs_sa_albers))

# ---- (A) Fixtures ------------------------------------------------------------------
# 2011: left/right halves of a 2 km x 1 km block. 2016: same, but the boundary
# moved 20 m east (2% of the right ward). 2021: right half split in two.
w11 <- mk(c("W11_a", "W11_b"), list(sq(0, 0, 1000, 1000), sq(1000, 0, 2000, 1000)))
w16 <- mk(c("W16_a", "W16_b"), list(sq(0, 0, 1020, 1000), sq(1020, 0, 2000, 1000)))
w21 <- mk(c("W21_a", "W21_b", "W21_c"),
          list(sq(0, 0, 1020, 1000), sq(1020, 0, 2000, 500), sq(1020, 500, 2000, 1000)))
fx <- data.table(st_drop_geometry(build_pieces(w11, w16, w21)))
fx[, weight := area / 1e4]  # uniform density

test_that("fixture crosswalk weights sum to 1 per source ward", {
  cw <- crosswalk(fx, "w11", "w21")
  expect_equal(cw[, sum(w), by = src]$V1, c(1, 1), tolerance = 1e-12)
  expect_equal(cw[src == "W11_b" & tgt == "W21_a", w], 0.02, tolerance = 1e-9)
})

test_that("fixture SWUs: 2% shift does not merge, a split does", {
  comp <- swu_components(fx, 0.05)
  cb <- comp[wid %in% c("W11_b", "W16_b", "W21_b", "W21_c"), uniqueN(comp)]
  expect_equal(cb, 1)
  expect_false(comp[wid == "W21_a", comp] == comp[wid == "W21_b", comp])
  # at tau = 0.01 the 2% shift chains everything together
  expect_equal(uniqueN(swu_components(fx, 0.01)$comp), 1)
})

test_that("residual gaps preserve ward totals", {
  tot <- data.table(vintage = "w11", wid = c("W11_a", "W11_b"), area = c(1e6, 1.2e6),
                    weight = c(100, 150))
  tot <- rbind(tot, fx[, .(area = sum(area), weight = sum(weight)), by = .(wid = w16)][
    , vintage := "w16"], fx[, .(area = sum(area), weight = sum(weight)), by = .(wid = w21)][
    , vintage := "w21"])
  g <- add_residual_gaps(copy(fx)[, piece_id := seq_len(.N)], tot)
  expect_equal(g[!is.na(w11), sum(weight), by = w11][order(w11)]$V1, c(100, 150))
  expect_equal(sum(g$gap), 1)  # only W11_b has an excess
})

test_that("graph components keep isolated nodes", {
  cc <- overlap_components(data.table(from = "a", to = "b"), c("a", "b", "c"))
  expect_equal(uniqueN(cc$comp), 2)
})

test_that("station names normalise and keep homonyms apart", {
  expect_equal(norm_station("Heidelberg (Gp)"), "HEIDELBERG GP")
  expect_false(norm_station("HEIDELBERG(C)") == norm_station("HEIDELBERG (GP)"))
  expect_equal(norm_station(" Jhb  Central "), "JHB CENTRAL")
})

# ---- (A2) Synthetic SAL fixture (exercises _sal.R without the Census download) -----
source(here::here("scripts", "cleaning", "units", "_sal.R"))

make_sal_fixture <- function(drop_col = NULL, code_offset = 0L) {
  d <- tempfile("saccp"); dir.create(d)
  codes <- c(1001L, 1002L, 1003L)
  tab <- function(name, map, vals) {
    x <- data.table(sal_code = codes + code_offset)
    for (k in names(map)) x[, (k) := vals]
    if (!is.null(drop_col) && name == "type-of-main-dwelling") x[, (drop_col) := NULL]
    fwrite(x, file.path(d, paste0(name, ".csv")))
  }
  tab("type-of-main-dwelling", dw_map, c(3, 6, 9))
  tab("household-income-annual", c(inc_map, inchh_13 = "u"), c(3, 3, 3))
  tab("population-group-household-head", race_map, c(3, 0, 3))
  tab("population-group", c(pgrp_1 = 1, pgrp_2 = 1, pgrp_3 = 1, pgrp_4 = 1, pgrp_5 = 1),
      c(6, 6, 6))
  tab("tenure-status", c(tensta_1 = 1, tensta_2 = 1, tensta_3 = 1, tensta_4 = 1, tensta_5 = 1),
      c(3, 3, 3))
  tab("enumeration-area-type", setNames(rep(1, 10), paste0("eatyp_", 1:10)), c(3, 3, 3))
  tab("household-size", setNames(rep(1, 10), paste0("hhsize_", 1:10)), c(3, 3, 3))
  for (nm in c("geo-type")) fwrite(data.table(sal_code = codes, geotype_1 = 3),
                                   file.path(d, paste0(nm, ".csv")))
  sq1 <- function(x0) st_polygon(list(rbind(c(x0, 0), c(x0 + 1000, 0), c(x0 + 1000, 1000),
                                            c(x0, 1000), c(x0, 0))))
  g <- st_sf(SAL_CODE = codes, geometry = st_sfc(sq1(0), sq1(1000), sq1(2000),
                                                 crs = crs_sa_albers))
  st_write(g, file.path(d, "sal.gpkg"), quiet = TRUE)
  d
}
with_sal_dir <- function(d, code) {
  old <- get("dir_saccp", envir = globalenv())
  assign("dir_saccp", d, envir = globalenv())
  on.exit(assign("dir_saccp", old, envir = globalenv()))
  force(code)
}

test_that("synthetic SAL fixture: loaders, long form and apportionment", {
  d <- make_sal_fixture()
  with_sal_dir(d, {
    expect_true(sal_available())
    sal <- read_sal_geom()
    expect_equal(nrow(sal), 3)
    L <- sal_long()
    dw <- L[dimension == "dwelling_type", .(dwellings = sum(n)), by = sal_code]
    expect_equal(nrow(dw), 3)
    expect_equal(dw$dwellings[1], 3 * length(dw_map))   # 13 dwelling columns x 3
    expect_equal(assert_sal_match(sal$sal_code, dw$sal_code), 1)
    # a unit covering the left half of SAL 1002 and all of SAL 1001
    u <- st_sf(uid = "u1", geometry = st_sfc(st_polygon(list(rbind(
      c(0, 0), c(1500, 0), c(1500, 1000), c(0, 1000), c(0, 0)))), crs = crs_sa_albers))
    a <- sal_to_units(sal, u, "uid")
    expect_equal(a[sal_code == "1001", share], 1, tolerance = 1e-9)
    expect_equal(a[sal_code == "1002", share], 0.5, tolerance = 1e-9)
    expect_equal(nrow(sal_income_mean()), 3)
  })
})

test_that("SAL guards: missing column, and poor SAL code match, fail loudly", {
  d <- make_sal_fixture(drop_col = "dwltyp_5")
  with_sal_dir(d, expect_error(sal_long(), "missing expected columns"))
  # polygons and tables with different code formats match < 99% -> stop
  d2 <- make_sal_fixture(code_offset = 500L)
  with_sal_dir(d2, {
    sal <- read_sal_geom()
    dw <- sal_long()[dimension == "dwelling_type", .(dwellings = sum(n)), by = sal_code]
    expect_error(assert_sal_match(sal$sal_code, dw$sal_code), "code match")
  })
  # optional columns (dwltyp_13) may be absent
  d3 <- make_sal_fixture(drop_col = "dwltyp_13")
  with_sal_dir(d3, expect_silent(sal_long()))
})

# ---- (B) Real outputs --------------------------------------------------------------
pq <- function(...) {
  f <- file.path(...)
  if (!file.exists(f)) skip(paste("not built yet:", f))
  as.data.table(read_parquet(f))
}
swu_dir <- if (file.exists(file.path(dir_clean, "swu.gpkg"))) dir_clean else dir_prov

test_that("ward crosswalk weights sum to 1 per source ward (2011, 2016)", {
  for (v in c("2011", "2016")) {
    cw <- pq(swu_dir, sprintf("ward_crosswalk_%s_to_2021.parquet", v))
    s <- cw[, .(s = sum(w)), by = c(paste0("ward_", v))]
    expect_lt(max(abs(s$s - 1)), 1e-9)
    expect_true(all(cw$w >= 0))
  }
})

test_that("every ward of every vintage belongs to exactly one SWU", {
  wts <- pq(swu_dir, "ward_to_swu.parquet")
  expect_false(anyDuplicated(wts$wid) > 0)
  expect_false(any(is.na(wts$swu_id)))
  cnt <- pq(swu_dir, "intermediate", "ward_counts.parquet")
  expect_equal(wts[, .N, by = vintage][order(vintage)]$N,
               cnt[, sum(N), by = vintage][order(vintage)]$V1)
  # nesting: weight outside own SWU < 5% per vintage (memo 95% rule)
  out <- wts[, .(out = 1 - sum(weight_in_swu) / sum(weight)), by = vintage]
  expect_true(all(out$out < 0.05))
  # 2021 wards nest exactly (SWUs are unions of 2021 wards)
  expect_gt(min(wts[vintage == "2021" & weight > 0, share_in_swu]), 0.999)
})

test_that("SWU geometry partitions the 2021 wards", {
  f <- file.path(swu_dir, "swu.gpkg"); if (!file.exists(f)) skip("no swu.gpkg")
  s <- st_read(f, layer = "swu", quiet = TRUE)
  w <- st_read(f, layer = "wards_2021", quiet = TRUE)
  expect_equal(sum(s$n_w21), nrow(w))
  expect_equal(sum(area_m2(s)) / sum(area_m2(w)), 1, tolerance = 1e-4)
})

test_that("precinct clusters: one cluster per station, no overlaps", {
  s2c <- pq(dir_clean, "station_to_cluster.parquet")
  expect_false(anyDuplicated(s2c$station_id) > 0)
  expect_false(any(is.na(s2c$cluster_id)))
  f <- file.path(dir_clean, "precinct_clusters.gpkg")
  cl <- st_read(f, layer = "precinct_clusters", quiet = TRUE)
  st <- st_read(f, layer = "stations_2025", quiet = TRUE)
  expect_equal(sum(cl$n_stations[!is.na(cl$n_stations)]) >= nrow(st), TRUE)
  expect_equal(sum(area_m2(cl)) / sum(area_m2(st)), 1, tolerance = 1e-4)
  # every active in-panel station without its own polygon is attached to a host
  np <- s2c[has_2025_polygon == FALSE & !is.na(first_active_fy)]
  expect_true(all(np$n_members > 1))
})

test_that("cluster panel is stable: every in-scope cluster reports every FY", {
  s2c <- pq(dir_clean, "station_to_cluster.parquet")
  act <- pq(dir_clean, "intermediate", "station_fy_active.parquet")
  x <- merge(act[fy >= 2005 & fy <= 2025], s2c[in_scope == TRUE, .(station_id, cluster_id)],
             by = "station_id")
  cov <- x[, .(any_active = any(active)), by = .(cluster_id, fy)]
  expect_true(all(cov$any_active))
  expect_equal(cov[, uniqueN(fy), by = cluster_id][, unique(V1)], 21L)
  # clusters contain a station fully active in FY2005/06 (not only children)
  cl <- st_read(file.path(dir_clean, "precinct_clusters.gpkg"), "precinct_clusters",
                quiet = TRUE)
  expect_true(all(cl$n_active_fy2005[cl$in_scope] >= 1))
  # every station opened within the panel sits in a multi-station cluster
  expect_true(all(s2c[opened_in_panel == TRUE, n_members] > 1))
})

test_that("SAL assignment: exactly one SWU and cluster, or flagged", {
  su <- pq(dir_clean, "sal_units.parquet")
  expect_false(anyDuplicated(su$sal_code) > 0)
  inside <- su[flag_outside == FALSE]
  expect_true(all(!is.na(inside$swu_id)))
  expect_true(all(!is.na(inside$cluster_id) | inside$flag_no_pcl))
})

test_that("dwelling totals are preserved under aggregation", {
  sc <- pq(dir_clean, "sal_covariates.parquet")
  sw <- pq(dir_clean, "swu_covariates.parquet")
  su <- pq(dir_clean, "sal_units.parquet")
  tot <- sc[sal_code %in% su[flag_outside == FALSE, sal_code], sum(households)]
  expect_equal(sum(sw$households) / tot, 1, tolerance = 0.01)
  cal <- pq(dir_clean, "calibration_margins_swu.parquet")
  expect_equal(cal[, sum(share), by = .(swu_id, dimension)][, range(V1)], c(1, 1),
               tolerance = 1e-9)
})

# ==============================================================================
# _swu_functions.R -- Ward overlay, crosswalk and stable-ward-unit helpers
# Project: PSC Exposure (memo 2.6: "SWU: >= 95% population overlap, otherwise
#          the smallest nesting union. The merged share is reported.")
# Author:  data-engineer agent for Thomas Brailey
# Date:    2026-09-30
# Purpose: Pure functions (no I/O) used by 02_stable_ward_units.R and the tests.
#   build_pieces()   three-way overlay of 2011/2016/2021 wards into atoms
#   crosswalk()      source-ward -> 2021-ward apportionment weights (sum to 1)
#   swu_components() stable ward units as connected components of the
#                    population-overlap graph with nesting tolerance tau
# ==============================================================================

# Atoms of the 2011 x 2016 x 2021 overlay. Inputs are sf polygons in a projected
# CRS with a column `wid` (unique across vintages). Areas outside a vintage's
# coverage get NA for that vintage (e.g. land moved out of a metro).
build_pieces <- function(w11, w16, w21, min_area = 0) {
  a <- w11[, "wid"]; names(a)[names(a) == "wid"] <- "w11"
  b <- w16[, "wid"]; names(b)[names(b) == "wid"] <- "w16"
  c <- w21[, "wid"]; names(c)[names(c) == "wid"] <- "w21"
  ab <- suppressWarnings(st_intersection(a, b))
  ab <- st_collection_extract(ab, "POLYGON", warn = FALSE)
  abc <- suppressWarnings(st_intersection(ab, c))
  abc <- st_collection_extract(abc, "POLYGON", warn = FALSE)
  abc$area <- as.numeric(st_area(abc))
  abc <- abc[abc$area > min_area, c("w11", "w16", "w21", "area")]
  abc$piece_id <- seq_len(nrow(abc))
  abc
}

# Coverage gaps as residual rows (much cheaper than geometric differences):
# for each ward, whatever area/weight is not in a full three-way atom (land
# outside another vintage's metro, digitising gaps) becomes one row carrying
# only that ward's id. totals: data.table(wid, vintage in w11/w16/w21, area, weight).
add_residual_gaps <- function(pdt, totals, min_area = 1e4) {
  res <- rbindlist(lapply(c("w11", "w16", "w21"), function(v) {
    s <- pdt[, .(area_p = sum(area), weight_p = sum(weight)), by = c(v)]
    setnames(s, v, "wid")
    t <- merge(totals[vintage == v], s, by = "wid", all.x = TRUE)
    t[is.na(area_p), `:=`(area_p = 0, weight_p = 0)]
    t <- t[, .(wid, area = pmax(area - area_p, 0), weight = pmax(weight - weight_p, 0))]
    t <- t[area >= min_area | weight >= 1]
    if (!nrow(t)) return(NULL)
    out <- data.table(w11 = NA_character_, w16 = NA_character_, w21 = NA_character_,
                      area = t$area, weight = t$weight)
    out[[v]] <- t$wid
    out
  }))
  if (is.null(res) || !nrow(res)) return(pdt[, gap := FALSE][])
  res[, `:=`(piece_id = max(pdt$piece_id) + seq_len(.N), gap = TRUE)]
  rbind(pdt[, gap := FALSE], res, use.names = TRUE)
}

# Apportionment weights from source vintage `from` to target `to`.
# pieces: data.table with columns from, to, weight (population/dwellings), area.
# Weight-based shares; falls back to area shares for source wards with zero
# total weight (basis recorded). Rows with NA target are kept as "outside".
crosswalk <- function(pieces, from, to) {
  p <- pieces[!is.na(get(from))]
  p <- p[, .(weight = sum(weight), area = sum(area)), by = c(from, to)]
  setnames(p, c(from, to), c("src", "tgt"))
  p[, `:=`(w_tot = sum(weight), a_tot = sum(area)), by = src]
  p[, basis := fifelse(w_tot > 0, "weight", "area")]
  p[, w := fifelse(w_tot > 0, weight / w_tot, area / a_tot)]
  p[, w_area := area / a_tot]
  p[, .(src, tgt, w, w_area, weight, area, basis)]
}

# Stable ward units. An edge joins two wards of different vintages whenever
# their overlap holds >= tau of EITHER ward's weight; components of this graph
# nest every constituent ward to within tau. Returns ward -> swu membership.
swu_components <- function(pieces, tau, vint = c("w11", "w16", "w21")) {
  pr <- list(c("w11", "w21"), c("w16", "w21"), c("w11", "w16"))
  pr <- Filter(function(v) all(v %in% vint), pr)
  edges <- rbindlist(lapply(pr, function(v) {
    p <- pieces[!is.na(get(v[1])) & !is.na(get(v[2]))]
    p <- p[, .(weight = sum(weight), area = sum(area)), by = v]
    setnames(p, v, c("a", "b"))
    ta <- pieces[!is.na(get(v[1])), .(wa = sum(weight), aa = sum(area)), by = c(v[1])]
    tb <- pieces[!is.na(get(v[2])), .(wb = sum(weight), ab = sum(area)), by = c(v[2])]
    setnames(ta, 1, "a"); setnames(tb, 1, "b")
    p <- merge(merge(p, ta, by = "a"), tb, by = "b")
    p[, s := pmax(fifelse(wa > 0, weight / wa, area / aa),
                  fifelse(wb > 0, weight / wb, area / ab))]
    p[s >= tau, .(from = a, to = b, s)]
  }))
  nodes <- unique(na.omit(unlist(pieces[, ..vint])))
  comp <- overlap_components(if (nrow(edges)) edges else
                               data.table(from = character(), to = character()), nodes)
  setnames(comp, c("wid", "comp"))
  comp
}

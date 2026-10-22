# ==============================================================================
# 02_stable_ward_units.R -- 2011/2016/2021 wards -> stable ward units (SWU)
# Project: PSC Exposure (memo 2.6: SWU = >= 95% population overlap, otherwise the
#          smallest nesting union; merged share reported; 2021 wards as base)
# Author:  data-engineer agent for Thomas Brailey
# Date:    2026-09-30
# Purpose: Overlay MDB ward delimitations 2011, 2016 and 2021 (the 2020
#          delimitation used at the 2021 elections) for the four metros; weight
#          every overlay atom by Census 2011 SAL dwellings (area-apportioned
#          within split SALs); derive source->2021 crosswalks whose weights sum
#          to 1 per source ward; form SWUs as connected components of the
#          overlap graph at nesting tolerance tau = 0.05.
# Modes:   SAL (default)  -- requires the DataFirst study-517 files; writes to
#                            data/cleaned/units/
#          PROVISIONAL    -- PSC_UNITS_PROVISIONAL=1 and SAL absent: GHSL
#                            GHS-POP 2010 persons replace SAL dwellings; ALL
#                            outputs go to data/cleaned/units/provisional/ and
#                            carry weight_basis = "PROVISIONAL_ghsl_pop2010".
#          Otherwise the script stops with the manual-download message.
# Inputs:  data/raw/units/mdb/wards_{2011,2016,2021}; census2011_saccp (SAL mode)
#          or ghsl crops (provisional mode)
# Outputs: swu.gpkg (layers swu, wards_2021), ward_crosswalk_2011_to_2021.parquet,
#          ward_crosswalk_2016_to_2021.parquet, ward_to_swu.parquet,
#          intermediate/ward_pieces.parquet, intermediate/swu_sensitivity.parquet
# ==============================================================================

source(here::here("scripts", "cleaning", "units", "_common.R"))
source(here::here("scripts", "cleaning", "units", "_swu_functions.R"))
source(here::here("scripts", "cleaning", "units", "_sal.R"))

mode <- if (sal_available()) "sal" else
  if (identical(Sys.getenv("PSC_UNITS_PROVISIONAL"), "1")) "provisional" else NA
if (is.na(mode)) stop_if_no_sal("Stable ward units (SAL dwelling weights)")
out_dir <- if (mode == "sal") dir_clean else dir_prov
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
weight_basis <- if (mode == "sal") "census2011_sal_dwellings" else "PROVISIONAL_ghsl_pop2010"
log_msg("Mode:", mode, "| weights:", weight_basis, "| output:", out_dir)

# ---- Wards ----------------------------------------------------------------------
metro_codes <- metros$metro_code
w11 <- read_layer_albers(file.path(dir_raw, "mdb/wards_2011/MDBWard2011.gdb"))
n_raw11 <- nrow(w11)
w11 <- w11[!duplicated(w11$WardID), ]   # every 2011 feature is stored twice
w11 <- w11[w11$LocalMunicipalityCode %in% metro_codes, ]
w11$wid <- paste0("W11_", w11$WardID); w11$metro_code <- w11$LocalMunicipalityCode
w16 <- read_layer_albers(file.path(dir_raw, "mdb/wards_2016/MDBWard2016.gdb"))
w16 <- w16[w16$LocalMunicipalityCode %in% metro_codes, ]
w16$wid <- paste0("W16_", w16$WardID); w16$metro_code <- w16$LocalMunicipalityCode
w21 <- read_layer_albers(file.path(dir_raw, "mdb/wards_2021/SA_Wards2020.shp"))
w21 <- w21[w21$CAT_B %in% metro_codes, ]
w21$wid <- paste0("W21_", w21$WardID); w21$metro_code <- w21$CAT_B
agg1 <- function(g) {  # one feature per ward
  a <- aggregate(g[, "metro_code"], by = list(wid = g$wid), FUN = function(x) x[1])
  st_make_valid(a)
}
w11 <- agg1(w11); w16 <- agg1(w16); w21 <- agg1(w21)
ward_counts <- rbindlist(lapply(list(`2011` = w11, `2016` = w16, `2021` = w21), function(g)
  as.data.table(table(metro_code = g$metro_code))), idcol = "vintage")
log_msg("2011 layer: ", n_raw11, " features -> ", uniqueN(w11$wid), " metro wards kept after de-duplication")
print(dcast(ward_counts, metro_code ~ vintage, value.var = "N"))

# ---- Overlay atoms ------------------------------------------------------------------
log_msg("Three-way overlay")
pieces <- build_pieces(w11, w16, w21, min_area = 1)
log_msg("Atoms:", nrow(pieces), "| slivers < 1,000 m2:", sum(pieces$area < sliver_m2))

# ---- Weights ----------------------------------------------------------------------
# Households in housing units (dwelling types 1-13; "not applicable" excluded),
# area-apportioned within SALs split by a ward/atom boundary.
weigh <- function(g, id) {
  if (mode == "sal") {
    sp <- sal_to_units(sal, g, id)
    sp <- merge(sp, dw, by = "sal_code", all.x = TRUE)
    # after assert_sal_match every polygon SAL has a table row; any NA here is a
    # sliver SAL outside the match tolerance, reported rather than silently zeroed
    n_na <- sp[is.na(dwellings), uniqueN(sal_code)]
    if (n_na > 0) log_msg("SALs without a dwelling count, weight set to 0:", n_na)
    stopifnot(n_na <= 0.01 * uniqueN(sp$sal_code))
    sp[is.na(dwellings), dwellings := 0]
    sp[, .(weight = sum(dwellings * share)), by = .(id = uid)]
  } else {
    data.table(id = g[[id]], weight = fcoalesce(pop_in_polys(g), 0))
  }
}
if (mode == "sal") {
  sal <- read_sal_geom()
  sal <- sal[lengths(st_intersects(sal, st_union(w21))) > 0, ]
  dw <- sal_long()[dimension == "dwelling_type", .(dwellings = sum(n)), by = sal_code]
  assert_sal_match(sal$sal_code, dw$sal_code, what = "Dwelling-table")
}
pw <- weigh(pieces, "piece_id"); setnames(pw, "id", "piece_id")
pdt <- data.table(st_drop_geometry(pieces))
pdt <- merge(pdt, pw, by = "piece_id", all.x = TRUE)
pdt[is.na(weight), weight := 0]
totals <- rbindlist(lapply(list(w11 = w11, w16 = w16, w21 = w21), function(g) {
  w <- weigh(g, "wid"); setnames(w, "id", "wid")
  merge(data.table(wid = g$wid, area = area_m2(g)), w, by = "wid", all.x = TRUE)
}), idcol = "vintage")
totals[is.na(weight), weight := 0]
pdt <- add_residual_gaps(pdt, totals)
log_msg("Atom weight:", round(sum(pdt[gap == FALSE, weight])), "| residual gap rows:",
        sum(pdt$gap), "| gap weight:", round(sum(pdt[gap == TRUE, weight])))

# ---- Crosswalks ------------------------------------------------------------------
cw11 <- crosswalk(pdt, "w11", "w21"); cw16 <- crosswalk(pdt, "w16", "w21")
setnames(cw11, c("src", "tgt"), c("ward_2011", "ward_2021"))
setnames(cw16, c("src", "tgt"), c("ward_2016", "ward_2021"))
cw11[, weight_basis := weight_basis]; cw16[, weight_basis := weight_basis]
chk <- rbind(cw11[, .(s = sum(w)), by = ward_2011][, .(v = "2011", maxdev = max(abs(s - 1)))],
             cw16[, .(s = sum(w)), by = ward_2016][, .(v = "2016", maxdev = max(abs(s - 1)))])
print(chk); stopifnot(all(chk$maxdev < 1e-9))

# ---- SWUs ---------------------------------------------------------------------------
comp <- swu_components(pdt, swu_nest_tau)
wm <- rbindlist(list(data.table(wid = w11$wid, metro_code = w11$metro_code),
                     data.table(wid = w16$wid, metro_code = w16$metro_code),
                     data.table(wid = w21$wid, metro_code = w21$metro_code)))
comp <- merge(comp, wm, by = "wid")
# Name SWUs by metro and the smallest 2021 ward id they contain (deterministic)
nm <- comp[grepl("^W21_", wid), .(first21 = min(wid), metro_code = metro_code[1]), by = comp]
setorder(nm, metro_code, first21)
nm[, swu_id := sprintf("SWU_%s_%03d", metro_code, seq_len(.N)), by = metro_code]
orphan <- setdiff(unique(comp$comp), nm$comp)  # components without a 2021 ward
if (length(orphan)) log_msg("WARNING components without a 2021 ward:", length(orphan))
comp <- merge(comp, nm[, .(comp, swu_id)], by = "comp", all.x = TRUE)

# Share of each ward's weight that falls inside its own SWU (nesting quality)
s21 <- comp[grepl("^W21_", wid), .(w21 = wid, swu21 = swu_id)]
pdt <- merge(pdt, s21, by = "w21", all.x = TRUE)
nest <- rbindlist(lapply(c("w11", "w16", "w21"), function(v) {
  own <- comp[, .(wid, swu_own = swu_id)]
  x <- merge(pdt[!is.na(get(v))], own, by.x = v, by.y = "wid")
  x[, .(weight = sum(weight), area = sum(area),
        weight_in_swu = sum(weight[!is.na(swu21) & swu21 == swu_own]),
        area_in_swu = sum(area[!is.na(swu21) & swu21 == swu_own])),
    by = c(v, "swu_own")][, `:=`(vintage = substr(v, 2, 3))][]
}), use.names = FALSE)
setnames(nest, c("wid", "swu_id", "weight", "area", "weight_in_swu", "area_in_swu", "vintage"))
nest[, share_in_swu := fifelse(weight > 0, weight_in_swu / weight, area_in_swu / area)]
ward_to_swu <- merge(nest, comp[, .(wid, metro_code)], by = "wid")
ward_to_swu[, vintage := paste0("20", vintage)]
ward_to_swu[, weight_basis := weight_basis]

swu_attr <- comp[, .(n_w11 = sum(grepl("^W11_", wid)), n_w16 = sum(grepl("^W16_", wid)),
                     n_w21 = sum(grepl("^W21_", wid)),
                     wards_2021 = paste(sort(sub("W21_", "", wid[grepl("^W21_", wid)])),
                                        collapse = ";")),
                 by = .(swu_id, metro_code)]
swu_attr[, stable_single_ward := n_w11 == 1 & n_w16 == 1 & n_w21 == 1]
swu_w <- pdt[!is.na(swu21), .(weight_total = sum(weight)), by = .(swu_id = swu21)]
swu_attr <- merge(swu_attr, swu_w, by = "swu_id", all.x = TRUE)

w21s <- merge(w21, comp[grepl("^W21_", wid), .(wid, swu_id)], by = "wid")
swu <- aggregate(w21s[, "swu_id"], by = list(sid = w21s$swu_id), FUN = function(x) x[1])
swu <- st_make_valid(swu[, "sid"]); names(swu)[1] <- "swu_id"
swu <- merge(swu, swu_attr, by = "swu_id")
swu$area_km2 <- area_m2(swu) / 1e6
swu$weight_basis <- weight_basis
swu$rule <- sprintf(paste(
  "Connected components of 2011/2016/2021 wards linked when their overlap holds",
  ">= %.0f%% of either ward's %s; 2021 wards as geometry base."),
  100 * swu_nest_tau, weight_basis)

# ---- Summaries & sensitivity ----------------------------------------------------------
realloc <- pdt[!is.na(w11) & !is.na(w21)]
own11 <- comp[grepl("^W11_", wid), .(w11 = wid, swu11 = swu_id)]
realloc <- merge(realloc, own11, by = "w11")
realloc_share <- realloc[, .(reallocated_share_2011 = sum(weight[swu11 != swu21]) /
                               sum(weight)), by = .(metro_code = substr(swu21, 5, 7))]
# Sensitivity grid: nesting tolerance x which delimitations must nest. QoL III-IV
# sit on 2011 wards, V-6 on 2016 wards, 7 on 2021 wards (per-wave delimitation
# UNVERIFIED), so dropping a vintage is only an option for sub-panels.
grid <- CJ(tau = c(0.05, 0.10, 0.20, 0.25),
           vset = c("2011+2016+2021", "2016+2021", "2011+2021"))
sens <- rbindlist(lapply(seq_len(nrow(grid)), function(i) {
  t <- grid$tau[i]; vs <- paste0("w", substr(strsplit(grid$vset[i], "+", fixed = TRUE)[[1]], 3, 4))
  cc <- merge(swu_components(pdt, t, vs), wm, by = "wid")
  cc[, size21 := sum(grepl("^W21_", wid)), by = comp]
  cc[grepl("^W21_", wid), .(tau = t, vintages = grid$vset[i], swus = uniqueN(comp),
                            wards_2021 = .N, wards_2021_in_multiward_swu = sum(size21 > 1),
                            largest_swu_wards = max(size21)), by = metro_code]
}))
summary_tab <- swu_attr[, .(swus = .N, single_ward_stable = sum(stable_single_ward),
                            wards_2021 = sum(n_w21),
                            merged_share_2021_wards = sum(n_w21[n_w21 > 1]) / sum(n_w21)),
                        by = metro_code]
summary_tab <- merge(summary_tab, realloc_share, by = "metro_code", all.x = TRUE)
print(summary_tab[order(metro_code)]); print(sens)

# ---- Write -------------------------------------------------------------------------------
gp <- file.path(out_dir, "swu.gpkg")
if (file.exists(gp)) unlink(gp)
st_write(swu, gp, layer = "swu", quiet = TRUE)
st_write(merge(w21, comp[grepl("^W21_", wid), .(wid, swu_id)], by = "wid"),
         gp, layer = "wards_2021", quiet = TRUE, append = TRUE)
write_parquet(cw11, file.path(out_dir, "ward_crosswalk_2011_to_2021.parquet"))
write_parquet(cw16, file.path(out_dir, "ward_crosswalk_2016_to_2021.parquet"))
write_parquet(ward_to_swu, file.path(out_dir, "ward_to_swu.parquet"))
di <- file.path(out_dir, "intermediate"); dir.create(di, showWarnings = FALSE)
write_parquet(pdt[, .(piece_id, w11, w16, w21, area, weight)],
              file.path(di, "ward_pieces.parquet"))
write_parquet(sens, file.path(di, "swu_sensitivity.parquet"))
write_parquet(summary_tab, file.path(di, "swu_summary.parquet"))
write_parquet(ward_counts, file.path(di, "ward_counts.parquet"))
log_msg("Done:", nrow(swu), "SWUs written to", gp)

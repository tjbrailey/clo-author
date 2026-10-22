# ==============================================================================
# 03_sal_covariates.R -- Census 2011 SAL covariates, common support, calibration
# Project: PSC Exposure (memo 3.2 rule 1: common-support logit on Census 2011
#          income, freestanding share, race composition, density, distance to
#          the CBD; memo 6.3: calibration target = SAL composition by dwelling
#          type x race x income band)
# Author:  data-engineer agent for Thomas Brailey
# Date:    2026-09-30
# Purpose: (1) assign every SAL in the four metros to exactly one SWU and one
#          precinct cluster (majority area; split SALs flagged and apportioned
#          by area share); (2) derive SAL covariates; (3) aggregate counts to
#          SWU and cluster and build shares, density, distance to CBD;
#          (4) write the calibration margins.
# NOTE on 6.3: the community-profile files are one-way marginals by SAL, so the
#          calibration target delivered here is the three MARGINS (dwelling type,
#          household-head race, income band) for raking. The full three-way
#          joint cell target needs a SuperWEB2 cross-tab (Stats SA) -- flagged
#          in the units report for the strategist.
# Inputs:  data/raw/units/census2011_saccp/** (manual); swu.gpkg (02, SAL mode);
#          precinct_clusters.gpkg (01)
# Outputs: data/cleaned/units/sal_units.parquet, sal_covariates.parquet,
#          swu_covariates.parquet, pcl_covariates.parquet,
#          calibration_margins_swu.parquet, calibration_margins_pcl.parquet
# ==============================================================================

source(here::here("scripts", "cleaning", "units", "_common.R"))
source(here::here("scripts", "cleaning", "units", "_sal.R"))
stop_if_no_sal("Census 2011 SAL covariates and calibration margins")

swu_path <- file.path(dir_clean, "swu.gpkg")
if (!file.exists(swu_path)) stop("Run 02_stable_ward_units.R in SAL mode first")
swu <- st_read(swu_path, layer = "swu", quiet = TRUE)
pcl <- st_read(file.path(dir_clean, "precinct_clusters.gpkg"), layer = "precinct_clusters",
               quiet = TRUE)
pcl <- pcl[pcl$in_scope, ]

# ---- SAL geometry and assignment ---------------------------------------------
sal <- read_sal_geom()
metro_union <- st_union(swu)
sal <- sal[lengths(st_intersects(sal, metro_union)) > 0, ]
log_msg("SALs touching the four metros:", nrow(sal))
a_swu <- sal_to_units(sal, swu, "swu_id")
a_pcl <- sal_to_units(sal, pcl, "cluster_id")
maj <- function(a, nm) {
  m <- a[is_majority == TRUE, .SD[1], by = sal_code][, .(sal_code, uid, share)]
  setnames(m, c("sal_code", nm, paste0(nm, "_share")))
  m
}
sal_units <- Reduce(function(x, y) merge(x, y, by = "sal_code", all.x = TRUE),
                    list(data.table(sal_code = sal$sal_code), maj(a_swu, "swu_id"),
                         maj(a_pcl, "cluster_id")))
sal_units[, `:=`(
  metro_code = substr(swu_id, 5, 7),
  flag_split_swu = !is.na(swu_id_share) & swu_id_share < 0.95,
  flag_split_pcl = !is.na(cluster_id_share) & cluster_id_share < 0.95,
  flag_no_swu = is.na(swu_id), flag_no_pcl = is.na(cluster_id))]
sal_units[, flag_outside := flag_no_swu | swu_id_share < 0.5]

# ---- SAL covariates -------------------------------------------------------------
L_all <- sal_long()
assert_sal_match(sal$sal_code, L_all$sal_code)
L <- L_all[sal_code %in% sal$sal_code]
wide <- dcast(L, sal_code ~ dimension + category, value.var = "n", fun.aggregate = sum)
inc <- sal_income_mean()[sal_code %in% sal$sal_code]
sal_cov <- merge(wide, inc, by = "sal_code", all.x = TRUE)
sal_cov[, households := rowSums(.SD), .SDcols = patterns("^dwelling_type_")]
sal_cov[, persons := rowSums(.SD), .SDcols = patterns("^race_persons_")]
sal_cov <- merge(sal_cov, sal_units, by = "sal_code", all.x = TRUE)
sal_cov[, sal_area_km2 := as.numeric(st_area(sal))[match(sal_code, sal$sal_code)] / 1e6]

# ---- Aggregation (area-share apportionment of counts) ------------------------------
count_cols <- setdiff(names(wide), "sal_code")
count_cols <- c(count_cols, "inc_mid_sum", "inc_n", "households", "persons")
agg_units <- function(a, uid_name) {
  x <- merge(a[, .(sal_code, uid, share)], sal_cov[, c("sal_code", count_cols), with = FALSE],
             by = "sal_code")
  x[, (count_cols) := lapply(.SD, function(v) v * share), .SDcols = count_cols]
  out <- x[, lapply(.SD, sum, na.rm = TRUE), by = uid, .SDcols = count_cols]
  setnames(out, "uid", uid_name)
  out
}
cbd <- data.table(metro_code = c("JHB", "TSH", "EKU", "CPT"),
                  lon = c(28.0456, 28.1881, 28.1633, 18.4241),
                  lat = c(-26.2044, -25.7461, -26.2175, -33.9249),
                  cbd = c("Johannesburg CBD", "Pretoria CBD", "Germiston CBD",
                          "Cape Town CBD"))
cbd_sf <- st_transform(st_as_sf(cbd, coords = c("lon", "lat"), crs = 4326), crs_sa_albers)
major <- cbd_sf[cbd_sf$metro_code != "EKU", ]

derive <- function(d, geom, uid_name) {
  sh <- function(num, den) fifelse(den > 0, num / den, NA_real_)
  dwc <- grep("^dwelling_type_", names(d), value = TRUE)
  known_dw <- d$households - fcoalesce(d$dwelling_type_unspecified, 0)
  for (c in setdiff(dwc, "dwelling_type_unspecified"))
    d[, (sub("dwelling_type_", "sh_dw_", c)) := sh(get(c), known_dw)]
  rpc <- grep("^race_persons_", names(d), value = TRUE)
  for (c in rpc) d[, (sub("race_persons_", "sh_pop_", c)) := sh(get(c), persons)]
  rhc <- setdiff(grep("^race_hh_head_", names(d), value = TRUE), "race_hh_head_unspecified")
  hh_known <- rowSums(d[, ..rhc])
  for (c in rhc) d[, (sub("race_hh_head_", "sh_hhh_", c)) := sh(get(c), hh_known)]
  inc_c <- setdiff(grep("^income_band_", names(d), value = TRUE), "income_band_unspecified")
  inc_known <- rowSums(d[, ..inc_c])
  for (c in inc_c) d[, (sub("income_band_", "sh_inc_", c)) := sh(get(c), inc_known)]
  d[, inc_mean_zar := sh(inc_mid_sum, inc_n)]
  d[, ln_inc_mean := log(inc_mean_zar)]
  d[, sh_owned := sh(fcoalesce(tenure_owned_bond, 0) + fcoalesce(tenure_owned_paid, 0),
                     rowSums(.SD)), .SDcols = patterns("^tenure_")]
  d[, sh_formal_res_ea := sh(fcoalesce(ea_type_persons_formal_res, 0),
                             rowSums(.SD)), .SDcols = patterns("^ea_type_persons_")]
  d[, freestanding_share := sh_dw_house]
  g <- geom[match(d[[uid_name]], geom[[uid_name]]), ]
  d[, area_km2 := as.numeric(st_area(g)) / 1e6]
  d[, hh_density_km2 := households / area_km2]
  cen <- st_point_on_surface(st_geometry(g))
  own <- cbd_sf[match(d$metro_code, cbd_sf$metro_code), ]
  d[, dist_own_cbd_km := as.numeric(st_distance(cen, own, by_element = TRUE)) / 1000]
  d[, dist_major_cbd_km := apply(st_distance(cen, major), 1, min) / 1000]
  d[, source := "Census 2011 community profiles (Stats SA via DataFirst 517), base-3 rounded"]
  d
}

swu_cov <- agg_units(a_swu, "swu_id")
swu_cov <- merge(swu_cov, as.data.table(st_drop_geometry(swu))[, .(swu_id, metro_code)],
                 by = "swu_id")
swu_cov <- derive(swu_cov, swu, "swu_id")
pcl_cov <- agg_units(a_pcl, "cluster_id")
pcl_cov <- merge(pcl_cov, as.data.table(st_drop_geometry(pcl))[, .(cluster_id, metro_code)],
                 by = "cluster_id")
pcl_cov <- derive(pcl_cov, pcl, "cluster_id")

# ---- Calibration margins (memo 6.3) -------------------------------------------------
margins <- function(a, uid_name) {
  x <- merge(a[, .(sal_code, uid, share)],
             L[dimension %in% c("dwelling_type", "race_hh_head", "income_band")],
             by = "sal_code", allow.cartesian = TRUE)
  x[dimension == "dwelling_type", category := fifelse(category %in% names(dw_cal),
                                                      dw_cal[category], category)]
  x <- x[category != "unspecified"]
  x <- x[, .(households = sum(n * share)), by = .(uid, dimension, category)]
  x[, share := households / sum(households), by = .(uid, dimension)]
  setnames(x, "uid", uid_name)
  x[, note := "one-way margins for raking; joint cells need a SuperWEB2 cross-tab"]
  x
}
cal_swu <- margins(a_swu, "swu_id"); cal_pcl <- margins(a_pcl, "cluster_id")

# ---- Checks ---------------------------------------------------------------------------
in_metro <- sal_units[flag_outside == FALSE]
tot_sal <- sal_cov[sal_code %in% in_metro$sal_code, sum(households)]
tot_swu <- sum(swu_cov$households)
log_msg("Households: SALs mostly inside metros", round(tot_sal), "| apportioned to SWUs",
        round(tot_swu), "| to in-scope clusters", round(sum(pcl_cov$households)))
stopifnot(!anyDuplicated(sal_units$sal_code))

# ---- Write ----------------------------------------------------------------------------
write_parquet(sal_units, file.path(dir_clean, "sal_units.parquet"))
write_parquet(sal_cov, file.path(dir_clean, "sal_covariates.parquet"))
write_parquet(swu_cov, file.path(dir_clean, "swu_covariates.parquet"))
write_parquet(pcl_cov, file.path(dir_clean, "pcl_covariates.parquet"))
write_parquet(cal_swu, file.path(dir_clean, "calibration_margins_swu.parquet"))
write_parquet(cal_pcl, file.path(dir_clean, "calibration_margins_pcl.parquet"))
print(sal_units[, .(sals = .N, split_swu = sum(flag_split_swu), split_pcl = sum(flag_split_pcl),
                    no_pcl = sum(flag_no_pcl)), by = metro_code])
log_msg("Done: SAL covariates written")

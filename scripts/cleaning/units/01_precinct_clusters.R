# ==============================================================================
# 01_precinct_clusters.R -- Time-invariant SAPS precinct clusters, FY2005/06-2025/26
# Project: PSC Exposure (memo 2.6 "precinct clusters are time-invariant";
#          data exploration 7: parents/children merged, never-split robustness)
# Author:  data-engineer agent for Thomas Brailey
# Date:    2026-09-30
# Purpose: Build clusters of police stations whose union is stable over the SAPS
#          panel. Four kinds of merge edge (all pre-specified below):
#   E1 vintage overlay   -- a station first appearing in boundary vintage v is
#                           linked to every v-1 precinct for which the overlap
#                           holds >= 5% of EITHER the v-1 precinct's population
#                           or the new station's population (evidence =
#                           max(share_old, share_new); area share outside the
#                           GHSL grid).
#   E2 boundary exchange -- two stations present in consecutive vintages are
#                           linked if territory holding >= 5% of either station's
#                           population moved between them (undocumented shifts).
#   E3 count-drop rule   -- stations that opened FY2005/06-2014/15 already appear
#                           in the earliest (2014) boundaries, so their parents
#                           are adjacent precincts whose 17-category count fell,
#                           relative to the provincial trend (2-year means), by
#                           >= 25% of the child's first full-year count AND >= 5%
#                           of the neighbour's own expected count; if none
#                           qualifies, the neighbour with the largest drop.
#   E4 no-polygon point  -- an active station with no precinct polygon in any
#                           vintage joins the precinct containing its station
#                           point (SAPS 2018 points), e.g. Table Bay Harbour.
#          Clusters = connected components. Singletons = never-split stations.
# Inputs:  data/raw/units/saps/boundaries_{2014..2020}, statssa/PoliceDistrict_2025,
#          saps/stats_* (station x FY presence), mdb/wards_2021 (province, metro),
#          ghsl/ghs_pop_2010_*.tif (population weights for materiality only)
# Outputs: data/cleaned/units/precinct_clusters.gpkg (layers: precinct_clusters,
#            stations_2025)
#          data/cleaned/units/station_to_cluster.parquet
#          data/cleaned/units/intermediate/precinct_{edges,e3_evidence}.parquet
#          data/cleaned/units/intermediate/station_fy_active.parquet
#          data/cleaned/units/intermediate/cluster_sensitivity.parquet
#          data/cleaned/units/intermediate/overlay_2014_2025_check.parquet
# ==============================================================================

source(here::here("scripts", "cleaning", "units", "_common.R"))
source(here::here("scripts", "cleaning", "units", "_saps_parse.R"))

panel_first_fy <- 2005L  # FY2005/06
e3_child_min   <- 0.25   # E3: drop >= 25% of child's first full-year count ...
e3_nbr_min     <- 0.05   # ... and >= 5% of the neighbour's expected count
nbr_dist_m     <- 100    # adjacency tolerance for E3 (coverage gaps)

cluster_rule <- paste(
  "Connected components of: (E1) new station -> v-1 precincts whose overlap holds",
  ">= 5% of either precinct's GHSL-2010 population; (E2) population exchange >= 5% of either station",
  "between consecutive SAPS boundary vintages 2014-2025; (E3) stations opened",
  "FY2005/06-FY2014/15 -> adjacent precincts whose 17-category count fell (2-yr",
  "means, provincial trend) by >= 25% of the child's count and >= 5% of their own",
  "(largest drop if none); (E4) active station without polygon -> precinct",
  "containing its station point. Openings before FY2005/06 are not merged.")

# ---- Station-name aliases (province-aware; raw normalised key -> 2025 key) -----
aliases <- data.table(
  province = c(NA, NA, NA, NA, "GT", "WC"),
  from = c("JOHANNESBURG CENTRAL", "OR TAMBO INTERNATIONAL AIRPORT", "PROTEA GLEN",
           "RIEBEECK WEST", "HEIDELBERG", "HEIDELBERG"),
  to   = c("JHB CENTRAL", "OR TAMBO INTERN AIRP", "PROTEA", "RIEBEEK WEST",
           "HEIDELBERG GP", "HEIDELBERG C"),
  note = c("2013 release long form", "2013 release long form",
           "renamed c. 2015 (same precinct)", "spelling",
           "2013 release drops the (GP) tag", "2013 release drops the (C) tag"))
canon <- function(k, prov = NA_character_) {
  prov <- rep_len(prov, length(k))
  out <- k
  for (i in seq_len(nrow(aliases))) {
    hit <- k == aliases$from[i] & (is.na(aliases$province[i]) | prov == aliases$province[i])
    out[hit] <- aliases$to[i]
  }
  out
}

# ---- Province and metro geometry (MDB 2021 wards) ----------------------------
log_msg("Reading MDB 2021 wards for province / metro geometry")
w21 <- read_layer_albers(file.path(dir_raw, "mdb", "wards_2021", "SA_Wards2020.shp"))
w21$prov <- c("Gauteng" = "GT", "Western Cape" = "WC")[w21$Province]
w21p <- w21[!is.na(w21$prov), ]
prov_poly <- aggregate(w21p[, "prov"], by = list(p = w21p$prov), FUN = length)
prov_poly <- st_make_valid(prov_poly[, "p"]); names(prov_poly)[1] <- "prov"
metro_poly <- w21[w21$CAT_B %in% metros$metro_code, ]
metro_poly <- aggregate(metro_poly[, "CAT_B"], by = list(m = metro_poly$CAT_B),
                        FUN = length)
metro_poly <- st_make_valid(metro_poly[, "m"]); names(metro_poly)[1] <- "metro_code"
stopifnot(nrow(metro_poly) == 4, nrow(prov_poly) == 2)
scope_union <- st_union(prov_poly)

# ---- Police boundary vintages -------------------------------------------------
vintages <- list(
  `2014` = "saps/boundaries_2014/Police_bounds.shp",
  `2015` = "saps/boundaries_2015/Police_bounds.shp",
  `2016` = "saps/boundaries_2016/Police_bounds.shp",
  `2017` = "saps/boundaries_2017/Police_bounds.shp",
  `2018` = "saps/boundaries_2018/station_boundaries_points/Police_bounds.shp",
  # 2019 file carries the same CREATE_DT/VERSION (20180306, 1.2.3) as 2018: skipped
  `2020` = "saps/boundaries_2020/station_boundaries/Police_bounds.shp",
  `2025` = "statssa/PoliceDistrict_2025/PoliceDistrict.shp"
)

# Keep every precinct that touches GT or WC by more than a sliver, so that
# precincts straddling a provincial border are present in every vintage.
read_vintage <- function(rel, yr) {
  g <- read_layer_albers(file.path(dir_raw, rel))
  g <- g[lengths(st_intersects(g, scope_union)) > 0, ]
  ov <- area_m2(suppressWarnings(st_intersection(st_geometry(g), scope_union)))
  g <- g[ov >= 1e5, ]  # >= 10 ha inside GT/WC
  g$sid <- norm_station(g$COMPNT_NM)
  g$sid <- canon(g$sid)
  g <- aggregate(g[, "COMPNT_NM"], by = list(sid = g$sid), FUN = function(x) x[1])
  g <- st_make_valid(g)
  g$vintage <- as.integer(yr)
  g
}
log_msg("Reading", length(vintages), "boundary vintages (precincts touching GT/WC)")
V <- Map(read_vintage, vintages, names(vintages))
print(vapply(V, nrow, integer(1)))

# ---- Station x FY activity (presence only) ------------------------------------
log_msg("Parsing SAPS station workbooks (presence by FY)")
saps <- parse_all_saps(file.path(dir_raw, "saps"))
saps[, sid := canon(norm_station(station_raw), province)]
# Later releases revise earlier years: keep the most recent full-FY source per
# station-FY; Q4-only counts are used only where no full-FY source exists.
src_rank <- c(saps_stats_2013 = 1, saps_stats_2015 = 2, saps_stats_2021 = 3,
              saps_stats_2024 = 4, saps_stats_2026q4 = 0)
saps[, rank := src_rank[source]]
series <- saps[order(-rank)][, .SD[1], by = .(sid, fy)]
act <- series[, .(sid, fy, active = tot17 > 0)]
wb_prov <- saps[, .(wb_province = province[1]), by = sid]
st_fy <- act[, .(first_fy = if (any(active)) min(fy[active]) else NA_integer_,
                 last_fy  = if (any(active)) max(fy[active]) else NA_integer_),
             by = sid]
first_obs_fy <- min(act$fy)

# ---- Universe of stations ------------------------------------------------------
all_sid <- sort(unique(c(unlist(lapply(V, `[[`, "sid")), st_fy$sid)))
stations <- data.table(sid = all_sid)
for (yr in names(V)) stations[, (paste0("in_", yr)) := sid %in% V[[yr]]$sid]
stations <- merge(stations, st_fy, by = "sid", all.x = TRUE)
stations <- merge(stations, wb_prov, by = "sid", all.x = TRUE)
vcols <- paste0("in_", names(V))
fv <- apply(as.matrix(stations[, ..vcols]), 1, function(r)
  if (any(r)) as.integer(sub("in_", "", vcols[which(r)[1]])) else NA_integer_)
stations[, first_vintage := fv]
stations[, child_new := !is.na(first_fy) & first_fy >= panel_first_fy]
log_msg("Stations:", nrow(stations), "| opened FY2005+:", sum(stations$child_new),
        "| no polygon in any vintage:", sum(is.na(stations$first_vintage)))

# ---- Population per polygon per vintage ---------------------------------------
log_msg("GHSL population per precinct per vintage")
for (yr in names(V)) {
  V[[yr]]$pop <- pop_in_polys(V[[yr]])
  V[[yr]]$area <- area_m2(V[[yr]])
}

# ---- E1 + E2: consecutive-vintage overlays ------------------------------------
pieces_pop <- function(old, new) {
  nn <- new[, "sid"]
  names(nn)[names(nn) == "sid"] <- "sid_new"
  x <- suppressWarnings(st_intersection(old[, "sid"], nn))
  x <- st_collection_extract(x, "POLYGON", warn = FALSE)
  x$area <- area_m2(x)
  x <- x[x$area >= sliver_m2, ]
  x$pop <- pop_in_polys(x)
  dt <- data.table(sid_old = x$sid, sid_new = x$sid_new, area = x$area, pop = x$pop)
  dt[, .(area = sum(area), pop = sum(pop)), by = .(sid_old, sid_new)]
}

overlay_rows <- list()
yrs <- names(V)
for (k in 2:length(yrs)) {
  o <- V[[yrs[k - 1]]]; n <- V[[yrs[k]]]
  log_msg("Overlay", yrs[k - 1], "->", yrs[k])
  p <- pieces_pop(o, n)
  p <- merge(p, data.table(sid_old = o$sid, pop_old = o$pop, area_old = o$area),
             by = "sid_old")
  p <- merge(p, data.table(sid_new = n$sid, pop_new = n$pop, area_new = n$area),
             by = "sid_new")
  p <- p[sid_old != sid_new]
  use_pop <- !is.na(p$pop_old) & p$pop_old >= 1 & !is.na(p$pop_new) & p$pop_new >= 1
  p[, share_old := ifelse(use_pop, pop / pop_old, area / area_old)]
  p[, share_new := ifelse(use_pop, pop / pop_new, area / area_new)]
  p[, basis := ifelse(use_pop, "ghsl_pop_2010", "area")]
  p[, new_station := !(sid_new %in% o$sid)]
  p[, `:=`(vintage_from = as.integer(yrs[k - 1]), vintage_to = as.integer(yrs[k]))]
  overlay_rows[[k]] <- p
}
ov_all <- rbindlist(overlay_rows)
ov_all[, evidence := pmax(share_old, share_new)]
ov_all[, rule := ifelse(new_station, "E1_vintage_overlay", "E2_boundary_exchange")]
edges_ov <- function(tau) {
  ov_all[evidence >= tau, .(from = sid_old, to = sid_new, rule, vintage_from,
                            vintage_to, evidence = round(evidence, 4), basis)]
}

# ---- E3: pre-2014 children, count-drop rule -----------------------------------
b14 <- V[["2014"]]
tot_mean <- function(s, f) {
  v <- series[sid == s & fy %in% f, tot17]
  if (length(v) == 0) NA_real_ else mean(v)
}
e3_candidates <- stations[!is.na(first_fy) & in_2014 == TRUE &
                            first_fy >= panel_first_fy - 1L & first_fy <= 2014L]
log_msg("E3 count-drop rule for", nrow(e3_candidates),
        "stations opened FY2004-FY2014 (FY2004 only for the strict flag)")
e3_rows <- list()
for (s in e3_candidates$sid) {
  f <- stations[sid == s, first_fy]
  child_geom <- b14[b14$sid == s, ]
  nb <- b14$sid[st_is_within_distance(b14, child_geom, dist = nbr_dist_m,
                                      sparse = FALSE)[, 1]]
  nb <- setdiff(nb, s)
  pre_y <- (f - 2L):(f - 1L); post_y <- (f + 1L):(f + 2L)
  prov <- stations[sid == s, wb_province]
  others <- series[sid %in% wb_prov[wb_province == prov, sid] & !(sid %in% c(s, nb))]
  others <- others[, .(pre = mean(tot17[fy %in% pre_y]), post = mean(tot17[fy %in% post_y]),
                       n_pre = sum(fy %in% pre_y), n_post = sum(fy %in% post_y)), by = sid]
  others <- others[n_pre > 0 & n_post > 0 & pre > 0 & post > 0]
  g <- sum(others$post) / sum(others$pre)
  v_child <- tot_mean(s, post_y)
  d <- data.table(child = s, nbr = nb,
                  pre = vapply(nb, tot_mean, numeric(1), f = pre_y),
                  post = vapply(nb, tot_mean, numeric(1), f = post_y))
  d[, expected := pre * g]
  d[, drop := expected - post]
  d[, `:=`(drop_share_child = drop / v_child, drop_share_own = drop / expected)]
  d[, parent := !is.na(drop) & drop_share_child >= e3_child_min &
      drop_share_own >= e3_nbr_min]
  d[, weak := FALSE]
  if (!any(d$parent)) d[which.max(drop), `:=`(parent = TRUE, weak = TRUE)]
  d[, `:=`(first_fy = f, trend_g = g, merged = f >= panel_first_fy)]
  e3_rows[[s]] <- d
}
e3 <- rbindlist(e3_rows)
e3_edges <- e3[parent == TRUE & merged == TRUE,
               .(from = nbr, to = child, rule = "E3_count_drop",
                 vintage_from = NA_integer_, vintage_to = 2014L,
                 evidence = round(drop_share_child, 4), basis = "saps_17cat_counts")]

# ---- E4: active stations without any polygon ----------------------------------
pts <- read_layer_albers_pts <- st_transform(st_read(file.path(
  dir_raw, "saps/boundaries_2018/station_boundaries_points/Police_points.shp"),
  quiet = TRUE), crs_sa_albers)
pts$sid <- canon(norm_station(pts$COMPNT_NM))
nopoly <- stations[is.na(first_vintage)]
b25 <- V[["2025"]]
e4_edges <- rbindlist(lapply(nopoly$sid, function(s) {
  if (is.na(stations[sid == s, first_fy])) return(NULL)  # never active: excluded
  pp <- pts[pts$sid == s, ]
  if (nrow(pp) == 0) return(NULL)
  host <- b25$sid[lengths(st_intersects(b25, pp[1, ])) > 0]
  if (length(host) == 0) return(NULL)
  data.table(from = host[1], to = s, rule = "E4_no_polygon_point",
             vintage_from = NA_integer_, vintage_to = 2025L, evidence = 1,
             basis = "saps_2018_station_point")
}))

# ---- Clusters -----------------------------------------------------------------
build_components <- function(edges) {
  comp <- overlap_components(edges[, .(from, to)], stations$sid)
  setnames(comp, c("sid", "comp"))
  comp
}
edges <- rbindlist(list(edges_ov(pcl_parent_min_share), e3_edges, e4_edges),
                   use.names = TRUE)
comp <- build_components(edges)
stations <- merge(stations, comp, by = "sid")
stations <- merge(stations, data.table(sid = b25$sid, pop25 = b25$pop, area25 = b25$area,
                                       name25 = b25$COMPNT_NM),
                  by = "sid", all.x = TRUE)
# Cluster named after its largest member (population, then area): stable IDs.
setorder(stations, comp, -pop25, -area25, sid, na.last = TRUE)
cl_names <- stations[, .(cluster_id = paste0("PCL_", gsub(" ", "_", sid[1]))), by = comp]
stations <- merge(stations, cl_names, by = "comp")
stations[, n_members := .N, by = cluster_id]

parent_src <- edges[rule %in% c("E1_vintage_overlay", "E3_count_drop", "E4_no_polygon_point")]
stations[, role := fifelse(n_members == 1, "singleton",
                   fifelse(child_new | sid %in% parent_src$to, "child",
                   fifelse(sid %in% parent_src$from, "parent", "exchange_partner")))]
cl_reason <- merge(stations[, .(sid, cluster_id)],
                   edges[, .(sid = c(from, to), rule = c(rule, rule))], by = "sid")[
  , .(merge_rules = paste(sort(unique(rule)), collapse = "+")), by = cluster_id]
stations <- merge(stations, cl_reason, by = "cluster_id", all.x = TRUE)
stations[is.na(merge_rules), merge_rules := "none"]
stations[, never_split := n_members == 1]
early_parents <- e3[merged == FALSE & parent == TRUE, unique(nbr)]
# strict: also not a parent of an FY2004/05 opening, and itself active since
# the first observable FY (2003/04)
stations[, never_split_strict := never_split & !(sid %in% early_parents) &
           !is.na(first_fy) & first_fy == first_obs_fy]
parents_of <- parent_src[, .(parents = paste(sort(unique(from)), collapse = "; ")),
                         by = .(sid = to)]
stations <- merge(stations, parents_of, by = "sid", all.x = TRUE)
# E2 pairs that moved in both directions across different vintage steps
flip <- ov_all[rule == "E2_boundary_exchange" & evidence >= pcl_parent_min_share,
               .(a = pmin(sid_old, sid_new), b = pmax(sid_old, sid_new), sid_old, vintage_to)]
flip <- flip[, .(n_dir = uniqueN(sid_old), n_steps = uniqueN(vintage_to)), by = .(a, b)]
flip_sids <- flip[n_dir == 2 & n_steps >= 2, unique(c(a, b))]
stations[, e2_flip_flop := sid %in% flip_sids]

# ---- Cluster geometry, metro assignment ---------------------------------------
b25c <- merge(b25[, "sid"], stations[, .(sid, cluster_id)], by = "sid")
clusters <- aggregate(b25c[, "cluster_id"], by = list(cid = b25c$cluster_id), FUN = length)
clusters <- st_make_valid(clusters[, "cid"]); names(clusters)[1] <- "cluster_id"
clusters$area_km2 <- area_m2(clusters) / 1e6
clusters$pop_ghsl2010 <- pop_in_polys(clusters)

assign_metro <- function(cl) {
  cm <- suppressWarnings(st_intersection(cl[, "cluster_id"], metro_poly))
  cm <- st_collection_extract(cm, "POLYGON", warn = FALSE)
  cm$area <- area_m2(cm); cm$pop <- pop_in_polys(cm)
  cm <- data.table(cluster_id = cm$cluster_id, metro_code = cm$metro_code,
                   area = cm$area, pop = cm$pop)
  cm <- merge(cm, data.table(cluster_id = cl$cluster_id, ca = area_m2(cl),
                             cp = cl$pop_ghsl2010), by = "cluster_id")
  cm[, `:=`(metro_area_share = area / ca, metro_pop_share = pop / cp)]
  cm[, any_metro_pop_share := sum(metro_pop_share), by = cluster_id]
  cm[order(cluster_id, -metro_pop_share)][, .SD[1], by = cluster_id][
    , .(cluster_id, metro_code, metro_pop_share, metro_area_share, any_metro_pop_share)]
}
# Scope: >= 50% of the cluster's population inside the four metros combined;
# assigned to the metro holding the largest share. Clusters chained across a
# metro boundary (e.g. Diepsloot-Midrand-Olievenhoutbosch, JHB/TSH) stay in
# scope and are flagged cross_metro.
cm <- assign_metro(clusters)
clusters <- merge(clusters, cm, by = "cluster_id", all.x = TRUE)
clusters$metro_pop_share[is.na(clusters$metro_pop_share)] <- 0
clusters$any_metro_pop_share[is.na(clusters$any_metro_pop_share)] <- 0
clusters$in_scope <- clusters$any_metro_pop_share >= 0.5
clusters$cross_metro <- clusters$in_scope & clusters$metro_pop_share < 0.9
clusters$metro_code[!clusters$in_scope] <- NA

cl_attr <- stations[, .(
  n_stations = .N, members = paste(sort(sid), collapse = "; "),
  n_children = sum(child_new), never_split = all(never_split),
  never_split_strict = all(never_split_strict), merge_rules = merge_rules[1],
  n_active_fy2005 = sum(!is.na(first_fy) & first_fy < panel_first_fy &
                          (is.na(last_fy) | last_fy >= panel_first_fy)),
  weak_e3 = any(sid %in% e3[weak == TRUE & merged == TRUE, child]),
  e2_flip_flop = any(e2_flip_flop)), by = cluster_id]
clusters <- merge(clusters, cl_attr, by = "cluster_id", all.x = TRUE)
clusters$weight_note <- "pop_ghsl2010 is a GHSL grid estimate (materiality/scope only)"
clusters$rule <- cluster_rule

stations <- merge(stations, st_drop_geometry(clusters)[, c("cluster_id", "metro_code",
                                                           "in_scope")],
                  by = "cluster_id", all.x = TRUE)
stations[is.na(in_scope), in_scope := FALSE]
# Station-level metro of its own 2025 polygon (to report stations lost to
# out-of-scope clusters)
own <- assign_metro(transform(b25[, "sid"], cluster_id = sid, pop_ghsl2010 = b25$pop))
stations <- merge(stations, own[metro_pop_share >= 0.5,
                               .(sid = cluster_id, own_metro = metro_code)],
                  by = "sid", all.x = TRUE)

# ---- Direct 2014 -> 2025 overlay check (diagnostic; not used for clusters) -------
# Consecutive-vintage chaining could miss an exchange that nets out stepwise or
# involves a skipped vintage. Overlay the earliest and latest vintages directly.
log_msg("Direct overlay 2014 -> 2025 (check)")
pd_ <- pieces_pop(V[["2014"]], V[["2025"]])
pd_ <- merge(pd_, data.table(sid_old = V[["2014"]]$sid, pop_old = V[["2014"]]$pop,
                             area_old = V[["2014"]]$area), by = "sid_old")
pd_ <- merge(pd_, data.table(sid_new = V[["2025"]]$sid, pop_new = V[["2025"]]$pop,
                             area_new = V[["2025"]]$area), by = "sid_new")
pd_ <- pd_[sid_old != sid_new]
use_pop_d <- !is.na(pd_$pop_old) & pd_$pop_old >= 1 & !is.na(pd_$pop_new) & pd_$pop_new >= 1
pd_[, evidence := pmax(ifelse(use_pop_d, pop / pop_old, area / area_old),
                       ifelse(use_pop_d, pop / pop_new, area / area_new))]
direct_edges <- pd_[evidence >= pcl_parent_min_share,
                    .(from = sid_old, to = sid_new, rule = "direct_2014_2025",
                      vintage_from = 2014L, vintage_to = 2025L,
                      evidence = round(evidence, 4), basis = "ghsl_pop_2010")]
cid_of <- setNames(stations$cluster_id, stations$sid)
direct_edges[, `:=`(cluster_from = cid_of[from], cluster_to = cid_of[to])]
direct_edges[, crosses_clusters := cluster_from != cluster_to]
log_msg("Direct 2014->2025 pairs >= 5%:", nrow(direct_edges),
        "| linking DIFFERENT clusters:", sum(direct_edges$crosses_clusters))
if (any(direct_edges$crosses_clusters)) print(direct_edges[crosses_clusters == TRUE])

# ---- Sensitivity: alternative thresholds -----------------------------------------
sens <- rbindlist(lapply(list(
  list(lab = "primary (tau = 0.05, E3 strict)", e = edges),
  list(lab = "tau = 0.10 for E1/E2", e = rbindlist(list(edges_ov(0.10), e3_edges, e4_edges))),
  list(lab = "no E2 exchanges", e = rbindlist(list(edges_ov(0.05)[rule != "E2_boundary_exchange"],
                                                   e3_edges, e4_edges))),
  list(lab = "E3 off (no count-drop merges)",
       e = rbindlist(list(edges_ov(pcl_parent_min_share), e4_edges))),
  list(lab = "primary + direct 2014-2025 edges",
       e = rbindlist(list(edges, direct_edges[, !c("cluster_from", "cluster_to",
                                                    "crosses_clusters")])))), function(x) {
  cc <- build_components(x$e)
  cc[, size := .N, by = comp]
  cc <- merge(cc, stations[, .(sid, own_metro)], by = "sid")
  # clusters counted by the metro of their stations (a cross-metro cluster
  # counts once in each metro it touches)
  cc[!is.na(own_metro), .(scenario = x$lab, stations = .N, clusters = uniqueN(comp),
                          singleton_stations = sum(size == 1)), by = own_metro]
}))

# Bekkersdal-Lenasia (E3 link): same cluster with and without E3?
bl <- c("BEKKERSDAL", "LENASIA")
same_cl <- function(e) {
  cc <- build_components(e)
  nrow(cc[sid %in% bl]) == 2 && uniqueN(cc[sid %in% bl, comp]) == 1
}
bl_primary <- same_cl(edges)
bl_e3off <- same_cl(rbindlist(list(edges_ov(pcl_parent_min_share), e4_edges)))
log_msg("Bekkersdal & Lenasia in one cluster | primary:", bl_primary, "| E3 off:", bl_e3off)
sens_stations <- rbindlist(lapply(c("primary", "E3 off"), function(lab) {
  e <- if (lab == "primary") edges else rbindlist(list(edges_ov(pcl_parent_min_share), e4_edges))
  cc <- build_components(e)
  cc[, size := .N, by = comp]
  cc[, scenario := lab]
  cc
}))
# stations whose cluster membership changes when E3 is switched off
chg <- merge(sens_stations[scenario == "primary", .(sid, size_primary = size)],
             sens_stations[scenario == "E3 off", .(sid, size_e3off = size)], by = "sid")
log_msg("Stations in a smaller cluster when E3 is off:", sum(chg$size_e3off < chg$size_primary))

# ---- Checks --------------------------------------------------------------------
stopifnot(!anyDuplicated(stations$sid))
sc <- st_drop_geometry(clusters)
bad_panel <- sc$cluster_id[sc$in_scope & sc$n_active_fy2005 == 0]
if (length(bad_panel)) log_msg("WARNING in-scope clusters without an FY2005 station:",
                               paste(bad_panel, collapse = ", "))
if (sum(stations$in_scope & is.na(stations$area25) & stations$role == "singleton"))
  log_msg("WARNING in-scope singleton without polygon")

# ---- Write ---------------------------------------------------------------------
out_gpkg <- file.path(dir_clean, "precinct_clusters.gpkg")
if (file.exists(out_gpkg)) unlink(out_gpkg)
st_write(clusters, out_gpkg, layer = "precinct_clusters", quiet = TRUE)
b25_out <- merge(b25[, c("sid", "COMPNT_NM")],
                 stations[, .(sid, cluster_id, role, never_split, metro_code, in_scope)],
                 by = "sid")
st_write(b25_out, out_gpkg, layer = "stations_2025", quiet = TRUE, append = TRUE)

s2c <- stations[, .(
  station_id = sid, workbook_province = wb_province, station_name_2025 = name25,
  cluster_id, metro_code, in_scope, own_metro, role, parents, n_members,
  first_active_fy = first_fy, last_active_fy = last_fy,
  opened_in_panel = child_new, first_boundary_vintage = first_vintage,
  in_2014_boundaries = in_2014, has_2025_polygon = !is.na(area25),
  never_split, never_split_strict, e2_flip_flop, merge_rules, rule = cluster_rule)]
setorder(s2c, cluster_id, station_id)
write_parquet(s2c, file.path(dir_clean, "station_to_cluster.parquet"))
write_parquet(edges, file.path(dir_intermediate, "precinct_edges.parquet"))
write_parquet(e3[, .(child, nbr, first_fy, drop_share_child = round(drop_share_child, 4),
                     drop_share_own = round(drop_share_own, 4), parent, weak, merged)],
              file.path(dir_intermediate, "precinct_e3_evidence.parquet"))
write_parquet(act[, .(station_id = sid, fy, active)],
              file.path(dir_intermediate, "station_fy_active.parquet"))
write_parquet(aliases, file.path(dir_intermediate, "station_aliases.parquet"))
write_parquet(sens, file.path(dir_intermediate, "cluster_sensitivity.parquet"))
write_parquet(direct_edges, file.path(dir_intermediate, "overlay_2014_2025_check.parquet"))

# ---- Console summary ------------------------------------------------------------
summ <- stations[in_scope == TRUE, .(
  stations = .N, clusters = uniqueN(cluster_id),
  never_split_stations = sum(never_split),
  never_split_strict = sum(never_split_strict),
  opened_in_panel = sum(child_new)), by = metro_code]
print(summ[order(metro_code)])
print(edges[, .N, by = rule])
print(sens)
lost <- stations[!is.na(own_metro) & (is.na(metro_code) | metro_code != own_metro),
                 .(sid, own_metro, cluster_id, metro_code)]
if (nrow(lost)) { log_msg("Metro stations placed in another/no-metro cluster:"); print(lost) }
log_msg("Done: precinct clusters written to", out_gpkg)

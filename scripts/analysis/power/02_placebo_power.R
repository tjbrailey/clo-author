# ==============================================================================
# 02_placebo_power.R -- P-E placebo-simulation power (memo S9.2), SAPS arm
# Project: PSC Exposure (WP3, pilot step P-E)
# Purpose: Estimate minimum detectable effects (MDE) for E1 (Gauteng pooled, JHB
#          only; A2-P: BJS imputation aggregated by t-G, headline = mean ell 0..3)
#          and E3 (Cape Town; A3: Callaway-Sant'Anna), by placebo simulation on
#          the real SAPS cluster panel.
#          Protocol (S9.2): in-scope clusters -> pseudo (G_tilde, G) with lag bins,
#          realistic treated share, stock bins {0,>0}, contiguity loss, range rule
#          (switcher/control overlap), >=5-controls-per-cell drop rule counting
#          not-yet-treated units, FE pcl + metro^fy + bin^fy -> inject delta*dE
#          (exposure-scaled) or delta (area) from G -> actual estimator -> actual
#          inference: placebo-unit randomisation inference within metro (memo
#          S13.2; primary because J_T < 20 in every scenario) -> MDE = smallest
#          delta with RI power >= 0.80. Size at delta = 0 under RI, the analytic
#          cluster-robust SE, BJS without bin^fy, and a static TWFE benchmark.
#          Both estimators are linear in y (theta = sum(V * Y)); V is built once
#          per draw, so the delta grid and RI are exact (see _power_functions.R).
#          The in-house point estimate is checked against didimputation / did at
#          delta = 0 on every draw.
# Inputs:  data/cleaned/power/saps_cluster_panel.parquet   (01_saps_panel.R)
#          data/cleaned/units/precinct_clusters.gpkg       (WP2; geometry only)
#          data/cleaned/e3/sra_onsets.parquet              (WP5; G3 TIMING only)
#          data/cleaned/e3/sra_polygons.gpkg               (WP5; to EXCLUDE SRA clusters)
# Outputs: data/cleaned/power/pe_draws.parquet       (RI / analytic rejection on the delta grid)
#          data/cleaned/power/pe_diag_draws.parquet  (delta = 0 diagnostics per draw)
#          data/cleaned/power/pe_design_draws.parquet, pe_inputs.rds, cpt_non_sra_pool.parquet
# Dependencies: data.table, arrow, sf, fixest, didimputation, did, digest, parallel
# Runtime knobs (env): PE_NDRAWS (default 1000), PE_WORKERS (default 4; 14 exhausted RAM)
# RULE: no real treatment onset is ever merged with outcomes. The 12 residential
#       G3 onset years are used as a timing structure on clusters that do not
#       overlap any SRA polygon; real SRA clusters are excluded from the pool.
# ==============================================================================

suppressPackageStartupMessages({
  library(data.table); library(arrow); library(sf); library(fixest); library(here)
  library(parallel); library(digest)
})
sf_use_s2(FALSE)
t_start <- Sys.time()

# ==============================================================================
# 0. CONFIG  (everything marked ASSUMED is a placeholder pending P-B / P-C / P-D)
# ==============================================================================
CFG <- list(
  seed        = 20260930,
  n_draws     = as.integer(Sys.getenv("PE_NDRAWS", "1000")),
  n_workers   = as.integer(Sys.getenv("PE_WORKERS", "4")),
  n_perm      = 999L,                      # RI permutations per draw (p-value grid 1/1000)
  years       = 2005:2025,                 # FY start year; 2005 = FY2005/06
  # onset window (memo S9.4, A2/A3): G_tilde >= FY2009/10, G <= FY2023/24
  G_min = 2011L, G_max = 2023L, gt_min = 2009L,
  G_weights   = NULL,                      # NULL -> uniform over G_min..G_max (memo S8.4 window)
  # lag L = G - G_tilde in FY: ASSUMED distribution, replaced by P-D's L^app
  lag_probs   = c("2" = 0.55, "3" = 0.25, "4" = 0.12, "5" = 0.08),
  pre_window_Gt  = 2006:2008,              # G_tilde < FY2009/10: treated, no effect, control only before G_tilde
  post_window_G  = 2024:2026,              # G after window: control until G_tilde
  stock_share = 0.25,                      # ASSUMED share of units with B_u > 0 (P-C)
  contig_drop = 0.25,                      # ASSUMED share of controls lost to contiguity (memo S3.2)
  cap_share   = 0.25,                      # ASSUMED max share of in-scope clusters that are reported
                                           #   switchers (critic r1 H1; P-C recount replaces it)
  min_ctrl    = 5L,                        # S3.2 rule 6 floor (ASSUMED)
  cell_horizon = 5L,                       # periods G_tilde .. G+5 must pass the cell rule
  ell_max     = 3L,                        # headline = mean of ell = 0..3
  min_JT      = 3L,                        # a draw with fewer switchers left is 'infeasible'
  alpha       = 0.05, target_power = 0.80,
  # injected-effect grids: area in log (asinh) points; exposure grid = grid_expo_area / dE
  grid_V1        = seq(0, 0.60, 0.01),
  grid_V0        = seq(0, 1.20, 0.02),
  grid_expo_area = seq(0, 1.20, 0.02),
  # memo S8 parameters used only in the formula sanity check
  f = 1.2, sigma_V1 = 0.12, sigma_V0 = 0.30, infl_rho03 = 1.68
)

# cohort / dose scenarios from memo S8.4 (E1) and S5.8 (E3). dE = k1*S/35,000.
dE_E1 <- c(Low = 1 * 100, Mid = 1.5 * 300, High = 2 * 600, `High+` = 2 * 1000) / 35000
JT_pool <- c(Low = 20, Mid = 30, High = 40, `High+` = 40)   # memo S8.4 (3 metros)
JT_jhb  <- round(JT_pool * 0.42)                           # JHB share of ever-enclosed (20-25 of 45-60)
mk <- function(pool, est, J_T, dE, n_pre, n_post, J_C_formula, cv_dose, label,
               do = c("area_V1", "expo_V1", "area_V0"), diag = TRUE, ...) {
  base <- list(pool = pool, est = est, J_T = J_T, dE = dE, n_pre = n_pre, n_post = n_post,
               J_C_formula = J_C_formula, cv_dose = cv_dose, label = label, do = do, diag = diag,
               stock_share = CFG$stock_share, contig_drop = CFG$contig_drop,
               cap_share = CFG$cap_share, min_ctrl = CFG$min_ctrl)
  modifyList(base, list(...))
}
SC <- list()
for (s in names(dE_E1)) {
  dflt <- if (s == "High+") "expo_V1" else c("area_V1", "expo_V1", "area_V0")
  SC[[paste0("E1P_", s)]] <- mk("E1P", "bjs", JT_pool[[s]], dE_E1[[s]], n_pre = 5, n_post = 4,
                                J_C_formula = 30, cv_dose = 1.0, label = paste("E1 pooled", s), do = dflt)
  SC[[paste0("E1J_", s)]] <- mk("E1J", "bjs", JT_jhb[[s]], dE_E1[[s]], n_pre = 2, n_post = 2,
                                J_C_formula = 10, cv_dose = 1.0, label = paste("E1 JHB-only", s), do = dflt)
}
# Sensitivities (pooled, area V1 only)
SC$SENS_nobin    <- modifyList(SC$E1P_Mid, list(stock_share = 0, label = "Mid: no stock bins", do = "area_V1", diag = FALSE))
SC$SENS_nocontig <- modifyList(SC$E1P_Mid, list(contig_drop = 0, label = "Mid: no contiguity loss", do = "area_V1", diag = FALSE))
SC$SENS_norule   <- modifyList(SC$E1P_Mid, list(min_ctrl = 0, label = "Mid: cell rule off", do = "area_V1"))
SC$SENS_L2       <- modifyList(SC$E1P_Mid, list(lag_probs = c("2" = 1), label = "Mid: all L = 2", do = "area_V1", diag = FALSE))
SC$SENS_nocap    <- modifyList(SC$E1P_High, list(cap_share = NA_real_, label = "High: no treated-share cap (memo $J_T = 40$)", do = "area_V1"))

# ==============================================================================
# 1. DATA
# ==============================================================================
fn_path <- here("scripts", "analysis", "power", "_power_functions.R")
source(fn_path)

panel <- as.data.table(read_parquet(here("data", "cleaned", "power", "saps_cluster_panel.parquet")))
panel[, `:=`(y_V1 = asinh(V1_total), y_V0 = asinh(V0_index))]
ids <- sort(unique(panel$cluster_id)); panel[, id := match(cluster_id, ids)]
BASE <- panel[, .(cluster_id, id, metro = metro_code, fy, y_V1, y_V0)]
setkey(BASE, cluster_id)
stopifnot(BASE[, .N, by = cluster_id][, all(N == length(CFG$years))], !anyNA(BASE$y_V1))
PRE <- pre_stats(BASE)
meta <- unique(BASE[, .(cluster_id, id, metro)])
# outcome matrices: clusters x years (rownames = cluster_id)
to_mat <- function(v) {
  w <- dcast(BASE, cluster_id ~ fy, value.var = v)
  m <- as.matrix(w[, -1]); rownames(m) <- w$cluster_id
  stopifnot(identical(colnames(m), as.character(CFG$years)), !anyNA(m))
  m
}
YMAT <- list(V1 = to_mat("y_V1"), V0 = to_mat("y_V0"))

# Cape Town clusters that do NOT overlap any SRA polygon (geometry only; >2% of the
# cluster's area inside any SRA polygon excludes it)
g  <- st_read(here("data", "cleaned", "units", "precinct_clusters.gpkg"),
              layer = "precinct_clusters", quiet = TRUE)
g  <- g[g$in_scope & g$metro_code == "CPT", ]
sr <- st_make_valid(st_transform(st_read(here("data", "cleaned", "e3", "sra_polygons.gpkg"),
                                         quiet = TRUE), st_crs(g)))
u_sra <- st_union(st_geometry(sr)); a_g <- as.numeric(st_area(g))
sra_share <- vapply(seq_len(nrow(g)), function(i) {
  z <- suppressWarnings(st_intersection(st_geometry(g)[i], u_sra))
  if (length(z)) sum(as.numeric(st_area(z))) / a_g[i] else 0 }, 0)
cpt_flag <- data.table(cluster_id = g$cluster_id, sra_area_share = sra_share,
                       non_sra = sra_share <= 0.02)
write_parquet(cpt_flag, here("data", "cleaned", "power", "cpt_non_sra_pool.parquet"))
message("CPT clusters: ", nrow(cpt_flag), "; non-SRA (<=2% overlap): ", sum(cpt_flag$non_sra))

# Pools = all in-scope clusters; the range rule is applied per draw on the
# switcher/control overlap (support_overlap), not on the whole pool.
ids_pool <- list(
  E1P = meta[metro %in% c("JHB", "TSH", "EKU"), cluster_id],
  E1J = meta[metro == "JHB", cluster_id],
  E3  = intersect(meta[metro == "CPT", cluster_id], cpt_flag[non_sra == TRUE, cluster_id]))
POOLS <- lapply(ids_pool, function(i) meta[cluster_id %in% i, .(cluster_id, metro)])
pool_sizes <- vapply(POOLS, nrow, 1L)
message("Pools (in scope): ", paste(names(POOLS), pool_sizes, collapse = ", "))

# E3 scenarios: timing structure from the 12 residential G3 candidates (timing ONLY).
# No treated-share cap: J_T is the real candidate count; the real controls are the
# non-SRA pool itself, so simulated J_C (pool - J_T) understates the real J_C.
onsets <- as.data.table(read_parquet(here("data", "cleaned", "e3", "sra_onsets.parquet")))
tm <- onsets[g3_candidate_with_first_stage == TRUE, .(G = as.integer(G_fy), Gt = as.integer(G_tilde_fy))]
stopifnot(nrow(tm) == 12, all(tm$G - tm$Gt == 2L), all(tm$Gt >= CFG$gt_min))
message("E3 timing structure (G_tilde years): ", paste(sort(tm$Gt), collapse = " "))
mk3 <- function(J_T, dE, J_C_formula, label, do = c("area_V1", "expo_V1", "area_V0"))
  mk("E3", "cs", J_T, dE, n_pre = 0, n_post = 0, J_C_formula = J_C_formula, cv_dose = 0.5,
     label = label, do = do, timing = tm, stock_share = 0, cap_share = NA_real_)
SC$E3_all      <- mk3(12, 0.30, 18, "E3 (12 treated, dE = 0.3)")
SC$E3_J9       <- mk3(9, 0.30, 18, "E3 (9 treated, dE = 0.3)", do = c("area_V1", "expo_V1"))
SC$E3_highdose <- mk3(5, 0.60, 18, "E3 high-dose subset (5 treated, dE = 0.6)", do = c("area_V1", "expo_V1"))

# Noise diagnostics: compare with the memo's ASSUMED sigma_c and rho (V1 0.12; murder 0.30; rho 0.3)
diag_noise <- rbindlist(lapply(c("y_V1", "y_V0"), function(v) {
  d <- copy(BASE)[metro %in% c("JHB", "TSH", "EKU")]
  m <- feols(as.formula(paste(v, "~ 1 | id + metro^fy")), data = d)
  d[, r := resid(m)]; setorder(d, id, fy)
  d[, r_l := shift(r), by = id]
  rho <- d[!is.na(r_l), sum(r * r_l) / sum(r_l^2)]
  data.table(outcome = v, sd_resid_twfe = sd(d$r), ar1_rho = rho,
             sd_resid_twfe_post2010 = sd(d[fy >= 2010]$r))
}))
message(paste(capture.output(print(diag_noise)), collapse = "\n"))

# ==============================================================================
# 2. WORKER: one placebo draw for one scenario
# ==============================================================================
run_draw <- function(task) {
  assign(".Random.seed", task$seed, envir = .GlobalEnv)
  sc <- SC[[task$cfg_id]]; yrs <- CFG$years; zc <- qnorm(1 - CFG$alpha / 2)
  des <- draw_design(POOLS[[sc$pool]], sc, CFG, PRE)
  rep_all <- des$cls == "reported"
  design_row <- data.table(cfg_id = task$cfg_id, draw = task$draw,
    J_T_drawn = attr(des, "n_reported_drawn"),
    n_off_support_T = sum(rep_all & des$off_support),
    n_off_support_C = sum(des$cls %in% c("never", "post_window") & des$off_support),
    n_fail_cell = sum(des$dropped_cell), n_fail_bin = sum(des$dropped_cell & des$fail_bin),
    n_fail_metro = sum(des$dropped_cell & des$fail_metro), J_NYT_mean = attr(des, "nyt_mean"))
  des <- des[keep == TRUE]
  rep <- des$cls == "reported"
  J_T <- sum(rep); J_C <- sum(des$cls %in% c("never", "post_window"))
  design_row[, `:=`(J_T = J_T, J_C = J_C, N_sample = nrow(des),
    share_bin1_reported = if (J_T) mean(des$bin[rep]) else NA_real_,
    mean_L = if (J_T) mean(des$L[rep]) else NA_real_,
    mean_dose = if (J_T) mean(des$dose[rep]) else NA_real_)]
  feasible <- J_T >= CFG$min_JT && J_C >= 3
  N <- nrow(des); nT <- length(yrs)
  # long panel, unit-major (row k*nT + t), aligned with matrix(V, N, nT, byrow = TRUE)
  dat <- des[rep(seq_len(N), each = nT), .(cluster_id, metro, cls, G, Gt, bin)]
  dat[, `:=`(id = rep(seq_len(N), each = nT), fy = rep(yrs, N))]
  dat[, g_imp := fifelse(cls == "never", 0L, as.integer(Gt))]
  Y <- lapply(YMAT, function(m) m[des$cluster_id, , drop = FALSE])
  dat[, `:=`(y_V1 = as.vector(t(Y$V1)), y_V0 = as.vector(t(Y$V0)))]
  V <- NULL
  if (feasible) {
    if (sc$est == "bjs") { dat <- add_weights(dat, CFG); V <- bjs_V(dat) }
    else V <- cs_V(dat, L = 2L, ell_max = CFG$ell_max)
  }
  design_row[, `:=`(feasible = feasible && !is.null(V), estimable = !feasible || !is.null(V))]
  if (!feasible || is.null(V)) return(list(design = design_row, res = NULL, diag = NULL))

  Vm <- matrix(V, N, nT, byrow = TRUE)
  Dm <- outer(ifelse(rep, des$G, Inf), yrs, "<=") * 1
  De <- Dm * ifelse(rep, des$dose, 0)
  perms <- draw_perms(des$metro, CFG$n_perm)
  pkg <- function(y, fe_bin = TRUE) if (sc$est == "bjs") est_bjs(dat, y, fe_bin)
                                    else est_cs(dat, L = 2L, ell_max = CFG$ell_max, yname = y)
  series <- list(
    area_V1 = list(o = "V1", cur = "area", D = Dm, grid = CFG$grid_V1),
    expo_V1 = list(o = "V1", cur = "expo", D = De, grid = CFG$grid_expo_area / sc$dE),
    area_V0 = list(o = "V0", cur = "area", D = Dm, grid = CFG$grid_V0))[sc$do]
  an <- list()                                   # package estimate + analytic SE at delta = 0
  for (o in unique(vapply(series, `[[`, "", "o"))) an[[o]] <- pkg(paste0("y_", o))
  res <- list(); dg <- list()
  for (nm in names(series)) {
    s <- series[[nm]]
    r <- ri_grid(Vm, Y[[s$o]], s$D, perms, s$grid, CFG$alpha)
    # analytic test: the BJS / CS analytic SE is invariant to a constant shift of
    # treated post-period outcomes, so it is valid along the area grid only
    rej_an <- if (s$cur == "area") abs(r$s0 + s$grid * r$c) / an[[s$o]][["se"]] > zc else NA
    res[[nm]] <- data.table(outcome = s$o, currency = s$cur, delta = s$grid,
                            rej_ri = r$rej, rej_an = rej_an)
    if (s$cur == "area")
      dg[[nm]] <- data.table(outcome = s$o, est = r$s0, c_inject = r$c, p_ri = r$p_at0,
                             est_pkg = an[[s$o]][["est"]], se_pkg = an[[s$o]][["se"]])
  }
  dg <- rbindlist(dg)
  if (isTRUE(sc$diag) && nrow(dg)) {
    tw <- est_twfe(dat, "y_V1")
    nb <- if (sc$est == "bjs" && uniqueN(des$bin) > 1) pkg("y_V1", fe_bin = FALSE) else c(est = NA, se = NA)
    dg[outcome == "V1", `:=`(est_twfe = tw[["est"]], se_twfe = tw[["se"]],
                             est_nobin = nb[["est"]], se_nobin = nb[["se"]])]
  }
  res <- rbindlist(res)
  res[, `:=`(cfg_id = task$cfg_id, draw = task$draw)]
  dg[, `:=`(cfg_id = task$cfg_id, draw = task$draw, J_T = J_T, J_C = J_C)]
  list(design = design_row, res = res, diag = dg)
}

# ==============================================================================
# 3. RUN (parallel, reproducible: per-scenario seed from a hash of the scenario
#    id, then L'Ecuyer streams per draw -- results do not depend on which other
#    scenarios are run or in what order)
# ==============================================================================
RNGkind("L'Ecuyer-CMRG")
sc_seed <- function(id) (CFG$seed + strtoi(substr(digest(id, algo = "xxhash32"), 1, 6), 16L)) %% .Machine$integer.max
task_list <- unlist(lapply(names(SC), function(id) {
  set.seed(sc_seed(id)); s <- .Random.seed
  lapply(seq_len(CFG$n_draws), function(d) {
    tk <- list(cfg_id = id, draw = d, seed = s); s <<- nextRNGStream(s); tk })
}), recursive = FALSE)
message("tasks: ", length(task_list), " (", length(SC), " scenarios x ", CFG$n_draws, " draws)")

# Checkpoint per scenario, keyed on a hash of everything that determines its draws
fn_src <- readLines(fn_path)
ckpt_key <- function(id) substr(digest(list(CFG[setdiff(names(CFG), "n_workers")], SC[[id]],
  POOLS[[SC[[id]]$pool]], BASE, PRE, fn_src, deparse(run_draw), sc_seed(id))), 1, 12)
ckpt_dir <- here("data", "cleaned", "power", "intermediate", "checkpoints")
dir.create(ckpt_dir, recursive = TRUE, showWarnings = FALSE)

cl <- makeCluster(min(CFG$n_workers, detectCores() - 1L))
t_sim <- Sys.time()
out <- list()
tryCatch({
  invisible(clusterEvalQ(cl, {
    library(data.table); library(fixest); library(didimputation); library(did)
    setFixest_nthreads(1); data.table::setDTthreads(1); RNGkind("L'Ecuyer-CMRG"); NULL }))
  clusterExport(cl, c("CFG", "SC", "POOLS", "BASE", "PRE", "YMAT", "run_draw", "fn_path"),
                envir = environment())
  invisible(clusterEvalQ(cl, source(fn_path)))
  for (sc_id in names(SC)) {
    ckpt <- file.path(ckpt_dir, sprintf("%s_%s.rds", sc_id, ckpt_key(sc_id)))
    if (file.exists(ckpt)) {
      out[[sc_id]] <- readRDS(ckpt); message("checkpoint loaded: ", sc_id); next
    }
    t_sc <- Sys.time()
    out[[sc_id]] <- parLapplyLB(cl, Filter(function(t) t$cfg_id == sc_id, task_list), run_draw)
    saveRDS(out[[sc_id]], ckpt)
    message(sprintf("scenario %s: %d draws, %.1f min", sc_id, CFG$n_draws,
                    as.numeric(difftime(Sys.time(), t_sc, units = "mins"))))
  }
}, finally = stopCluster(cl))
sim_secs <- as.numeric(difftime(Sys.time(), t_sim, units = "secs"))
out <- unlist(out, recursive = FALSE)
res  <- rbindlist(lapply(out, `[[`, "res"))
des  <- rbindlist(lapply(out, `[[`, "design"), fill = TRUE)    # infeasible draws lack the estimation columns
diag <- rbindlist(lapply(out, `[[`, "diag"), fill = TRUE)      # TWFE / no-bin columns only where run
message(sprintf("simulation: %.1f min; %d result rows", sim_secs / 60, nrow(res)))
message("max |in-house - package| estimate at delta = 0: ",
        signif(diag[, max(abs(est - est_pkg), na.rm = TRUE)], 3))

write_parquet(res, here("data", "cleaned", "power", "pe_draws.parquet"))
write_parquet(diag, here("data", "cleaned", "power", "pe_diag_draws.parquet"))
write_parquet(des, here("data", "cleaned", "power", "pe_design_draws.parquet"))
saveRDS(list(CFG = CFG, SC = SC, pool_sizes = pool_sizes, diag_noise = diag_noise,
             e3_timing = tm, sim_secs = sim_secs, sc_seeds = vapply(names(SC), sc_seed, 0),
             total_secs = as.numeric(difftime(Sys.time(), t_start, units = "secs")),
             sessionInfo = utils::sessionInfo(), seed = CFG$seed),
        here("data", "cleaned", "power", "pe_inputs.rds"))
message("done. total ", round(as.numeric(difftime(Sys.time(), t_start, units = "mins")), 1), " min")

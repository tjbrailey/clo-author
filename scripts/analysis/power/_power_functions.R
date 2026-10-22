# ==============================================================================
# _power_functions.R -- design draws, cell rule, estimators and inference for P-E
# Project: PSC Exposure (WP3, pilot step P-E)
# Purpose: Helper functions sourced by 02_placebo_power.R (master and workers).
#          Nothing in here touches real treatment onsets: pseudo (G_tilde, G)
#          pairs are drawn from the ASSUMED distributions in the config.
#          Both primary estimators (BJS imputation, unconditional CS) are linear
#          in the outcome, theta_hat = sum(V * Y), with V fixed by the design. The
#          weight matrix V is built once per draw; the injected-effect grid and the
#          placebo-unit randomisation inference are then exact and cheap.
# Inputs:  none (functions only)
# Outputs: none
# Dependencies: data.table, fixest, didimputation, did
# ==============================================================================

suppressPackageStartupMessages({
  library(data.table); library(fixest); library(didimputation); library(did)
})

# ---- Pre-period statistics ---------------------------------------------------------
# Pre-period crime level (FY2005-07) and trend (FY2005-09 slope) on the asinh(V1)
# scale. The memo's logit of ever-enclosed on Census-2011 covariates cannot be built
# yet (SAL data pending); the range rule uses these two variables only.
pre_stats <- function(base) {
  b <- base[fy %in% 2005:2009]
  b[, .(lvl0507 = mean(y_V1[fy <= 2007]),
        gr0509  = coef(lm(y_V1 ~ fy))[2]), by = cluster_id]
}

# Range rule (memo S3.2 rule 1), applied per draw: keep units whose pre-period
# level and trend lie inside the overlap of the switcher range and the control range.
support_overlap <- function(u, pre) {
  u <- merge(u, pre, by = "cluster_id", sort = FALSE)
  tr <- u$cls == "reported"; cn <- u$cls %in% c("never", "post_window")
  if (!any(tr) || !any(cn)) return(u[, `:=`(off_support = FALSE)][])
  keep <- rep(TRUE, nrow(u))
  for (v in c("lvl0507", "gr0509")) {
    lo <- max(min(u[[v]][tr]), min(u[[v]][cn])); hi <- min(max(u[[v]][tr]), max(u[[v]][cn]))
    keep <- keep & u[[v]] >= lo & u[[v]] <= hi
  }
  u[, off_support := !keep][]
}

# ---- Random draws ----------------------------------------------------------------
draw_lognormal <- function(n, mean, cv) {
  s2 <- log(1 + cv^2)
  rlnorm(n, log(mean) - s2 / 2, sqrt(s2))
}

# Eligible controls at each year (memo S3.2 rule 6): never units, and any unit not
# yet treated (G_tilde > t) -- reported, pre-window and post-window switchers alike.
eligible_matrix <- function(u, yrs) {
  vapply(yrs, function(t) u$cls == "never" | (!is.na(u$Gt) & u$Gt > t), logical(nrow(u)))
}

# Draw one pseudo design. `pool` has columns cluster_id, metro (all in-scope
# clusters). Returns the unit table with class in {reported, pre_window,
# post_window, never}, G, Gt, L, bin, dose, and drop flags (contiguity, support,
# cell rule). Only rows with keep == TRUE enter estimation.
draw_design <- function(pool, sc, cfg, pre) {
  N <- nrow(pool)
  n_rep <- sc$J_T; n_pre <- sc$n_pre; n_post <- sc$n_post
  # realistic treated share: cap reported switchers at cap_share of the in-scope pool
  if (!is.na(sc$cap_share)) n_rep <- min(n_rep, floor(sc$cap_share * N))
  # never let treated classes crowd out controls entirely
  max_tr <- N - cfg$min_ctrl
  if (n_rep + n_pre + n_post > max_tr) {
    shrink <- max_tr / (n_rep + n_pre + n_post)
    n_rep <- floor(n_rep * shrink); n_pre <- floor(n_pre * shrink)
    n_post <- floor(n_post * shrink)
  }
  u <- copy(pool)[sample.int(N)]
  u[, cls := "never"]
  u[seq_len(n_rep), cls := "reported"]
  u[n_rep + seq_len(n_pre), cls := "pre_window"]
  u[n_rep + n_pre + seq_len(n_post), cls := "post_window"]
  u[, `:=`(G = NA_integer_, Gt = NA_integer_, L = NA_integer_, dose = NA_real_)]
  # stock bin {0, >0}
  u[, bin := as.integer(runif(.N) < sc$stock_share)]
  # reported cohort: G from the window, L from the lag distribution truncated so
  # that Gt >= gt_min (>= 4 clean pre-years)
  if (n_rep > 0) {
    if (!is.null(sc$timing)) {
      # E3: timing structure only -- the (G, G_tilde) pairs of the residential G3
      # candidates are re-assigned to randomly drawn NON-SRA clusters
      tm <- sc$timing[sample.int(nrow(sc$timing), n_rep)]
      Gs <- as.integer(tm$G); Ls <- as.integer(tm$G - tm$Gt)
    } else {
      Gs <- sample(cfg$G_min:cfg$G_max, n_rep, TRUE, prob = cfg$G_weights)
      lp <- if (is.null(sc$lag_probs)) cfg$lag_probs else sc$lag_probs
      lv <- as.integer(names(lp))
      Ls <- vapply(Gs, function(g) {
        ok <- lv <= g - cfg$gt_min
        lv[ok][sample.int(sum(ok), 1, prob = lp[ok])]
      }, integer(1))
    }
    idx <- which(u$cls == "reported")
    set(u, idx, "G", Gs); set(u, idx, "L", Ls); set(u, idx, "Gt", Gs - Ls)
    set(u, idx, "dose", draw_lognormal(n_rep, sc$dE, sc$cv_dose))
  }
  if (n_pre > 0) {   # kept as treated, no effect, never a control after Gt
    idx <- which(u$cls == "pre_window")
    Gt <- sample(cfg$pre_window_Gt, n_pre, TRUE)
    set(u, idx, "Gt", Gt); set(u, idx, "L", 2L); set(u, idx, "G", Gt + 2L)
  }
  if (n_post > 0) {  # G after the window: control until Gt, effect never injected
    idx <- which(u$cls == "post_window")
    G <- sample(cfg$post_window_G, n_post, TRUE)
    set(u, idx, "G", G); set(u, idx, "L", 2L); set(u, idx, "Gt", G - 2L)
  }
  attr_n_rep <- n_rep
  # contiguity: controls removed at random (static stand-in for the dynamic rule)
  u[, drop_contig := cls %in% c("never", "post_window") & runif(.N) < sc$contig_drop]
  u <- support_overlap(u[drop_contig == FALSE], pre)
  u[, keep := !off_support]
  # cell rule (memo S3.2 rule 6), iterated to a fixed point because a dropped
  # switcher also stops counting as a not-yet-treated control
  yrs <- cfg$years
  u[, `:=`(fail_bin = FALSE, fail_metro = FALSE)]
  if (sc$min_ctrl > 0) {
    repeat {
      k <- u$keep
      em <- eligible_matrix(u, yrs) & k                      # unit x year
      cb <- lapply(0:1, function(b) colSums(em[u$bin == b, , drop = FALSE]))
      mets <- unique(u$metro)
      cm <- setNames(lapply(mets, function(m) colSums(em[u$metro == m, , drop = FALSE])), mets)
      for (i in which(u$cls == "reported" & k)) {
        cols <- match(u$Gt[i]:min(u$G[i] + cfg$cell_horizon, max(yrs)), yrs)
        set(u, i, "fail_bin", min(cb[[u$bin[i] + 1]][cols]) < sc$min_ctrl)
        set(u, i, "fail_metro", min(cm[[u$metro[i]]][cols]) < sc$min_ctrl)
      }
      u[cls == "reported" & keep & (fail_bin | fail_metro), keep := FALSE]
      if (identical(k, u$keep)) break
    }
  }
  u[, dropped_cell := cls == "reported" & !off_support & (fail_bin | fail_metro)]
  # mean number of not-yet-treated switchers eligible as controls over the onset window
  em <- eligible_matrix(u, yrs) & u$keep & u$cls != "never"
  attr(u, "nyt_mean") <- mean(colSums(em[, yrs >= cfg$G_min & yrs <= cfg$G_max, drop = FALSE]))
  attr(u, "n_reported_drawn") <- attr_n_rep
  u
}

# ---- Linear estimator weights ---------------------------------------------------------
# Headline weights: mean of ell = 0..3 (equal weight on each ell present, equal
# weight across treated observations within an ell); reported switchers only.
add_weights <- function(dat, cfg) {
  dat[, ell := fifelse(cls == "reported", fy - G, NA_integer_)]
  dat[, w := 0]
  ok <- dat$cls == "reported" & !is.na(dat$ell) & dat$ell >= 0 & dat$ell <= cfg$ell_max
  dat[ok, w := 1 / .N, by = ell]
  s <- dat[, sum(w)]
  if (s > 0) dat[, w := w / s]   # guard: no treated observations -> all zero
  dat
}

# BJS imputation as a weight vector: theta = sum_T w (y - Z1 b), b = OLS on untreated
# obs, so theta = sum(V * y) with V = w on treated obs, -Z0 (Z0'Z0)^+ Z1'w on untreated.
# Returns NULL if a headline observation's fixed effects are not estimable.
# `dat` columns: id, fy, metro, bin, g_imp, w (any order; V is aligned with rows).
bjs_V <- function(dat, fe_bin = TRUE) {
  treat <- dat$g_imp > 0 & dat$fy >= dat$g_imp
  Z <- cbind(model.matrix(~ factor(id) - 1, dat),
             model.matrix(~ factor(paste(metro, fy)) - 1, dat))
  if (fe_bin && uniqueN(dat$bin) > 1)
    Z <- cbind(Z, model.matrix(~ factor(paste(bin, fy)) - 1, dat))
  Z0 <- Z[!treat, , drop = FALSE]; w1 <- dat$w[treat]
  a <- crossprod(Z[treat, , drop = FALSE], w1)[, 1]
  qz <- qr(Z0); r <- qz$rank; piv <- qz$pivot[seq_len(r)]
  R11 <- qr.R(qz)[seq_len(r), seq_len(r), drop = FALSE]
  u <- backsolve(R11, a[piv], transpose = TRUE)
  x <- numeric(ncol(Z)); x[piv] <- backsolve(R11, u)
  if (max(abs(a - crossprod(Z0, Z0 %*% x))) > 1e-8) return(NULL)   # not estimable
  V <- numeric(nrow(dat)); V[treat] <- w1
  V[!treat] <- -(qr.Q(qz)[, seq_len(r), drop = FALSE] %*% u)[, 1]
  V
}

# Callaway-Sant'Anna (E3) as a weight vector: not-yet-treated controls (g_j > t or
# never), universal base period g - 1 (g = G_tilde), unconditional; dynamic
# aggregation over e = L..L + ell_max with group-size weights within e and equal
# weight across e (as did::aggte(type = "dynamic")). Returns NULL if a cell has no
# controls. Assumes a common lag L (true for the 12 E3 candidates).
cs_V <- function(dat, L = 2L, ell_max = 3L) {
  ut <- unique(dat[, .(id, g_imp)]); yrs <- sort(unique(dat$fy))
  key <- paste(dat$id, dat$fy); V <- numeric(nrow(dat))
  pos <- function(ids, t) match(paste(ids, t), key)
  groups <- sort(unique(ut$g_imp[ut$g_imp > 0]))
  ng <- table(ut$g_imp[ut$g_imp > 0])
  es <- L:(L + ell_max); n_e <- 0L
  for (e in es) {
    gs <- groups[groups + e <= max(yrs)]
    if (!length(gs)) next
    pg <- as.numeric(ng[as.character(gs)]); pg <- pg / sum(pg)
    n_e <- n_e + 1L
    for (j in seq_along(gs)) {
      g <- gs[j]; t <- g + e; b <- g - 1L
      tr <- ut$id[ut$g_imp == g]; cn <- ut$id[ut$g_imp == 0 | ut$g_imp > t]
      if (!length(cn)) return(NULL)
      for (ids_s in list(list(tr, 1), list(cn, -1))) {
        ids <- ids_s[[1]]; s <- ids_s[[2]] * pg[j] / length(ids)
        V[pos(ids, t)] <- V[pos(ids, t)] + s
        V[pos(ids, b)] <- V[pos(ids, b)] - s
      }
    }
  }
  if (n_e == 0L) return(NULL)
  V / n_e
}

# ---- Package estimators (analytic SE; used at delta = 0 only) ------------------------
bjs_formula <- function(dat, fe_bin = TRUE) {
  nm <- uniqueN(dat$metro); nb <- if (fe_bin) uniqueN(dat$bin) else 1L
  if (nm > 1 && nb > 1) ~ 0 | id + metro^fy + bin^fy
  else if (nm > 1)      ~ 0 | id + metro^fy
  else if (nb > 1)      ~ 0 | id + bin^fy
  else                  ~ 0 | id + fy
}

est_bjs <- function(dat, yname = "y", fe_bin = TRUE) {
  out <- tryCatch(suppressWarnings(suppressMessages(
    did_imputation(data = dat, yname = yname, gname = "g_imp", tname = "fy", idname = "id",
                   first_stage = bjs_formula(dat, fe_bin), wtr = "w", cluster_var = "id"))),
    error = function(e) NULL)
  if (is.null(out) || nrow(out) == 0) return(c(est = NA_real_, se = NA_real_))
  c(est = out$estimate[1], se = out$std.error[1])
}

est_cs <- function(dat, L = 2L, ell_max = 3L, yname = "y") {
  d <- as.data.frame(dat[, .(id, fy, yy = get(yname), g_imp)])
  tryCatch(suppressWarnings(suppressMessages({
    a <- att_gt(yname = "yy", tname = "fy", idname = "id", gname = "g_imp", data = d,
                xformla = ~1, control_group = "notyettreated", base_period = "universal",
                anticipation = 0, bstrap = FALSE, cband = FALSE, panel = TRUE,
                print_details = FALSE)
    ag <- aggte(a, type = "dynamic", min_e = L, max_e = L + ell_max, bstrap = FALSE,
                cband = FALSE)
    c(est = ag$overall.att, se = ag$overall.se)
  })), error = function(e) c(est = NA_real_, se = NA_real_))
}

# Static TWFE benchmark (size diagnostic only): D = 1 for reported switchers from G;
# dip-window obs (G_tilde <= t < G) and treated-period obs of pre/post-window units dropped.
est_twfe <- function(dat, yname = "y") {
  d <- dat[!(cls == "reported" & fy >= Gt & fy < G) & !(cls %in% c("pre_window", "post_window") & fy >= Gt)]
  d[, D := as.numeric(cls == "reported" & fy >= G)]
  f <- if (uniqueN(d$metro) > 1) as.formula(paste(yname, "~ D | id + metro^fy"))
       else as.formula(paste(yname, "~ D | id + fy"))
  m <- tryCatch(feols(f, data = d, cluster = ~id, warn = FALSE, notes = FALSE), error = function(e) NULL)
  if (is.null(m) || !"D" %in% names(coef(m))) return(c(est = NA_real_, se = NA_real_))
  c(est = unname(coef(m)["D"]), se = unname(se(m)["D"]))
}

# ---- Placebo-unit randomisation inference (memo S13.2) -----------------------------
# Permutations of units within metro strata (equivalently, re-assignment of the
# drawn treatment profiles to other units in the analysis sample). Returns an
# R x N matrix of row permutations.
draw_perms <- function(strata, R) {
  idx <- split(seq_along(strata), strata)
  t(vapply(seq_len(R), function(r) {
    p <- seq_along(strata)
    for (s in idx) p[s] <- s[sample.int(length(s))]
    p
  }, integer(length(strata))))
}

# For Y_obs(delta) = Y0 + delta * D: observed statistic s0 + delta * c, permuted
# statistic p0_r + delta * q_r. Returns, on the delta grid, the RI rejection
# indicator (p-value <= alpha, p = (1 + #{|perm| >= |obs|}) / (R + 1)), and the
# p-value at delta = 0.
ri_grid <- function(V, Y0, D, perms, grid, alpha) {
  s0 <- sum(V * Y0); cc <- sum(V * D)
  p0 <- apply(perms, 1, function(p) sum(V * Y0[p, , drop = FALSE]))
  q  <- apply(perms, 1, function(p) sum(V * D[p, , drop = FALSE]))
  R <- length(p0)
  pv <- vapply(grid, function(dl) {
    (1 + sum(abs(p0 + dl * q) >= abs(s0 + dl * cc) - 1e-12)) / (R + 1)
  }, 0)
  list(rej = pv <= alpha, p_at0 = pv[grid == 0][1], s0 = s0, c = cc)
}

# ---- Formula MDEs (memo S8.1 / S8.4) -------------------------------------------
mean_PQ <- function(g = 2011:2023) mean(1 / (g - 2007) + 1 / pmin(6, 2026 - g))
formula_mde <- function(J_T, J_C, sigma, infl, pq, f = 1.2) {
  2.8 * f * sigma * sqrt(infl * pq * (1 / J_T + 1 / J_C))
}

# ---- Power-curve summaries -------------------------------------------------------
# MDE: smallest delta with (isotonic-smoothed) power >= target, by linear
# interpolation between grid points; NA if not reached on the grid.
mde_from_curve <- function(delta, power, target = 0.8) {
  o <- order(delta); delta <- delta[o]; power <- power[o]
  pw <- if (length(power) > 2) stats::isoreg(delta, power)$yf else power
  j <- which(pw >= target)[1]
  if (is.na(j)) return(NA_real_)
  if (j == 1) return(delta[1])
  delta[j - 1] + (target - pw[j - 1]) * (delta[j] - delta[j - 1]) / (pw[j] - pw[j - 1])
}

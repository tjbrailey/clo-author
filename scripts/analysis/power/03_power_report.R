# ==============================================================================
# 03_power_report.R -- MDE tables, size diagnostics, formula comparison, power curves
# Project: PSC Exposure (WP3, pilot step P-E)
# Purpose: Summarise the placebo simulation of 02_placebo_power.R. Primary
#          inference is placebo-unit randomisation inference (RI); MDEs use RI
#          power, with bootstrap CIs over draws. Analytic cluster-robust MDEs are
#          shown for comparison only. Size at delta = 0 under RI, the analytic SE,
#          BJS without bin^fy and a static TWFE benchmark, overall and by J_C.
#          The memo S8.4 formula MDEs are reproduced as a sanity check. Writes
#          tables (bare tabular), figures (PDF) and the numbers that
#          quality_reports/pilot/P-E_power.md quotes.
# Inputs:  data/cleaned/power/pe_draws.parquet, pe_diag_draws.parquet,
#          pe_design_draws.parquet, pe_inputs.rds
# Outputs: paper/tables/03_power_report/*.tex
#          paper/figures/03_power_report/*.pdf
#          data/cleaned/power/pe_mde_summary.rds  (all summary tables)
# Dependencies: data.table, arrow, ggplot2, here; _power_functions.R
# ==============================================================================

suppressPackageStartupMessages({
  library(data.table); library(arrow); library(ggplot2); library(here)
})
source(here("scripts", "analysis", "power", "_power_functions.R"))
inp <- readRDS(here("data", "cleaned", "power", "pe_inputs.rds"))
CFG <- inp$CFG; SC <- inp$SC
res  <- as.data.table(read_parquet(here("data", "cleaned", "power", "pe_draws.parquet")))
dg   <- as.data.table(read_parquet(here("data", "cleaned", "power", "pe_diag_draws.parquet")))
des  <- as.data.table(read_parquet(here("data", "cleaned", "power", "pe_design_draws.parquet")))
n_draws <- CFG$n_draws
set.seed(CFG$seed)            # bootstrap over draws only
zc <- qnorm(1 - CFG$alpha / 2)
B_BOOT <- 500L

tab_dir <- here("paper", "tables", "03_power_report"); fig_dir <- here("paper", "figures", "03_power_report")
for (d in c(tab_dir, fig_dir)) dir.create(d, recursive = TRUE, showWarnings = FALSE)

# ---- 1. Power curves and MDEs ------------------------------------------------------
# Headline: infeasible draws (no estimate) count as non-rejections, power = rejections
# / n_draws, so power is capped at the feasible share. The MDE conditional on feasible
# draws is reported alongside, with feasibility as a separate design metric.
n_an_na <- res[currency == "area", sum(is.na(rej_an))]   # failed package calls (should be 0)
curves <- res[, .(power_ri = sum(rej_ri) / n_draws, power_an = sum(rej_an, na.rm = TRUE) / n_draws,
                  power_ri_feas = mean(rej_ri), n = .N), by = .(cfg_id, outcome, currency, delta)]
setorder(curves, cfg_id, outcome, currency, delta)

# Bootstrap the MDE by resampling draws (infeasible draws enter as all-FALSE rows).
boot_mde <- function(d, col, B) {
  grid <- sort(unique(d$delta))
  M <- matrix(FALSE, n_draws, length(grid))
  M[cbind(d$draw, match(d$delta, grid))] <- d[[col]] %in% TRUE
  point <- mde_from_curve(grid, colMeans(M), CFG$target_power)
  if (B == 0) return(c(mde = point, lo = NA_real_, hi = NA_real_, frac_na = NA_real_))
  bs <- replicate(B, mde_from_curve(grid, colMeans(M[sample.int(n_draws, n_draws, TRUE), , drop = FALSE]),
                                    CFG$target_power))
  c(mde = point, lo = unname(quantile(bs, .025, na.rm = TRUE)),
    hi = unname(quantile(bs, .975, na.rm = TRUE)), frac_na = mean(is.na(bs)))
}
mde <- res[, {
  r <- boot_mde(.SD, "rej_ri", B_BOOT)
  a <- if (currency[1] == "area") boot_mde(.SD, "rej_an", 0) else c(mde = NA_real_)
  cf <- .SD[, .(p = mean(rej_ri)), by = delta]
  .(mde = r[["mde"]], mde_lo = r[["lo"]], mde_hi = r[["hi"]], frac_na_boot = r[["frac_na"]],
    mde_analytic = a[["mde"]], mde_feasible = mde_from_curve(cf$delta, cf$p, CFG$target_power))
}, by = .(cfg_id, outcome, currency)]

# ---- 2. Size at delta = 0 ---------------------------------------------------------
rej <- function(est, se) abs(est / se) > zc
size <- dg[, .(n_feasible = .N,
  size_ri = mean(p_ri <= CFG$alpha),
  size_an = mean(rej(est_pkg, se_pkg), na.rm = TRUE),
  size_nobin = if (all(is.na(se_nobin))) NA_real_ else mean(rej(est_nobin, se_nobin), na.rm = TRUE),
  size_twfe = if (all(is.na(se_twfe))) NA_real_ else mean(rej(est_twfe, se_twfe), na.rm = TRUE),
  sd_over_se = sd(est) / mean(se_pkg),
  max_abs_diff_pkg = if (all(is.na(est_pkg))) NA_real_ else max(abs(est - est_pkg), na.rm = TRUE)), by = .(cfg_id, outcome)]
size[, mc_se := sqrt(CFG$alpha * (1 - CFG$alpha) / n_feasible)]   # Monte Carlo SE at nominal size

# size by J_C, pooled over the E1 scenarios that ran the diagnostics (V1)
e1_diag <- names(SC)[vapply(SC, function(s) s$pool %in% c("E1P", "E1J") && isTRUE(s$diag), TRUE)]
jc <- dg[outcome == "V1" & cfg_id %in% e1_diag]
jc[, jc_bin := cut(J_C, c(0, 10, 20, 30, 40, Inf), labels = c("3--10", "11--20", "21--30", "31--40", "$>$40"))]
size_jc <- jc[, .(n = .N, size_ri = mean(p_ri <= CFG$alpha), size_an = mean(rej(est_pkg, se_pkg), na.rm = TRUE),
                  size_twfe = mean(rej(est_twfe, se_twfe), na.rm = TRUE),
                  size_nobin = mean(rej(est_nobin, se_nobin), na.rm = TRUE),
                  mean_JT = mean(J_T)), keyby = jc_bin]

# ---- 3. Realised design --------------------------------------------------------------
design_sum <- des[, .(feasible = mean(feasible), non_estimable = mean(!estimable), J_T_drawn = mean(J_T_drawn),
                      off_support_T = mean(n_off_support_T), off_support_C = mean(n_off_support_C),
                      dropped_cell = mean(n_fail_cell), J_T_kept = mean(J_T, na.rm = TRUE),
                      J_C = mean(J_C, na.rm = TRUE), J_NYT = mean(J_NYT_mean),
                      share_bin1 = mean(share_bin1_reported, na.rm = TRUE),
                      mean_L = mean(mean_L, na.rm = TRUE)), by = cfg_id]

# ---- 4. Memo S8.4 formula MDEs ----------------------------------------------------
pq <- mean_PQ(2011:2023)
fm <- rbindlist(lapply(names(SC), function(k) {
  s <- SC[[k]]
  data.table(cfg_id = k, J_T = s$J_T, J_C_memo = s$J_C_formula, dE = s$dE,
             f_V1 = formula_mde(s$J_T, s$J_C_formula, CFG$sigma_V1, CFG$infl_rho03, pq, CFG$f),
             f_V0 = formula_mde(s$J_T, s$J_C_formula, CFG$sigma_V0, CFG$infl_rho03, pq, CFG$f))
}))
fm[, f_expo_V1 := f_V1 / dE]
# memo S8.4 published values (reproduction check for the pooled E1 and E3 rows)
memo <- data.table(
  cfg_id = c("E1P_Low", "E1P_Mid", "E1P_High", "E1P_High+", "E3_all", "E3_highdose", "E3_J9"),
  memo_V1 = c(.083, .075, .070, .070, .108, .146, .119),
  memo_V0 = c(.21, .19, .18, .18, .27, NA, NA),
  memo_expo = c(29, 5.8, 2.0, 1.2, .36, .24, .40))
fm <- merge(fm, memo, by = "cfg_id", all.x = TRUE)
fm[, `:=`(diff_V1 = f_V1 - memo_V1, diff_V0 = f_V0 - memo_V0, rel_expo = f_expo_V1 / memo_expo - 1)]

# ---- 5. Assemble ---------------------------------------------------------------------
wide <- dcast(mde, cfg_id ~ outcome + currency, value.var = c("mde", "mde_lo", "mde_hi", "mde_analytic", "mde_feasible"))
M <- Reduce(function(a, b) merge(a, b, by = "cfg_id", all.x = TRUE),
            list(wide, design_sum, fm[, .(cfg_id, dE, J_C_memo, f_V1, f_V0, f_expo_V1)],
                 size[outcome == "V1", .(cfg_id, size_ri_V1 = size_ri, size_an_V1 = size_an)]))
M[, label := vapply(cfg_id, function(k) SC[[k]]$label, "")]
main_ids <- c("E1P_Low", "E1P_Mid", "E1P_High", "E1P_High+", "E1J_Low", "E1J_Mid", "E1J_High",
              "E1J_High+", "E3_all", "E3_J9", "E3_highdose")
sens_ids <- c("SENS_nobin", "SENS_nocontig", "SENS_norule", "SENS_L2", "SENS_nocap")
M <- M[match(c(main_ids, sens_ids), cfg_id)]

saveRDS(list(curves = curves, mde = mde, size = size, size_jc = size_jc, design = design_sum,
             formula = fm, M = M, pq = pq, n_draws = n_draws, n_perm = CFG$n_perm),
        here("data", "cleaned", "power", "pe_mde_summary.rds"))

# ---- 6. Tables (bare tabular; titles/notes are added in LaTeX) --------------------
# Labels: "$>$grid" = 80% power not reached on the grid; "n.r." = not run for this scenario.
NR <- "n.r."
fmt <- function(x, d = 3) ifelse(is.na(x), "$>$grid", formatC(x, format = "f", digits = d))
fmt_ci <- function(m, lo, hi, d = 3) ifelse(is.na(m), "$>$grid",
  sprintf("%s [%s, %s]", formatC(m, format = "f", digits = d),
          ifelse(is.na(lo), "$>$grid", formatC(lo, format = "f", digits = d)),
          ifelse(is.na(hi), "$>$grid", formatC(hi, format = "f", digits = d))))
ran <- function(k, s) s %in% SC[[k]]$do
write_tab <- function(lines, file) writeLines(lines, file.path(tab_dir, file))

rows <- vapply(main_ids, function(k) {
  r <- M[cfg_id == k]
  sprintf("%s & %.0f & %.1f & %.1f & %.0f & %.2f & %s & %s & %s & %s & %s & %s & %s & %s \\\\",
          r$label, r$J_T_drawn, r$J_T_kept, r$J_C, r$J_C_memo, r$feasible,
          if (ran(k, "area_V1")) fmt_ci(r$mde_V1_area, r$mde_lo_V1_area, r$mde_hi_V1_area) else NR,
          if (ran(k, "area_V1")) fmt(r$mde_feasible_V1_area) else NR,
          if (ran(k, "area_V1")) fmt(r$mde_analytic_V1_area) else NR,
          fmt(r$f_V1),
          if (ran(k, "expo_V1")) fmt(r$mde_V1_expo, 2) else NR,
          fmt(r$f_expo_V1, 2),
          if (ran(k, "area_V0")) fmt(r$mde_V0_area) else NR,
          fmt(r$f_V0))
}, "")
write_tab(c("\\begin{tabular}{lrrrrrlrrrrrrr}", "\\toprule",
  paste(" & \\multicolumn{5}{c}{Design (mean over draws)} & \\multicolumn{4}{c}{Area effect, V1 (asinh pts)}",
        "& \\multicolumn{2}{c}{Exposure-scaled, V1} & \\multicolumn{2}{c}{Area effect, murder} \\\\"),
  "\\cmidrule(lr){2-6}\\cmidrule(lr){7-10}\\cmidrule(lr){11-12}\\cmidrule(lr){13-14}",
  paste("Scenario & $J_T$ drawn & $J_T$ kept & $J_C$ & Memo $J_C$ & Feasible & RI MDE [95\\% CI]",
        "& RI, feasible draws & Analytic & Formula & RI MDE & Formula & RI MDE & Formula \\\\"),
  "\\midrule", rows, "\\bottomrule", "\\end{tabular}"), "mde_main.tex")

srow <- vapply(c("E1P_Mid", sens_ids), function(k) {
  r <- M[cfg_id == k]
  lab <- if (k == "E1P_Mid") "Baseline (E1 pooled Mid)" else r$label
  sprintf("%s & %.1f & %.1f & %.1f & %s & %s \\\\", lab, r$J_T_kept, r$J_C, r$J_NYT,
          fmt_ci(r$mde_V1_area, r$mde_lo_V1_area, r$mde_hi_V1_area), fmt(r$mde_analytic_V1_area))
}, "")
write_tab(c("\\begin{tabular}{lrrrlr}", "\\toprule",
  "Scenario & $J_T$ kept & $J_C$ & Not-yet-treated & RI area MDE [95\\% CI] & Analytic MDE \\\\", "\\midrule",
  srow, "\\bottomrule", "\\end{tabular}"), "mde_sensitivity.tex")

f3 <- function(x) ifelse(is.na(x), NR, formatC(x, format = "f", digits = 3))
zrow <- vapply(c(main_ids[main_ids != "E1J_High+" & main_ids != "E1P_High+"], "SENS_norule", "SENS_nocap"), function(k) {
  r <- size[cfg_id == k & outcome == "V1"]
  sprintf("%s & %d & %s & %s & %s & %s & %.2f \\\\", SC[[k]]$label, r$n_feasible, f3(r$size_ri),
          f3(r$size_an), f3(r$size_nobin), f3(r$size_twfe), r$sd_over_se)
}, "")
write_tab(c("\\begin{tabular}{lrrrrrr}", "\\toprule",
  " & & \\multicolumn{4}{c}{Rejection rate at $\\delta = 0$, nominal 5\\%} & \\\\",
  "\\cmidrule(lr){3-6}",
  "Scenario & Feasible draws & RI & Analytic SE & Analytic, no bin$\\times$year FE & TWFE & SD($\\hat\\theta$)/mean SE \\\\",
  "\\midrule", zrow, "\\bottomrule", "\\end{tabular}"), "size_check.tex")

jrow <- vapply(seq_len(nrow(size_jc)), function(i) {
  r <- size_jc[i]
  sprintf("%s & %d & %.1f & %s & %s & %s & %s \\\\", r$jc_bin, r$n, r$mean_JT, f3(r$size_ri),
          f3(r$size_an), f3(r$size_nobin), f3(r$size_twfe))
}, "")
write_tab(c("\\begin{tabular}{lrrrrrr}", "\\toprule",
  "$J_C$ & Draws & Mean $J_T$ & RI & Analytic SE & Analytic, no bin$\\times$year FE & TWFE \\\\",
  "\\midrule", jrow, "\\bottomrule", "\\end{tabular}"), "size_by_jc.tex")

# ---- 7. Figures (RI power, the primary inference) -----------------------------------
pal <- c("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#000000", "#F0E442")
shp <- c(16, 17, 15, 18, 8, 4, 3, 1); lty <- c("solid", "dashed", "dotted", "dotdash", "longdash", "twodash", "solid", "dashed")
th <- theme_minimal(base_family = "serif", base_size = 14) +
  theme(legend.position = "bottom", panel.grid.minor = element_blank())
lab_dt <- data.table(cfg_id = names(SC), label = vapply(SC, function(s) s$label, ""),
                     design = vapply(SC, function(s) s$pool, ""))
lab_dt[, design_lab := c(E1P = "E1 Gauteng, pooled (3 metros)", E1J = "E1 Johannesburg only",
                         E3 = "E3 Cape Town")[design]]
lab_dt[, scen := sub("^(E1 pooled|E1 JHB-only) ", "", label)]
lab_dt[design == "E3", scen := c(E3_all = "12 treated (dose 0.3)", E3_J9 = "9 treated (dose 0.3)",
                                 E3_highdose = "5 treated (dose 0.6)")[cfg_id]]
cv <- merge(curves, lab_dt, by = "cfg_id")
cv[, design_lab := factor(design_lab, c("E1 Gauteng, pooled (3 metros)", "E1 Johannesburg only", "E3 Cape Town"))]
main_scen <- cv[cfg_id %in% main_ids]
y_lab <- "Power (RI)"
curve_layers <- function(n) list(
  geom_hline(yintercept = CFG$target_power, colour = "grey40", linewidth = .3),
  geom_line(linewidth = .6),
  scale_colour_manual(values = rep(pal, length.out = n)), scale_shape_manual(values = rep(shp, length.out = n)),
  scale_linetype_manual(values = rep(lty, length.out = n)),
  scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, .2)))

fig_area <- function(outc, xlab, file) {
  d <- main_scen[outcome == outc & currency == "area"]
  p <- ggplot(d, aes(delta, power_ri, colour = scen, linetype = scen)) + curve_layers(uniqueN(d$scen)) +
    facet_wrap(~design_lab, nrow = 1) +
    labs(x = xlab, y = y_lab, colour = NULL, linetype = NULL) + th
  ggsave(file.path(fig_dir, file), p, width = 9, height = 3.6, device = cairo_pdf)
}
fig_area("V1", "Injected area-level effect on the targeted index (asinh points)", "power_curves_area_V1.pdf")
fig_area("V0", "Injected area-level effect on murder (asinh points)", "power_curves_area_murder.pdf")

d <- main_scen[outcome == "V1" & currency == "expo" & delta > 0]
p <- ggplot(d, aes(delta, power_ri, colour = scen, linetype = scen)) + curve_layers(uniqueN(d$scen)) +
  facet_wrap(~design_lab, nrow = 1, scales = "free_x") + scale_x_log10() +
  labs(x = "Injected effect on the exposed population (asinh points per unit of exposure, log scale)",
       y = y_lab, colour = NULL, linetype = NULL) + th
ggsave(file.path(fig_dir, "power_curves_exposure_scaled_V1.pdf"), p, width = 9, height = 3.6, device = cairo_pdf)

d <- cv[cfg_id %in% c("E1P_Mid", sens_ids) & outcome == "V1" & currency == "area"]
d[, scen := fifelse(cfg_id == "E1P_Mid", "Baseline (Mid)", sub("^(Mid|High): ", "", label))]
p <- ggplot(d, aes(delta, power_ri, colour = scen, linetype = scen)) + curve_layers(uniqueN(d$scen)) +
  labs(x = "Injected area-level effect on the targeted index (asinh points)",
       y = y_lab, colour = NULL, linetype = NULL) + th + guides(colour = guide_legend(nrow = 2))
ggsave(file.path(fig_dir, "power_curves_sensitivity_mid.pdf"), p, width = 6.5, height = 4.2, device = cairo_pdf)

# RI vs analytic, pooled Mid (shows what the over-rejecting analytic test would claim)
d <- melt(cv[cfg_id == "E1P_Mid" & currency == "area"], id.vars = c("outcome", "delta"),
          measure.vars = c("power_ri", "power_an"), variable.name = "test", value.name = "power")
d[, test := factor(test, c("power_ri", "power_an"), c("Randomisation inference", "Analytic cluster-robust SE"))]
d[, outcome := factor(outcome, c("V1", "V0"), c("Targeted index (V1)", "Murder (V0)"))]
p <- ggplot(d, aes(delta, power, colour = test, linetype = test)) + curve_layers(2) +
  facet_wrap(~outcome, scales = "free_x") +
  labs(x = "Injected area-level effect (asinh points)", y = "Power",
       colour = NULL, linetype = NULL) + th
ggsave(file.path(fig_dir, "power_ri_vs_analytic_mid.pdf"), p, width = 6.5, height = 3.6, device = cairo_pdf)

message("failed analytic calls: ", n_an_na, "; summary tables in data/cleaned/power/pe_mde_summary.rds")
message("03_power_report done")

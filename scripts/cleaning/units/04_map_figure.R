# ==============================================================================
# 04_map_figure.R -- Map of stable ward units and precinct clusters, four metros
# Project: PSC Exposure
# Author:  data-engineer agent for Thomas Brailey
# Date:    2026-09-30
# Purpose: Publication map: row A = stable ward units (single-ward vs merged),
#          row B = time-invariant precinct clusters (never-split vs merged), one
#          column per metro. Serif font, colourblind-safe and grayscale-readable
#          (light vs dark fills), no in-plot title. Uses SAL-weighted SWUs when
#          present, otherwise the provisional SWUs (flagged in the panel label).
# Inputs:  data/cleaned/units/{swu.gpkg | provisional/swu.gpkg},
#          data/cleaned/units/precinct_clusters.gpkg
# Outputs: paper/figures/fig_units_swu_precinct_clusters.pdf
#          data/cleaned/units/intermediate/fig_units_map_data.rds
# ==============================================================================

source(here::here("scripts", "cleaning", "units", "_common.R"))
suppressPackageStartupMessages({ library(ggplot2); library(patchwork) })

swu_file <- file.path(dir_clean, "swu.gpkg")
provisional <- !file.exists(swu_file)
if (provisional) swu_file <- file.path(dir_prov, "swu.gpkg")
swu <- st_read(swu_file, layer = "swu", quiet = TRUE)
w21 <- st_read(swu_file, layer = "wards_2021", quiet = TRUE)
pcl <- st_read(file.path(dir_clean, "precinct_clusters.gpkg"), "precinct_clusters",
               quiet = TRUE)
pcl <- pcl[pcl$in_scope, ]

swu$type <- factor(ifelse(swu$n_w21 == 1 & swu$n_w11 == 1 & swu$n_w16 == 1,
                          "Single ward, unchanged", "Merged (nesting union)"),
                   levels = c("Single ward, unchanged", "Merged (nesting union)"))
pcl$type <- factor(ifelse(pcl$n_stations == 1, "Single precinct, never split",
                          "Merged cluster"),
                   levels = c("Single precinct, never split", "Merged cluster"))

metro_lab <- c(JHB = "Johannesburg", TSH = "Tshwane", EKU = "Ekurhuleni", CPT = "Cape Town")
pal <- c("#DCE3EA", "#2C5F8A")  # light grey-blue vs dark blue: grayscale-safe

theme_map <- theme_void(base_family = "serif", base_size = 14) +
  theme(legend.position = "bottom", legend.direction = "horizontal",
        legend.title = element_blank(), plot.background = element_rect(fill = "white", colour = NA),
        strip.text = element_text(size = 12, margin = margin(b = 3)),
        plot.tag = element_text(size = 12, face = "plain"))

panel <- function(x, m, lines = NULL, fill_vals) {
  x <- x[x$metro_code == m, ]
  p <- ggplot() + geom_sf(data = x, aes(fill = type), colour = "white", linewidth = 0.25)
  if (!is.null(lines)) p <- p + geom_sf(data = lines[lines$metro_code == m, ],
                                        fill = NA, colour = "grey45", linewidth = 0.08)
  p + scale_fill_manual(values = fill_vals, drop = FALSE) +
    labs(title = NULL, subtitle = metro_lab[[m]]) + coord_sf(datum = NA) + theme_map +
    theme(plot.subtitle = element_text(hjust = 0.5, size = 12))
}
ms <- c("JHB", "TSH", "EKU", "CPT")
rowA <- wrap_plots(lapply(ms, function(m) panel(swu, m, w21, pal)), nrow = 1)
rowB <- wrap_plots(lapply(ms, function(m) panel(pcl, m, NULL, pal)), nrow = 1)
labA <- if (provisional) "Panel A: Stable ward units (provisional GHSL weights)" else
  "Panel A: Stable ward units"
# Row labels as their own thin rows so they never overlap the maps
header <- function(txt) wrap_elements(full = grid::textGrob(
  txt, x = 0.01, hjust = 0, gp = grid::gpar(fontfamily = "serif", fontsize = 13)))
fig <- header(labA) /
  wrap_elements(full = rowA + plot_layout(guides = "collect") &
                  theme(legend.position = "bottom")) /
  header("Panel B: Time-invariant precinct clusters") /
  wrap_elements(full = rowB + plot_layout(guides = "collect") &
                  theme(legend.position = "bottom")) +
  plot_layout(heights = c(0.06, 1, 0.06, 1))

out <- file.path(dir_fig, "fig_units_swu_precinct_clusters.pdf")
ggsave(out, fig, width = 11, height = 7.5, device = cairo_pdf)
saveRDS(list(swu = st_drop_geometry(swu), pcl = st_drop_geometry(pcl),
             provisional = provisional),
        file.path(dir_intermediate, "fig_units_map_data.rds"))
log_msg("Figure written:", out)

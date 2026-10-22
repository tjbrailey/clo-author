# CLAUDE.MD -- Empirical Social Science Research with Claude Code

<!-- HOW TO USE: Replace [BRACKETED PLACEHOLDERS] with your project info.
     Customize Beamer environments for your talk preamble.
     Keep this file under ~150 lines — Claude loads it every session.
     See the guide at https://hugosantanna.github.io/clo-author/ for full documentation. -->

**Project:** Gated Communities & State Attitudes (PSC Exposure)
**Institution:** [YOUR INSTITUTION]
**Field:** Political Science / Comparative Politics
**Branch:** main

---

## Core Principles

- **Plan first** -- enter plan mode before non-trivial tasks; save plans to `quality_reports/plans/`
- **Verify after** -- compile and confirm output at the end of every task
- **Single source of truth** -- Paper `main.qmd` is authoritative; slides and supplements derive from it
- **Quality gates** -- weighted aggregate score; nothing ships below 80/100; see `quality.md`
- **Worker-critic pairs** -- every creator has a paired critic; critics never edit files
- **Auto-memory** -- corrections and preferences are saved automatically via Claude Code's built-in memory system

---

## Getting Started

1. Fill in the `[BRACKETED PLACEHOLDERS]` in this file
2. Run `/discover interview [topic]` to build your research specification
3. Or run `/new-project [topic]` for the full orchestrated pipeline

---

## Folder Structure

```
psc-exposure/
├── CLAUDE.MD                    # This file
├── .claude/                     # Rules, skills, agents, hooks
├── Bibliography_base.bib        # Centralized bibliography
├── paper/                       # Main Quarto manuscript (source of truth)
│   ├── main.qmd                 # Primary paper file (Quarto)
│   ├── sections/                # Section-level .qmd files
│   ├── figures/                 # Generated figures (.pdf, .png)
│   ├── tables/                  # Generated tables (.tex / .html)
│   ├── quarto/                  # Quarto RevealJS presentations
│   ├── supplementary/           # Online appendix and supplements
│   └── replication/             # Replication package for deposit
├── data/                        # Project data
│   ├── raw/                     # Original untouched data (gitignored)
│   └── cleaned/                 # Processed datasets ready for analysis
├── scripts/                     # Analysis code (R, Python)
│   ├── scraping/                # Property website scrapers (Python)
│   ├── cleaning/                # Data cleaning and geocoding (R/Python)
│   └── analysis/                # Estimation and figures (R)
├── quality_reports/             # Plans, session logs, reviews, scores
├── explorations/                # Research sandbox (see rules)
├── templates/                   # Session log, quality report templates
└── master_supporting_docs/      # Reference papers and data docs
```

---

## Commands

```bash
# Manuscript (Quarto → PDF or HTML)
cd paper && quarto render main.qmd

# Slides (RevealJS)
cd paper/quarto && quarto render slides.qmd

# Run R analysis script
Rscript scripts/analysis/main_analysis.R

# Run Python scraper
python3 scripts/scraping/scrape_property24.py
```

---

## Quality Thresholds

| Score | Gate | Applies To |
|-------|------|------------|
| 80 | Commit | Weighted aggregate (blocking) |
| 90 | PR | Weighted aggregate (blocking) |
| 95 | Submission | Aggregate + all components >= 80 |
| -- | Advisory | Talks (reported, non-blocking) |

See `quality.md` for weighted aggregation formula.

---

## Skills Quick Reference

| Command | What It Does |
|---------|-------------|
| `/new-project [topic]` | Full pipeline: idea → paper (orchestrated) |
| `/discover [mode] [topic]` | Discovery: interview, literature, data, ideation |
| `/strategize [question]` | Identification strategy or pre-analysis plan |
| `/analyze [dataset]` | End-to-end data analysis |
| `/write [section]` | Draft paper sections + humanizer pass |
| `/review [file/--flag]` | Quality reviews (routes by target: paper, code, peer) |
| `/revise [report]` | R&R cycle: classify + route referee comments |
| `/talk [mode] [format]` | Create, audit, or compile Beamer presentations |
| `/submit [mode]` | Journal targeting → package → audit → final gate |
| `/tools [subcommand]` | Utilities: commit, compile, validate-bib, journal, etc. |

---

## Presentation Format

This project uses **Quarto RevealJS** for all presentations — no Beamer/LaTeX talks.
Slides live in `paper/quarto/`. Render with `quarto render slides.qmd`.

For custom RevealJS CSS or SCSS, add to `paper/quarto/_custom.scss`.

---

## Output Organization

<!-- Options: by-script (default) or by-purpose -->
Output organization: by-script

<!-- by-script:  paper/figures/main_regression/figure1.pdf, paper/tables/main_regression/table1.tex -->
<!-- by-purpose: paper/figures/estimation/coefplot_main.pdf, paper/tables/robustness/alt_controls.tex -->

---

## Current Project State

| Component | File | Status | Description |
|-----------|------|--------|-------------|
| Paper | `paper/main.qmd` | not started | PSC exposure → state attitudes + violence (South Africa) |
| Scraper | `scripts/scraping/` | not started | Property24 / Private Property gated community scraper |
| Data cleaning | `scripts/cleaning/` | not started | Geocoding, PSC classification, Afrobarometer merge |
| Analysis | `scripts/analysis/` | not started | Spatial RD + DiD estimation |
| Replication | `paper/replication/` | not started | — |
| Slides | `paper/quarto/slides.qmd` | not started | — |

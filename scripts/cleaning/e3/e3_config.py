# ============================================================
# scripts/cleaning/e3/e3_config.py
# Title:   Shared paths, HTTP settings and fiscal-year helpers for WP5 (E3)
# Author:  data-engineer (PSC Exposure project)
# Date:    2026-09-30
# Purpose: One place for the repo-relative paths, the polite-fetch settings and
#          the City FY <-> SAPS FY mapping (strategy memo s5.4) used by every
#          E3 script, so the mapping cannot drift between scripts.
# Inputs:  none
# Outputs: none (imported)
# ============================================================

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
E3_SCRIPTS = Path(__file__).resolve().parent
MANUAL = E3_SCRIPTS / "manual"
RAW = REPO / "data" / "raw" / "e3"
RAW_DOCS = RAW / "docs"
RAW_TEXT = RAW / "text"
CLEAN = REPO / "data" / "cleaned" / "e3"
INTERMEDIATE = CLEAN / "intermediate"
PILOT_REPORT = REPO / "quality_reports" / "pilot" / "E3_sra_compile.md"

PROVENANCE = RAW / "provenance.csv"
MANIFEST = RAW / "sources_manifest.csv"

# Identify ourselves; the City site, ArcGIS and the Wayback Machine all allow
# crawling (robots.txt "Allow: /" on capetown.gov.za, checked 2026-09-30).
USER_AGENT = (
    "Mozilla/5.0 (compatible; psc-exposure-research/1.0; "
    "academic data compile; contact thomasjbrailey@gmail.com)"
)
MIN_DELAY_S = 2.5      # >= 2.5 s between requests to any host
TIMEOUT_S = 120
MAX_RETRIES = 3

# ---------------------------------------------------------------------------
# Fiscal years
# ---------------------------------------------------------------------------
# City of Cape Town FY runs 1 July (Y) to 30 June (Y+1). SRA additional rates
# are levied from 1 July of the first levy year (CID By-law; City CID page:
# "application must be received by 31 October ... for implementation on
# 1 July of the following year").
# SAPS FY runs 1 April (Y) to 31 March (Y+1).
# Memo s5.4: G = the SAPS FY that contains at least 9 months of the first levy
# year. City FY Y/Y+1 overlaps SAPS FY Y/Y+1 for Jul..Mar = 9 months and SAPS FY
# Y+1/Y+2 for Apr..Jun = 3 months, so the mapping is always the same-labelled FY.


def fy_label(start_year: int) -> str:
    """2011 -> '2011/12'."""
    return f"{start_year}/{(start_year + 1) % 100:02d}"


def fy_start(label: str) -> int:
    """'2011/12' or '2011/2012' or '2011-12' -> 2011."""
    m = re.match(r"^\s*(\d{4})\s*[/\-]\s*(\d{2,4})\s*$", str(label))
    if not m:
        raise ValueError(f"not a FY label: {label!r}")
    y0 = int(m.group(1))
    y1 = int(m.group(2)) % 100
    if (y0 + 1) % 100 != y1:
        raise ValueError(f"non-consecutive FY label: {label!r}")
    return y0


def city_fy_to_saps_fy(city_fy_start: int) -> int:
    """Memo s5.4 mapping: the SAPS FY holding >= 9 months of the City FY.

    City FY Y/Y+1 = Jul Y..Jun Y+1. Months falling in SAPS FY Y/Y+1 (Apr Y..
    Mar Y+1) = Jul..Mar = 9. Hence the SAPS FY start year equals Y.
    """
    months_in_same = 9   # Jul, Aug, Sep, Oct, Nov, Dec, Jan, Feb, Mar
    assert months_in_same >= 9
    return city_fy_start


def city_fy_of_date(year: int, month: int) -> int:
    """City FY start year containing a calendar month."""
    return year if month >= 7 else year - 1


# Onset window for arm A3 (memo s5.7 / s9.4): G in FY2011/12..FY2023/24 and
# G_tilde = G - 2 >= FY2009/10.
A3_G_MIN = 2011
A3_G_MAX = 2023
RETIME_LAG_FY = 2

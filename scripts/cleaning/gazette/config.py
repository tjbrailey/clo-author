# ============================================================
# config.py — Gazette pilot (P-B) configuration
# Project: Gated Communities & State Attitudes (PSC Exposure)
# Purpose: Windows, sources, paths, rate limits and notice patterns for
#          the Gauteng Provincial Gazette SAR-notice pilot (strategy memo
#          §9.2 P-B; plan quality_reports/plans/2026-09-30_execution-stage0.md
#          WP1).
# Used by: 01_fetch_gazettes.py, 02_extract_sar_notices.py,
#          03_parse_notices.py, 04_pilot_report.py, tests/test_parse.py
# Requires: Python >= 3.10
# ============================================================

import importlib.util
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (all relative to repository root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRAPING_DIR = REPO_ROOT / "scripts" / "scraping"

RAW_DIR = REPO_ROOT / "data" / "raw" / "gazettes"
PDF_DIR = RAW_DIR / "pdf"                 # PDF cache: pdf/<source>/<folder>/<file>
LISTING_DIR = RAW_DIR / "listings"        # raw listing responses (HTML / JSON)
TEXT_CACHE_DIR = RAW_DIR / "text_cache"   # per-PDF page text incl. OCR (JSON)
CLEAN_DIR = REPO_ROOT / "data" / "cleaned" / "gazette"
REPORT_DIR = REPO_ROOT / "quality_reports" / "pilot"
LOG_DIR = RAW_DIR / "logs"

for _d in (PDF_DIR, LISTING_DIR, TEXT_CACHE_DIR, CLEAN_DIR, REPORT_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

LISTING_RECORDS = CLEAN_DIR / "listing_records.parquet"     # 01, listing level
INVENTORY = CLEAN_DIR / "gazette_inventory.parquet"         # 01, file level
EXTRACTION_LOG = CLEAN_DIR / "extraction_log.parquet"       # 02, per PDF
SAR_CANDIDATES = CLEAN_DIR / "sar_candidates.parquet"       # 02, per notice
CONTENTS_ENTRIES = CLEAN_DIR / "contents_sar_entries.parquet"  # 02, contents hits
ALL_SEGMENTS = CLEAN_DIR / "all_segments.parquet"            # 02, every notice segment (recall sample)
SAR_NOTICES = CLEAN_DIR / "sar_notices_jhb_pilot.parquet"   # 03
VALIDATION_SAMPLE = CLEAN_DIR / "validation_sample.csv"     # 03
PILOT_REPORT = REPORT_DIR / "P-B_gazette_pilot.md"          # 04

# ---------------------------------------------------------------------------
# Pilot windows (strategy memo §9.2 P-B)
# ---------------------------------------------------------------------------
WINDOWS = {
    "W1": (date(2017, 1, 1), date(2018, 12, 31)),
    "W2": (date(2021, 7, 1), date(2022, 6, 30)),
}
# Listing dates contain typos, so issues within this many days of a window
# are also downloaded; the PDF cover date decides window membership.
WINDOW_BUFFER_DAYS = 31

# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------
# Gazettes.Africa (the source named in the plan) is NOT used: its robots.txt
# (checked 2026-09-30) disallows /gazettes/ for all agents, and
# archive.gazettes.africa/robots.txt disallows /archive/ (the PDFs). Its
# Cloudflare rule also returns 403 to a UA that identifies as a research
# scraper. SAFLII serves a Cloudflare JS challenge. Both are therefore
# excluded rather than worked around.
#
# Source 1: OpenGazettes (Code for Africa mirror of GPW; robots.txt Allow /).
#           Coverage for ZA-GT ends in early Dec 2021.
OPENGAZETTES_YEAR_URL = "https://opengazettes.org.za/gazettes/ZA-GT/{year}"
OPENGAZETTES_YEARS = [2017, 2018, 2021, 2022]  # 2022 expected 404 (logged)

# Source 2: Government Printing Works (official publisher). Provincial
#           gazettes sit in a SharePoint library embedded in a WordPress page;
#           the page's own AJAX endpoint lists and serves files, and the embed
#           config grants anonymous view/download. No robots.txt (404).
GPW_BASE = "https://www.gpwonline.co.za"
GPW_PAGES = {
    # page slug : folder label (years covered per the page's button text)
    "provincial-gazettes-3": "2016-2020",
    "provincial-gazettes-2": "2021-2024",
}
GPW_AJAX = GPW_BASE + "/wp-admin/admin-ajax.php"

# Preference when an issue is listed by both sources (same content expected;
# OpenGazettes is a static host with stable URLs).
SOURCE_PREFERENCE = ["opengazettes", "gpw"]
# Download both variants when the two listings disagree on the date by more
# than this many days (then the cover decides which issue each file is).
LISTING_DATE_CONFLICT_DAYS = 3

# ---------------------------------------------------------------------------
# Politeness
# ---------------------------------------------------------------------------
MIN_SECONDS_BETWEEN_REQUESTS = 2.0   # <= 1 request / 2 s, all hosts combined
REQUEST_TIMEOUT = 180
MAX_RETRIES = 3


def _load_scraping_config():
    """Load scripts/scraping/config.py under another module name.

    Both pipelines name their module `config`, so a plain import would
    shadow this file. Loading by path keeps one definition of the contact UA.
    """
    spec = importlib.util.spec_from_file_location(
        "scraping_config", SCRAPING_DIR / "config.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


USER_AGENT = _load_scraping_config().SCRAPER_CONTACT

# ---------------------------------------------------------------------------
# Text extraction / OCR
# ---------------------------------------------------------------------------
TESSERACT_CMD = "C:/Program Files/Tesseract-OCR/tesseract.exe"  # not on PATH
OCR_DPI = 300
COVER_OCR_DPI = 200
OCR_LANG = "eng"
# A page is "image-only" when its text layer has fewer than this many words
# and embedded images cover at least IMAGE_AREA_SHARE of the page.
IMAGE_PAGE_MAX_WORDS = 80
IMAGE_AREA_SHARE = 0.40
# A text layer is "garbled" when the share of letters among non-space
# characters is below this, or it has many (cid:NN) / U+FFFD glyphs.
GARBLED_ALPHA_SHARE = 0.55
GARBLED_BAD_GLYPH_SHARE = 0.05
N_WORKERS = 6   # local CPU processes for extraction/OCR (no network)

# ---------------------------------------------------------------------------
# Municipalities (Gauteng)
# ---------------------------------------------------------------------------
METRO_PATTERNS = {
    "JHB": [r"city\s+of\s+johannesburg", r"johannesburg\s+roads?\s+agency",
            r"\bJRA\b", r"johannesburg\s+metropolitan"],
    "Tshwane": [r"city\s+of\s+tshwane", r"tshwane\s+metropolitan", r"\btshwane\b"],
    "Ekurhuleni": [r"ekurhuleni"],
    "other": [r"mogale\s+city", r"vanderbijlpark", r"vereeniging", r"krugersdorp", r"emfuleni", r"midvaal", r"lesedi", r"rand\s+west",
              r"merafong", r"west\s+rand\s+district", r"sedibeng"],
}

# Town names used only when no municipality is named (lower priority).
METRO_TOWN_FALLBACK = {
    "JHB": [r"\brandburg\b", r"\broodepoort\b", r"\bsandton\b", r"\bmidrand\b",
            r"\bsoweto\b", r"\bfourways\b", r"\bbryanston\b", r"\brivonia\b"],
    "Tshwane": [r"\bpretoria\b", r"\bcenturion\b", r"\blyttelton\b"],
    "Ekurhuleni": [r"\bboksburg\b", r"\bbenoni\b", r"\bgermiston\b", r"\bkempton\s+park\b",
                   r"\bedenvale\b", r"\bbedfordview\b", r"\balberton\b", r"\bsprings\b",
                   r"\bbrakpan\b", r"\bnigel\b"],
}

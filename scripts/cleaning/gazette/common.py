# ============================================================
# common.py — shared helpers for the gazette pilot pipeline
# Purpose: logging, the polite HTTP session, PDF text/OCR helpers and
#          cover-page parsing. Reuses scripts/scraping/utils (rate limiter,
#          backoff, missing-text test) by import rather than copying.
# Used by: 01_fetch_gazettes.py, 02_extract_sar_notices.py, 03_parse_notices.py
# Requires: Python >= 3.10; requests, pymupdf, pytesseract, Pillow
# ============================================================

import logging
import re
import sys
from datetime import date, datetime

import config

# scripts/scraping/utils is a package named `utils`; this directory has no
# package of that name, so appending the scraping dir cannot shadow anything.
if str(config.SCRAPING_DIR) not in sys.path:
    sys.path.append(str(config.SCRAPING_DIR))
from utils.rate_limiter import RateLimiter, with_backoff  # noqa: E402
from utils.text_utils import is_missing_text  # noqa: E402,F401  (re-exported)

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
_MONTH_RE = "|".join(MONTHS)


def setup_logging(script_name: str) -> logging.Logger:
    """Log to console and to data/raw/gazettes/logs/<script>_<timestamp>.log."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile = config.LOG_DIR / f"{script_name}_{stamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(logfile, encoding="utf-8")],
        force=True,
    )
    logger = logging.getLogger(script_name)
    logger.info("Log file: %s", logfile.relative_to(config.REPO_ROOT))
    return logger


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
class PoliteSession:
    """requests.Session with one global rate limiter and retry/backoff.

    One limiter for all hosts keeps the pipeline at <= 1 request / 2 s in
    total, which is stricter than a per-host limit.
    """

    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.headers["User-Agent"] = config.USER_AGENT
        self.limiter = RateLimiter(1.0 / config.MIN_SECONDS_BETWEEN_REQUESTS)
        self.n_requests = 0

    @with_backoff(max_retries=config.MAX_RETRIES, base_delay=10.0)
    def request(self, method: str, url: str, ok_statuses=(200,), **kwargs):
        """Rate-limited request. Statuses outside ok_statuses (other than the
        permanent 403/404/410, which are returned for the caller to log) raise
        and are retried with exponential backoff."""
        self.limiter.wait()
        self.n_requests += 1
        kwargs.setdefault("timeout", config.REQUEST_TIMEOUT)
        resp = self.session.request(method, url, **kwargs)
        if resp.status_code in ok_statuses or resp.status_code in (403, 404, 410):
            return resp
        raise RuntimeError(f"HTTP {resp.status_code} for {url[:120]}")


# ---------------------------------------------------------------------------
# Dates and windows
# ---------------------------------------------------------------------------
def window_of(d) -> str | None:
    """Pilot window label for a date, or None."""
    if d is None:
        return None
    for label, (lo, hi) in config.WINDOWS.items():
        if lo <= d <= hi:
            return label
    return None


def near_window(d, buffer_days: int) -> bool:
    """True if d lies within buffer_days of any pilot window."""
    from datetime import timedelta
    buf = timedelta(days=buffer_days)
    return any(lo - buf <= d <= hi + buf for lo, hi in config.WINDOWS.values())


def parse_english_date(text: str):
    """First 'D Month YYYY' date in text, or None."""
    m = re.search(rf"\b(\d{{1,2}})\s+({_MONTH_RE})\s*,?\s+(\d{{4}})\b", text, re.I)
    if not m:
        return None
    try:
        return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# PDF text
# ---------------------------------------------------------------------------
def open_pdf(path):
    """Open a PDF with PyMuPDF, silencing its per-object syntax warnings."""
    import pymupdf
    pymupdf.TOOLS.mupdf_display_errors(False)
    return pymupdf.open(path)


_BAD_GLYPH = re.compile(r"\(cid:\d+\)|�")


def page_quality(page) -> dict:
    """Text-layer diagnostics for one PyMuPDF page.

    sort=True returns blocks in reading order (top-to-bottom). Without it the
    gazette's notice header is sometimes emitted after the notice body.
    """
    # Landscape notices (text lines not left-to-right) are scrambled word by
    # word by sort=True; their unsorted text layer is in reading order.
    dirs = [ln["dir"] for b in page.get_text("dict")["blocks"] if b.get("type") == 0
            for ln in b["lines"]]
    rotated = bool(dirs) and sum(abs(d[0]) < 0.5 for d in dirs) / len(dirs) > 0.5
    text = page.get_text() if rotated else page.get_text(sort=True)
    words = len(text.split())
    # Letters as a share of letters + unusual symbols. Digits and ordinary
    # punctuation are excluded: contents pages are mostly dot leaders and
    # page numbers, which is not garbling.
    symbols = re.sub(r"[\s\d.,;:()'\"\-/&%’“”–—]", "", text)
    alpha_share = (sum(c.isalpha() for c in symbols) / len(symbols)) if symbols else 0.0
    bad_share = (len(_BAD_GLYPH.findall(text)) / max(words, 1))
    area = page.rect.width * page.rect.height
    img_area = sum((b["bbox"][2] - b["bbox"][0]) * (b["bbox"][3] - b["bbox"][1])
                   for b in page.get_image_info())
    image_only = words < config.IMAGE_PAGE_MAX_WORDS and img_area >= config.IMAGE_AREA_SHARE * area
    garbled = words >= 20 and (alpha_share < config.GARBLED_ALPHA_SHARE
                               or bad_share > config.GARBLED_BAD_GLYPH_SHARE)
    return {"text": text, "words": words, "alpha_share": round(alpha_share, 3), "rotated": rotated,
            "image_only": image_only, "garbled": garbled,
            "empty": words == 0}


def ocr_page(page, dpi: int) -> str:
    """Render one PyMuPDF page and OCR it with Tesseract."""
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return pytesseract.image_to_string(img, lang=config.OCR_LANG, config="--psm 6")


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------
def parse_cover(text: str) -> dict:
    """Volume, issue number, date and type from a gazette cover page.

    Covers vary: 2021 'Vol: 27 / 20 October 2021 / No: 355'; 2017
    'Vol. 23 ... 11 OCTOBER 2017 ... No_ 247' (OCR-like text layer).
    """
    vol = re.search(r"\bVol(?:ume)?\s*[.:_]?\s*(\d{1,3})\b", text, re.I)
    # "No" followed by the issue number; skip ISSN/barcode digits by
    # requiring 1-4 digits and a separator.
    num = re.search(r"\bNo\s*[.:_]?\s*(\d{1,4})\b", text)
    d = parse_english_date(text)
    extraordinary = bool(re.search(r"extra\s*-?\s*ordinary|buitengewone", text, re.I))
    liquor = bool(re.search(r"liquor\s+licen[cs]es?|dranklisensies", text, re.I))
    other_prov = re.search(r"eastern\s+cape|oos-?kaap|western\s+cape|kwazulu|limpopo|"
                           r"mpumalanga|north\s*west|noordwes|northern\s+cape|free\s+state|"
                           r"vrystaat", text, re.I)
    return {
        "cover_gauteng": bool(re.search(r"gauteng", text, re.I)),
        "cover_other_province": other_prov.group(0) if other_prov else None,
        "cover_vol": int(vol.group(1)) if vol else None,
        "cover_issue_no": int(num.group(1)) if num else None,
        "cover_date": d,
        "cover_extraordinary": extraordinary,
        "cover_liquor": liquor,
    }

# ============================================================
# utils/url_utils.py — Property24 URL parsing shared by the pipeline
# Used by: 00_archive_discovery.py (city labels), utils/html_parser.py,
#          03_merge_deduplicate.py, audit_classification.py, tests.
# Requires: Python >= 3.10
#
# Listing URL layout (archive and live):
#   /{for-sale|to-rent}/{suburb}/{town}/{province}/[Listing/]{area_id}/{p24_id}
# Search/index pages lack the trailing 7+ digit p24_id, e.g.
#   /for-sale/pretoria/gauteng/results/1/1
#   /for-sale/cape-town/western-cape/432?ListingNumber=P24-102174749
# ============================================================

import re
from urllib.parse import urlsplit

import pandas as pd

# Property24 listing numbers are >= 7 digits; suburb/area ids in the path
# (e.g. /9643/, /432) are shorter, so 7+ separates the two.
P24_ID_RE = re.compile(r"^\d{7,}$")
LISTING_NUMBER_RE = re.compile(r"[?&]listingnumber=(?:p24-)?(\d{7,})", re.IGNORECASE)
DEFAULT_PORTS = (":80", ":443")
LISTING_SECTIONS = ("for-sale", "to-rent")

PROVINCE_SLUGS = {
    "gauteng": "Gauteng",
    "western-cape": "Western Cape",
    "kwazulu-natal": "KwaZulu-Natal",
    "eastern-cape": "Eastern Cape",
    "free-state": "Free State",
    "limpopo": "Limpopo",
    "mpumalanga": "Mpumalanga",
    "north-west": "North West",
    "northern-cape": "Northern Cape",
}


def _blank(url) -> bool:
    if url is None:
        return True
    try:
        if pd.isna(url):
            return True
    except (TypeError, ValueError):
        pass
    return not str(url).strip()


def normalise_url(url) -> str | None:
    """Canonical URL: https, lower-case host, no default port, no query, no trailing /."""
    if _blank(url):
        return None
    parts = urlsplit(str(url).strip())
    host = parts.netloc.lower()
    for port in DEFAULT_PORTS:
        if host.endswith(port):
            host = host[: -len(port)]
    path = parts.path.rstrip("/")
    return f"https://{host}{path}"


def extract_p24_id(url) -> str | None:
    """Property24 listing number from a listing-page URL; None for any other page."""
    canonical = normalise_url(url)
    if canonical is None:
        return None
    last_segment = canonical.rsplit("/", 1)[-1]
    return last_segment if P24_ID_RE.match(last_segment) else None


def extract_embedded_listing_number(url) -> str | None:
    """Listing number carried in a ?ListingNumber= search URL (None otherwise)."""
    if _blank(url):
        return None
    m = LISTING_NUMBER_RE.search(str(url))
    return m.group(1) if m else None


def _path_segments(url) -> list[str]:
    if _blank(url):
        return []
    return [s for s in urlsplit(str(url).strip()).path.lower().split("/") if s]


def parse_location_slugs(url) -> tuple[str | None, str | None, str | None]:
    """(suburb_slug, town_slug, province_slug) from a listing URL, by exact segment.

    Returns (None, None, None) unless the URL has the full listing layout and the
    fourth segment is a known province slug; prefix matching is never used.
    """
    seg = _path_segments(url)
    if len(seg) >= 4 and seg[0] in LISTING_SECTIONS and seg[3] in PROVINCE_SLUGS:
        return seg[1], seg[2], seg[3]
    return None, None, None


def slug_to_name(slug: str | None) -> str | None:
    """'durban-north' -> 'Durban North'."""
    if not slug:
        return None
    return slug.replace("-", " ").title()

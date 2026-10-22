# ============================================================
# utils/html_parser.py — Property24 HTML parsing logic
# Handles both modern (Next.js/JSON-LD) and older archive pages
# ============================================================

import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def listing_id_from_url(url: str) -> str:
    """Stable MD5 hash of the canonical URL (strips query params + fragments)."""
    parsed = urlparse(url)
    canonical = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return hashlib.md5(canonical.encode()).hexdigest()


def parse_listing_html(html: str, url: str, source: str, snapshot_date: str) -> dict:
    """
    Parse a Property24 listing page HTML into a structured record.

    Priority order:
      1. JSON-LD structured data (most reliable; present since ~2018)
      2. OpenGraph / meta tags
      3. HTML selectors (fallback for older archive pages)

    Returns a dict matching LISTING_SCHEMA from utils/storage.py.
    All missing fields are None.
    """
    from utils.storage import empty_listing

    record = empty_listing()
    record["listing_id"] = listing_id_from_url(url)
    record["url"] = url
    record["source"] = source
    record["snapshot_date"] = snapshot_date

    soup = BeautifulSoup(html, "lxml")

    # -------------------------------------------------------------------
    # 1. JSON-LD — preferred source
    # -------------------------------------------------------------------
    jsonld = _extract_jsonld(soup)
    if jsonld:
        record = _parse_jsonld(jsonld, record)

    # -------------------------------------------------------------------
    # 2. OpenGraph / meta tags — fill any remaining gaps
    # -------------------------------------------------------------------
    meta = _extract_meta(soup)
    if not record["title"] and meta.get("og:title"):
        record["title"] = _clean(meta["og:title"])
    if not record["description"] and meta.get("og:description"):
        record["description"] = _clean(meta["og:description"])
    if not record["publish_date"] and meta.get("article:published_time"):
        record["publish_date"] = _parse_date(meta["article:published_time"])

    # -------------------------------------------------------------------
    # 3. HTML selectors — fallback
    # -------------------------------------------------------------------
    if not record["title"]:
        record["title"] = _html_title(soup)
    if not record["description"]:
        record["description"] = _html_description(soup)
    if not record["address_raw"]:
        record["address_raw"] = _html_address(soup)
    if not record["publish_date"]:
        record["publish_date"] = _html_date(soup)
    if not record["price"]:
        record["price"] = _html_price(soup)

    # -------------------------------------------------------------------
    # Derive fields — URL and title fallbacks for old archive pages
    # -------------------------------------------------------------------
    if record["description"]:
        record["word_count"] = len(record["description"].split())

    # Suburb: extract from URL path (segment after /for-sale/ or /to-rent/)
    if not record["suburb"]:
        record["suburb"] = _suburb_from_url(url)

    # Province: extract from URL (segment after city slug)
    if not record["province"]:
        record["province"] = _province_from_url(url)

    # Address: build from suburb + city if both present
    if not record["address_raw"] and record["suburb"] and record["city"]:
        record["address_raw"] = f"{record['suburb']}, {record['city']}, South Africa"

    # Property type: extract from title if not from JSON-LD
    if not record["property_type"] and record["title"]:
        record["property_type"] = _property_type_from_title(record["title"])

    # Infer city/province from URL if not already set
    if not record["city"]:
        record["city"] = _city_from_url(url)
    if not record["listing_type"]:
        record["listing_type"] = "for_sale" if "/for-sale/" in url else (
            "to_rent" if "/to-rent/" in url else None
        )

    return record


# ---------------------------------------------------------------------------
# JSON-LD helpers
# ---------------------------------------------------------------------------

def _extract_jsonld(soup: BeautifulSoup) -> Optional[dict]:
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            # Accept Product, RealEstateListing, or any dict with a description
            if isinstance(data, dict) and (
                data.get("@type") in ("Product", "RealEstateListing", "Residence", "House", "Apartment")
                or "description" in data
            ):
                return data
            # Array of objects
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "description" in item:
                        return item
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def _parse_jsonld(data: dict, record: dict) -> dict:
    record["title"] = _clean(data.get("name") or data.get("headline"))
    record["description"] = _clean(data.get("description"))
    record["publish_date"] = _parse_date(
        data.get("datePosted") or data.get("datePublished") or data.get("dateCreated")
    )

    # Price
    offers = data.get("offers") or {}
    if isinstance(offers, list) and offers:
        offers = offers[0]
    price_str = str(offers.get("price", "") or data.get("price", "") or "")
    record["price"] = _parse_price(price_str)

    # Address
    addr = data.get("address") or {}
    if isinstance(addr, dict):
        parts = [
            addr.get("streetAddress"),
            addr.get("addressLocality"),
            addr.get("addressRegion"),
        ]
        record["address_raw"] = ", ".join(p for p in parts if p)
        record["suburb"] = _clean(addr.get("addressLocality"))
        record["province"] = _clean(addr.get("addressRegion"))
    elif isinstance(addr, str):
        record["address_raw"] = addr

    # Geo
    geo = data.get("geo") or {}
    if isinstance(geo, dict):
        try:
            record["lat"] = float(geo.get("latitude") or 0) or None
            record["lon"] = float(geo.get("longitude") or 0) or None
        except (ValueError, TypeError):
            pass

    # Property type
    ptype = data.get("@type", "")
    if isinstance(ptype, str):
        record["property_type"] = _normalize_property_type(ptype)

    return record


# ---------------------------------------------------------------------------
# Meta tag helpers
# ---------------------------------------------------------------------------

def _extract_meta(soup: BeautifulSoup) -> dict:
    meta = {}
    for tag in soup.find_all("meta"):
        name = tag.get("name") or tag.get("property") or ""
        content = tag.get("content") or ""
        if name and content:
            meta[name] = content
    return meta


# ---------------------------------------------------------------------------
# HTML fallback helpers
# ---------------------------------------------------------------------------

def _html_title(soup: BeautifulSoup) -> Optional[str]:
    for selector in ["h1.p24_title", "h1", "title"]:
        el = soup.select_one(selector)
        if el:
            text = _clean(el.get_text())
            if text and len(text) > 5:
                return text
    return None


def _html_description(soup: BeautifulSoup) -> Optional[str]:
    # 1. Modern Property24 CSS classes
    for selector in [
        ".p24_description",
        "[class*='description']",
        "[id*='description']",
        ".listing-description",
        ".property-description",
    ]:
        el = soup.select_one(selector)
        if el:
            text = _clean(el.get_text(separator=" "))
            if text and len(text) > 20:
                return text

    # 2. Old ASP.NET Property24 (2009-2016): description header + following <p> siblings
    header = soup.find(id="ctl00_MainContent_DescriptionHeaderDiv")
    if header:
        parts = [header.get_text(strip=True)]
        for sib in header.next_siblings:
            if not hasattr(sib, "name"):
                continue
            if sib.name == "p" and not sib.get("class"):
                t = sib.get_text(strip=True)
                if t:
                    parts.append(t)
            elif sib.name in ("div", "p") and sib.get("class"):
                break  # hit next section header
        text = " ".join(parts)
        if len(text) > 10:
            return _clean(text)

    return None


def _html_address(soup: BeautifulSoup) -> Optional[str]:
    for selector in [
        ".p24_address",
        "[class*='address']",
        "[itemprop='address']",
        ".listing-address",
    ]:
        el = soup.select_one(selector)
        if el:
            text = _clean(el.get_text())
            if text:
                return text
    # Breadcrumb fallback
    breadcrumbs = soup.select("nav.breadcrumb li, .breadcrumb span")
    if breadcrumbs:
        return " > ".join(_clean(b.get_text()) for b in breadcrumbs if _clean(b.get_text()))
    return None


def _html_date(soup: BeautifulSoup) -> Optional[str]:
    time_el = soup.find("time")
    if time_el:
        dt = time_el.get("datetime") or time_el.get_text()
        return _parse_date(dt)
    for selector in ["[class*='date']", "[class*='posted']", "[class*='listed']"]:
        el = soup.select_one(selector)
        if el:
            text = el.get("datetime") or el.get_text()
            parsed = _parse_date(text)
            if parsed:
                return parsed
    return None


def _html_price(soup: BeautifulSoup) -> Optional[int]:
    for selector in [".p24_price", "[class*='price']", "[itemprop='price']"]:
        el = soup.select_one(selector)
        if el:
            price = _parse_price(el.get_text())
            if price:
                return price
    return None


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _clean(text) -> Optional[str]:
    if not text:
        return None
    text = str(text).strip()
    text = re.sub(r"\s+", " ", text)
    return text if text else None


def _parse_date(value) -> Optional[str]:
    if not value:
        return None
    value = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d", "%d %B %Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value[:len(fmt)], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Try extracting date-like pattern
    match = re.search(r"(\d{4}-\d{2}-\d{2})", value)
    if match:
        return match.group(1)
    return None


def _parse_price(text: str) -> Optional[int]:
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", str(text))
    if digits and 4 <= len(digits) <= 10:
        try:
            return int(digits)
        except ValueError:
            pass
    return None


def _normalize_property_type(raw: str) -> Optional[str]:
    raw = raw.lower()
    if "house" in raw or "home" in raw:
        return "house"
    if "apartment" in raw or "flat" in raw:
        return "apartment"
    if "townhouse" in raw or "town house" in raw:
        return "townhouse"
    if "estate" in raw:
        return "estate"
    if "farm" in raw:
        return "farm"
    if "land" in raw or "plot" in raw or "erf" in raw:
        return "land"
    return raw if raw else None


def _city_from_url(url: str) -> Optional[str]:
    """Study metro from the URL by exact segment (revised 2026-09-29).

    The old substring test ("/durban/" or "/durban-" anywhere) labelled
    durban-deep (Roodepoort, Gauteng) as Durban. Now: the town segment of a
    listing URL is mapped via P24_TOWN_TO_METRO; otherwise the suburb segment
    must equal a target city slug exactly. No prefix matching.
    """
    from config import CITY_SLUG_MAP, P24_TOWN_TO_METRO
    from utils.url_utils import parse_location_slugs
    _, town, _ = parse_location_slugs(url)
    if town is not None:
        return P24_TOWN_TO_METRO.get(town)
    parts = [p for p in urlparse(url).path.lower().split("/") if p]
    if len(parts) >= 2 and parts[0] in ("for-sale", "to-rent"):
        return CITY_SLUG_MAP.get(parts[1])
    return None


def _suburb_from_url(url: str) -> Optional[str]:
    """
    Extract suburb from Property24 URL path.
    URL pattern: /for-sale/{suburb-slug}/{city-slug}/{province-slug}/{area_id}/...
    Returns a human-readable suburb name (title-cased slug).
    """
    from urllib.parse import urlparse
    path = urlparse(url).path
    parts = [p for p in path.split("/") if p]
    # parts[0] = 'for-sale' or 'to-rent'
    # parts[1] = suburb slug (e.g. 'johannesburg-central')
    if len(parts) >= 2 and parts[0] in ("for-sale", "to-rent"):
        slug = parts[1]
        return slug.replace("-", " ").title()
    return None


def _province_from_url(url: str) -> Optional[str]:
    """
    Extract province from Property24 URL path.
    URL pattern: /for-sale/{suburb}/{city}/{province}/{area_id}/...
    """
    from urllib.parse import urlparse
    PROVINCE_MAP = {
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
    path = urlparse(url).path.lower()
    for slug, name in PROVINCE_MAP.items():
        if f"/{slug}/" in path or path.endswith(f"/{slug}"):
            return name
    return None


def _property_type_from_title(title: str) -> Optional[str]:
    """Extract property type from listing title string."""
    t = title.lower()
    if "apartment" in t or "flat" in t:
        return "apartment"
    if "townhouse" in t or "town house" in t:
        return "townhouse"
    if "commercial" in t or "retail" in t or "office" in t or "industrial" in t:
        return "commercial"
    if "farm" in t:
        return "farm"
    if "plot" in t or "vacant land" in t or "erf" in t:
        return "land"
    if "house" in t or "home" in t:
        return "house"
    return None

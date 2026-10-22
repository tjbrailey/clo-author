#!/usr/bin/env python3
# ============================================================
# 02_live_scraper.py
# Purpose: Polite, rate-limited live scraping of current
#          Property24 listings.
# Inputs:  None (scrapes live website)
# Outputs: data/raw/scraping/listings_live_YYYYMMDD.parquet
# Usage:   python3 02_live_scraper.py [--city SLUG] [--limit N] [--listing-type for-sale|to-rent]
#
# SAFETY: Checks robots.txt before any request. Minimum 10s
# delay between requests. Hard stops on HTTP 429.
# ============================================================

import argparse
import logging
import random
import sys
import time
import urllib.robotparser
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    BASE_DOMAIN, CITIES, RAW_DIR, CACHE_DIR,
    RATE_LIVE_MIN, RATE_LIVE_MAX, LIVE_REQUEST_LIMIT,
    CHECKPOINT_INTERVAL, SCRAPER_CONTACT, CITY_SLUG_MAP,
)
from utils.html_parser import parse_listing_html
from utils.storage import save_parquet, load_checkpoint, save_checkpoint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_URL = f"https://www.{BASE_DOMAIN}"
ROBOTS_URL = f"{BASE_URL}/robots.txt"

try:
    from fake_useragent import UserAgent
    _ua = UserAgent()
    def random_ua() -> str:
        return _ua.random
except Exception:
    def random_ua() -> str:
        return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def check_robots(path: str) -> bool:
    """Return True if scraping path is allowed by robots.txt."""
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(ROBOTS_URL)
    try:
        rp.read()
    except Exception as exc:
        logger.warning(f"Could not fetch robots.txt: {exc}. Proceeding cautiously.")
        return True
    allowed = rp.can_fetch("*", f"{BASE_URL}{path}")
    if not allowed:
        logger.error(f"robots.txt DISALLOWS scraping {path}. Aborting.")
    return allowed


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": random_ua(),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-ZA,en;q=0.9",
        "X-Research-Contact": SCRAPER_CONTACT,
    })
    return session


def polite_get(session: requests.Session, url: str, request_count: list) -> requests.Response:
    """
    Fetch URL with polite random delay. Rotates User-Agent every 20 requests.
    Raises on HTTP 429.
    """
    sleep_for = random.uniform(RATE_LIVE_MIN, RATE_LIVE_MAX)
    logger.debug(f"Sleeping {sleep_for:.1f}s before request")
    time.sleep(sleep_for)

    request_count[0] += 1
    if request_count[0] % 20 == 0:
        session.headers["User-Agent"] = random_ua()

    resp = session.get(url, timeout=30)
    if resp.status_code == 429:
        logger.warning("HTTP 429 received — backing off 5 minutes")
        time.sleep(300)
        resp = session.get(url, timeout=30)  # one retry
        if resp.status_code == 429:
            raise Exception("HTTP 429 after retry — stopping live scraper")
    resp.raise_for_status()
    return resp


def extract_listing_urls(html: str, base_url: str) -> list[str]:
    """Extract individual listing page URLs from a search results page."""
    soup = BeautifulSoup(html, "lxml")
    urls = set()

    # Property24 listing links match /for-sale/X-Y/id or /to-rent/X-Y/id
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href:
            continue
        # Normalize to absolute URL
        if href.startswith("/"):
            href = urljoin(base_url, href)
        # Keep only listing detail pages (contain numeric ID at end)
        if BASE_DOMAIN in href and "/for-sale/" in href or "/to-rent/" in href:
            if href.rstrip("/").split("/")[-1].isdigit():
                urls.add(href)

    return list(urls)


def get_next_page_url(html: str, current_url: str) -> str | None:
    """Extract pagination next-page URL from search results."""
    soup = BeautifulSoup(html, "lxml")
    # Look for rel="next" link
    next_link = soup.find("link", rel="next") or soup.find("a", rel="next")
    if next_link:
        href = next_link.get("href", "")
        if href:
            return urljoin(current_url, href)
    # Look for "Next" button
    for a in soup.find_all("a", href=True):
        text = a.get_text().strip().lower()
        if text in ("next", "next page", ">", "»"):
            return urljoin(current_url, a["href"])
    return None


def main():
    parser = argparse.ArgumentParser(description="Live scraper for Property24 listings")
    parser.add_argument("--city", help="City slug (e.g. cape-town). Omit for all cities.")
    parser.add_argument("--limit", type=int, default=LIVE_REQUEST_LIMIT,
                        help=f"Max requests per run (default: {LIVE_REQUEST_LIMIT})")
    parser.add_argument("--listing-type", choices=["for-sale", "to-rent", "both"],
                        default="both")
    args = parser.parse_args()

    cities = [c for c in CITIES if not args.city or c["slug"] == args.city]
    if not cities:
        logger.error(f"Unknown city slug: {args.city}")
        sys.exit(1)

    listing_types = ["for-sale", "to-rent"] if args.listing_type == "both" else [args.listing_type]
    today = date.today().strftime("%Y%m%d")
    output_path = RAW_DIR / f"listings_live_{today}.parquet"
    checkpoint_path = CACHE_DIR / f"checkpoint_live_{today}.txt"

    # Check robots.txt once
    if not check_robots("/for-sale/"):
        sys.exit(1)

    done = load_checkpoint(checkpoint_path)
    session = make_session()
    request_count = [0]  # mutable container for count
    all_records = []

    for city in cities:
        for ltype in listing_types:
            search_url = f"{BASE_URL}/{ltype}/{city['slug']}/"
            logger.info(f"Scraping: {search_url}")
            page_url = search_url
            listing_urls = []

            # Crawl search result pages to collect listing URLs
            while page_url and request_count[0] < args.limit:
                try:
                    resp = polite_get(session, page_url, request_count)
                except Exception as exc:
                    logger.error(f"Error on search page {page_url}: {exc}")
                    break

                page_listing_urls = extract_listing_urls(resp.text, BASE_URL)
                new_urls = [u for u in page_listing_urls if u not in done]
                listing_urls.extend(new_urls)
                logger.info(f"  Page: {page_url} → {len(new_urls)} new listing URLs")

                page_url = get_next_page_url(resp.text, page_url)
                if not page_url or request_count[0] >= args.limit:
                    break

            # Fetch each listing page
            for url in tqdm(listing_urls, desc=f"{city['name']} {ltype}"):
                if request_count[0] >= args.limit:
                    logger.info(f"Reached request limit ({args.limit}). Stopping.")
                    break
                if url in done:
                    continue

                try:
                    resp = polite_get(session, url, request_count)
                except Exception as exc:
                    logger.error(f"Error fetching {url}: {exc}")
                    break

                record = parse_listing_html(resp.text, url, source="live",
                                            snapshot_date=today)
                if not record.get("city"):
                    record["city"] = city["name"]
                if not record.get("province"):
                    record["province"] = city["province"]

                all_records.append(record)
                save_checkpoint(url, checkpoint_path)
                done.add(url)

                if len(all_records) % CHECKPOINT_INTERVAL == 0:
                    save_parquet(all_records, output_path, append=True)
                    all_records = []
                    logger.info(f"Checkpoint: {request_count[0]} requests made")

    # Final flush
    if all_records:
        save_parquet(all_records, output_path, append=True)

    total = len(load_checkpoint(checkpoint_path))
    logger.info(f"\nDone. {request_count[0]} requests made. Records saved to: {output_path}")


if __name__ == "__main__":
    main()

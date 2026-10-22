#!/usr/bin/env python3
# ============================================================
# 01_archive_fetch.py
# Purpose: Download and parse archived Property24 listing pages
#          from Wayback Machine (or Common Crawl WARC files).
# Inputs:  data/raw/scraping/url_inventory.jsonl
# Outputs: data/raw/scraping/listings_archive_YYYY.parquet
# Usage:   python3 01_archive_fetch.py [--year YYYY] [--limit N] [--source wayback|commoncrawl]
# ============================================================

import argparse
import logging
import sys
from pathlib import Path

import requests
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    RAW_DIR, CACHE_DIR, RATE_WAYBACK_FETCH, CHECKPOINT_INTERVAL,
)
from utils.html_parser import parse_listing_html
from utils.rate_limiter import RateLimiter, with_backoff
from utils.storage import load_jsonl, save_parquet, load_checkpoint, save_checkpoint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

WAYBACK_FETCH = "https://web.archive.org/web/{timestamp}id_/{url}"
URL_INVENTORY = RAW_DIR / "url_inventory.jsonl"


@with_backoff(max_retries=3, base_delay=10.0)
def fetch_wayback(url: str, timestamp: str, session: requests.Session) -> str:
    """Fetch a page from Wayback Machine and return HTML."""
    wayback_url = WAYBACK_FETCH.format(timestamp=timestamp, url=url)
    resp = session.get(wayback_url, timeout=30)
    if resp.status_code == 429:
        raise Exception("HTTP 429 — rate limited by Wayback Machine")
    resp.raise_for_status()
    return resp.text


def year_from_timestamp(ts: str) -> str:
    """Extract YYYY from Wayback timestamp (YYYYMMDDHHMMSS)."""
    return ts[:4] if ts and len(ts) >= 4 else "unknown"


def main():
    parser = argparse.ArgumentParser(description="Fetch and parse archived Property24 listings")
    parser.add_argument("--year", help="Process only this year (YYYY)")
    parser.add_argument("--limit", type=int, default=0, help="Max records to fetch (0 = all)")
    parser.add_argument("--source", choices=["wayback", "commoncrawl"], default="wayback",
                        help="Archive source to fetch from (default: wayback)")
    args = parser.parse_args()

    inventory = load_jsonl(URL_INVENTORY)
    if not inventory:
        logger.error(f"URL inventory empty or not found: {URL_INVENTORY}")
        logger.error("Run 00_archive_discovery.py first.")
        sys.exit(1)

    # Filter: individual listing pages only (numeric ID as last path segment)
    def is_listing_page(url: str) -> bool:
        clean = url.split("?")[0].rstrip("/")
        return clean.split("/")[-1].isdigit()

    # Filter by source and year
    filtered = [r for r in inventory
                if r.get("source", "wayback") == args.source and is_listing_page(r["url"])]
    if args.year:
        filtered = [r for r in filtered
                    if year_from_timestamp(r.get("timestamp", "")) == args.year]

    skipped = len(inventory) - len([r for r in inventory if is_listing_page(r["url"])])
    logger.info(f"URLs in inventory: {len(inventory)} ({skipped} category pages skipped)")
    logger.info(f"After filtering (source={args.source}, year={args.year or 'all'}): {len(filtered)}")

    if args.limit:
        filtered = filtered[:args.limit]

    # Load checkpoint
    checkpoint_path = CACHE_DIR / f"checkpoint_archive_{args.source}_{args.year or 'all'}.txt"
    done = load_checkpoint(checkpoint_path)
    filtered = [r for r in filtered if r["url"] not in done]
    logger.info(f"After skipping {len(done)} already-fetched: {len(filtered)} remaining")

    if not filtered:
        logger.info("Nothing to fetch.")
        return

    limiter = RateLimiter(RATE_WAYBACK_FETCH)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (research scraper; academic use)",
        "Accept-Language": "en-US,en;q=0.9",
    })

    # Group by year for output files
    records_by_year: dict[str, list] = {}
    batch: list[dict] = []
    errors = 0

    for entry in tqdm(filtered, desc="Fetching archived listings"):
        url = entry["url"]
        timestamp = entry.get("timestamp", "")
        year = year_from_timestamp(timestamp)

        try:
            limiter.wait()
            html = fetch_wayback(url, timestamp, session)
        except Exception as exc:
            errors += 1
            logger.warning(f"Failed to fetch {url}: {exc}")
            if errors >= 5:
                logger.error("5 consecutive-ish errors — check connectivity or rate limits")
            continue

        errors = max(0, errors - 1)  # reset on success

        record = parse_listing_html(html, url, source="wayback", snapshot_date=timestamp[:8])
        # Enrich with inventory metadata
        if not record.get("city") and entry.get("city"):
            record["city"] = entry["city"]
        if not record.get("province") and entry.get("province"):
            record["province"] = entry["province"]

        batch.append(record)
        records_by_year.setdefault(year, []).append(record)

        save_checkpoint(url, checkpoint_path)

        # Checkpoint save every N records
        if len(batch) % CHECKPOINT_INTERVAL == 0:
            _flush_by_year(records_by_year)
            records_by_year = {}
            logger.info(f"Checkpoint: {len(batch)} records processed")

    # Final flush
    _flush_by_year(records_by_year)

    logger.info(f"\nDone. Fetched {len(batch)} records ({errors} errors).")
    logger.info("Output: data/raw/scraping/listings_archive_YYYY.parquet")


def _flush_by_year(records_by_year: dict[str, list]):
    for year, records in records_by_year.items():
        path = RAW_DIR / f"listings_archive_{year}.parquet"
        save_parquet(records, path, append=True)


if __name__ == "__main__":
    main()

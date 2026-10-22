#!/usr/bin/env python3
# ============================================================
# 00_archive_discovery.py
# Purpose: Query Common Crawl CDX and Wayback Machine CDX APIs
#          to build a URL inventory of Property24 listing pages.
# Inputs:  None (queries public CDX APIs)
# Outputs: data/raw/scraping/url_inventory.jsonl
# Usage:   python3 00_archive_discovery.py [--city SLUG] [--limit N] [--source both|wayback|commoncrawl]
#
# Revision 2026-09-29 (coder-critic round 1, B5), code change only,
# NOT re-run: the CDX query is a prefix match, so "durban" also
# returned Durbanville (Cape Town) and Durban Deep (Roodepoort).
# Records are now labelled by exact URL segment (label_location);
# the query city is kept as `city_target`. The existing inventory
# was built with the old labels; 03 corrects them downstream.
# ============================================================

import argparse
import logging
import sys
import time
from pathlib import Path

from urllib.parse import urlsplit

import requests

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    COMMON_CRAWL_INDEXES, CITIES, EXTRA_TOWNS, LISTING_URL_PATTERNS,
    P24_TOWN_TO_METRO, RATE_COMMONCRAWL_CDX, RATE_WAYBACK_CDX, URL_INVENTORY,
)
from utils.rate_limiter import RateLimiter
from utils.storage import append_jsonl, load_jsonl
from utils.url_utils import PROVINCE_SLUGS, parse_location_slugs, slug_to_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

WAYBACK_CDX = "http://web.archive.org/cdx/search/cdx"
CC_CDX_TEMPLATE = "https://index.commoncrawl.org/{index}/cdx"


def query_wayback(url_pattern: str, limiter: RateLimiter, limit: int = 0) -> list[dict]:
    """Query Wayback Machine CDX for a URL pattern."""
    params = {
        "url": url_pattern,
        "output": "json",
        "fl": "original,timestamp,statuscode,mimetype",
        "filter": "statuscode:200",
        "filter2": "mimetype:text/html",
        "collapse": "urlkey",  # one result per unique URL
    }
    if limit:
        params["limit"] = limit

    limiter.wait()
    try:
        resp = requests.get(WAYBACK_CDX, params=params, timeout=90)
        resp.raise_for_status()
        rows = resp.json()
    except Exception as exc:
        logger.warning(f"Wayback CDX query failed for {url_pattern}: {exc}")
        return []

    records = []
    for row in rows[1:]:  # first row is header
        if len(row) >= 2:
            records.append({
                "url": row[0],
                "timestamp": row[1],
                "source": "wayback",
            })
    return records


def query_commoncrawl(url_pattern: str, limiter: RateLimiter, limit: int = 0) -> list[dict]:
    """Query Common Crawl CDX across all available indexes."""
    records = []
    seen_urls = set()

    for index in COMMON_CRAWL_INDEXES:
        params = {
            "url": url_pattern,
            "output": "json",
            "fl": "url,timestamp,status,mime",
            "filter": "status:200",
        }
        if limit and len(records) >= limit:
            break

        limiter.wait()
        try:
            resp = requests.get(CC_CDX_TEMPLATE.format(index=index), params=params, timeout=30)
            if resp.status_code == 404:
                continue  # index doesn't have this pattern
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            if exc.response and exc.response.status_code in (404, 400):
                continue
            logger.warning(f"CC CDX {index} failed: {exc}")
            continue
        except Exception as exc:
            logger.warning(f"CC CDX {index} error: {exc}")
            continue

        try:
            for line in resp.text.strip().split("\n"):
                if not line:
                    continue
                import json
                row = json.loads(line)
                url = row.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    records.append({
                        "url": url,
                        "timestamp": row.get("timestamp", ""),
                        "source": "common_crawl",
                        "cc_index": index,
                    })
                    if limit and len(records) >= limit:
                        break
        except Exception as exc:
            logger.warning(f"CC CDX parse error ({index}): {exc}")

        logger.info(f"  {index}: {len(seen_urls)} unique URLs so far")

    return records


def label_location(record: dict, city: dict) -> dict:
    """Set city/province on an inventory record from its URL, by exact segment.

    CDX `url=.../for-sale/{slug}/*` is a PREFIX query: "durban" also returns
    durbanville (Western Cape) and durban-deep (Gauteng). The query target is
    kept as `city_target`; `city`/`province` come from the URL itself:
      - listing layout /{section}/{suburb}/{town}/{province}/...: town slug ->
        P24_TOWN_TO_METRO (None if unknown), province from its slug;
      - other pages: the target label only if the suburb segment is exactly the
        slug or "{slug}-..." AND no other province appears in the path.
    """
    record["city_target"] = city["name"]
    _, town, prov = parse_location_slugs(record["url"])
    if town is not None:
        record["city_url"] = slug_to_name(town)
        record["city"] = P24_TOWN_TO_METRO.get(town)
        record["province"] = PROVINCE_SLUGS[prov]
        return record

    seg = [s for s in urlsplit(record["url"]).path.lower().split("/") if s]
    suburb = seg[1] if len(seg) >= 2 else ""
    slug = city["slug"]
    same_place = suburb == slug or suburb.startswith(slug + "-")
    provinces = {PROVINCE_SLUGS[s] for s in seg if s in PROVINCE_SLUGS}
    same_province = not provinces or provinces == {city["province"]}
    if same_place and same_province:
        record["city"], record["province"] = city["name"], city["province"]
    else:
        record["city"] = None
        record["province"] = provinces.pop() if len(provinces) == 1 else None
    return record


def main():
    parser = argparse.ArgumentParser(description="Discover Property24 listing URLs from archives")
    parser.add_argument("--city", help="City slug (e.g. johannesburg). Omit for all cities.")
    parser.add_argument("--limit", type=int, default=0, help="Max URLs per city (0 = unlimited)")
    parser.add_argument("--source", choices=["both", "wayback", "commoncrawl"], default="both")
    parser.add_argument("--fresh", action="store_true", help="Overwrite existing inventory")
    parser.add_argument("--towns", action="store_true",
                        help="Also query EXTRA_TOWNS (75 additional suburb/town slugs)")
    parser.add_argument("--towns-only", action="store_true",
                        help="Query EXTRA_TOWNS only, skip the 9 original city slugs")
    args = parser.parse_args()

    if args.towns_only:
        cities = EXTRA_TOWNS
    else:
        cities = [c for c in CITIES if not args.city or c["slug"] == args.city]
        if args.towns:
            cities = cities + EXTRA_TOWNS
    if not cities:
        logger.error(f"Unknown city slug: {args.city}")
        sys.exit(1)

    if args.fresh and URL_INVENTORY.exists():
        URL_INVENTORY.unlink()
        logger.info("Removed existing inventory (--fresh)")

    existing = {r["url"] for r in load_jsonl(URL_INVENTORY)}
    logger.info(f"Existing inventory: {len(existing)} URLs")

    wb_limiter = RateLimiter(RATE_WAYBACK_CDX)
    cc_limiter = RateLimiter(RATE_COMMONCRAWL_CDX)

    total_new = 0
    for city in cities:
        logger.info(f"--- Discovering: {city['name']} ---")
        slug = city["slug"]
        patterns = [
            f"property24.com/for-sale/{slug}/*",
            f"property24.com/to-rent/{slug}/*",
        ]

        for pattern in patterns:
            records = []
            if args.source in ("both", "wayback"):
                wb_records = query_wayback(pattern, wb_limiter, limit=args.limit)
                logger.info(f"  Wayback: {len(wb_records)} results for {pattern}")
                records.extend(wb_records)

            if args.source in ("both", "commoncrawl"):
                cc_records = query_commoncrawl(pattern, cc_limiter, limit=args.limit)
                logger.info(f"  CommonCrawl: {len(cc_records)} results for {pattern}")
                records.extend(cc_records)

            new_count = 0
            relabelled = 0
            for r in records:
                if r["url"] not in existing:
                    label_location(r, city)
                    relabelled += r["city"] != city["name"]
                    append_jsonl(r, URL_INVENTORY)
                    existing.add(r["url"])
                    new_count += 1

            total_new += new_count
            logger.info(f"  Added {new_count} new URLs for {pattern} "
                        f"({relabelled} not in {city['name']} by exact URL segment)")

    logger.info(f"\nDone. Total new URLs added: {total_new}")
    logger.info(f"Total inventory size: {len(existing)} URLs")
    logger.info(f"Inventory saved to: {URL_INVENTORY}")


if __name__ == "__main__":
    main()


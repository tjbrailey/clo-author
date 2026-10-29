#!/usr/bin/env python3
# ============================================================
# 05a_fetch_osm_gazetteer.py
# Purpose: Download an offline gazetteer for Gauteng from OpenStreetMap
#          (Overpass API): named places (suburbs, neighbourhoods, towns)
#          and named street geometries. 05_geocode_notices.py uses these
#          to locate SAR notices by place name and street co-location
#          instead of per-notice Nominatim queries.
# Outputs: data/raw/osm/gauteng/places.json
#          data/raw/osm/gauteng/streets.json
# Usage:   py -3.12 05a_fetch_osm_gazetteer.py [--force]
# Notes:   Two Overpass queries; respects the public instance's usage
#          policy (contact UA, single requests, long timeout).
#          OSM data (c) OpenStreetMap contributors, ODbL.
# ============================================================

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import config  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("05a_fetch_osm_gazetteer")

OSM_DIR = config.REPO_ROOT / "data" / "raw" / "osm" / "gauteng"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
AREA = 'area["name"="Gauteng"]["admin_level"="4"]->.gp;'

QUERIES = {
    "places": f"""
        [out:json][timeout:600];
        {AREA}
        nwr["place"~"^(city|town|suburb|neighbourhood|quarter|village|hamlet|locality)$"]["name"](area.gp);
        out center tags;
    """,
    "streets": f"""
        [out:json][timeout:900][maxsize:1073741824];
        {AREA}
        way["highway"]["name"](area.gp);
        out tags geom;
    """,
}


def fetch(name: str, query: str, force: bool) -> None:
    out_path = OSM_DIR / f"{name}.json"
    if out_path.exists() and not force:
        logger.info(f"{out_path.name} exists; skipping (use --force to refresh)")
        return
    logger.info(f"Querying Overpass for {name} ...")
    for attempt in range(3):
        try:
            r = requests.post(OVERPASS_URL, data={"data": query},
                              headers={"User-Agent": config.USER_AGENT}, timeout=1200)
            if r.status_code == 200:
                payload = r.json()
                n = len(payload.get("elements", []))
                if n == 0:
                    raise RuntimeError("Overpass returned zero elements (area lookup failed?)")
                out_path.write_text(json.dumps(payload), encoding="utf-8")
                logger.info(f"  wrote {n:,} elements -> {out_path}")
                return
            logger.warning(f"  HTTP {r.status_code}: {r.text[:200]}")
        except (requests.RequestException, ValueError) as exc:
            logger.warning(f"  attempt {attempt + 1} failed: {exc}")
        time.sleep(60 * (attempt + 1))
    raise RuntimeError(f"Overpass query for {name} failed after 3 attempts")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    OSM_DIR.mkdir(parents=True, exist_ok=True)
    for name, q in QUERIES.items():
        fetch(name, q, args.force)


if __name__ == "__main__":
    main()

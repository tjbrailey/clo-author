#!/usr/bin/env python3
# ============================================================
# 05_geocode.py
# Purpose: Geocode listings by suburb + city_url + province_url
#          → lat/lon using Nominatim (OpenStreetMap). Caches
#          results. Geocodes unique location combinations first,
#          then merges back to all rows.
# Inputs:  data/raw/scraping/listings_classified.parquet
# Outputs: data/cleaned/listings_geocoded.parquet
# Usage:   python3 05_geocode.py [--input FILE] [--output FILE]
# Notes:   Nominatim requires ≤1 req/sec and a valid contact
#          email in the User-Agent.
#
# Revision 2026-10-22:
#   - Query uses suburb_canonical + city_url + province_url
#     (from 03_merge), not the old city/suburb fields.
#   - Geocodes unique (suburb, city_url, province) combos first,
#     then joins back — avoids 138K row-level API calls.
#   - Cache keyed on suburb|city_url|province_url.
#   - city (study metro) used only for centroid fallback.
# ============================================================

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    LISTINGS_CLASSIFIED, LISTINGS_GEOCODED,
    GEOCODE_CACHE, RATE_NOMINATIM, CITY_CENTROIDS, SCRAPER_CONTACT,
)
from utils.rate_limiter import RateLimiter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_cache(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_cache(cache: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(cache, f)


def geocode_query(geolocator: Nominatim, query: str,
                  limiter: RateLimiter, retries: int = 3) -> tuple[float, float] | None:
    for attempt in range(retries):
        try:
            limiter.wait()
            location = geolocator.geocode(query, exactly_one=True, timeout=10,
                                          country_codes=["za"])
            if location:
                return location.latitude, location.longitude
            return None
        except (GeocoderTimedOut, GeocoderServiceError) as exc:
            if attempt < retries - 1:
                logger.warning(f"Geocoding retry for '{query}': {exc}")
            else:
                logger.warning(f"Geocoding failed for '{query}': {exc}")
    return None


def geocode_location(suburb: str, city_url: str, province_url: str,
                     city_metro: str | None,
                     geolocator: Nominatim, limiter: RateLimiter,
                     cache: dict) -> tuple[float | None, float | None, str]:
    """
    Geocode one (suburb, city_url, province_url) combination.
    Cascade: suburb+city_url+province → city_url+province → metro centroid.
    """
    cache_key = f"{suburb}|{city_url}|{province_url}".lower().strip()

    if cache_key in cache:
        c = cache[cache_key]
        return c["lat"], c["lon"], c["source"]

    # Try suburb + city_url + province + country
    if suburb and city_url and province_url:
        query = f"{suburb}, {city_url}, {province_url}, South Africa"
        result = geocode_query(geolocator, query, limiter)
        if result:
            lat, lon = result
            cache[cache_key] = {"lat": lat, "lon": lon, "source": "nominatim"}
            return lat, lon, "nominatim"

    # Try city_url + province only
    if city_url and province_url:
        city_key = f"|{city_url}|{province_url}".lower().strip()
        if city_key in cache:
            c = cache[city_key]
            cache[cache_key] = c
            return c["lat"], c["lon"], "nominatim_city"

        query = f"{city_url}, {province_url}, South Africa"
        result = geocode_query(geolocator, query, limiter)
        if result:
            lat, lon = result
            entry = {"lat": lat, "lon": lon, "source": "nominatim_city"}
            cache[city_key] = entry
            cache[cache_key] = entry
            return lat, lon, "nominatim_city"

    # Metro centroid fallback
    if city_metro and city_metro in CITY_CENTROIDS:
        lat, lon = CITY_CENTROIDS[city_metro]
        cache[cache_key] = {"lat": lat, "lon": lon, "source": "centroid"}
        return lat, lon, "centroid"

    cache[cache_key] = {"lat": None, "lon": None, "source": "none"}
    return None, None, "none"


def main():
    parser = argparse.ArgumentParser(description="Geocode listings by suburb/city")
    parser.add_argument("--input", default=str(LISTINGS_CLASSIFIED))
    parser.add_argument("--output", default=str(LISTINGS_GEOCODED))
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-geocode even if cache has results")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    df = pd.read_parquet(input_path)
    logger.info(f"Loaded {len(df):,} records from {input_path}")

    for col in ("suburb_canonical", "city_url", "province_url"):
        if col not in df.columns:
            logger.error(f"Missing column '{col}'. Run 03_merge_deduplicate.py first.")
            sys.exit(1)

    # Unique location combinations to geocode
    loc_cols = ["suburb_canonical", "city_url", "province_url"]
    if "city" in df.columns:
        loc_cols_with_metro = loc_cols + ["city"]
    else:
        loc_cols_with_metro = loc_cols

    uniq = df[loc_cols_with_metro].drop_duplicates().reset_index(drop=True)
    logger.info(f"Unique location combinations to geocode: {len(uniq):,}")

    cache = load_cache(GEOCODE_CACHE)
    cached_before = len(cache)
    logger.info(f"Loaded {cached_before} cached geocode results")

    if not args.overwrite:
        already = sum(1 for _, r in uniq.iterrows()
                      if f"{r['suburb_canonical']}|{r['city_url']}|{r['province_url']}"
                      .lower().strip() in cache)
        logger.info(f"Already cached: {already}, need API calls: {len(uniq) - already}")

    geolocator = Nominatim(user_agent=SCRAPER_CONTACT)
    limiter = RateLimiter(RATE_NOMINATIM)

    results = []
    for _, row in tqdm(uniq.iterrows(), total=len(uniq), desc="Geocoding unique locations"):
        lat, lon, src = geocode_location(
            suburb=row["suburb_canonical"],
            city_url=row["city_url"],
            province_url=row["province_url"],
            city_metro=row.get("city"),
            geolocator=geolocator,
            limiter=limiter,
            cache=cache,
        )
        results.append({"lat": lat, "lon": lon, "geocode_source": src})

        if len(results) % 50 == 0:
            save_cache(cache, GEOCODE_CACHE)

    save_cache(cache, GEOCODE_CACHE)
    logger.info(f"Cache grew from {cached_before} to {len(cache)} entries")

    # Attach results to unique combos, then merge back
    geo = pd.DataFrame(results)
    uniq = pd.concat([uniq[loc_cols], geo], axis=1)

    df = df.drop(columns=[c for c in ("lat", "lon", "geocode_source") if c in df.columns])
    df = df.merge(uniq, on=loc_cols, how="left")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")
    logger.info(f"Saved {len(df):,} geocoded records to {output_path}")

    # Summary
    geocoded = df["lat"].notna().sum()
    by_src = df["geocode_source"].value_counts()
    print(f"\n=== Geocoding Summary ===")
    print(f"Total records: {len(df):,}")
    for src, n in by_src.items():
        print(f"  {src:20s}: {n:>7,} ({100*n/len(df):.1f}%)")
    failed = df["lat"].isna().sum()
    if failed:
        print(f"  {'not geocoded':20s}: {failed:>7,} ({100*failed/len(df):.1f}%)")

    # Outlier check: South Africa bounding box roughly
    # lat: -35.0 to -22.0, lon: 16.0 to 33.0
    SA_LAT_MIN, SA_LAT_MAX = -35.5, -21.5
    SA_LON_MIN, SA_LON_MAX = 15.5, 33.5
    geo = df[df["lat"].notna()].copy()
    outside_lat = (geo["lat"] < SA_LAT_MIN) | (geo["lat"] > SA_LAT_MAX)
    outside_lon = (geo["lon"] < SA_LON_MIN) | (geo["lon"] > SA_LON_MAX)
    outliers = geo[outside_lat | outside_lon]
    print(f"\n=== Outlier Check (outside SA bounding box) ===")
    print(f"Records outside SA bounds: {len(outliers):,} of {len(geo):,}")
    if len(outliers) > 0:
        show_cols = ["suburb_canonical", "city_url", "province_url", "lat", "lon",
                     "geocode_source"]
        show_cols = [c for c in show_cols if c in outliers.columns]
        outlier_locs = outliers[show_cols].drop_duplicates()
        for _, row in outlier_locs.head(20).iterrows():
            print(f"  {row['suburb_canonical']:25s} {row['city_url']:20s} "
                  f"{row['province_url']:15s} -> ({row['lat']:.4f}, {row['lon']:.4f})")

    # Within-province sanity: flag points far from provincial centroid
    PROV_CENTROIDS = {
        "Gauteng": (-26.27, 28.11), "Western Cape": (-33.46, 19.66),
        "KwaZulu-Natal": (-29.61, 30.51), "Eastern Cape": (-32.30, 27.40),
        "Free State": (-29.08, 26.16), "Limpopo": (-23.90, 29.47),
        "Mpumalanga": (-25.57, 30.53), "North West": (-26.66, 25.29),
        "Northern Cape": (-29.12, 21.86),
    }
    print(f"\n=== Province Distance Check ===")
    far_count = 0
    for prov, (plat, plon) in PROV_CENTROIDS.items():
        mask = geo["province_url"] == prov
        if not mask.any():
            continue
        subset = geo.loc[mask]
        dist_deg = ((subset["lat"] - plat)**2 + (subset["lon"] - plon)**2)**0.5
        far = dist_deg > 5.0
        if far.any():
            far_rows = subset.loc[far]
            far_locs = far_rows[["suburb_canonical", "city_url", "lat", "lon"]].drop_duplicates()
            far_count += len(far_rows)
            print(f"  {prov}: {len(far_rows):,} records >5 deg from provincial centroid")
            for _, row in far_locs.head(5).iterrows():
                print(f"    {row['suburb_canonical']:25s} {row['city_url']:20s} "
                      f"-> ({row['lat']:.4f}, {row['lon']:.4f})")
    if far_count == 0:
        print(f"  All records within 5 degrees of their provincial centroid.")


if __name__ == "__main__":
    main()

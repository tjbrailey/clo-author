#!/usr/bin/env python3
# ============================================================
# 03_merge_deduplicate.py
# Purpose: Combine archive + live parquets, keep listing pages
#          only, deduplicate to one row per (listing, capture
#          date), repair location labels, add panel descriptors.
# Inputs:  data/raw/scraping/listings_archive_*.parquet
#          data/raw/scraping/listings_live_*.parquet
# Outputs: data/raw/scraping/listings_all.parquet
#          data/raw/scraping/listing_stubs_listingnumber.parquet
# Usage:   python3 scripts/scraping/03_merge_deduplicate.py
#          (Windows: py -3.12 ...). Requires Python >= 3.10.
#
# Revision 2026-09-29 (scrape audit + coder-critic round 1):
#   IDs and pages
#   - `url_canonical`: host lower-cased, :80/:443 dropped, https,
#     query/fragment dropped, trailing slash stripped. Raw `url` kept.
#   - `p24_id`: last path segment if it is 7+ digits (Property24's
#     listing number). `listing_id` is SET EQUAL TO `p24_id` so the
#     downstream column name keeps working; the former MD5-of-URL id
#     is kept as `url_hash`.
#   - Rows without a p24_id are search / index pages and are dropped
#     from listings_all (counts logged). `?ListingNumber=` search
#     pages carry a listing number and that listing's price, but the
#     scraped text is the search page's sidebar (news teasers), not the
#     listing description. They are written to a separate stub file
#     (listing number, capture date, price, target city) instead of
#     being discarded; they are NOT merged into listings_all.
#   - "Listing Not Found" pages (expired listings; no text, no price)
#     are dropped and logged.
#   - Dedup key (p24_id, snapshot_date). Tie-break: informative
#     description (utils.text_utils.is_missing_text, the same rule 04
#     uses), then most informative fields, then the https capture.
#   Panel
#   - first_captured / last_captured (YYYYMMDD, archive capture
#     dates, NOT listing dates) and n_snapshots (distinct dates).
#   Location
#   - `city_target`: the old `city` label (scrape-target city). It is
#     wrong for Durbanville / Durban Deep (CDX prefix match in 00).
#   - `suburb_url`, `city_url`, `province_url`: parsed by exact URL
#     segment (/{section}/{suburb}/{town}/{province}/...). `city_url`
#     is Property24's town name, e.g. "Durbanville", "Randburg".
#     05_geocode.py must geocode on suburb + city_url + province.
#   - `city`: study metro from config.P24_TOWN_TO_METRO(town slug);
#     asserted consistent with province_url and with `province`.
#   - `suburb_canonical`: modal suburb_url per p24_id (latest capture
#     breaks ties); 94 listings appear under two suburb slugs.
#   Property use
#   - `property_use` in {residential, commercial, farm_land} or NA,
#     from property_type then title; `is_commercial`, `is_residential`
#     are 0/1 (NA when property_use is NA).
# ============================================================

import logging
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from config import RAW_DIR, P24_TOWN_TO_METRO, CITY_PROVINCE
from utils.text_utils import is_missing_text, count_informative
from utils.url_utils import (
    normalise_url, extract_p24_id, extract_embedded_listing_number,
    parse_location_slugs, slug_to_name, PROVINCE_SLUGS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_PATH = RAW_DIR / "listings_all.parquet"
STUBS_PATH = RAW_DIR / "listing_stubs_listingnumber.parquet"

NOT_FOUND_TITLE_RE = re.compile(r"^\s*listing not found\s*$", re.IGNORECASE)

RESIDENTIAL_TYPES = {"apartment", "house", "townhouse"}
PROPERTY_TYPE_USE = {
    "apartment": "residential", "house": "residential", "townhouse": "residential",
    "commercial": "commercial", "farm": "farm_land", "land": "farm_land",
}
# Title fallback when property_type is missing (checked in this order)
TITLE_USE_PATTERNS = [
    ("commercial", re.compile(r"\b(?:commercial|industrial|office|retail|warehouse)",
                              re.IGNORECASE)),
    ("farm_land", re.compile(r"\b(?:farm|smallholding|vacant land|plot)\b", re.IGNORECASE)),
    ("residential", re.compile(r"\b(?:cluster|complex|simplex|duplex|bachelor|freehold"
                               r"|residential|house|apartment|flat|townhouse|estate)\b",
                               re.IGNORECASE)),
]


def classify_nonlisting(url: str) -> str:
    """Coarse label for dropped rows, used only for the drop log."""
    u = str(url)
    if extract_embedded_listing_number(u):
        return "search page (?ListingNumber=), kept as stub"
    if "/results" in u:
        return "search results page"
    if "?" in u:
        return "filtered search page (other query)"
    return "suburb/area index page"


def property_use(property_type, title) -> str | None:
    """residential / commercial / farm_land from property_type, else title; else None."""
    if isinstance(property_type, str) and property_type in PROPERTY_TYPE_USE:
        return PROPERTY_TYPE_USE[property_type]
    if isinstance(title, str):
        for use, pattern in TITLE_USE_PATTERNS:
            if pattern.search(title):
                return use
    return None


def build_stubs(nonlisting: pd.DataFrame, listing_ids: set) -> pd.DataFrame:
    """Listing-number stubs recovered from ?ListingNumber= search pages."""
    stubs = nonlisting.assign(
        p24_id=nonlisting["url"].map(extract_embedded_listing_number).astype("string"))
    stubs = stubs[stubs["p24_id"].notna()].copy()
    section = stubs["url"].str.extract(r"/(for-sale|to-rent)/", expand=False)
    stubs["listing_type"] = section.str.replace("-", "_")
    stubs = stubs.rename(columns={"city": "city_target", "title": "page_title",
                                  "description": "page_snippet"})
    stubs["in_listings_all"] = stubs["p24_id"].isin(listing_ids)
    keep = ["p24_id", "snapshot_date", "url", "city_target", "province", "listing_type",
            "price", "page_title", "page_snippet", "in_listings_all", "source"]
    stubs = stubs[[c for c in keep if c in stubs.columns]]
    stubs = stubs.sort_values(["p24_id", "snapshot_date"]).drop_duplicates(
        ["p24_id", "snapshot_date"])
    return stubs.reset_index(drop=True)


def add_location(df: pd.DataFrame) -> pd.DataFrame:
    """city_target / suburb_url / city_url / province_url / city (metro), with checks."""
    df = df.copy()
    if "city_target" not in df.columns:  # idempotent on already-cleaned input
        df = df.rename(columns={"city": "city_target"})
    slugs = df["url"].map(parse_location_slugs)
    sub_slug = slugs.str[0]
    town_slug = slugs.str[1]
    prov_slug = slugs.str[2]
    df["suburb_url"] = sub_slug.map(slug_to_name).astype("string")
    df["city_url"] = town_slug.map(slug_to_name).astype("string")
    df["province_url"] = prov_slug.map(PROVINCE_SLUGS).astype("string")
    df["city"] = town_slug.map(P24_TOWN_TO_METRO).astype("string")

    unparsed = town_slug.isna()
    if unparsed.any():
        logger.warning(f"{int(unparsed.sum()):,} listing URLs lack the "
                       f"/suburb/town/province/ layout; city left NA for them")
    unknown = town_slug.notna() & df["city"].isna()
    if unknown.any():
        logger.warning(f"Town slugs not in P24_TOWN_TO_METRO (city NA): "
                       f"{town_slug[unknown].value_counts().to_dict()}")

    # Consistency checks: metro vs URL province, and parsed `province` vs URL
    both = df["city"].notna() & df["province_url"].notna()
    bad_metro = both & df["city"].map(CITY_PROVINCE).ne(df["province_url"])
    assert not bad_metro.any(), (
        f"{int(bad_metro.sum())} rows: metro inconsistent with URL province; "
        f"fix P24_TOWN_TO_METRO")
    if "province" in df.columns:
        both_p = df["province"].notna() & df["province_url"].notna()
        bad_prov = both_p & df["province"].ne(df["province_url"])
        assert not bad_prov.any(), (
            f"{int(bad_prov.sum())} rows: `province` disagrees with URL province")

    corrected = df["city"].notna() & df["city"].ne(df["city_target"])
    logger.info(f"`city` corrected from the scrape-target label on "
                f"{int(corrected.sum()):,} rows:")
    if corrected.any():
        tab = df.loc[corrected].groupby(["city_target", "city_url", "city"]).size()
        for (tgt, town, metro), n in tab.items():
            logger.info(f"    {tgt} -> {metro} (town {town}): {n:,}")
    return df


def clean_listings(combined: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (listings, listing-number stubs) from the combined raw rows."""
    df = combined.copy()
    df["url_canonical"] = df["url"].map(normalise_url).astype("string")
    df["p24_id"] = df["url"].map(extract_p24_id).astype("string")

    # --- Non-listing pages ----------------------------------------------
    nonlisting = df["p24_id"].isna()
    logger.info(f"Non-listing rows removed (no 7+ digit id in URL path): "
                f"{int(nonlisting.sum()):,} of {len(df):,}")
    if nonlisting.any():
        kinds = df.loc[nonlisting, "url"].map(classify_nonlisting).value_counts()
        for kind, n in kinds.items():
            logger.info(f"    {kind:45s}: {n:,}")
    nonlisting_df = df.loc[nonlisting]
    df = df.loc[~nonlisting].copy()

    if "title" in df.columns:
        not_found = df["title"].fillna("").str.match(NOT_FOUND_TITLE_RE)
        logger.info(f"'Listing Not Found' pages dropped (expired; no text or price): "
                    f"{int(not_found.sum()):,}")
        df = df.loc[~not_found].copy()

    # --- Deduplicate on (p24_id, snapshot_date) ---------------------------
    desc = df.get("description", pd.Series(pd.NA, index=df.index))
    df["_has_desc"] = (~desc.map(is_missing_text)).astype(int)
    df["_n_info"] = df.apply(count_informative, axis=1)
    df["_is_https"] = df["url"].astype(str).str.startswith("https").astype(int)
    df = df.sort_values(["p24_id", "snapshot_date", "_has_desc", "_n_info", "_is_https"],
                        ascending=[True, True, False, False, False], kind="mergesort")
    before = len(df)
    df = df.drop_duplicates(subset=["p24_id", "snapshot_date"], keep="first")
    logger.info(f"After dedup by (p24_id, snapshot_date): {len(df):,} "
                f"(removed {before - len(df):,} duplicates)")
    df = df.drop(columns=["_has_desc", "_n_info", "_is_https"])

    # --- Stable id + panel descriptors -------------------------------------
    # Idempotent: on already-cleaned input, url_hash exists and listing_id == p24_id.
    if "listing_id" in df.columns and "url_hash" not in df.columns:
        df = df.rename(columns={"listing_id": "url_hash"})
    df["listing_id"] = df["p24_id"]
    grp = df.groupby("p24_id")["snapshot_date"]
    df["first_captured"] = grp.transform("min").astype("string")
    df["last_captured"] = grp.transform("max").astype("string")
    df["n_snapshots"] = grp.transform("nunique").astype("Int64")

    # --- Location and property use -----------------------------------------
    df = add_location(df)
    latest_first = df.sort_values("snapshot_date", ascending=False, kind="mergesort")
    modal = (latest_first.groupby("p24_id")["suburb_url"]
             .agg(lambda s: s.value_counts(sort=True).index[0] if s.notna().any() else pd.NA))
    df["suburb_canonical"] = df["p24_id"].map(modal).astype("string")

    ptype = df.get("property_type", pd.Series(pd.NA, index=df.index))
    title = df.get("title", pd.Series(pd.NA, index=df.index))
    df["property_use"] = pd.Series(
        [property_use(p, t) for p, t in zip(ptype, title)], index=df.index, dtype="string")
    df["is_commercial"] = df["property_use"].eq("commercial").astype("Int64")
    df["is_residential"] = df["property_use"].eq("residential").astype("Int64")
    df.loc[df["property_use"].isna(), ["is_commercial", "is_residential"]] = pd.NA

    stubs = build_stubs(nonlisting_df, set(df["p24_id"]))

    lead = ["listing_id", "p24_id", "snapshot_date", "first_captured", "last_captured",
            "n_snapshots", "url", "url_canonical", "url_hash", "city", "city_target",
            "city_url", "province", "province_url", "suburb", "suburb_url",
            "suburb_canonical", "property_type", "property_use", "is_residential",
            "is_commercial"]
    lead = [c for c in lead if c in df.columns]
    df = df[lead + [c for c in df.columns if c not in lead]]
    return df, stubs


def main():
    archive_files = sorted(RAW_DIR.glob("listings_archive_*.parquet"))
    live_files = sorted(RAW_DIR.glob("listings_live_*.parquet"))

    if not archive_files and not live_files:
        logger.error("No listings parquet files found. "
                     "Run archive fetch and/or live scraper first.")
        sys.exit(1)

    dfs = []
    for f in archive_files + live_files:
        df = pd.read_parquet(f)
        logger.info(f"Loaded {len(df):,} records from {f.name}")
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Combined: {len(combined):,} records")

    listings, stubs = clean_listings(combined)
    listings = listings.sort_values(["city", "p24_id", "snapshot_date"]).reset_index(drop=True)

    listings.to_parquet(OUTPUT_PATH, index=False, engine="pyarrow", compression="snappy")
    logger.info(f"Saved {len(listings):,} records to {OUTPUT_PATH}")
    stubs.to_parquet(STUBS_PATH, index=False, engine="pyarrow", compression="snappy")
    logger.info(f"Saved {len(stubs):,} listing-number stubs "
                f"({stubs['p24_id'].nunique():,} ids, "
                f"{int(stubs.drop_duplicates('p24_id')['in_listings_all'].sum()):,} "
                f"already in listings_all) to {STUBS_PATH}")

    # Summary
    per_listing = listings.drop_duplicates("p24_id")
    logger.info("=== Summary ===")
    logger.info(f"Total records:   {len(listings):,}")
    logger.info(f"Unique listings: {listings['p24_id'].nunique():,}")
    logger.info("Snapshots per listing: "
                + ", ".join(f"{k}: {v:,}" for k, v in
                            per_listing["n_snapshots"].value_counts().sort_index().items()))
    logger.info("Records by city (metro): "
                + ", ".join(f"{k}: {v:,}" for k, v in listings["city"].value_counts().items()))
    logger.info("Property use: "
                + ", ".join(f"{k}: {v:,}" for k, v in
                            listings["property_use"].value_counts(dropna=False).items()))
    year = listings["snapshot_date"].astype(str).str[:4]
    logger.info("Records by capture year: "
                + ", ".join(f"{k}: {v:,}" for k, v in year.value_counts().sort_index().items()))


if __name__ == "__main__":
    main()

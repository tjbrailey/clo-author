#!/usr/bin/env python3
# ============================================================
# 05_geocode_notices.py
# Purpose: Locate SAR notices offline using an OpenStreetMap gazetteer
#          (05a), then join to 2016 wards (QoL pipeline), 2020 wards and
#          2013 EAs. Never falls back to a municipal centroid: notices
#          that cannot be located get NA coordinates.
#
# Location strategies, in order of precision:
#   streets        >= 2 listed streets co-located within CLUSTER_M of each
#                  other, unambiguous within the municipality (~100-300 m).
#                  Clusters of generic names only (e.g. "7th Road") need a
#                  corroborating place name.
#   streets+place  street clusters ambiguous; the one nearest a named place
#   place          suburb name (OSM places + Property24 suburbs) found in the
#                  suburb field, title or applicant; body text is excluded
#                  because it names municipal offices, not the site
#   none           not located (NA coordinates)
# Validation: geo_text_agrees = notice text names one of the 3 nearest
#   suburbs; also distance to the original Nominatim run (frozen in
#   sar_notices_geocoded_nominatim_v1.parquet).
#
# Inputs:  data/cleaned/gazette/sar_notices_jhb_pilot.parquet (03)
#          data/raw/osm/gauteng/{places,streets}.json (05a)
#          data/cleaned/listings_geocoded.parquet (Property24 suburb names)
#          data/raw/units/mdb/wards_2016/MDBWard2016.gdb
#          data/raw/units/mdb/wards_2021/SA_Wards2020.shp
#          data/raw/units/statssa/ea_boundaries_2013/SA_nogaps_2013.shp
# Outputs: data/cleaned/gazette/sar_notices_geocoded.parquet
#          data/cleaned/gazette/geocode_audit.csv (per-notice evidence)
# Usage:   py -3.12 05_geocode_notices.py
# ============================================================

import json
import logging
import math
import re
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).parent))
import config  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("05_geocode_notices")

OSM_DIR = config.REPO_ROOT / "data" / "raw" / "osm" / "gauteng"
UNITS = config.REPO_ROOT / "data" / "raw" / "units"
WARDS_2016 = UNITS / "mdb" / "wards_2016" / "MDBWard2016.gdb"
WARDS_2020 = UNITS / "mdb" / "wards_2021" / "SA_Wards2020.shp"
EAS_2013 = UNITS / "statssa" / "ea_boundaries_2013" / "SA_nogaps_2013.shp"
OUT = config.CLEAN_DIR / "sar_notices_geocoded.parquet"
# frozen copy of the original Nominatim run (suburb hits reused, and used for validation)
PREV = config.CLEAN_DIR / "sar_notices_geocoded_nominatim_v1.parquet"
AUDIT = config.CLEAN_DIR / "geocode_audit.csv"

LISTINGS = config.REPO_ROOT / "data" / "cleaned" / "listings_geocoded.parquet"

CRS_M = "EPSG:32735"          # UTM 35S, metres
CLUSTER_M = 400               # max gap between co-located streets
AMBIGUOUS_M = 1500            # rival clusters further apart than this = ambiguous
PLACE_AGREE_M = 3000          # street cluster must lie this close to a named place
MUNI_BUFFER_M = 1500
BOILERPLATE_SHARE = 0.10      # place names in >10% of notices are boilerplate
GRID_M = 2000                 # cell size for measuring how widespread a street name is
DISTINCTIVE_MAX_CELLS = 8     # names in more cells than this are generic (e.g. "7th Road")
MIN_LISTINGS_PER_SUBURB = 5

MUNI_CODES = {"JHB": ["JHB"], "Ekurhuleni": ["EKU"], "Tshwane": ["TSH"]}
PLACE_RANK = {"neighbourhood": 0, "quarter": 0, "suburb": 1, "hamlet": 2, "village": 2,
              "locality": 2, "town": 3}

ABBREV = [(r"\bave?\b", "avenue"), (r"\bavn\b", "avenue"), (r"\brd\b", "road"),
          (r"\bstr?\b", "street"), (r"\bdr\b", "drive"), (r"\bcres\b", "crescent"),
          (r"\bcr\b", "crescent"), (r"\bpl\b", "place"), (r"\bln\b", "lane"),
          (r"\bcl\b", "close"), (r"\bblvd\b", "boulevard"), (r"\bext\b", "extension")]
ORDINALS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth",
            "ninth", "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth",
            "fifteenth", "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth"]
GENERIC_PLACE_WORDS = {"central", "park", "gardens", "north", "south", "east", "west",
                       "view", "heights", "extension", "estate", "village", "city",
                       "glen", "hill", "ridge", "township", "golf", "airport", "industrial",
                       "industria", "station", "manor", "the", "riverside", "lakeside"}


def ordinal_suffix(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }".replace(" ", "")


ORDINAL_MAP = {w: ordinal_suffix(i + 1) for i, w in enumerate(ORDINALS)}


def norm(s) -> str:
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return ""
    s = str(s).lower().replace("’", "'")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    for pat, rep in ABBREV:
        s = re.sub(pat, rep, s)
    s = " ".join(ORDINAL_MAP.get(w, w) for w in s.split())
    return s.strip()


# ------------------------------------------------------------------ gazetteer

def load_osm(muni_polys: dict):
    places_raw = json.loads((OSM_DIR / "places.json").read_text(encoding="utf-8"))["elements"]
    rows = []
    for e in places_raw:
        tags = e.get("tags", {})
        lat = e.get("lat", e.get("center", {}).get("lat"))
        lon = e.get("lon", e.get("center", {}).get("lon"))
        ptype = tags.get("place")
        if lat is None or ptype not in PLACE_RANK:
            continue
        for key in ("name", "alt_name", "old_name"):
            for nm in str(tags.get(key, "")).split(";"):
                n = norm(nm)
                if len(n) >= 4 and n not in GENERIC_PLACE_WORDS:
                    rows.append({"pname": n, "ptype": ptype, "rank": PLACE_RANK[ptype],
                                 "geometry": Point(lon, lat)})
    places = gpd.GeoDataFrame(rows, crs="EPSG:4326").to_crs(CRS_M)
    places["psrc"] = "osm"

    # Property24 suburb names (Nominatim suburb-level points): median location per suburb
    lst = pd.read_parquet(LISTINGS, columns=["suburb", "lat", "lon", "geocode_source"])
    lst = lst[(lst.geocode_source == "nominatim") & lst.suburb.notna()].copy()
    lst["pname"] = lst.suburb.map(norm)
    agg = lst.groupby("pname").agg(lat=("lat", "median"), lon=("lon", "median"),
                                   n=("lat", "size")).reset_index()
    agg = agg[(agg.n >= MIN_LISTINGS_PER_SUBURB) & (agg.pname.str.len() >= 4)
              & ~agg.pname.isin(GENERIC_PLACE_WORDS)]
    lp = gpd.GeoDataFrame({"pname": agg.pname, "ptype": "suburb", "rank": PLACE_RANK["suburb"],
                           "psrc": "listings"},
                          geometry=gpd.points_from_xy(agg.lon, agg.lat), crs="EPSG:4326").to_crs(CRS_M)
    places = pd.concat([places, lp], ignore_index=True)

    streets_raw = json.loads((OSM_DIR / "streets.json").read_text(encoding="utf-8"))["elements"]
    srows = []
    for e in streets_raw:
        geom = e.get("geometry")
        name = norm(e.get("tags", {}).get("name"))
        if not geom or len(geom) < 2 or not name:
            continue
        srows.append({"sname": name, "geometry": LineString([(p["lon"], p["lat"]) for p in geom])})
    streets = gpd.GeoDataFrame(srows, crs="EPSG:4326").to_crs(CRS_M)
    c = streets.geometry.centroid
    cells = (c.x // GRID_M).astype(int).astype(str) + "_" + (c.y // GRID_M).astype(int).astype(str)
    spread = cells.groupby(streets.sname).nunique()
    streets["distinctive"] = streets.sname.map(spread) <= DISTINCTIVE_MAX_CELLS

    for muni, poly in muni_polys.items():
        places[f"in_{muni}"] = places.within(poly)
        streets[f"in_{muni}"] = streets.intersects(poly)
    logger.info(f"Gazetteer: {len(places):,} place names, {len(streets):,} named street segments")
    return places, streets


def municipality_polygons() -> dict:
    w = gpd.read_file(WARDS_2020)[["CAT_B", "geometry"]].to_crs(CRS_M)
    polys = {}
    for muni, codes in MUNI_CODES.items():
        polys[muni] = w[w.CAT_B.isin(codes)].union_all().buffer(MUNI_BUFFER_M)
    gp = gpd.read_file(WARDS_2020)
    gp = gp[gp.Province.str.contains("Gauteng", case=False, na=False)].to_crs(CRS_M)
    polys["Gauteng"] = gp.union_all().buffer(MUNI_BUFFER_M)
    return polys


def muni_key(m) -> str:
    return m if m in MUNI_CODES else "Gauteng"


# ------------------------------------------------------------------ locators

def street_names(street_field) -> list:
    names = []
    for s in str(street_field or "").split(";"):
        n = norm(s)
        if n and n not in names:
            names.append(n)
    return names


def street_cluster(street_field, muni: str, streets: gpd.GeoDataFrame, by_name: dict) -> dict:
    """Locate the point where >= 2 listed streets come within CLUSTER_M of each other.

    strong = the cluster contains at least one distinctive (non-generic) street name.
    """
    out = {"pt": None, "score": 0, "matched": 0, "ambiguous": False, "tops": [], "strong": False}
    cands = {}
    for n in street_names(street_field):
        idx = [i for i in by_name.get(n, []) if streets.at[i, f"in_{muni}"]]
        if idx:
            cands[n] = streets.loc[idx, ["geometry", "distinctive"]]
    out["matched"] = len(cands)
    if len(cands) < 2:
        return out

    anchor = min(cands, key=lambda k: len(cands[k]))
    results = []
    for _, a in cands[anchor].iterrows():
        members = [(anchor, a.geometry, bool(a.distinctive))]
        for n, df in cands.items():
            if n == anchor:
                continue
            d = df.geometry.distance(a.geometry)
            if d.min() <= CLUSTER_M:
                j = d.idxmin()
                members.append((n, df.at[j, "geometry"], bool(df.at[j, "distinctive"])))
        if len(members) >= 2:
            pts = [g.interpolate(g.project(a.geometry.centroid)) for _, g, _ in members]
            results.append((len(members), any(dist for _, _, dist in members),
                            Point(np.mean([p.x for p in pts]), np.mean([p.y for p in pts]))))
    if not results:
        return out
    best_score = max(r[0] for r in results)
    out["score"] = best_score
    if best_score < max(2, math.ceil(0.5 * len(cands))):
        return out
    tops = [(strong, p) for s, strong, p in results if s == best_score]
    best_strong, best = tops[0]
    rivals = [p for _, p in tops if p.distance(best) > AMBIGUOUS_M]
    out.update(pt=best, ambiguous=bool(rivals), tops=[best] + rivals,
               strong=best_strong or any(s for s, _ in tops))
    return out


def find_place(texts: list, muni: str, places: gpd.GeoDataFrame, boiler: set) -> dict:
    """Search fields in priority order for the longest known place name.

    Returns candidate points for that name; ambiguous if they lie > AMBIGUOUS_M apart
    (e.g. 'Kelvin' the Sandton suburb vs Kelvin power station).
    """
    out = {"pts": [], "name": None, "field": None, "ambiguous": False}
    pool = places[places[f"in_{muni}"] & ~places.pname.isin(boiler)]
    names = sorted(pool.pname.unique(), key=len, reverse=True)
    for field, txt in texts:
        t = " " + norm(txt) + " "
        if len(t) < 6:
            continue
        found = [n for n in names if f" {n} " in t]
        if found:
            n = found[0]
            rows = pool[pool.pname == n].sort_values("rank")
            pts = list(rows.geometry)
            # collapse duplicates (OSM point + listings median of the same suburb)
            uniq = []
            for p in pts:
                if all(p.distance(q) > AMBIGUOUS_M for q in uniq):
                    uniq.append(p)
            out.update(pts=uniq, name=n, field=field, ambiguous=len(uniq) > 1)
            return out
    return out


# ------------------------------------------------------------------ main

def main():
    sar = pd.read_parquet(config.SAR_NOTICES)
    sar = sar[sar["is_sar_notice"] == True].copy().reset_index(drop=True)  # noqa: E712
    logger.info(f"Loaded {len(sar)} SAR notices")

    polys = municipality_polygons()
    places, streets = load_osm(polys)
    by_name = streets.groupby("sname").groups
    by_name = {k: list(v) for k, v in by_name.items()}

    # boilerplate: place names appearing in many notice bodies (e.g. city names)
    bodies = (" " + sar.text_clean.fillna("").map(norm) + " ")
    counts = {n: bodies.str.contains(f" {re.escape(n)} ", regex=True).mean()
              for n in places.pname.unique()
              if len(n) >= 4}
    boiler = {n for n, share in counts.items() if share > BOILERPLATE_SHARE}
    logger.info(f"Boilerplate place names excluded ({len(boiler)}): {sorted(boiler)[:20]}")

    recs = []
    for i, r in sar.iterrows():
        mk = muni_key(r.municipality)
        sc = street_cluster(r.streets, mk, streets, by_name)
        # body text excluded: it names municipal offices (objection addresses), not the site
        texts = [("suburb", r.suburb), ("title", r.notice_title), ("applicant", r.applicant)]
        pl = find_place(texts, mk, places, boiler)

        def place_dist(p):
            return min(p.distance(q) for q in pl["pts"]) if pl["pts"] else None

        pt, src, flags = None, "none", []
        if sc["pt"] is not None and not sc["ambiguous"]:
            d = place_dist(sc["pt"])
            if d is not None and d > PLACE_AGREE_M:
                flags.append("street_place_conflict")
                if sc["strong"]:
                    pt, src = sc["pt"], "streets"
                elif not pl["ambiguous"]:
                    pt, src = pl["pts"][0], "place"
            elif sc["strong"] or d is not None:
                pt, src = sc["pt"], "streets"
            else:
                flags.append("generic_streets_uncorroborated")
        elif sc["pt"] is not None and pl["pts"]:
            near = min(sc["tops"], key=place_dist)
            if place_dist(near) <= PLACE_AGREE_M:
                pt, src = near, "streets+place"
            elif not pl["ambiguous"]:
                pt, src = pl["pts"][0], "place"
                flags.append("ambiguous_streets_far_from_place")
        elif pl["pts"] and not pl["ambiguous"]:
            pt, src = pl["pts"][0], "place"
        if sc["ambiguous"] and src == "none":
            flags.append("ambiguous_streets")
        if pl["ambiguous"] and src == "none":
            flags.append("ambiguous_place")

        recs.append({"_i": i, "x": pt.x if pt else np.nan, "y": pt.y if pt else np.nan,
                     "geo_source": src, "geo_n_streets_clustered": sc["score"],
                     "geo_n_streets_matched": sc["matched"], "geo_streets_strong": sc["strong"],
                     "geo_place": pl["name"], "geo_place_field": pl["field"],
                     "geo_flags": ";".join(flags) or None})
    loc = pd.DataFrame(recs).set_index("_i")
    sar = sar.join(loc)

    # No reference-number inheritance and no reuse of the earlier Nominatim geocodes:
    # validated at 20% and 6% text agreement respectively (2026-10-28). Unlocated = NA.
    prev = None
    if PREV.exists():
        prev = pd.read_parquet(PREV)
        prev = prev[prev.geo_source == "suburb"].set_index("notice_id")[["lat", "lon"]]

    # spatial joins
    has = sar.x.notna()
    gdf = gpd.GeoDataFrame(sar[has], geometry=gpd.points_from_xy(sar[has].x, sar[has].y),
                           crs=CRS_M)
    w16 = gpd.read_file(WARDS_2016)[["WardID", "geometry"]].to_crs(CRS_M)
    w20 = gpd.read_file(WARDS_2020)[["WardID", "geometry"]].to_crs(CRS_M)
    eas = gpd.read_file(EAS_2013)[["EA_CODE", "geometry"]]
    eas = eas[(eas.EA_CODE >= 70000000) & (eas.EA_CODE < 80000000)].to_crs(CRS_M)
    for tgt, col, newcol in [(w16, "WardID", "ward_code"), (w20, "WardID", "ward_code_2020"),
                             (eas, "EA_CODE", "ea_code")]:
        j = gpd.sjoin(gdf[["geometry"]], tgt, how="left", predicate="within")
        j = j[~j.index.duplicated(keep="first")]
        sar.loc[j.index, newcol] = j[col].map(lambda v: str(int(v)) if pd.notna(v) else None)
    ll = gpd.GeoSeries(gdf.geometry, crs=CRS_M).to_crs("EPSG:4326")
    sar.loc[ll.index, "lat"] = ll.y
    sar.loc[ll.index, "lon"] = ll.x
    sar["geo_precision"] = sar.geo_source.map({"streets": "street", "streets+place": "street",
                                               "place": "suburb", "none": None})

    # independent check: do any of the 3 nearest known suburbs appear in the notice's text?
    sub_pts = places[places.ptype.isin(["suburb", "neighbourhood", "quarter"])]
    sar["geo_nearby_suburbs"] = None
    sar["geo_text_agrees"] = np.nan
    for i, r in sar[has].iterrows():
        p = Point(r.x, r.y)
        near = sub_pts.assign(d=sub_pts.distance(p)).nsmallest(12, "d")
        names = list(dict.fromkeys(near.pname))[:3]
        full = " " + norm(" ".join(str(v) for v in (r.suburb, r.notice_title, r.applicant,
                                                     r.text_clean) if v is not None)) + " "
        sar.at[i, "geo_nearby_suburbs"] = "; ".join(names)
        sar.at[i, "geo_text_agrees"] = float(any(f" {n} " in full for n in names))
    logger.info("Share of located notices whose text names one of the 3 nearest suburbs:\n"
                + sar[has].groupby("geo_source").geo_text_agrees.agg(["mean", "size"]).round(2).to_string())

    # report
    logger.info("Location source: " + str(sar.geo_source.value_counts().to_dict()))
    logger.info(f"Located: {sar.lat.notna().sum()}/{len(sar)}  "
                f"wards(2016): {sar.ward_code.nunique()}  "
                f"max notices in one ward: {sar.ward_code.value_counts().max()}")
    logger.info("Top wards: " + str(sar.ward_code.value_counts().head(8).to_dict()))

    if prev is not None:
        cmp_ = sar[["notice_id", "lat", "lon", "geo_source"]].merge(
            prev.reset_index(), on="notice_id", suffixes=("", "_prev")).dropna()
        if len(cmp_):
            a = gpd.GeoSeries(gpd.points_from_xy(cmp_.lon, cmp_.lat), crs="EPSG:4326").to_crs(CRS_M)
            b = gpd.GeoSeries(gpd.points_from_xy(cmp_.lon_prev, cmp_.lat_prev), crs="EPSG:4326").to_crs(CRS_M)
            cmp_["dist_m"] = a.distance(b).values
            logger.info("Distance to previous Nominatim suburb geocode (m), by new source:\n"
                        + cmp_.groupby("geo_source").dist_m.describe(
                            percentiles=[.5, .9]).round(0).to_string())

    audit_cols = ["notice_id", "municipality", "stage", "first_issue_date", "ref_number",
                  "suburb", "streets", "geo_source", "geo_precision", "geo_place",
                  "geo_place_field", "geo_n_streets_clustered", "geo_n_streets_matched",
                  "geo_streets_strong", "geo_flags", "geo_nearby_suburbs", "geo_text_agrees",
                  "lat", "lon", "ward_code", "ward_code_2020", "ea_code"]
    sar[audit_cols].to_csv(AUDIT, index=False)
    sar.drop(columns=["x", "y"]).to_parquet(OUT, index=False)
    logger.info(f"Wrote {len(sar)} rows -> {OUT}; audit -> {AUDIT}")


if __name__ == "__main__":
    main()
